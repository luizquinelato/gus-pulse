"""
Jira Extraction Worker - Processes Jira-specific extraction requests.

This worker handles Jira extraction messages from the extraction queue.
It contains all the extraction logic for different Jira extraction types.

Note: This is NOT a queue consumer itself. It's called from ExtractionWorkerRouter
which is the actual queue consumer. This class contains provider-specific logic.

Architecture:
- Receives messages from extraction_queue_premium (tier-based)
- Processes extraction based on message type
- Fetches data from Jira API
- Stores in raw_extraction_data
- Queues to transform worker
- Sends WebSocket status updates
- Queues next extraction step

Uses dependency injection to receive WorkerStatusManager for sending status updates.
"""

import json
import pika
from typing import Dict, Any, Optional, Tuple
from contextlib import contextmanager
from sqlalchemy import text

from app.core.logging_config import get_logger
from app.core.database import get_database
from app.etl.jira.jira_client import JiraAPIClient
from app.etl.workers.queue_manager import QueueManager

logger = get_logger(__name__)


class JiraExtractionWorker:
    """
    Worker for processing Jira-specific extraction requests.

    Note: This is NOT a queue consumer itself. It's called from ExtractionWorkerRouter
    which is the actual queue consumer. This class contains provider-specific logic.

    Handles all Jira extraction types with built-in extraction logic.
    """

    def __init__(self, status_manager=None):
        """
        Initialize Jira extraction worker.

        Args:
            status_manager: WorkerStatusManager instance for sending status updates (injected by router)
        """
        self.database = get_database()
        self.status_manager = status_manager  # 🔑 Dependency injection
        logger.debug("Initialized JiraExtractionWorker")

    @contextmanager
    def get_db_session(self):
        """
        Get a database session with automatic cleanup.

        Usage:
            with self.get_db_session() as session:
                # Use session for writes

        Note: This uses write session context. For read-only operations,
        consider using database.get_read_session_context() instead.
        """
        with self.database.get_write_session_context() as session:
            yield session

    def _get_raw_data(self, session, raw_data_id: int) -> Optional[Dict[str, Any]]:
        """
        Get raw data from database.

        Args:
            session: Database session
            raw_data_id: ID of the raw data record

        Returns:
            Dict containing the raw_data JSONB field, or None if not found
        """
        try:
            query = text("""
                SELECT raw_data FROM raw_extraction_data
                WHERE id = :raw_data_id
            """)
            result = session.execute(query, {'raw_data_id': raw_data_id}).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting raw data: {e}")
            return None

    async def _send_worker_status(self, step: str, tenant_id: int, job_id: int, status: str, step_type: str = None):
        """
        Send WebSocket status update for ETL job step.

        Delegates to the injected WorkerStatusManager.

        Args:
            step: ETL step name (extraction, transform, embedding)
            tenant_id: Tenant ID
            job_id: Job ID
            status: Status to send (running, finished, failed)
            step_type: Optional step type for logging
        """
        if self.status_manager:
            await self.status_manager.send_worker_status(step, tenant_id, job_id, status, step_type)
        else:
            logger.warning(f"⚠️ No status_manager available, skipping status update for job {job_id}")

    async def process_jira_extraction(self, extraction_type: str, message: Dict[str, Any]) -> bool:
        """
        Process Jira extraction message by routing to appropriate extraction method.

        Args:
            extraction_type: Type of extraction (e.g., 'jira_projects_and_issue_types')
            message: Message containing extraction parameters

        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        try:
            logger.debug(f"🚀 [JIRA] Processing {extraction_type} extraction")

            # Route to appropriate extraction method
            if extraction_type == 'jira_projects_and_issue_types':
                return await self._extract_projects_and_issue_types(message)
            elif extraction_type == 'jira_statuses_and_relationships':
                return await self._extract_statuses_and_relationships(message)
            elif extraction_type == 'jira_issues_with_changelogs':
                return await self._extract_issues_with_changelogs(message)
            elif extraction_type == 'jira_dev_status':
                return await self._fetch_jira_dev_status(message)
            elif extraction_type == 'jira_sprint_reports':
                return await self._extract_sprint_reports(message)
            elif extraction_type == 'config_custom_fields':
                return await self._extract_config_custom_fields(message)
            elif extraction_type == 'config_projects_and_issue_types':
                # Config job step 1: Projects & Types - uses same extraction as Jira job
                return await self._extract_projects_and_issue_types(message, extraction_type)
            elif extraction_type == 'config_statuses_and_relations':
                # Config job step 2: Statuses & Relations - uses same extraction as Jira job
                return await self._extract_statuses_and_relationships(message, extraction_type)
            elif extraction_type in ['config_wit_hierarchies', 'config_wit_mappings', 'config_status_mappings', 'config_workflows']:
                # These config steps have no extraction phase - send completion message directly to transform
                return await self._skip_extraction_to_transform(extraction_type, message)
            else:
                logger.error(f"❌ [JIRA] Unknown extraction type: {extraction_type}")
                return False

        except Exception as e:
            logger.error(f"❌ [JIRA] Error processing {extraction_type}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def _get_jira_client(self, tenant_id: int, integration_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[JiraAPIClient]]:
        """
        Get integration and create Jira client.

        Returns:
            Tuple of (integration_data dict, JiraAPIClient instance) or (None, None) if failed
        """
        try:
            database = get_database()
            with database.get_read_session_context() as db:
                query = text("""
                    SELECT id, provider, base_url, username, password, active, settings
                    FROM integrations
                    WHERE id = :integration_id AND tenant_id = :tenant_id
                """)
                result = db.execute(query, {
                    'integration_id': integration_id,
                    'tenant_id': tenant_id
                }).fetchone()

                if not result:
                    logger.error(f"Integration {integration_id} not found for tenant {tenant_id}")
                    return None, None

                integration_data = {
                    'id': result[0],
                    'provider': result[1],
                    'base_url': result[2],
                    'username': result[3],
                    'password': result[4],
                    'active': result[5],
                    'settings': result[6]  # JSONB field with projects list
                }

            # Decrypt password if needed
            from app.core.config import AppConfig
            password = integration_data['password']
            if password:
                try:
                    key = AppConfig.load_key()
                    password = AppConfig.decrypt_token(password, key)
                except Exception as e:
                    logger.warning(f"Failed to decrypt password, using as-is: {e}")

            # Create Jira client with username, token, base_url
            jira_client = JiraAPIClient(
                username=integration_data['username'],
                token=password,
                base_url=integration_data['base_url']
            )

            return integration_data, jira_client

        except Exception as e:
            logger.error(f"Error getting Jira client: {e}")
            return None, None

    def _store_raw_data(self, tenant_id: int, integration_id: int, data_type: str, raw_data: dict) -> Optional[int]:
        """
        Store raw extraction data in database.

        Returns:
            int: raw_data_id if successful, None otherwise
        """
        try:
            database = get_database()
            from app.core.utils import DateTimeHelper
            now = DateTimeHelper.now_default()

            with database.get_write_session_context() as db:
                insert_query = text("""
                    INSERT INTO raw_extraction_data (
                        tenant_id, integration_id, type, raw_data, created_at
                    ) VALUES (
                        :tenant_id, :integration_id, :type, CAST(:raw_data AS jsonb), :created_at
                    ) RETURNING id
                """)

                import json
                result = db.execute(insert_query, {
                    'tenant_id': tenant_id,
                    'integration_id': integration_id,
                    'type': data_type,
                    'raw_data': json.dumps(raw_data),
                    'created_at': now
                })

                raw_data_id = result.fetchone()[0]
                logger.debug(f"✅ Stored raw data with ID: {raw_data_id}")
                return raw_data_id

        except Exception as e:
            logger.error(f"Error storing raw data: {e}")
            return None

    def _queue_next_step(self, tenant_id: int, integration_id: int, job_id: int, next_step: str, token: str = None, old_last_sync_date: str = None, first_item: bool = False, last_item: bool = False, last_job_item: bool = False):
        """
        Queue the next extraction step.

        This queues a new extraction job step (e.g., from projects to statuses).
        Uses direct message publishing instead of publish_extraction_job since
        we're triggering a new step, not queuing individual items.
        """
        try:
            queue_manager = QueueManager()

            # Build message for next extraction step
            message = {
                'tenant_id': tenant_id,
                'integration_id': integration_id,
                'job_id': job_id,
                'type': next_step,
                'provider': 'jira',
                'token': token,
                'old_last_sync_date': old_last_sync_date,   # 🔑 Forward last_sync_date through pipeline
                'first_item': first_item,                   # 🔑 True only on first item of job
                'last_item': last_item,                     # 🔑 True only on last item of job
                'last_job_item': last_job_item              # 🔑 True only on last item of job
            }

            # Get tenant tier and route to tier-based extraction queue
            tier = queue_manager._get_tenant_tier(tenant_id)
            tier_queue = queue_manager.get_tier_queue_name(tier, 'extraction')

            success = queue_manager._publish_message(tier_queue, message)

            if success:
                logger.debug(f"✅ Queued next step: {next_step} to {tier_queue}")
            else:
                logger.error(f"❌ Failed to queue next step: {next_step}")

        except Exception as e:
            logger.error(f"Error queuing next step: {e}")

    def _update_job_status(self, job_id: int, status: str, error_message: str = None):
        """
        Update job overall status in database.

        Args:
            job_id: Job ID
            status: Overall status (READY, RUNNING, FINISHED, FAILED)
            error_message: Optional error message
        """
        try:
            from app.core.utils import DateTimeHelper
            now = DateTimeHelper.now_default()

            database = get_database()
            with database.get_write_session_context() as db:
                if error_message:
                    # Update overall status and error message
                    # Use string formatting for the status value to avoid parameter binding issues
                    query = text(f"""
                        UPDATE etl_jobs
                        SET status = jsonb_set(status, ARRAY['overall'], '"{status}"'::jsonb),
                            error_message = :error_message,
                            last_updated_at = :now
                        WHERE id = :job_id
                    """)
                    db.execute(query, {
                        'error_message': error_message,
                        'job_id': job_id,
                        'now': now
                    })
                else:
                    # Update overall status only
                    query = text(f"""
                        UPDATE etl_jobs
                        SET status = jsonb_set(status, ARRAY['overall'], '"{status}"'::jsonb),
                            last_updated_at = :now
                        WHERE id = :job_id
                    """)
                    db.execute(query, {
                        'job_id': job_id,
                        'now': now
                    })

            logger.debug(f"Updated job {job_id} overall status to {status}")

        except Exception as e:
            logger.error(f"Error updating job status: {e}")

    async def _extract_projects_and_issue_types(self, message: Dict[str, Any], extraction_type: str = 'jira_projects_and_issue_types') -> bool:
        """
        Extract Jira projects and issue types.

        This is Step 1 of the Jira extraction pipeline (or Config job step 1).

        Args:
            message: Message containing extraction parameters
            extraction_type: The current step name (jira_projects_and_issue_types or config_projects_and_issue_types)
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            old_last_sync_date = message.get('old_last_sync_date')  # 🔑 Extract from message

            logger.debug(f"🏁 [JIRA] Starting projects and issue types extraction (step={extraction_type})")

            # Get Jira client
            integration, jira_client = self._get_jira_client(tenant_id, integration_id)
            if not integration or not jira_client:
                self._update_job_status(job_id, "FAILED", "Failed to initialize Jira client")
                return False

            # Get project keys from integration settings
            settings = integration.get('settings', {})
            project_keys = settings.get('projects', [])

            if project_keys:
                logger.debug(f"📊 Fetching {len(project_keys)} configured projects: {project_keys}")
            else:
                logger.debug(f"📊 No project filter configured - fetching ALL projects")

            # Fetch projects from Jira (filtered by project_keys if configured, otherwise all projects)
            projects = jira_client.get_projects(project_keys=project_keys if project_keys else None, expand="issueTypes")

            # Determine next step based on current step (job-aware routing)
            if extraction_type == 'config_projects_and_issue_types':
                next_step = 'config_statuses_and_relations'
                data_type_for_transform = 'config_projects_and_issue_types'
                status_step_name = 'config_projects_and_issue_types'
            else:  # jira_projects_and_issue_types
                next_step = 'jira_statuses_and_relationships'
                data_type_for_transform = 'jira_projects_and_issue_types'
                status_step_name = 'jira_projects_and_issue_types'

            if not projects:
                logger.warning(f"No projects found")
                # Still queue next step even if no projects
                self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, old_last_sync_date)
                return True

            logger.debug(f"📊 Found {len(projects)} projects")

            # Store raw data
            raw_data_id = self._store_raw_data(tenant_id, integration_id, 'jira_projects_and_issue_types', projects)
            if not raw_data_id:
                self._update_job_status(job_id, "FAILED", "Failed to store raw data")
                return False

            # Queue to transform
            queue_manager = QueueManager()
            success = queue_manager.publish_transform_job(
                tenant_id=tenant_id,
                integration_id=integration_id,
                raw_data_id=raw_data_id,
                data_type=data_type_for_transform,
                job_id=job_id,
                provider='jira',
                old_last_sync_date=old_last_sync_date,  # 🔑 Forward to transform
                first_item=True,
                last_item=True,
                last_job_item=False,  # Not the final step
                token=token
            )

            if not success:
                self._update_job_status(job_id, "FAILED", "Failed to queue for transformation")
                return False

            # Send finished status for this step
            await self._send_worker_status("extraction", tenant_id, job_id, "finished", status_step_name)

            # Queue next step (job-aware)
            self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, old_last_sync_date, True, False, False)

            logger.info(f"✅ Projects and issue types extraction completed (next step: {next_step})")
            return True

        except Exception as e:
            logger.error(f"❌ Error in projects extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _extract_statuses_and_relationships(self, message: Dict[str, Any], extraction_type: str = 'jira_statuses_and_relationships') -> bool:
        """
        Extract Jira statuses and project relationships.

        This is Step 2 of the Jira extraction pipeline (or Config job step 2).
        Fetches statuses for EACH project individually and queues one message per project.

        Args:
            message: Message containing extraction parameters
            extraction_type: The current step name (jira_statuses_and_relationships or config_statuses_and_relations)
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            old_last_sync_date = message.get('old_last_sync_date')  # 🔑 Extract from message

            logger.debug(f"🏁 [JIRA] Starting statuses and relationships extraction (step={extraction_type})")

            # 🔑 Set new_last_sync_date to current time (extraction start time)
            # This will be used by transform worker to check for updated statuses
            from app.core.utils import DateTimeHelper
            new_last_sync_date = DateTimeHelper.now_default().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"📅 Setting new_last_sync_date for statuses step: {new_last_sync_date}")

            # Get Jira client and integration settings
            integration, jira_client = self._get_jira_client(tenant_id, integration_id)
            if not integration or not jira_client:
                self._update_job_status(job_id, "FAILED", "Failed to initialize Jira client")
                return False

            # Determine next step and data type based on current step (job-aware routing)
            if extraction_type == 'config_statuses_and_relations':
                next_step = 'config_wit_hierarchies'
                data_type_for_transform = 'config_statuses_and_relations'
                status_step_name = 'config_statuses_and_relations'
            else:  # jira_statuses_and_relationships
                next_step = 'jira_issues_with_changelogs'
                data_type_for_transform = 'jira_statuses_and_relationships'
                status_step_name = 'jira_statuses_and_relationships'

            # Get projects from integration settings
            settings = integration.get('settings', {})
            project_keys = settings.get('projects', [])

            if not project_keys:
                logger.warning(f"No projects configured in integration settings")
                # Queue next step even if no projects
                self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, old_last_sync_date, True, False, False)
                return True

            logger.info(f"📊 Fetching and queuing statuses for {len(project_keys)} projects")

            queue_manager = QueueManager()
            total_projects = len(project_keys)

            # Step 1: Fetch all project statuses and combine into single payload
            all_projects_statuses = []

            for i, project_key in enumerate(project_keys):
                logger.debug(f"📋 Fetching statuses for project {project_key} ({i+1}/{total_projects})")

                # Fetch project-specific statuses
                project_statuses = jira_client.get_project_statuses(project_key)

                if not project_statuses:
                    logger.warning(f"No statuses found for project {project_key}")
                    continue

                logger.debug(f"📊 Found {len(project_statuses)} issue types with statuses for project {project_key}")

                # Add to combined payload (don't deduplicate - let transform handle it)
                all_projects_statuses.append({
                    'project_key': project_key,
                    'statuses': project_statuses
                })

                # Log progress every 10 projects
                if (i + 1) % 10 == 0 or (i + 1) == total_projects:
                    logger.info(f"Fetched {i+1}/{total_projects} project statuses")

            if not all_projects_statuses:
                logger.warning(f"No statuses found for any project")
                # Queue next step even if no statuses
                self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, old_last_sync_date, True, False, False)
                return True

            logger.info(f"✅ Fetched statuses from {len(all_projects_statuses)} projects")

            # Step 2: Store combined payload in a SINGLE raw_data record
            raw_data_id = self._store_raw_data(
                tenant_id,
                integration_id,
                'jira_project_statuses',
                {
                    'projects': all_projects_statuses  # Array of {project_key, statuses}
                }
            )

            if not raw_data_id:
                logger.error(f"Failed to store combined raw data for statuses")
                return False

            logger.info(f"✅ Stored combined statuses payload in raw_extraction_data (id={raw_data_id})")

            # Step 3: Queue SINGLE message to transform
            message = {
                'tenant_id': tenant_id,
                'integration_id': integration_id,
                'job_id': job_id,
                'type': data_type_for_transform,
                'provider': 'jira',
                'first_item': True,   # Single message is both first and last
                'last_item': True,    # Single message is both first and last
                'old_last_sync_date': old_last_sync_date,
                'new_last_sync_date': new_last_sync_date,
                'last_job_item': False,
                'token': token,
                'raw_data_id': raw_data_id,
                'last_repo': False,
                'last_pr_last_nested': False
            }

            with queue_manager.get_channel() as channel:
                tier = queue_manager._get_tenant_tier(tenant_id)
                tier_queue = queue_manager.get_tier_queue_name(tier, 'transform')

                channel.basic_publish(
                    exchange='',
                    routing_key=tier_queue,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )

            logger.info(f"✅ Queued combined statuses payload to transform (first=True, last=True)")

            # Send finished status for this step
            await self._send_worker_status("extraction", tenant_id, job_id, "finished", status_step_name)

            # Queue next step (job-aware: wit_hierarchies for Config, issues_with_changelogs for Jira)
            self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, old_last_sync_date, True)

            logger.info(f"✅ Statuses and relationships extraction completed for {total_projects} projects (next step: {next_step})")
            return True

        except Exception as e:
            logger.error(f"❌ Error in statuses extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _extract_issues_with_changelogs(self, message: Dict[str, Any]) -> bool:
        """
        Extract Jira issues with changelogs.

        This is Step 3 of the Jira extraction pipeline.
        Fetches ALL issues based on last_sync_date and projects filter,
        then queues individual messages to transform for each issue.
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            old_last_sync_date = message.get('old_last_sync_date')  # 🔑 Extract from message

            logger.debug(f"🏁 [JIRA] Starting issues with changelogs extraction")

            # Get Jira client and integration settings
            integration, jira_client = self._get_jira_client(tenant_id, integration_id)
            if not integration or not jira_client:
                self._update_job_status(job_id, "FAILED", "Failed to initialize Jira client")
                return False

            # Get projects from integration settings
            settings = integration.get('settings', {})
            project_keys = settings.get('projects', [])
            base_search = settings.get('base_search')  # Optional additional filter

            if not project_keys:
                logger.warning(f"No projects configured in integration settings")
                # Send completion message (no issues case)
                # Set new_last_sync_date even for no-data case
                from app.core.utils import DateTimeHelper
                new_last_sync_date = DateTimeHelper.now_default().strftime('%Y-%m-%d')

                queue_manager = QueueManager()
                queue_manager.publish_transform_job(
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    raw_data_id=None,  # Completion message
                    data_type='jira_issues_with_changelogs',
                    job_id=job_id,
                    provider='jira',
                    old_last_sync_date=old_last_sync_date,  # 🔑 Forward to transform
                    new_last_sync_date=new_last_sync_date,  # 🔑 Forward to transform
                    first_item=True,
                    last_item=True,
                    last_job_item=True,  # Skip Step 4 (no issues)
                    token=token
                )
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_issues_with_changelogs")
                return True

            # 🔑 Use old_last_sync_date from message (passed from jobs.py)
            # Convert string to datetime if needed for JQL formatting
            last_sync_date = None
            if old_last_sync_date:
                from datetime import datetime
                try:
                    # Try parsing with timestamp first (YYYY-MM-DD HH:MM:SS)
                    try:
                        last_sync_date = datetime.strptime(old_last_sync_date, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        # Fall back to date-only format (YYYY-MM-DD)
                        last_sync_date = datetime.strptime(old_last_sync_date, '%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"Failed to parse old_last_sync_date '{old_last_sync_date}': {e}")
                    last_sync_date = None

            # 🔑 Set new_last_sync_date to current time (extraction start time)
            # This will be saved to last_sync_date when job completes successfully
            from app.core.utils import DateTimeHelper
            new_last_sync_date_dt = DateTimeHelper.now_default()
            new_last_sync_date = new_last_sync_date_dt.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"📅 Setting new_last_sync_date for job completion: {new_last_sync_date}")

            # Build JQL query with projects filter and date range filter
            jql_parts = []

            # Projects filter using IN operator (cleaner and more efficient than multiple OR conditions)
            projects_list = ", ".join(project_keys)
            jql_parts.append(f"project IN ({projects_list})")

            # Base search filter (optional)
            if base_search:
                jql_parts.append(f"({base_search})")

            # Date range filter: updated >= old_last_sync_date AND updated < new_last_sync_date
            if last_sync_date:
                # Lower bound: updated >= old_last_sync_date
                lower_bound_str = last_sync_date.strftime('%Y-%m-%d %H:%M')
                jql_parts.append(f"updated >= '{lower_bound_str}'")

                # Upper bound: updated < new_last_sync_date (to avoid re-processing same issues)
                upper_bound_str = new_last_sync_date_dt.strftime('%Y-%m-%d %H:%M')
                jql_parts.append(f"updated < '{upper_bound_str}'")

                logger.debug(f"📅 Incremental sync window: {lower_bound_str} to {upper_bound_str}")
            else:
                logger.debug(f"📅 Full sync (no last_sync_date)")

            # Combine all parts
            jql = " AND ".join(jql_parts) + " ORDER BY updated ASC"
            logger.info(f"📋 JQL Query: {jql}")

            # 🔄 Get development field and sprints field external_ids BEFORE pagination
            # We need these to track dev_count and sprint_combinations incrementally
            development_field_external_id = None
            sprints_field_external_id = None
            database = get_database()
            with database.get_read_session_context() as db:
                query = text("""
                    SELECT cf_dev.external_id, cf_sprint.external_id
                    FROM custom_fields_mappings cfm
                    LEFT JOIN custom_fields cf_dev ON cf_dev.id = cfm.development_field_id AND cf_dev.active = true
                    LEFT JOIN custom_fields cf_sprint ON cf_sprint.id = cfm.sprints_field_id AND cf_sprint.active = true
                    WHERE cfm.tenant_id = :tenant_id
                    AND cfm.integration_id = :integration_id
                    AND cfm.active = true
                """)
                result = db.execute(query, {
                    'tenant_id': tenant_id,
                    'integration_id': integration_id
                }).fetchone()

                if result:
                    development_field_external_id = result[0]
                    sprints_field_external_id = result[1]
                    logger.debug(f"📋 Development field from mapping: {development_field_external_id}")
                    logger.debug(f"📋 Sprints field from mapping: {sprints_field_external_id}")
                else:
                    logger.debug(f"⚠️ No custom field mappings found in custom_fields_mappings table")

            # 🔄 Stream issues page-by-page with incremental tracking
            next_page_token = None
            page_number = 1
            total_issues_processed = 0

            # Track dev and sprint data incrementally across all pages
            issues_with_dev = []
            sprint_combinations = set()

            queue_manager = QueueManager()

            logger.info(f"🔄 Starting paginated fetch and streaming of issues...")

            while True:
                # Fetch one page of issues
                issues_response = jira_client.search_issues(
                    jql=jql,
                    expand=['changelog'],
                    fields=['*all'],
                    max_results=100,
                    next_page_token=next_page_token
                )

                if not issues_response:
                    logger.warning(f"No response from Jira API on page {page_number}")
                    break

                page_issues = issues_response.get('issues', [])
                if not page_issues:
                    logger.info(f"No issues found on page {page_number}")
                    break

                # Check if this is the last page
                is_last_page = issues_response.get('isLast', True)
                next_page_token = issues_response.get('nextPageToken')

                logger.info(f"📄 Page {page_number}: Fetched {len(page_issues)} issues (isLast={is_last_page})")

                # 🔑 Process this page: store, queue, and track dev/sprint data
                await self._process_issues_page(
                    page_issues=page_issues,
                    page_number=page_number,
                    is_last_page=is_last_page,
                    total_issues_processed=total_issues_processed,
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    job_id=job_id,
                    token=token,
                    old_last_sync_date=old_last_sync_date,
                    new_last_sync_date=new_last_sync_date,
                    development_field_external_id=development_field_external_id,
                    sprints_field_external_id=sprints_field_external_id,
                    issues_with_dev=issues_with_dev,
                    sprint_combinations=sprint_combinations,
                    queue_manager=queue_manager
                )

                total_issues_processed += len(page_issues)
                logger.info(f"✅ Page {page_number} processed: {len(page_issues)} issues (total so far: {total_issues_processed})")

                if is_last_page or not next_page_token:
                    logger.info(f"✅ Reached last page (page {page_number})")
                    break

                page_number += 1

            logger.info(f"📊 Pagination complete: Processed {total_issues_processed} total issues across {page_number} page(s)")

            if total_issues_processed == 0:
                logger.warning(f"No issues found - marking all remaining steps as finished")

                # 🎯 OPTION 1: Mark all remaining steps as finished directly (current approach)
                # This avoids sending unnecessary completion messages through the queue
                # Step 3 (issues_with_changelogs): extraction, transform, embedding
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_issues_with_changelogs")
                await self._send_worker_status("transform", tenant_id, job_id, "finished", "jira_issues_with_changelogs")
                await self._send_worker_status("embedding", tenant_id, job_id, "finished", "jira_issues_with_changelogs")

                # Step 4 (dev_status): extraction, transform, embedding
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_dev_status")
                await self._send_worker_status("transform", tenant_id, job_id, "finished", "jira_dev_status")
                await self._send_worker_status("embedding", tenant_id, job_id, "finished", "jira_dev_status")

                # Step 5 (sprint_reports): extraction, transform, embedding
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_sprint_reports")
                await self._send_worker_status("transform", tenant_id, job_id, "finished", "jira_sprint_reports")
                await self._send_worker_status("embedding", tenant_id, job_id, "finished", "jira_sprint_reports")

                # Mark overall job as FINISHED and update last_sync_date (using generic method)
                await self.status_manager.complete_etl_job(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    last_sync_date=new_last_sync_date
                )

                logger.info(f"✅ All steps marked as finished and job marked as FINISHED (no issues to process)")

                # 🎯 OPTION 2: Send completion message to transform (uncomment if you want the message to flow through workers)
                # queue_manager = QueueManager()
                # queue_manager.publish_transform_job(
                #     tenant_id=tenant_id,
                #     integration_id=integration_id,
                #     raw_data_id=None,  # Completion message
                #     data_type='jira_issues_with_changelogs',
                #     job_id=job_id,
                #     provider='jira',
                #     old_last_sync_date=old_last_sync_date,  # 🔑 Forward to transform
                #     new_last_sync_date=new_last_sync_date,  # 🔑 Forward to transform
                #     first_item=True,
                #     last_item=True,
                #     last_job_item=True,  # Skip Step 4 (no issues)
                #     token=token
                # )
                # await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_issues_with_changelogs")

                return True

            # Send finished status for issues extraction step
            await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_issues_with_changelogs")

            # 🔑 Send completion message to transform worker to trigger "finished" status
            # This is needed because the last page might not have had last_item=True
            # (e.g., if the API said hasNext=True but the next page was empty)
            logger.info(f"📨 Sending completion message to transform worker for jira_issues_with_changelogs")
            queue_manager.publish_transform_job(
                tenant_id=tenant_id,
                integration_id=integration_id,
                raw_data_id=None,  # Completion message (no data to process)
                data_type='jira_issues_with_changelogs_completion',
                job_id=job_id,
                provider='jira',
                old_last_sync_date=old_last_sync_date,
                new_last_sync_date=new_last_sync_date,
                first_item=False,
                last_item=True,  # 🔑 This triggers transform "finished" status
                last_job_item=False,  # Dev/sprint steps may follow
                token=token
            )

            # 📊 Now queue dev_status and sprint_reports based on incremental tracking
            logger.info(f"📊 Final counts: {total_issues_processed} issues, {len(issues_with_dev)} with dev field, {len(sprint_combinations)} unique sprints")

            # Count items for each step
            dev_count = len(issues_with_dev)
            sprint_count = len(sprint_combinations)

            logger.info(f"� Step completion analysis: dev_count={dev_count}, sprint_count={sprint_count}")

            # 🎯 Determine which step gets last_job_item=True based on 4 scenarios
            # Scenario 1: Dev YES, Sprint NO → Dev gets last_job_item
            # Scenario 2: Dev NO, Sprint YES → Sprint gets last_job_item
            # Scenario 3: Dev NO, Sprint NO → Already handled (no steps to queue)
            # Scenario 4: Dev YES, Sprint YES → Bigger one gets last_job_item, queue smaller first

            # Determine queue order and last_job_item assignment
            if dev_count > 0 and sprint_count > 0:
                # Scenario 4: Both exist - queue smaller first, bigger gets last_job_item
                if sprint_count > dev_count:
                    # Sprint has more items - queue dev first, sprint second (sprint gets last_job_item)
                    logger.info(f"🎯 Scenario 4a: Both steps exist, sprint_count > dev_count → Queue dev first, sprint gets last_job_item")
                    queue_order = [('dev', False), ('sprint', True)]
                else:
                    # Dev has more items (or equal) - queue sprint first, dev second (dev gets last_job_item)
                    logger.info(f"🎯 Scenario 4b: Both steps exist, dev_count >= sprint_count → Queue sprint first, dev gets last_job_item")
                    queue_order = [('sprint', False), ('dev', True)]
            elif dev_count > 0:
                # Scenario 1: Only dev exists
                logger.info(f"🎯 Scenario 1: Only dev_status exists → Dev gets last_job_item")
                queue_order = [('dev', True)]
            elif sprint_count > 0:
                # Scenario 2: Only sprint exists
                logger.info(f"🎯 Scenario 2: Only sprint_reports exists → Sprint gets last_job_item")
                queue_order = [('sprint', True)]
            else:
                # Scenario 3: Neither exists - mark remaining steps as finished and complete job
                logger.info(f"🎯 Scenario 3: No dev_status or sprint_reports to queue - marking remaining steps as finished")

                # Step 4 (dev_status): extraction, transform, embedding
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_dev_status")
                await self._send_worker_status("transform", tenant_id, job_id, "finished", "jira_dev_status")
                await self._send_worker_status("embedding", tenant_id, job_id, "finished", "jira_dev_status")

                # Step 5 (sprint_reports): extraction, transform, embedding
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_sprint_reports")
                await self._send_worker_status("transform", tenant_id, job_id, "finished", "jira_sprint_reports")
                await self._send_worker_status("embedding", tenant_id, job_id, "finished", "jira_sprint_reports")

                # Mark overall job as FINISHED and update last_sync_date
                await self.status_manager.complete_etl_job(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    last_sync_date=new_last_sync_date
                )

                logger.info(f"✅ All remaining steps marked as finished and job marked as FINISHED (no dev_status or sprint_reports to process)")
                queue_order = []

            # Execute queuing based on determined order
            for step_type, gets_last_job_item in queue_order:
                if step_type == 'dev':
                    # 🔑 NEW: Batch dev_status items and store extraction triggers
                    logger.info(f"📋 Queuing Step 4 (dev_status) for {dev_count} issues (last_job_item={gets_last_job_item})")

                    BATCH_SIZE = 20
                    num_dev_batches = (dev_count + BATCH_SIZE - 1) // BATCH_SIZE

                    logger.info(f"📦 [DEV-STATUS] Batching {dev_count} issues into {num_dev_batches} batches of {BATCH_SIZE}")

                    # 🔑 IMPORTANT: When multiple batches, queue in REVERSE order so largest batch (with last_item=True) finishes last
                    # This prevents smaller batches from finishing first and sending "finished" status prematurely
                    batch_indices = list(range(num_dev_batches))
                    if num_dev_batches > 1:
                        batch_indices = list(reversed(batch_indices))
                        logger.info(f"🔄 [DEV-STATUS] Queuing {num_dev_batches} batches in REVERSE order (smallest first, largest last)")

                    with queue_manager.get_channel() as channel:
                        for queue_position, batch_idx in enumerate(batch_indices):
                            start_idx = batch_idx * BATCH_SIZE
                            end_idx = min(start_idx + BATCH_SIZE, dev_count)
                            batch_issues = issues_with_dev[start_idx:end_idx]

                            # 🔑 Store raw_data with type 'jira_dev_status_extraction' (extraction trigger)
                            raw_data_id = self._store_raw_data(
                                tenant_id, integration_id,
                                'jira_dev_status_extraction',  # 🔑 Different type for extraction trigger
                                {
                                    'issues': [
                                        {'key': issue['key'], 'id': issue['id']}
                                        for issue in batch_issues
                                    ]
                                }
                            )

                            if not raw_data_id:
                                logger.error(f"Failed to store dev_status extraction trigger for batch {batch_idx + 1}")
                                continue

                            # 🔑 Queue dev_status extraction with raw_data_id
                            # Use queue_position (not batch_idx) to determine first/last flags when batches are reversed
                            is_first_dev = (queue_position == 0)
                            is_last_dev = (queue_position == num_dev_batches - 1)

                            dev_message = {
                                'tenant_id': tenant_id,
                                'integration_id': integration_id,
                                'job_id': job_id,
                                'type': 'jira_dev_status',
                                'provider': 'jira',
                                'raw_data_id': raw_data_id,  # 🔑 ID of extraction trigger record
                                'first_item': is_first_dev,
                                'last_item': is_last_dev,
                                'last_job_item': gets_last_job_item and is_last_dev,  # Only set on last item if this step gets it
                                'token': token,
                                'old_last_sync_date': old_last_sync_date,
                                'new_last_sync_date': new_last_sync_date
                            }

                            # Publish using shared channel
                            tier = queue_manager._get_tenant_tier(tenant_id)
                            tier_queue = queue_manager.get_tier_queue_name(tier, 'extraction')

                            channel.basic_publish(
                                exchange='',
                                routing_key=tier_queue,
                                body=json.dumps(dev_message),
                                properties=pika.BasicProperties(
                                    delivery_mode=2,
                                    content_type='application/json'
                                )
                            )

                            logger.info(f"📦 Queued dev_status batch {batch_idx + 1}/{num_dev_batches} ({len(batch_issues)} issues, raw_data_id={raw_data_id})")

                    logger.info(f"✅ All {num_dev_batches} dev_status extraction batches queued (last_job_item={gets_last_job_item})")

                elif step_type == 'sprint':
                    # 🔑 NEW: Batch sprint_reports items and store extraction triggers
                    sprint_list = list(sprint_combinations)
                    logger.info(f"📋 Queuing Step 5 (sprint_reports) for {sprint_count} unique sprints (last_job_item={gets_last_job_item})")

                    BATCH_SIZE = 20
                    num_sprint_batches = (sprint_count + BATCH_SIZE - 1) // BATCH_SIZE

                    logger.info(f"📦 [SPRINT-REPORTS] Batching {sprint_count} sprints into {num_sprint_batches} batches of {BATCH_SIZE}")

                    # 🔑 IMPORTANT: When multiple batches, queue in REVERSE order so largest batch (with last_item=True) finishes last
                    # This prevents smaller batches from finishing first and sending "finished" status prematurely
                    batch_indices = list(range(num_sprint_batches))
                    if num_sprint_batches > 1:
                        batch_indices = list(reversed(batch_indices))
                        logger.info(f"🔄 [SPRINT-REPORTS] Queuing {num_sprint_batches} batches in REVERSE order (smallest first, largest last)")

                    with queue_manager.get_channel() as channel:
                        for queue_position, batch_idx in enumerate(batch_indices):
                            start_idx = batch_idx * BATCH_SIZE
                            end_idx = min(start_idx + BATCH_SIZE, sprint_count)
                            batch_sprints = sprint_list[start_idx:end_idx]

                            # 🔑 Store raw_data with type 'jira_sprint_reports_extraction' (extraction trigger)
                            raw_data_id = self._store_raw_data(
                                tenant_id, integration_id,
                                'jira_sprint_reports_extraction',  # 🔑 Different type for extraction trigger
                                {
                                    'sprints': [
                                        {'board_id': board_id, 'sprint_id': sprint_id}
                                        for board_id, sprint_id in batch_sprints
                                    ]
                                }
                            )

                            if not raw_data_id:
                                logger.error(f"Failed to store sprint_reports extraction trigger for batch {batch_idx + 1}")
                                continue

                            # 🔑 Queue sprint_reports extraction with raw_data_id
                            # Use queue_position (not batch_idx) to determine first/last flags when batches are reversed
                            is_first_sprint = (queue_position == 0)
                            is_last_sprint = (queue_position == num_sprint_batches - 1)

                            sprint_message = {
                                'tenant_id': tenant_id,
                                'integration_id': integration_id,
                                'job_id': job_id,
                                'type': 'jira_sprint_reports',
                                'provider': 'jira',
                                'raw_data_id': raw_data_id,  # 🔑 ID of extraction trigger record
                                'first_item': is_first_sprint,
                                'last_item': is_last_sprint,
                                'last_job_item': gets_last_job_item and is_last_sprint,  # Only set on last item if this step gets it
                                'token': token,
                                'old_last_sync_date': old_last_sync_date,
                                'new_last_sync_date': new_last_sync_date
                            }

                            # Publish using shared channel
                            tier = queue_manager._get_tenant_tier(tenant_id)
                            tier_queue = queue_manager.get_tier_queue_name(tier, 'extraction')

                            channel.basic_publish(
                                exchange='',
                                routing_key=tier_queue,
                                body=json.dumps(sprint_message),
                                properties=pika.BasicProperties(
                                    delivery_mode=2,
                                    content_type='application/json'
                                )
                            )

                            logger.info(f"📦 Queued sprint_reports batch {batch_idx + 1}/{num_sprint_batches} ({len(batch_sprints)} sprints, raw_data_id={raw_data_id})")

                    logger.info(f"✅ All {num_sprint_batches} sprint_reports extraction batches queued (last_job_item={gets_last_job_item})")

            logger.info(f"✅ Issues with changelogs extraction completed ({total_issues_processed} issues, {dev_count} with dev status, {sprint_count} unique sprints)")
            return True

        except Exception as e:
            logger.error(f"❌ Error in issues extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _fetch_jira_dev_status(self, message: Dict[str, Any]) -> bool:
        """
        Fetch Jira development status (BATCH MODE).

        This is Step 4 of the Jira extraction pipeline.
        This step is ONLY queued if Step 3 found issues with development field.

        NEW BATCH APPROACH:
        - Receives raw_data_id pointing to extraction trigger (type: jira_dev_status_extraction)
        - Loads batch of issue keys from extraction trigger
        - Fetches dev_status for all issues in batch
        - Inserts NEW raw_data record with actual dev_status data (type: jira_dev_status)
        - Marks extraction trigger as completed
        - Queues transform with NEW raw_data_id
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            old_last_sync_date = message.get('old_last_sync_date')
            new_last_sync_date = message.get('new_last_sync_date')
            raw_data_id = message.get('raw_data_id')
            first_item = message.get('first_item', False)
            last_item = message.get('last_item', False)
            last_job_item = message.get('last_job_item', False)

            if raw_data_id:
                # 🔑 NEW: Batch mode - load issue keys from extraction trigger
                logger.info(f"📦 [DEV-STATUS-BATCH] Processing batch from raw_data_id={raw_data_id}")

                # 1️⃣ Load extraction trigger raw_data (type: jira_dev_status_extraction)
                with self.get_db_session() as db:
                    raw_data = self._get_raw_data(db, raw_data_id)
                    if not raw_data:
                        logger.error(f"Raw data {raw_data_id} not found")
                        return False

                    issues = raw_data.get('issues', [])

                logger.info(f"� [DEV-STATUS-BATCH] Fetching dev_status for {len(issues)} issues")

                # 2️⃣ Get Jira client
                integration, jira_client = self._get_jira_client(tenant_id, integration_id)
                if not integration or not jira_client:
                    logger.error("Failed to initialize Jira client")
                    return False

                # 3️⃣ Fetch dev_status for all issues in batch
                dev_status_results = []
                total_issues = len(issues)
                for idx, issue in enumerate(issues, 1):
                    try:
                        dev_status = jira_client.get_dev_status(issue['id'])
                        dev_status_results.append({
                            'issue_id': issue['id'],
                            'issue_key': issue['key'],
                            'dev_status': dev_status or {}
                        })
                    except Exception as e:
                        logger.error(f"Error fetching dev_status for {issue['key']}: {e}")
                        dev_status_results.append({
                            'issue_id': issue['id'],
                            'issue_key': issue['key'],
                            'dev_status': {}
                        })

                    # Log progress every 20 items
                    if idx % 20 == 0 or idx == total_issues:
                        logger.info(f"📊 [DEV-STATUS] Fetched dev_status for {idx}/{total_issues} issues")

                # 4️⃣ Insert NEW raw_data record with actual dev_status data (type: jira_dev_status)
                new_raw_data_id = self._store_raw_data(
                    tenant_id, integration_id,
                    'jira_dev_status',  # 🔑 Different type for actual data
                    {'dev_status_batch': dev_status_results}
                )

                if not new_raw_data_id:
                    logger.error("Failed to store dev_status results")
                    return False

                logger.info(f"📦 [DEV-STATUS-BATCH] Stored {len(issues)} dev_status in new raw_data_id={new_raw_data_id}")

                # 5️⃣ Mark extraction trigger raw_data as completed
                with self.get_db_session() as db:
                    from app.core.utils import DateTimeHelper
                    now = DateTimeHelper.now_default()

                    update_query = text("""
                        UPDATE raw_extraction_data
                        SET status = 'completed',
                            last_updated_at = :now
                        WHERE id = :raw_data_id
                    """)
                    db.execute(update_query, {'raw_data_id': raw_data_id, 'now': now})
                    db.commit()

                logger.debug(f"✅ Marked extraction trigger raw_data_id={raw_data_id} as completed")

                # 6️⃣ Queue transform with NEW raw_data_id
                queue_manager = QueueManager()
                success = queue_manager.publish_transform_job(
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    raw_data_id=new_raw_data_id,  # 🔑 Use NEW raw_data_id
                    data_type='jira_dev_status',
                    job_id=job_id,
                    provider='jira',
                    first_item=first_item,
                    last_item=last_item,
                    last_job_item=last_job_item,
                    token=token,
                    old_last_sync_date=old_last_sync_date,
                    new_last_sync_date=new_last_sync_date
                )

                if not success:
                    logger.error("Failed to queue dev_status to transform")
                    return False

                logger.info(f"✅ [DEV-STATUS-BATCH] Queued transform for {len(issues)} dev_status (raw_data_id={new_raw_data_id})")

                # 7️⃣ Send finished status on last item
                if last_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_dev_status")

                return True

            else:
                # OLD: Single issue mode (backward compatibility) - should not be used anymore
                logger.warning("⚠️ [DEV-STATUS] Received old-style single issue message - this should not happen with batch mode")
                issue_id = message.get('issue_id')
                issue_key = message.get('issue_key')

                logger.debug(f"🏁 [JIRA] Starting dev status extraction for issue {issue_key} (first_item={first_item}, last_item={last_item}, last_job_item={last_job_item})")

                # Get Jira client
                integration, jira_client = self._get_jira_client(tenant_id, integration_id)
                if not integration or not jira_client:
                    self._update_job_status(job_id, "FAILED", "Failed to initialize Jira client")
                    return False

                # Fetch dev status for this issue
                try:
                    dev_status = jira_client.get_dev_status(issue_id)

                    if not dev_status:
                        logger.warning(f"No dev status found for issue {issue_key}")
                        # Even if no data, we still need to queue to transform to maintain the chain
                        # Use empty dict as placeholder
                        dev_status = {}

                    logger.debug(f"📊 Fetched dev status for issue {issue_key}")

                except Exception as e:
                    logger.error(f"Error fetching dev status for issue {issue_key}: {e}")
                    # Use empty dict as placeholder to maintain the chain
                    dev_status = {}

                # Store raw data
                raw_data_id = self._store_raw_data(
                    tenant_id,
                    integration_id,
                    'jira_dev_status',
                    {
                        'issue_id': issue_id,
                        'issue_key': issue_key,
                        'dev_status': dev_status
                    }
                )

                if not raw_data_id:
                    logger.error(f"Failed to store raw data for issue {issue_key}")
                    self._update_job_status(job_id, "FAILED", f"Failed to store dev status for {issue_key}")
                    return False

                # Queue to transform
                queue_manager = QueueManager()
                success = queue_manager.publish_transform_job(
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    raw_data_id=raw_data_id,
                    data_type='jira_dev_status',
                    job_id=job_id,
                    provider='jira',
                    old_last_sync_date=old_last_sync_date,  # 🔑 Forward to transform
                    new_last_sync_date=new_last_sync_date,  # 🔑 Forward to transform
                    first_item=first_item,      # True only for first dev status
                    last_item=last_item,        # True only for last dev status
                    last_job_item=last_job_item,    # 🎯 Forward from message (set by Step 3 logic)
                    token=token
                )

                if not success:
                    logger.error(f"Failed to queue dev status for issue {issue_key} to transform")
                    self._update_job_status(job_id, "FAILED", f"Failed to queue dev status for {issue_key}")
                    return False

                logger.debug(f"✅ Queued dev status for issue {issue_key} to transform (first_item={first_item}, last_item={last_item}, last_job_item={last_job_item})")

                # Send finished status ONLY on last item
                if last_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_dev_status")
                    logger.debug(f"✅ Dev status extraction completed (last item)")

                return True

        except Exception as e:
            logger.error(f"❌ Error in dev status extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _extract_sprint_reports(self, message: Dict[str, Any]) -> bool:
        """
        Extract sprint report data from Jira's sprint report API (BATCH MODE).

        NEW BATCH APPROACH:
        - Receives raw_data_id pointing to extraction trigger (type: jira_sprint_reports_extraction)
        - Loads batch of sprint metadata (board_id, sprint_id pairs) from extraction trigger
        - Fetches sprint reports for all sprints in batch
        - Inserts NEW raw_data record with actual sprint report data (type: jira_sprint_reports)
        - Marks extraction trigger as completed
        - Queues transform with NEW raw_data_id

        This method fetches sprint report data from Jira API:
        - Endpoint: /rest/greenhopper/1.0/rapid/charts/sprintreport
        - Parameters: rapidViewId (board_id), sprintId (sprint_id)
        - Data: completed issues, not completed issues, punted issues, velocity, completion %

        Args:
            message: Message containing:
                - raw_data_id: ID of extraction trigger record
                - tenant_id, integration_id, job_id, token
                - first_item, last_item, last_job_item flags
                - old_last_sync_date, new_last_sync_date

        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            old_last_sync_date = message.get('old_last_sync_date')
            new_last_sync_date = message.get('new_last_sync_date')
            raw_data_id = message.get('raw_data_id')
            first_item = message.get('first_item', False)
            last_item = message.get('last_item', False)
            last_job_item = message.get('last_job_item', False)

            if raw_data_id:
                # 🔑 NEW: Batch mode - load sprint metadata from extraction trigger
                logger.info(f"� [SPRINT-REPORTS-BATCH] Processing batch from raw_data_id={raw_data_id}")

                # Send running status on first item
                if first_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "running", "jira_sprint_reports")
                    logger.info(f"✅ Sent 'running' status for jira_sprint_reports")

                # 1️⃣ Load extraction trigger raw_data (type: jira_sprint_reports_extraction)
                with self.get_db_session() as db:
                    raw_data = self._get_raw_data(db, raw_data_id)
                    if not raw_data:
                        logger.error(f"Raw data {raw_data_id} not found")
                        return False

                    sprints = raw_data.get('sprints', [])

                logger.info(f"📦 [SPRINT-REPORTS-BATCH] Fetching sprint reports for {len(sprints)} sprints")

                # 2️⃣ Get Jira client
                integration, jira_client = self._get_jira_client(tenant_id, integration_id)
                if not integration or not jira_client:
                    logger.error("Failed to initialize Jira client")
                    return False

                # 3️⃣ Fetch sprint reports for all sprints in batch
                sprint_report_results = []
                for sprint in sprints:
                    board_id = sprint['board_id']
                    sprint_id = sprint['sprint_id']

                    try:
                        logger.debug(f"🔍 Fetching sprint report: board_id={board_id}, sprint_id={sprint_id}")
                        sprint_report_data = jira_client.get_sprint_report(board_id, sprint_id)

                        if sprint_report_data:
                            sprint_report_results.append({
                                'board_id': board_id,
                                'sprint_id': sprint_id,
                                'sprint_report': sprint_report_data
                            })
                            logger.debug(f"✅ Fetched sprint report: board_id={board_id}, sprint_id={sprint_id}")
                        else:
                            logger.warning(f"No sprint report data for board_id={board_id}, sprint_id={sprint_id}")
                            sprint_report_results.append({
                                'board_id': board_id,
                                'sprint_id': sprint_id,
                                'sprint_report': {}
                            })
                    except Exception as e:
                        logger.error(f"Error fetching sprint report for board_id={board_id}, sprint_id={sprint_id}: {e}")
                        sprint_report_results.append({
                            'board_id': board_id,
                            'sprint_id': sprint_id,
                            'sprint_report': {}
                        })

                # 4️⃣ Insert NEW raw_data record with actual sprint report data (type: jira_sprint_reports)
                new_raw_data_id = self._store_raw_data(
                    tenant_id, integration_id,
                    'jira_sprint_reports',  # 🔑 Different type for actual data
                    {'sprint_reports_batch': sprint_report_results}
                )

                if not new_raw_data_id:
                    logger.error("Failed to store sprint report results")
                    return False

                logger.info(f"📦 [SPRINT-REPORTS-BATCH] Stored {len(sprints)} sprint reports in new raw_data_id={new_raw_data_id}")

                # 5️⃣ Mark extraction trigger raw_data as completed
                with self.get_db_session() as db:
                    from app.core.utils import DateTimeHelper
                    now = DateTimeHelper.now_default()

                    update_query = text("""
                        UPDATE raw_extraction_data
                        SET status = 'completed',
                            last_updated_at = :now
                        WHERE id = :raw_data_id
                    """)
                    db.execute(update_query, {'raw_data_id': raw_data_id, 'now': now})
                    db.commit()

                logger.debug(f"✅ Marked extraction trigger raw_data_id={raw_data_id} as completed")

                # 6️⃣ Queue transform with NEW raw_data_id
                queue_manager = QueueManager()
                success = queue_manager.publish_transform_job(
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    raw_data_id=new_raw_data_id,  # 🔑 Use NEW raw_data_id
                    data_type='jira_sprint_reports',
                    job_id=job_id,
                    provider='jira',
                    first_item=first_item,
                    last_item=last_item,
                    last_job_item=last_job_item,
                    token=token,
                    old_last_sync_date=old_last_sync_date,
                    new_last_sync_date=new_last_sync_date
                )

                if not success:
                    logger.error("Failed to queue sprint reports to transform")
                    return False

                logger.info(f"✅ [SPRINT-REPORTS-BATCH] Queued transform for {len(sprints)} sprint reports (raw_data_id={new_raw_data_id})")

                # 7️⃣ Send finished status on last item
                if last_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_sprint_reports")

                return True

            else:
                # OLD: Single sprint mode (backward compatibility) - should not be used anymore
                logger.warning("⚠️ [SPRINT-REPORTS] Received old-style single sprint message - this should not happen with batch mode")
                board_id = message.get('board_id')
                sprint_id = message.get('sprint_id')

                logger.debug(f"📊 [JIRA] Extracting sprint report for board_id={board_id}, sprint_id={sprint_id} (first_item={first_item}, last_item={last_item}, last_job_item={last_job_item})")

                # Send running status on first item
                if first_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "running", "jira_sprint_reports")
                    logger.info(f"✅ Sent 'running' status for jira_sprint_reports")

                # Get Jira client
                integration, jira_client = self._get_jira_client(tenant_id, integration_id)
                if not integration or not jira_client:
                    logger.error(f"Failed to initialize Jira client for sprint report extraction")
                    return False

                logger.info(f"🔍 Fetching sprint report from Jira API: board_id={board_id}, sprint_id={sprint_id}")
                # Fetch sprint report data from Jira API
                sprint_report_data = jira_client.get_sprint_report(board_id, sprint_id)
                logger.info(f"📊 Sprint report API response: {bool(sprint_report_data)} (has data: {sprint_report_data is not None})")

                if not sprint_report_data:
                    logger.warning(f"No sprint report data returned for board_id={board_id}, sprint_id={sprint_id}")
                    # Still queue to transform with empty data to maintain flow
                    queue_manager = QueueManager()
                    queue_manager.publish_transform_job(
                        tenant_id=tenant_id,
                        integration_id=integration_id,
                        raw_data_id=None,  # No data to process
                        data_type='jira_sprint_reports',
                        job_id=job_id,
                        provider='jira',
                        old_last_sync_date=old_last_sync_date,
                        new_last_sync_date=new_last_sync_date,
                        first_item=first_item,
                        last_item=last_item,
                        last_job_item=last_job_item,
                        token=token
                    )
                    return True

                # Store raw data in raw_extraction_data table
                raw_data_id = self._store_raw_data(
                    tenant_id,
                    integration_id,
                    'jira_sprint_reports',
                    {
                        'board_id': board_id,
                        'sprint_id': sprint_id,
                        'sprint_report': sprint_report_data
                    }
                )

                if not raw_data_id:
                    logger.error(f"Failed to store raw data for sprint report (board_id={board_id}, sprint_id={sprint_id})")
                    return False

                logger.debug(f"Stored sprint report raw data with raw_data_id={raw_data_id}")

                # Queue to transform worker
                queue_manager = QueueManager()
                success = queue_manager.publish_transform_job(
                    tenant_id=tenant_id,
                    integration_id=integration_id,
                    raw_data_id=raw_data_id,
                    data_type='jira_sprint_reports',
                    job_id=job_id,
                    provider='jira',
                    old_last_sync_date=old_last_sync_date,
                    new_last_sync_date=new_last_sync_date,
                    first_item=first_item,
                    last_item=last_item,
                    last_job_item=last_job_item,
                    token=token
                )

                if not success:
                    logger.error(f"Failed to queue sprint report to transform (board_id={board_id}, sprint_id={sprint_id})")
                    return False

                logger.info(f"✅ Sprint report queued to transform (board_id={board_id}, sprint_id={sprint_id}, raw_data_id={raw_data_id})")

                # Send finished status on last item
                if last_item:
                    await self._send_worker_status("extraction", tenant_id, job_id, "finished", "jira_sprint_reports")
                    logger.debug(f"✅ Sprint reports extraction completed (last item)")

                return True

        except Exception as e:
            logger.error(f"❌ Error in sprint reports extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _process_issues_page(
        self,
        page_issues: list,
        page_number: int,
        is_last_page: bool,
        total_issues_processed: int,
        tenant_id: str,
        integration_id: str,
        job_id: str,
        token: str,
        old_last_sync_date: str,
        new_last_sync_date: str,
        development_field_external_id: Optional[str],
        sprints_field_external_id: Optional[str],
        issues_with_dev: list,
        sprint_combinations: set,
        queue_manager
    ):
        """
        Process a single page of issues (BATCH MODE): store ONE raw_data, send ONE message, track dev/sprint data.

        NEW BATCH APPROACH:
        - Stores ONE raw_data record with all 100 issues
        - Sends ONE message to transform (instead of 100 individual messages)
        - Tracks dev and sprint data for this page

        Args:
            page_issues: List of issues from this page (up to 100)
            page_number: Current page number (1-based)
            is_last_page: Whether this is the last page (from isLast flag)
            total_issues_processed: Count of issues processed before this page
            tenant_id: Tenant ID
            integration_id: Integration ID
            job_id: Job ID
            token: Job execution token
            old_last_sync_date: Previous sync date
            new_last_sync_date: New sync date
            development_field_external_id: External ID of development custom field
            sprints_field_external_id: External ID of sprints custom field
            issues_with_dev: List to accumulate issues with dev field (modified in place)
            sprint_combinations: Set to accumulate sprint combinations (modified in place)
            queue_manager: QueueManager instance
        """
        logger.info(f"� [BATCH] Processing page {page_number}: {len(page_issues)} issues")

        # 🔑 Track dev and sprint data for this page
        page_issues_with_dev = []
        page_sprint_combinations = set()

        for issue in page_issues:
            # Track if issue has development field
            if development_field_external_id:
                fields = issue.get('fields', {})
                field_value = fields.get(development_field_external_id)
                if field_value:
                    page_issues_with_dev.append(issue)
                    issues_with_dev.append(issue)  # Add to overall list

            # Track sprint combinations
            if sprints_field_external_id:
                sprints_field = issue.get('fields', {}).get(sprints_field_external_id)
                if sprints_field and isinstance(sprints_field, list):
                    for sprint in sprints_field:
                        if isinstance(sprint, dict):
                            board_id = sprint.get('boardId')
                            sprint_id = sprint.get('id')
                            if board_id and sprint_id:
                                page_sprint_combinations.add((board_id, sprint_id))
                                sprint_combinations.add((board_id, sprint_id))  # Add to overall set

        logger.info(f"📊 [BATCH] Page {page_number} tracking: {len(page_issues_with_dev)} with dev, {len(page_sprint_combinations)} new sprints")

        # 🔑 Store ONE raw_data record with all 100 issues
        raw_data_id = self._store_raw_data(
            tenant_id,
            integration_id,
            'jira_issues_with_changelogs',
            {'issues': page_issues}  # Store entire page
        )

        if not raw_data_id:
            logger.error(f"Failed to store raw data for page {page_number}")
            return

        logger.info(f"✅ [BATCH] Stored raw_data_id={raw_data_id} with {len(page_issues)} issues")

        # 🔑 Determine flags for this page
        is_first_page = (page_number == 1)

        # Determine last_job_item flag
        # We can only set this correctly on the last page when we know final counts
        last_job_item = False
        if is_last_page:
            # On last page, check if dev/sprint steps will follow
            dev_count = len(issues_with_dev)
            sprint_count = len(sprint_combinations)
            if dev_count == 0 and sprint_count == 0:
                last_job_item = True  # No more steps!
                logger.info(f"🎯 Last page with NO dev/sprint steps - setting last_job_item=True")

        # 🔑 Send ONE message to transform for this page
        queue_manager.publish_transform_job(
            tenant_id=tenant_id,
            integration_id=integration_id,
            raw_data_id=raw_data_id,
            data_type='jira_issues_with_changelogs',
            job_id=job_id,
            provider='jira',
            old_last_sync_date=old_last_sync_date,
            new_last_sync_date=new_last_sync_date,
            first_item=is_first_page,
            last_item=is_last_page,
            last_job_item=last_job_item,
            token=token
        )

        logger.info(f"✅ [BATCH] Page {page_number} complete: Queued 1 message with {len(page_issues)} issues (first={is_first_page}, last={is_last_page}, last_job={last_job_item})")

    async def _extract_config_custom_fields(self, message: Dict[str, Any]) -> bool:
        """
        Extract custom fields for Config job.

        This is Step 1 of the Config job (config_custom_fields).
        Performs two-step extraction:
        1. Get ALL custom fields from /rest/api/latest/field
        2. Get project-field relationships from /createmeta (broken by project)

        Args:
            message: Message containing extraction parameters

        Returns:
            bool: True if extraction succeeded, False otherwise
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')
            first_item = message.get('first_item', False)
            last_item = message.get('last_item', False)
            last_job_item = message.get('last_job_item', False)

            logger.info(f"🏁 [CONFIG] Starting custom fields extraction (first_item={first_item}, last_item={last_item}, last_job_item={last_job_item})")

            # Get Jira client
            integration, jira_client = self._get_jira_client(tenant_id, integration_id)
            if not integration or not jira_client:
                self._update_job_status(job_id, "FAILED", "Failed to initialize Jira client")
                return False

            queue_manager = QueueManager()

            # ========================================
            # STEP 1: Extract ALL custom fields (BATCH)
            # ========================================
            logger.info(f"📋 Step 1: Fetching ALL custom fields from /rest/api/latest/field")

            all_fields = jira_client.get_all_fields()
            if not all_fields:
                logger.warning(f"No fields found from Jira API")
                all_fields = []

            # Filter to only custom fields (id starts with 'customfield_')
            custom_fields = [f for f in all_fields if f.get('id', '').startswith('customfield_')]
            logger.info(f"📊 Found {len(custom_fields)} custom fields out of {len(all_fields)} total fields")

            # Store ALL custom fields in ONE raw_data record
            raw_data_ids = []  # 🔑 Ordered array of raw_data_ids to process

            if custom_fields:
                all_fields_raw_data_id = self._store_raw_data(
                    tenant_id,
                    integration_id,
                    'config_custom_fields_all',
                    {
                        'type': 'all_custom_fields',
                        'total_count': len(custom_fields),
                        'data': custom_fields
                    }
                )

                if not all_fields_raw_data_id:
                    logger.error(f"Failed to store raw data for all custom fields")
                    self._update_job_status(job_id, "FAILED", "Failed to store custom fields raw data")
                    return False

                raw_data_ids.append(all_fields_raw_data_id)
                logger.info(f"✅ Stored {len(custom_fields)} custom fields in raw_data_id={all_fields_raw_data_id}")

            # ========================================
            # STEP 2: Extract project-field relationships from createmeta (BATCHED)
            # ========================================
            logger.info(f"📋 Step 2: Fetching project-field relationships from /createmeta")

            # Get project keys from integration settings
            settings = integration.get('settings', {})
            project_keys = settings.get('projects', [])

            if not project_keys:
                logger.warning(f"No projects configured in integration settings")
                # Send "extraction finished" status
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "config_custom_fields")
                return True

            logger.info(f"📊 Fetching createmeta for {len(project_keys)} projects (batched 3 at a time)")

            # Batch projects into groups of 3
            BATCH_SIZE = 3
            project_batches = [project_keys[i:i + BATCH_SIZE] for i in range(0, len(project_keys), BATCH_SIZE)]

            logger.info(f"📦 Created {len(project_batches)} batches of projects (max {BATCH_SIZE} per batch)")

            for batch_num, batch_project_keys in enumerate(project_batches, start=1):
                logger.info(f"📋 Fetching createmeta batch {batch_num}/{len(project_batches)} for projects: {batch_project_keys}")

                # Fetch createmeta for this batch of projects (Jira API supports multiple projects)
                createmeta = jira_client.get_createmeta(
                    project_keys=batch_project_keys,
                    expand="projects.issuetypes.fields"
                )

                if not createmeta or not createmeta.get('projects'):
                    logger.warning(f"No createmeta found for batch {batch_num}: {batch_project_keys}")
                    continue

                # Store raw data for this batch
                batch_raw_data_id = self._store_raw_data(
                    tenant_id,
                    integration_id,
                    'config_custom_fields_createmeta_batch',
                    {
                        'type': 'createmeta_batch',
                        'batch_number': batch_num,
                        'project_keys': batch_project_keys,
                        'data': createmeta
                    }
                )

                if not batch_raw_data_id:
                    logger.error(f"Failed to store raw data for createmeta batch {batch_num}")
                    continue

                raw_data_ids.append(batch_raw_data_id)
                logger.info(f"✅ Stored createmeta batch {batch_num} ({len(createmeta.get('projects', []))} projects) in raw_data_id={batch_raw_data_id}")

            logger.info(f"✅ All createmeta batches stored: {len(project_batches)} batches for {len(project_keys)} projects")

            # ========================================
            # STEP 3: Send ONE batch message to transform with ordered raw_data_ids
            # ========================================
            if not raw_data_ids:
                logger.warning(f"No raw_data_ids to process - skipping transform")
                await self._send_worker_status("extraction", tenant_id, job_id, "finished", "config_custom_fields")
                return True

            logger.info(f"📤 Sending batch message to transform with {len(raw_data_ids)} raw_data_ids: {raw_data_ids}")

            # Build batch message with ordered raw_data_ids array
            # 🔑 NOTE: Transform worker handles change detection and job completion
            # - If changes detected: queues for embedding with last_job_item=True → embedding completes job
            # - If no changes: sends "finished" to all workers and completes job itself
            batch_message = {
                'tenant_id': tenant_id,
                'integration_id': integration_id,
                'job_id': job_id,
                'type': 'config_custom_fields_batch',  # 🔑 New message type for batch processing
                'provider': 'jira',
                'first_item': True,
                'last_item': True,  # 🔑 Always True for custom_fields (single batch message)
                'last_job_item': False,  # 🔑 Transform worker handles job completion based on change detection
                'token': token,
                'raw_data_ids': raw_data_ids  # 🔑 Ordered array: [all_fields, batch1, batch2, ...]
            }

            # Publish batch message to transform queue
            tier = queue_manager._get_tenant_tier(tenant_id)
            tier_queue = queue_manager.get_tier_queue_name(tier, 'transform')

            with queue_manager.get_channel() as channel:
                channel.basic_publish(
                    exchange='',
                    routing_key=tier_queue,
                    body=json.dumps(batch_message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )

            logger.info(f"✅ Batch message sent to transform queue: {tier_queue}")

            # Send "extraction finished" status
            # NOTE: custom_fields is the LAST step - do NOT queue any next step
            # Config job execution order: wit_hierarchies (1) → wit_mappings (2) → status_mappings (3) → workflows (4) → custom_fields (5 - LAST)
            await self._send_worker_status("extraction", tenant_id, job_id, "finished", "config_custom_fields")

            logger.info(f"✅ Custom fields extraction completed (batch mode: {len(raw_data_ids)} raw_data records)")
            return True

        except Exception as e:
            logger.error(f"❌ Error in config custom fields extraction: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False

    async def _skip_extraction_to_transform(self, extraction_type: str, message: Dict[str, Any]) -> bool:
        """
        Skip extraction phase for config steps that have no extraction (WIT Hierarchies, WIT Mappings, Status Mappings, Workflows).

        These steps only have Transform and Embedding phases.
        This method immediately sends "extraction finished" status and queues directly to transform.

        Args:
            extraction_type: Type of config step (e.g., 'config_wit_hierarchies')
            message: Message containing extraction parameters

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            tenant_id = message.get('tenant_id')
            integration_id = message.get('integration_id')
            job_id = message.get('job_id')
            token = message.get('token')

            logger.info(f"🏁 [CONFIG] Skipping extraction for {extraction_type} (no extraction phase)")

            # Queue directly to transform with first_item=True, last_item=True
            # The transform worker will handle the actual data processing
            queue_manager = QueueManager()

            # Determine if this is the last step of the config job
            # Config job steps order: projects_and_issue_types (1) → statuses_and_relations (2) → wit_hierarchies (3) → wit_mappings (4) → status_mappings (5) → workflows (6) → custom_fields (7)
            # None of these steps (1-6) should get last_job_item=True - only custom_fields (step 7) gets it
            step_is_last_job_item = False  # Steps 1-6 never get last_job_item=True (custom_fields is the last step)

            success = queue_manager.publish_transform_job(
                tenant_id=tenant_id,
                integration_id=integration_id,
                raw_data_id="x",  # Placeholder value - transform reads directly from DB (not from raw_data)
                data_type=extraction_type,
                job_id=job_id,
                provider='jira',
                first_item=True,   # Always true for these single-message steps
                last_item=False,    # Always true for these single-message steps
                last_job_item=step_is_last_job_item,  # Always False for these steps (custom_fields is the last step)
                token=token
            )

            if not success:
                logger.error(f"Failed to queue {extraction_type} to transform")
                self._update_job_status(job_id, "FAILED", f"Failed to queue {extraction_type}")
                return False

            logger.info(f"✅ {extraction_type} queued directly to transform (skipped extraction)")

            # Queue next config step (if not the last step) with first_item=True
            # Config job execution order: projects_and_issue_types (1) → statuses_and_relations (2) → wit_hierarchies (3) → wit_mappings (4) → status_mappings (5) → workflows (6) → custom_fields (7 - LAST)
            next_step_map = {
                'config_projects_and_issue_types': 'config_statuses_and_relations',
                'config_statuses_and_relations': 'config_wit_hierarchies',
                'config_wit_hierarchies': 'config_wit_mappings',
                'config_wit_mappings': 'config_status_mappings',
                'config_status_mappings': 'config_workflows',
                'config_workflows': 'config_custom_fields',  # Queue custom fields after workflows
                'config_custom_fields': None  # Last step - no next step
            }

            next_step = next_step_map.get(extraction_type)
            if next_step:
                logger.info(f"📋 Queuing next config step: {next_step}")
                self._queue_next_step(tenant_id, integration_id, job_id, next_step, token, None, True, True, False)

            # Send "extraction finished" status AFTER queuing next step
            await self._send_worker_status("extraction", tenant_id, job_id, "finished", extraction_type)

            return True

        except Exception as e:
            logger.error(f"❌ Error skipping extraction for {extraction_type}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if 'job_id' in locals():
                self._update_job_status(job_id, "FAILED", str(e))
            return False
