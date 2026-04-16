"""
Jira Embedding Worker - Handles embedding generation for all Jira entity types.

Processes embedding requests for:
- Work Items (issues)
- Projects
- Work Item Types (WITs)
- Statuses
- Changelogs
- Work Items-PRs Links
- Mapping Tables (status_mappings, wits_mappings, wits_hierarchies, workflows)

Architecture:
- Fetches entities from database using external_id
- Generates embeddings using HybridProviderManager
- Stores vectors in Qdrant with proper tenant isolation
- Updates qdrant_vectors bridge table
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from sqlalchemy import text

from app.core.utils import DateTimeHelper

from app.core.logging_config import get_logger
from app.core.database import get_database
from app.models.unified_models import (
    WorkItem, Changelog, Project, Status, Wit,
    WorkItemPrLink, WitHierarchy, WitMapping, StatusMapping, Workflow, QdrantVector,
    Sprint, CustomField
)
from app.etl.workers.embedding_worker_router import SOURCE_TYPE_MAPPING

if TYPE_CHECKING:
    from app.etl.workers.worker_status_manager import WorkerStatusManager
    from app.etl.workers.queue_manager import QueueManager

logger = get_logger(__name__)


class JiraEmbeddingWorker:
    """
    Jira Embedding Worker - Processes embedding requests for all Jira entity types.

    Handles:
    - Fetching Jira entities from database
    - Generating embeddings using HybridProviderManager
    - Storing vectors in Qdrant
    - Updating qdrant_vectors bridge table
    """

    def __init__(self, status_manager: Optional['WorkerStatusManager'] = None,
                 queue_manager: Optional['QueueManager'] = None):
        """
        Initialize Jira embedding worker.

        Args:
            status_manager: WorkerStatusManager for sending status updates
            queue_manager: QueueManager for publishing messages (if needed)
        """
        self.status_manager = status_manager
        self.queue_manager = queue_manager
        self.hybrid_provider = None
        self._initialize_hybrid_provider()
        logger.debug("✅ Initialized JiraEmbeddingWorker")

    def _initialize_hybrid_provider(self):
        """Initialize the hybrid provider with a persistent database session."""
        try:
            from app.ai.hybrid_provider_manager import HybridProviderManager
            from app.core.database import get_database

            # Create a persistent database session for the hybrid provider
            # Use read session since initialization mainly reads provider configs
            db = get_database()
            db_session = db.get_read_session()

            self.hybrid_provider = HybridProviderManager(db_session)
            # Note: Providers will be initialized per tenant when processing messages

            logger.debug(f"✅ [JIRA EMBEDDING] Hybrid provider manager created")

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Failed to initialize hybrid provider: {e}")
            raise

    async def cleanup(self):
        """
        Cleanup async resources to prevent event loop errors.

        Called by BaseWorker after processing each message to ensure
        httpx AsyncClient instances are properly closed before event loop closes.
        """
        try:
            if self.hybrid_provider:
                await self.hybrid_provider.cleanup()
                logger.debug("✅ [JIRA EMBEDDING] Hybrid provider cleaned up")
        except Exception as e:
            logger.debug(f"Error during Jira embedding worker cleanup (suppressed): {e}")

    async def _send_worker_status(self, step: str, tenant_id: int, job_id: int,
                                   status: str, step_type: str = None):
        """
        Send worker status update using injected status manager.

        Args:
            step: ETL step name (e.g., 'extraction', 'transform', 'embedding')
            tenant_id: Tenant ID
            job_id: Job ID
            status: Status to send (e.g., 'running', 'finished', 'failed')
            step_type: Optional step type for logging (e.g., 'jira_issues')
        """
        if self.status_manager:
            await self.status_manager.send_worker_status(
                step=step,
                tenant_id=tenant_id,
                job_id=job_id,
                status=status,
                step_type=step_type
            )
        else:
            logger.warning(f"Status manager not available - cannot send {status} status for {step_type}")

    async def process_jira_embedding(self, message: Dict[str, Any]) -> bool:
        """
        Process Jira embedding message (supports both single-entity and batch messages).

        Args:
            message: Embedding message

        Returns:
            bool: True if processed successfully
        """
        try:
            tenant_id = message.get('tenant_id')
            job_id = message.get('job_id')
            step_type = message.get('type')
            table_name = message.get('table_name')
            external_id = message.get('external_id')
            entities = message.get('entities')  # 🔑 NEW: Batch of entities
            first_item = message.get('first_item', False)
            last_item = message.get('last_item', False)
            last_job_item = message.get('last_job_item', False)
            new_last_sync_date = message.get('new_last_sync_date')
            rate_limited = message.get('rate_limited', False)  # 🔑 Rate limit flag from transform

            # Determine if this is a batch message
            # 🔑 Batch messages have external_id='batch' AND entities list
            is_batch = (external_id == 'batch' and entities and len(entities) > 1)
            batch_size = len(entities) if entities else (1 if external_id else 0)

            logger.debug(f"🔍 [JIRA EMBEDDING] Processing: table={table_name}, batch_size={batch_size}, is_batch={is_batch}, external_id={external_id}, step={step_type}, rate_limited={rate_limited}")

            # Handle mapping tables differently - bulk process entire table
            if step_type == 'mappings':
                if not all([tenant_id, table_name]):
                    logger.error(f"❌ [JIRA EMBEDDING] Missing required fields for mappings message")
                    return False

                logger.debug(f"🔄 [JIRA EMBEDDING] Processing entire {table_name} table for tenant {tenant_id}")
                result = await self._process_mapping_table(tenant_id, table_name)

                # 🔑 Send embedding worker "finished" status when last_item=True
                if last_item and job_id:
                    await self._send_worker_status("embedding", tenant_id, job_id, "finished", step_type)
                    logger.debug(f"✅ [JIRA EMBEDDING] Embedding step marked as finished for {table_name} (mappings)")

                # 🔑 Complete ETL job when last_job_item=True (only for successful processing)
                if last_job_item and job_id and result:
                    logger.debug(f"🏁 [JIRA EMBEDDING] Processing last job item - completing ETL job {job_id}")
                    await self.status_manager.complete_etl_job(
                        job_id=job_id,
                        tenant_id=tenant_id,
                        last_sync_date=new_last_sync_date,
                        rate_limited=rate_limited  # 🔑 Forward rate_limited flag
                    )
                    logger.info(f"✅ [JIRA EMBEDDING] ETL job {job_id} marked as FINISHED")

                return result

            # 🚀 Handle batch entity messages (NEW: batch processing)
            # 🔑 Batch messages have external_id='batch' AND entities list with one or more items
            if table_name and external_id == 'batch' and entities and len(entities) >= 1:
                if not tenant_id:
                    logger.error(f"❌ [JIRA EMBEDDING] Missing tenant_id for batch")
                    return False

                logger.info(f"📦 [JIRA EMBEDDING] Processing batch of {len(entities)} {table_name} entities")
                result = await self._process_entity_batch(tenant_id, table_name, entities, message)

                # 🔑 Send embedding worker "finished" status when last_item=True
                # 🔑 IMPORTANT: For sprint reports, check if all batches are completed before sending "finished"
                # With parallel processing, batches may complete out of order
                if last_item and job_id:
                    should_send_finished = True

                    # Special handling for sprint reports - check if all batches are done
                    if table_name == 'sprints':
                        from app.core.database import get_database
                        from sqlalchemy import text

                        database = get_database()
                        with database.get_read_session_context() as db:
                            pending_query = text("""
                                SELECT COUNT(*) as pending_count
                                FROM raw_extraction_data
                                WHERE tenant_id = :tenant_id
                                  AND integration_id = :integration_id
                                  AND type = 'jira_sprint_reports'
                                  AND status != 'completed'
                            """)
                            result_check = db.execute(pending_query, {
                                'tenant_id': tenant_id,
                                'integration_id': message.get('integration_id')
                            }).fetchone()
                            pending_count = result_check[0] if result_check else 0

                        if pending_count > 0:
                            should_send_finished = False
                            logger.info(f"⏳ [SPRINT-REPORTS] {pending_count} embedding batches still pending - NOT sending 'finished' yet")
                        else:
                            logger.info(f"✅ [SPRINT-REPORTS] All embedding batches completed - sending 'finished' status")

                    if should_send_finished:
                        await self._send_worker_status("embedding", tenant_id, job_id, "finished", step_type)
                        logger.debug(f"✅ [JIRA EMBEDDING] Embedding step marked as finished for {table_name} (batch)")

                # Send completion event for custom fields (last_job_item)
                if last_job_item and table_name == 'custom_fields':
                    try:
                        from app.api.websocket_routes import get_custom_fields_websocket_manager
                        cf_ws_manager = get_custom_fields_websocket_manager()
                        await cf_ws_manager.send_completion_event(tenant_id)
                        logger.info(f"✅ [CF-WS] Sent completion event for custom fields - UI will refresh")
                    except Exception as e:
                        logger.warning(f"⚠️ [CF-WS] Failed to send completion event: {e}")

                # 🔑 Complete ETL job when last_job_item=True (only for successful processing)
                if last_job_item and job_id and result:
                    logger.debug(f"🏁 [JIRA EMBEDDING] Processing last job item (batch) - completing ETL job {job_id}")
                    await self.status_manager.complete_etl_job(
                        job_id=job_id,
                        tenant_id=tenant_id,
                        last_sync_date=new_last_sync_date,
                        rate_limited=rate_limited  # 🔑 Forward rate_limited flag
                    )
                    logger.info(f"✅ [JIRA EMBEDDING] ETL job {job_id} marked as FINISHED (batch)")

                return result

            # Handle completion messages - external_id=None signals completion
            # 🔑 Completion messages have external_id=None AND no entities
            if table_name and external_id is None:
                if not tenant_id:
                    logger.error(f"❌ [JIRA EMBEDDING] Missing tenant_id for batch")
                    return False

                # Check if entities is None (completion message) or has data
                entity_count = len(entities) if entities is not None else 0
                logger.info(f"📦 [JIRA EMBEDDING] Processing batch of {entity_count} {table_name} entities")
                result = await self._process_entity_batch(tenant_id, table_name, entities, message)

                # 🔑 Send embedding worker "finished" status when last_item=True
                if last_item and job_id:
                    await self._send_worker_status("embedding", tenant_id, job_id, "finished", step_type)
                    logger.debug(f"✅ [JIRA EMBEDDING] Embedding step marked as finished for {table_name} (batch)")

                # Send completion event for custom fields (last_job_item)
                if last_job_item and table_name == 'custom_fields':
                    try:
                        from app.api.websocket_routes import get_custom_fields_websocket_manager
                        cf_ws_manager = get_custom_fields_websocket_manager()
                        await cf_ws_manager.send_completion_event(tenant_id)
                        logger.info(f"✅ [CF-WS] Sent completion event for custom fields - UI will refresh")
                    except Exception as e:
                        logger.warning(f"⚠️ [CF-WS] Failed to send completion event: {e}")

                # 🔑 Complete ETL job when last_job_item=True (only for successful processing)
                if last_job_item and job_id and result:
                    logger.debug(f"🏁 [JIRA EMBEDDING] Processing last job item (batch) - completing ETL job {job_id}")
                    await self.status_manager.complete_etl_job(
                        job_id=job_id,
                        tenant_id=tenant_id,
                        last_sync_date=new_last_sync_date,
                        rate_limited=rate_limited  # 🔑 Forward rate_limited flag
                    )
                    logger.info(f"✅ [JIRA EMBEDDING] ETL job {job_id} marked as FINISHED (batch)")

                return result

            # Handle individual entity messages (backward compatible)
            if table_name and external_id:
                if not tenant_id:
                    logger.error(f"❌ [JIRA EMBEDDING] Missing tenant_id")
                    return False

                logger.debug(f"🔍 [JIRA EMBEDDING] Fetching entity data for {table_name} ID {external_id}")
                result = await self._process_entity(tenant_id, table_name, external_id, message)

                # 🔑 Send embedding worker "finished" status when last_item=True
                if last_item and job_id:
                    await self._send_worker_status("embedding", tenant_id, job_id, "finished", step_type)
                    logger.debug(f"✅ [JIRA EMBEDDING] Embedding step marked as finished for {table_name}")

                # Send completion event for custom fields (last_job_item)
                if last_job_item and table_name == 'custom_fields':
                    try:
                        from app.api.websocket_routes import get_custom_fields_websocket_manager
                        cf_ws_manager = get_custom_fields_websocket_manager()
                        await cf_ws_manager.send_completion_event(tenant_id)
                        logger.info(f"✅ [CF-WS] Sent completion event for custom fields - UI will refresh")
                    except Exception as e:
                        logger.warning(f"⚠️ [CF-WS] Failed to send completion event: {e}")

                # 🔑 Complete ETL job when last_job_item=True (only for successful processing)
                if last_job_item and job_id and result:
                    logger.debug(f"🏁 [JIRA EMBEDDING] Processing last job item - completing ETL job {job_id}")
                    await self.status_manager.complete_etl_job(
                        job_id=job_id,
                        tenant_id=tenant_id,
                        last_sync_date=new_last_sync_date,
                        rate_limited=rate_limited  # 🔑 Forward rate_limited flag
                    )
                    logger.info(f"✅ [JIRA EMBEDDING] ETL job {job_id} marked as FINISHED")

                return result

            logger.warning(f"⚠️ [JIRA EMBEDDING] Unknown message format")
            return False

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error processing message: {e}")
            import traceback
            logger.error(f"❌ [JIRA EMBEDDING] Full traceback: {traceback.format_exc()}")
            return False

    async def _process_entity(self, tenant_id: int, entity_type: str, entity_id: str, message: Dict[str, Any]) -> bool:
        """Process a single Jira entity for embedding."""
        try:
            # Initialize providers for this tenant if not already done
            if not self.hybrid_provider.providers:
                logger.debug(f"🔄 [JIRA EMBEDDING] Initializing providers for tenant {tenant_id}")
                init_success = await self.hybrid_provider.initialize_providers(tenant_id)
                if not init_success:
                    logger.error(f"❌ [JIRA EMBEDDING] Failed to initialize providers for tenant {tenant_id}")
                    return False

            # Fetch entity data
            entity_data = await self._fetch_entity_data(tenant_id, entity_type, entity_id)
            if not entity_data:
                logger.debug(f"🔍 [JIRA EMBEDDING] Entity not found: {entity_type} ID {entity_id}")
                return True  # Not an error, entity might have been deleted

            # Generate embedding
            text_content = self._extract_text_content(entity_data, entity_type)
            if not text_content:
                logger.debug(f"🔍 [JIRA EMBEDDING] No text content for {entity_type} ID {entity_id}")
                return True  # Not an error, just no content to embed

            # Generate embedding vector
            embedding_result = await self.hybrid_provider.generate_embeddings(
                texts=[text_content],
                tenant_id=tenant_id
            )
            if not embedding_result.success or not embedding_result.data:
                logger.error(f"❌ [JIRA EMBEDDING] Failed to generate embedding: {embedding_result.error}")
                return False

            embedding_vector = embedding_result.data[0]

            # Store in Qdrant and update bridge table
            success = await self._store_embedding(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_data['id'],  # Use internal ID for storage
                embedding_vector=embedding_vector,
                entity_data=entity_data,
                message=message or {}
            )

            if success:
                logger.debug(f"✅ [JIRA EMBEDDING] Successfully processed {entity_type} ID {entity_id}")
            else:
                logger.error(f"❌ [JIRA EMBEDDING] Failed to store embedding for {entity_type} ID {entity_id}")

            return success

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error processing {entity_type} entity {entity_id}: {e}")
            import traceback
            logger.error(f"❌ [JIRA EMBEDDING] Full traceback: {traceback.format_exc()}")
            return False

    async def _process_entity_batch(self, tenant_id: int, entity_type: str, entities: List[Dict[str, Any]], message: Dict[str, Any]) -> bool:
        """
        Process a BATCH of Jira entities for embedding (up to 100 entities).

        This method processes multiple entities in a single operation:
        - 1 database query to fetch all entities (WHERE IN)
        - 1 API call to generate all embeddings (batch_size=100)
        - 1 Qdrant upsert to store all vectors
        - 1 database update to update all bridge table records

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (e.g., 'custom_fields')
            entities: List of entity dicts with 'external_id' keys (can be None for completion messages)
            message: Original message for context

        Returns:
            bool: True if all entities processed successfully
        """
        try:
            # Handle completion messages where entities is None
            if entities is None:
                logger.debug(f"📦 [BATCH-EMBEDDING] Received completion message for {entity_type} (no entities to process)")
                return True

            batch_size = len(entities)
            logger.info(f"📦 [BATCH-EMBEDDING] Processing batch of {batch_size} {entity_type} entities")

            # Initialize providers for this tenant if not already done
            if not self.hybrid_provider.providers:
                logger.debug(f"🔄 [BATCH-EMBEDDING] Initializing providers for tenant {tenant_id}")
                init_success = await self.hybrid_provider.initialize_providers(tenant_id)
                if not init_success:
                    logger.error(f"❌ [BATCH-EMBEDDING] Failed to initialize providers for tenant {tenant_id}")
                    return False

            # Extract external_ids from entities list and fetch from database
            # 🔑 Config tables and link tables use internal 'id' (not external_id from Jira)
            # 🔑 All other tables use 'external_id' from Jira
            # 🔑 statuses uses 'external_id' (like projects and wits) because it comes from Jira
            tables_with_internal_id = ['workflows', 'workflows_steps', 'wits_hierarchies', 'wits_mappings', 'statuses_mappings', 'work_items_prs_links']

            # 🔑 Handle different ID types:
            # - Config tables and link tables: use internal 'id' (converted to appropriate type for database query)
            # - Standard Jira entities (issues, sprints, etc.): use 'external_id' from Jira

            if entity_type in tables_with_internal_id:
                # Config tables and link tables: use internal 'id'
                # Extract as-is (can be int or string depending on source)
                external_ids = [entity.get('id') for entity in entities if entity.get('id')]
            else:
                # Standard Jira entities: use 'external_id'
                external_ids = [entity.get('external_id') for entity in entities if entity.get('external_id')]

            if not external_ids:
                logger.debug(f"📭 [BATCH-EMBEDDING] No valid IDs in batch (entity_type={entity_type}) - likely a flag message for status updates")
                return True

            logger.debug(f"📦 [BATCH-EMBEDDING] Fetching {len(external_ids)} {entity_type} entities from database")

            # Step 1: Fetch all entities in ONE database query
            integration_id = message.get('integration_id')
            entities_data = await self._fetch_entities_batch(tenant_id, entity_type, external_ids, integration_id)
            if not entities_data:
                logger.debug(f"📭 [BATCH-EMBEDDING] No entities found for batch - entities may have been deleted or filtered")
                return True  # Not an error, entities might have been deleted

            logger.debug(f"📦 [BATCH-EMBEDDING] Prepared {len(entities_data)} entities, extracting text content")

            # Step 2: Extract text content from all entities
            texts = []
            entity_ids = []
            valid_entities_data = []

            for entity_data in entities_data:
                text_content = self._extract_text_content(entity_data, entity_type)
                if text_content:
                    texts.append(text_content)
                    entity_ids.append(entity_data['id'])
                    valid_entities_data.append(entity_data)

            if not texts:
                logger.debug(f"🔍 [BATCH-EMBEDDING] No text content for any entities in batch")
                return True  # Not an error, just no content to embed

            logger.info(f"📦 [BATCH-EMBEDDING] Generating {len(texts)} embeddings in ONE API call")

            # Step 3: Generate ALL embeddings in ONE API call
            embedding_result = await self.hybrid_provider.generate_embeddings(
                texts=texts,
                tenant_id=tenant_id
            )
            if not embedding_result.success or not embedding_result.data:
                logger.error(f"❌ [BATCH-EMBEDDING] Failed to generate embeddings: {embedding_result.error}")
                return False

            embeddings = embedding_result.data
            if len(embeddings) != len(texts):
                logger.error(f"❌ [BATCH-EMBEDDING] Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}")
                return False

            logger.info(f"✅ [BATCH-EMBEDDING] Generated {len(embeddings)} embeddings, storing in Qdrant")

            # Step 4: Store ALL embeddings in ONE Qdrant upsert + ONE database update
            success = await self._store_embeddings_batch(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_ids=entity_ids,
                embedding_vectors=embeddings,
                entities_data=valid_entities_data,
                message=message or {}
            )

            if success:
                logger.info(f"✅ [BATCH-EMBEDDING] Successfully processed batch of {len(texts)} {entity_type} entities")
            else:
                logger.error(f"❌ [BATCH-EMBEDDING] Failed to store embeddings for batch")

            return success

        except Exception as e:
            logger.error(f"❌ [BATCH-EMBEDDING] Error processing {entity_type} batch: {e}")
            import traceback
            logger.error(f"❌ [BATCH-EMBEDDING] Full traceback: {traceback.format_exc()}")
            return False

    async def _fetch_entity_data(self, tenant_id: int, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Fetch Jira entity data from database for embedding generation."""
        try:
            logger.debug(f"🔍 [JIRA EMBEDDING] Fetching {entity_type} with external_id={entity_id}, tenant_id={tenant_id}")
            database = get_database()

            # 🔑 Use WRITE session for reads to ensure we read from primary
            with database.get_write_session_context() as session:
                if entity_type == 'work_items':
                    entity = session.query(WorkItem).filter(
                        WorkItem.external_id == str(entity_id),
                        WorkItem.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'key': entity.key,
                            'summary': entity.summary,
                            'description': entity.description,
                            'acceptance_criteria': entity.acceptance_criteria,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'projects':
                    entity = session.query(Project).filter(
                        Project.external_id == str(entity_id),
                        Project.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'key': entity.key,
                            'name': entity.name,
                            # Project model doesn't have description field
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'wits':
                    entity = session.query(Wit).filter(
                        Wit.external_id == str(entity_id),
                        Wit.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.original_name,  # Wit model uses 'original_name'
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'statuses':
                    entity = session.query(Status).filter(
                        Status.external_id == str(entity_id),
                        Status.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.original_name,  # Status model uses 'original_name'
                            'description': entity.description,
                            'category': entity.category,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'changelogs':
                    entity = session.query(Changelog).filter(
                        Changelog.external_id == str(entity_id),
                        Changelog.tenant_id == tenant_id
                    ).first()

                    if entity:
                        # Get status names from relationships
                        from_status_name = entity.from_status.original_name if entity.from_status else None
                        to_status_name = entity.to_status.original_name if entity.to_status else None

                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'changed_by': entity.changed_by,
                            'from_status': from_status_name,
                            'to_status': to_status_name,
                            'transition_change_date': entity.transition_change_date,
                            'time_in_status_seconds': entity.time_in_status_seconds,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'work_items_prs_links':
                    entity = session.query(WorkItemPrLink).filter(
                        WorkItemPrLink.id == int(entity_id),  # This table uses internal ID
                        WorkItemPrLink.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'work_item_id': entity.work_item_id,
                            'external_repo_id': entity.external_repo_id,
                            'repo_full_name': entity.repo_full_name,
                            'pull_request_number': entity.pull_request_number,
                            'branch_name': entity.branch_name,
                            'pr_status': entity.pr_status,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'sprints':
                    entity = session.query(Sprint).filter(
                        Sprint.external_id == str(entity_id),
                        Sprint.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.name,
                            'state': entity.state,
                            'goal': entity.goal,
                            'start_date': entity.start_date,
                            'end_date': entity.end_date,
                            'complete_date': entity.complete_date,
                            'completed_estimate': entity.completed_estimate,
                            'not_completed_estimate': entity.not_completed_estimate,
                            'punted_estimate': entity.punted_estimate,
                            'total_estimate': entity.total_estimate,
                            'completion_percentage': entity.completion_percentage,
                            'velocity': entity.velocity,
                            'scope_change_count': entity.scope_change_count,
                            'carry_over_count': entity.carry_over_count,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'custom_fields':
                    entity = session.query(CustomField).filter(
                        CustomField.external_id == str(entity_id),
                        CustomField.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.name,
                            'field_type': entity.field_type,
                            'operations': entity.operations,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'wits_hierarchies':
                    from app.models.unified_models import WitHierarchy
                    entity = session.query(WitHierarchy).filter(
                        WitHierarchy.id == int(entity_id),  # This table uses internal ID
                        WitHierarchy.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'name': entity.name,
                            'level': entity.level,
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'wits_mappings':
                    from app.models.unified_models import WitMapping
                    entity = session.query(WitMapping).filter(
                        WitMapping.id == int(entity_id),  # This table uses internal ID
                        WitMapping.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'wit_to': entity.wit_to,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'statuses_mappings':
                    from app.models.unified_models import StatusMapping
                    entity = session.query(StatusMapping).filter(
                        StatusMapping.id == int(entity_id),  # This table uses internal ID
                        StatusMapping.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'status_from': entity.status_from,
                            'status_to': entity.status_to,
                            'status_category': entity.status_category.name if entity.status_category else None,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                elif entity_type == 'workflows':
                    from app.models.unified_models import Workflow
                    entity = session.query(Workflow).filter(
                        Workflow.id == int(entity_id),  # This table uses internal ID
                        Workflow.tenant_id == tenant_id
                    ).first()

                    if entity:
                        return {
                            'id': entity.id,
                            'name': entity.name,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        }

                else:
                    logger.warning(f"⚠️ [JIRA EMBEDDING] Unknown entity type: {entity_type}")
                    return None

            return None

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error fetching {entity_type} entity {entity_id}: {e}")
            return None

    async def _fetch_entities_batch(self, tenant_id: int, entity_type: str, external_ids: List[str], integration_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch multiple Jira entities from database in ONE query using WHERE IN.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (e.g., 'custom_fields')
            external_ids: List of external_ids to fetch
            integration_id: Optional integration ID for filtering (required for statuses and other integration-specific entities)

        Returns:
            List of entity data dictionaries
        """
        try:
            logger.debug(f"📦 [BATCH-FETCH] Fetching {len(external_ids)} {entity_type} entities with WHERE IN")
            database = get_database()
            entities_data = []

            # 🔑 Use WRITE session for reads to ensure we read from primary
            with database.get_write_session_context() as session:
                if entity_type == 'custom_fields':
                    from app.models.unified_models import CustomField
                    entities = session.query(CustomField).filter(
                        CustomField.external_id.in_(external_ids),
                        CustomField.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.name,
                            'field_type': entity.field_type,
                            'operations': entity.operations,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'work_items':
                    from app.models.unified_models import WorkItem
                    entities = session.query(WorkItem).filter(
                        WorkItem.external_id.in_(external_ids),
                        WorkItem.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'key': entity.key,
                            'summary': entity.summary,
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'wits_hierarchies':
                    from app.models.unified_models import WitHierarchy
                    # These tables use internal ID, not external_id
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(WitHierarchy).filter(
                        WitHierarchy.id.in_(entity_ids),
                        WitHierarchy.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'name': entity.name,
                            'level': entity.level,
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'wits_mappings':
                    from app.models.unified_models import WitMapping
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(WitMapping).filter(
                        WitMapping.id.in_(entity_ids),
                        WitMapping.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'wit_from': entity.wit_from,
                            'wit_to': entity.wit_to,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'statuses_mappings':
                    from app.models.unified_models import StatusMapping
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(StatusMapping).filter(
                        StatusMapping.id.in_(entity_ids),
                        StatusMapping.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'status_from': entity.status_from,
                            'status_to': entity.status_to,
                            'status_category': entity.status_category.name if entity.status_category else None,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'workflows':
                    from app.models.unified_models import Workflow
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(Workflow).filter(
                        Workflow.id.in_(entity_ids),
                        Workflow.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'name': entity.name,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'workflows_steps':
                    from app.models.unified_models import WorkflowsStep, Workflow, Status
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(
                        WorkflowsStep,
                        Workflow.name.label('workflow_name'),
                        Status.name.label('status_name')
                    ).outerjoin(
                        Workflow, WorkflowsStep.workflow_id == Workflow.id
                    ).outerjoin(
                        Status, WorkflowsStep.status_id == Status.id
                    ).filter(
                        WorkflowsStep.id.in_(entity_ids),
                        WorkflowsStep.tenant_id == tenant_id
                    ).all()

                    for entity, workflow_name, status_name in entities:
                        entities_data.append({
                            'id': entity.id,
                            'workflow_id': entity.workflow_id,
                            'workflow_name': workflow_name,
                            'name': entity.name,
                            'order': entity.order,
                            'status_id': entity.status_id,
                            'status_name': status_name,
                            'is_commitment_point': entity.is_commitment_point,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'projects':
                    from app.models.unified_models import Project
                    entities = session.query(Project).filter(
                        Project.external_id.in_(external_ids),
                        Project.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'key': entity.key,
                            'name': entity.name,
                            'project_type': entity.project_type,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'wits':
                    from app.models.unified_models import Wit
                    entities = session.query(Wit).filter(
                        Wit.external_id.in_(external_ids),
                        Wit.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.original_name,  # Wit model uses 'original_name', not 'name'
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'statuses':
                    from app.models.unified_models import Status
                    # 🔑 Filter by integration_id to ensure we get the correct statuses for this integration
                    filters = [
                        Status.external_id.in_(external_ids),
                        Status.tenant_id == tenant_id
                    ]
                    if integration_id is not None:
                        filters.append(Status.integration_id == integration_id)

                    entities = session.query(Status).filter(*filters).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'original_name': entity.original_name,
                            'original_category': entity.original_category,
                            'description': entity.description,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'changelogs':
                    from app.models.unified_models import Changelog, Status
                    # 🔑 Join with Status table to get status names for text extraction
                    from sqlalchemy.orm import aliased
                    FromStatus = aliased(Status)
                    ToStatus = aliased(Status)

                    results = session.query(
                        Changelog,
                        FromStatus.original_name.label('from_status_name'),
                        ToStatus.original_name.label('to_status_name')
                    ).outerjoin(
                        FromStatus, Changelog.from_status_id == FromStatus.id
                    ).outerjoin(
                        ToStatus, Changelog.to_status_id == ToStatus.id
                    ).filter(
                        Changelog.external_id.in_(external_ids),
                        Changelog.tenant_id == tenant_id
                    ).all()

                    for entity, from_status_name, to_status_name in results:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'work_item_id': entity.work_item_id,
                            'from_status_id': entity.from_status_id,
                            'to_status_id': entity.to_status_id,
                            'from_status': from_status_name,  # 🔑 Status name for text extraction
                            'to_status': to_status_name,  # 🔑 Status name for text extraction
                            'transition_change_date': entity.transition_change_date,
                            'changed_by': entity.changed_by,  # 🔑 Added for text extraction
                            'time_in_status_seconds': entity.time_in_status_seconds,  # 🔑 Added for text extraction
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'sprints':
                    from app.models.unified_models import Sprint
                    entities = session.query(Sprint).filter(
                        Sprint.external_id.in_(external_ids),
                        Sprint.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'external_id': entity.external_id,
                            'name': entity.name,
                            'state': entity.state,
                            'start_date': entity.start_date,
                            'end_date': entity.end_date,
                            'complete_date': entity.complete_date,
                            'goal': entity.goal,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                elif entity_type == 'work_items_prs_links':
                    from app.models.unified_models import WorkItemPrLink
                    # These use internal ID, not external_id
                    entity_ids = [int(eid) for eid in external_ids]
                    entities = session.query(WorkItemPrLink).filter(
                        WorkItemPrLink.id.in_(entity_ids),
                        WorkItemPrLink.tenant_id == tenant_id
                    ).all()

                    for entity in entities:
                        entities_data.append({
                            'id': entity.id,
                            'work_item_id': entity.work_item_id,
                            'external_repo_id': entity.external_repo_id,
                            'repo_full_name': entity.repo_full_name,
                            'pull_request_number': entity.pull_request_number,
                            'branch_name': entity.branch_name,
                            'commit_sha': entity.commit_sha,
                            'pr_status': entity.pr_status,
                            'entity_type': entity_type,
                            'tenant_id': tenant_id
                        })

                else:
                    logger.warning(f"⚠️ [BATCH-FETCH] Batch fetch not implemented for entity type: {entity_type}")
                    return []

            logger.debug(f"✅ [BATCH-FETCH] Fetched {len(entities_data)} {entity_type} entities")
            return entities_data

        except Exception as e:
            logger.error(f"❌ [BATCH-FETCH] Error fetching {entity_type} entities batch: {e}")
            import traceback
            logger.error(f"❌ [BATCH-FETCH] Full traceback: {traceback.format_exc()}")
            return []

    def _extract_text_content(self, entity_data: Dict[str, Any], entity_type: str) -> str:
        """Extract text content from Jira entity data for embedding generation."""
        text_parts = []
        logger.debug(f"🔍 [JIRA EMBEDDING] Extracting text content for {entity_type}: {entity_data}")

        if entity_type == 'work_items':
            if entity_data.get('key'):
                text_parts.append(f"Key: {entity_data['key']}")
            if entity_data.get('summary'):
                text_parts.append(f"Summary: {entity_data['summary']}")
            if entity_data.get('description'):
                text_parts.append(f"Description: {entity_data['description']}")
            if entity_data.get('acceptance_criteria'):
                text_parts.append(f"Acceptance Criteria: {entity_data['acceptance_criteria']}")

        elif entity_type == 'projects':
            if entity_data.get('key'):
                text_parts.append(f"Key: {entity_data['key']}")
            if entity_data.get('name'):
                text_parts.append(f"Name: {entity_data['name']}")
            if entity_data.get('description'):
                text_parts.append(f"Description: {entity_data['description']}")

        elif entity_type == 'wits':
            if entity_data.get('name'):
                text_parts.append(f"Work Item Type: {entity_data['name']}")
            if entity_data.get('description'):
                text_parts.append(f"Description: {entity_data['description']}")

        elif entity_type == 'statuses':
            # Status model uses 'original_name' and 'original_category', not 'name' and 'category'
            if entity_data.get('original_name'):
                text_parts.append(f"Status: {entity_data['original_name']}")
            if entity_data.get('original_category'):
                text_parts.append(f"Category: {entity_data['original_category']}")
            if entity_data.get('description'):
                text_parts.append(f"Description: {entity_data['description']}")

        elif entity_type == 'changelogs':
            # Changelogs track status transitions
            if entity_data.get('changed_by'):
                text_parts.append(f"Changed By: {entity_data['changed_by']}")
            if entity_data.get('from_status'):
                text_parts.append(f"From Status: {entity_data['from_status']}")
            if entity_data.get('to_status'):
                text_parts.append(f"To Status: {entity_data['to_status']}")
            if entity_data.get('time_in_status_seconds'):
                text_parts.append(f"Time in Status: {entity_data['time_in_status_seconds']} seconds")

        elif entity_type == 'work_items_prs_links':
            # Work item to PR link information
            if entity_data.get('work_item_id'):
                text_parts.append(f"Work Item ID: {entity_data['work_item_id']}")
            if entity_data.get('repo_full_name'):
                text_parts.append(f"Repository: {entity_data['repo_full_name']}")
            if entity_data.get('pull_request_number'):
                text_parts.append(f"PR Number: {entity_data['pull_request_number']}")
            if entity_data.get('branch_name'):
                text_parts.append(f"Branch: {entity_data['branch_name']}")
            if entity_data.get('pr_status'):
                text_parts.append(f"PR Status: {entity_data['pr_status']}")

        elif entity_type == 'sprints':
            # Sprint information with metrics
            if entity_data.get('name'):
                text_parts.append(f"Sprint: {entity_data['name']}")
            if entity_data.get('state'):
                text_parts.append(f"State: {entity_data['state']}")
            if entity_data.get('goal'):
                text_parts.append(f"Goal: {entity_data['goal']}")
            if entity_data.get('velocity'):
                text_parts.append(f"Velocity: {entity_data['velocity']}")
            if entity_data.get('completion_percentage'):
                text_parts.append(f"Completion: {entity_data['completion_percentage']}%")
            if entity_data.get('scope_change_count'):
                text_parts.append(f"Scope Changes: {entity_data['scope_change_count']}")
            if entity_data.get('carry_over_count'):
                text_parts.append(f"Carry Over Items: {entity_data['carry_over_count']}")

        # Mapping tables
        elif entity_type == 'wits_hierarchies':
            if entity_data.get('name'):
                text_parts.append(f"Name: {entity_data['name']}")
            if entity_data.get('level'):
                text_parts.append(f"Level: {entity_data['level']}")
            if entity_data.get('description'):
                text_parts.append(f"Description: {entity_data['description']}")

        elif entity_type == 'wits_mappings':
            if entity_data.get('wit_from'):
                text_parts.append(f"WIT From: {entity_data['wit_from']}")
            if entity_data.get('wit_to'):
                text_parts.append(f"WIT To: {entity_data['wit_to']}")

        elif entity_type == 'statuses_mappings':
            if entity_data.get('status_from'):
                text_parts.append(f"Status From: {entity_data['status_from']}")
            if entity_data.get('status_to'):
                text_parts.append(f"Status To: {entity_data['status_to']}")
            if entity_data.get('status_category'):
                text_parts.append(f"Status Category: {entity_data['status_category']}")

        elif entity_type == 'workflows':
            if entity_data.get('name'):
                text_parts.append(f"Workflow: {entity_data['name']}")

        elif entity_type == 'workflows_steps':
            if entity_data.get('workflow_name'):
                text_parts.append(f"Workflow: {entity_data['workflow_name']}")
            if entity_data.get('name'):
                text_parts.append(f"Step: {entity_data['name']}")
            if entity_data.get('order'):
                text_parts.append(f"Order: {entity_data['order']}")
            if entity_data.get('status_name'):
                text_parts.append(f"Status: {entity_data['status_name']}")
            if entity_data.get('is_commitment_point'):
                text_parts.append(f"Commitment Point: Yes")

        elif entity_type == 'custom_fields':
            if entity_data.get('name'):
                text_parts.append(f"Custom Field: {entity_data['name']}")
            if entity_data.get('external_id'):
                text_parts.append(f"Field ID: {entity_data['external_id']}")
            if entity_data.get('field_type'):
                text_parts.append(f"Type: {entity_data['field_type']}")
            if entity_data.get('operations'):
                text_parts.append(f"Operations: {entity_data['operations']}")

        result = " ".join(text_parts)
        logger.debug(f"✅ [JIRA EMBEDDING] Extracted text for {entity_type}: {result[:100] if result else 'EMPTY'}")
        return result

    async def _store_embedding(self, tenant_id: int, entity_type: str, entity_id: int,
                               embedding_vector: list, entity_data: Dict[str, Any], message: Dict[str, Any]) -> bool:
        """Store embedding in Qdrant and update qdrant_vectors bridge table."""
        try:
            # Store in Qdrant (tenant-isolated collection)
            qdrant_success = await self._store_in_qdrant(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                embedding_vector=embedding_vector,
                entity_data=entity_data
            )

            if not qdrant_success:
                logger.error(f"❌ [JIRA EMBEDDING] Failed to store in Qdrant")
                return False

            # Update qdrant_vectors bridge table
            bridge_success = await self._update_bridge_table(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                message=message
            )

            if not bridge_success:
                logger.error(f"❌ [JIRA EMBEDDING] Failed to update bridge table")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error storing embedding: {e}")
            import traceback
            logger.error(f"❌ [JIRA EMBEDDING] Full traceback: {traceback.format_exc()}")
            return False

    async def _store_embeddings_batch(self, tenant_id: int, entity_type: str, entity_ids: List[int],
                                      embedding_vectors: List[List[float]], entities_data: List[Dict[str, Any]],
                                      message: Dict[str, Any]) -> bool:
        """
        Store multiple embeddings in Qdrant and update bridge table in ONE operation.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (e.g., 'custom_fields')
            entity_ids: List of internal entity IDs
            embedding_vectors: List of embedding vectors (same order as entity_ids)
            entities_data: List of entity data dicts (same order as entity_ids)
            message: Original message for context

        Returns:
            bool: True if all embeddings stored successfully
        """
        try:
            batch_size = len(entity_ids)
            logger.info(f"📦 [BATCH-STORE] Storing {batch_size} embeddings in Qdrant + bridge table")

            # Store in Qdrant (ONE batch upsert)
            qdrant_success = await self._store_in_qdrant_batch(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_ids=entity_ids,
                embedding_vectors=embedding_vectors,
                entities_data=entities_data
            )

            if not qdrant_success:
                logger.error(f"❌ [BATCH-STORE] Failed to store batch in Qdrant")
                return False

            # Update qdrant_vectors bridge table (ONE bulk update)
            bridge_success = await self._update_bridge_table_batch(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_ids=entity_ids,
                message=message
            )

            if not bridge_success:
                logger.error(f"❌ [BATCH-STORE] Failed to update bridge table batch")
                return False

            logger.info(f"✅ [BATCH-STORE] Successfully stored {batch_size} embeddings")
            return True

        except Exception as e:
            logger.error(f"❌ [BATCH-STORE] Error storing embeddings batch: {e}")
            import traceback
            logger.error(f"❌ [BATCH-STORE] Full traceback: {traceback.format_exc()}")
            return False

    async def _store_in_qdrant(self, tenant_id: int, entity_type: str, entity_id: int,
                               embedding_vector: List[float], entity_data: Dict[str, Any]) -> bool:
        """Store embedding vector in Qdrant with tenant isolation."""
        try:
            logger.debug(f"🔄 [JIRA EMBEDDING] Storing embedding in Qdrant for {entity_type}_{entity_id}")
            # Use PulseQdrantClient to store in Qdrant
            from app.ai.qdrant_client import PulseQdrantClient

            qdrant_client = PulseQdrantClient()
            await qdrant_client.initialize()
            logger.debug(f"✅ [JIRA EMBEDDING] Qdrant client initialized")

            # Use entity_type directly as collection name (should always be database table name now)
            collection_name = f"tenant_{tenant_id}_{entity_type}"

            # Create deterministic UUID for point ID (Qdrant requires UUID or unsigned integer)
            unique_string = f"{tenant_id}_{entity_type}_{entity_id}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

            payload = {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'tenant_id': tenant_id,
                'source_type': SOURCE_TYPE_MAPPING.get(entity_type, 'UNKNOWN'),
                'created_at': DateTimeHelper.now_default().isoformat(),
                **entity_data  # Include entity data in payload
            }

            # Ensure collection exists
            await qdrant_client.ensure_collection_exists(
                collection_name=collection_name,
                vector_size=len(embedding_vector)
            )

            # Store using PulseQdrantClient
            result = await qdrant_client.upsert_vectors(
                collection_name=collection_name,
                vectors=[{
                    'id': point_id,
                    'vector': embedding_vector,
                    'payload': payload
                }]
            )

            if result.success:
                logger.debug(f"✅ [JIRA EMBEDDING] Stored vector in Qdrant: {point_id}")
                return True
            else:
                logger.error(f"❌ [JIRA EMBEDDING] Failed to store vector in Qdrant: {point_id} - {result.error}")
                return False

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error storing in Qdrant: {e}")
            return False

    async def _update_bridge_table(self, tenant_id: int, entity_type: str, entity_id: int, message: Dict[str, Any]) -> bool:
        """Update qdrant_vectors bridge table to track stored vectors."""
        try:
            from app.models.unified_models import QdrantVector, Integration
            database = get_database()

            # Get source_type from SOURCE_TYPE_MAPPING
            source_type = SOURCE_TYPE_MAPPING.get(entity_type, 'UNKNOWN')

            # Get integration_id from message or lookup
            integration_id = message.get('integration_id')
            if integration_id is None:
                integration_id = await self._get_integration_id_for_source_type(tenant_id, source_type)
                if integration_id is None:
                    logger.error(f"❌ [JIRA EMBEDDING] No integration_id found for {source_type} in tenant {tenant_id}")
                    return False

            # Generate the same point ID as used in Qdrant storage
            unique_string = f"{tenant_id}_{entity_type}_{entity_id}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

            with database.get_write_session_context() as session:
                # Check if record already exists (must match unique constraint)
                existing = session.query(QdrantVector).filter(
                    QdrantVector.source_type == source_type,
                    QdrantVector.table_name == entity_type,
                    QdrantVector.record_id == entity_id,
                    QdrantVector.tenant_id == tenant_id,
                    QdrantVector.vector_type == 'content'
                ).first()

                if existing:
                    # Update existing record
                    existing.active = True
                    existing.last_updated_at = DateTimeHelper.now_default()
                    existing.qdrant_point_id = point_id
                    logger.debug(f"✅ [JIRA EMBEDDING] Updated bridge table: {entity_type} ID {entity_id}")
                else:
                    # Create new record
                    new_vector = QdrantVector(
                        source_type=source_type,
                        table_name=entity_type,
                        record_id=entity_id,
                        qdrant_collection=f"tenant_{tenant_id}_{entity_type}",
                        qdrant_point_id=point_id,
                        vector_type='content',
                        integration_id=integration_id,
                        tenant_id=tenant_id,
                        active=True,
                        created_at=DateTimeHelper.now_default(),
                        last_updated_at=DateTimeHelper.now_default()
                    )
                    session.add(new_vector)
                    logger.debug(f"✅ [JIRA EMBEDDING] Inserted into bridge table: {entity_type} ID {entity_id}")

                session.commit()
                return True

        except Exception as e:
            # Handle race condition: another worker may have inserted the same record
            from psycopg2.errors import UniqueViolation
            if isinstance(e.__cause__, UniqueViolation) or 'duplicate key' in str(e).lower():
                logger.debug(f"ℹ️ [JIRA EMBEDDING] Record already exists (race condition handled): {entity_type}_{entity_id}")
                return True

            logger.error(f"❌ [JIRA EMBEDDING] Error updating bridge table: {e}")
            return False

    async def _store_in_qdrant_batch(self, tenant_id: int, entity_type: str, entity_ids: List[int],
                                     embedding_vectors: List[List[float]], entities_data: List[Dict[str, Any]]) -> bool:
        """
        Store multiple embedding vectors in Qdrant in ONE batch upsert.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (e.g., 'custom_fields')
            entity_ids: List of internal entity IDs
            embedding_vectors: List of embedding vectors (same order as entity_ids)
            entities_data: List of entity data dicts (same order as entity_ids)

        Returns:
            bool: True if batch stored successfully
        """
        try:
            batch_size = len(entity_ids)
            logger.info(f"📦 [BATCH-QDRANT] Storing {batch_size} vectors in Qdrant (ONE batch upsert)")

            from app.ai.qdrant_client import PulseQdrantClient
            import uuid

            qdrant_client = PulseQdrantClient()
            await qdrant_client.initialize()

            collection_name = f"tenant_{tenant_id}_{entity_type}"

            # Build batch of vectors for Qdrant
            vectors_batch = []
            for i, (entity_id, embedding_vector, entity_data) in enumerate(zip(entity_ids, embedding_vectors, entities_data)):
                # Create deterministic UUID for point ID
                unique_string = f"{tenant_id}_{entity_type}_{entity_id}"
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

                payload = {
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'tenant_id': tenant_id,
                    'source_type': SOURCE_TYPE_MAPPING.get(entity_type, 'UNKNOWN'),
                    'created_at': DateTimeHelper.now_default().isoformat(),
                    **entity_data  # Include entity data in payload
                }

                vectors_batch.append({
                    'id': point_id,
                    'vector': embedding_vector,
                    'payload': payload
                })

            # Ensure collection exists
            await qdrant_client.ensure_collection_exists(
                collection_name=collection_name,
                vector_size=len(embedding_vectors[0])
            )

            # Store using PulseQdrantClient (ONE batch upsert)
            result = await qdrant_client.upsert_vectors(
                collection_name=collection_name,
                vectors=vectors_batch
            )

            if result.success:
                logger.info(f"✅ [BATCH-QDRANT] Stored {batch_size} vectors in Qdrant")
                return True
            else:
                logger.error(f"❌ [BATCH-QDRANT] Failed to store vectors batch: {result.error}")
                return False

        except Exception as e:
            logger.error(f"❌ [BATCH-QDRANT] Error storing batch in Qdrant: {e}")
            import traceback
            logger.error(f"❌ [BATCH-QDRANT] Full traceback: {traceback.format_exc()}")
            return False

    async def _update_bridge_table_batch(self, tenant_id: int, entity_type: str, entity_ids: List[int], message: Dict[str, Any]) -> bool:
        """
        Update qdrant_vectors bridge table for multiple entities in ONE bulk operation.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type (e.g., 'custom_fields')
            entity_ids: List of internal entity IDs
            message: Original message for context

        Returns:
            bool: True if batch updated successfully
        """
        try:
            batch_size = len(entity_ids)
            logger.info(f"📦 [BATCH-BRIDGE] Updating {batch_size} bridge table records")

            from app.models.unified_models import QdrantVector, Integration
            import uuid
            database = get_database()

            # Get source_type from SOURCE_TYPE_MAPPING
            source_type = SOURCE_TYPE_MAPPING.get(entity_type, 'UNKNOWN')

            # Get integration_id from message or lookup
            integration_id = message.get('integration_id')
            if integration_id is None:
                integration_id = await self._get_integration_id_for_source_type(tenant_id, source_type)
                if integration_id is None:
                    logger.error(f"❌ [BATCH-BRIDGE] No integration_id found for {source_type} in tenant {tenant_id}")
                    return False

            with database.get_write_session_context() as session:
                # For each entity, upsert into bridge table
                for entity_id in entity_ids:
                    # Generate the same point ID as used in Qdrant storage
                    unique_string = f"{tenant_id}_{entity_type}_{entity_id}"
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

                    # Check if record already exists
                    existing = session.query(QdrantVector).filter(
                        QdrantVector.source_type == source_type,
                        QdrantVector.table_name == entity_type,
                        QdrantVector.record_id == entity_id,
                        QdrantVector.tenant_id == tenant_id,
                        QdrantVector.vector_type == 'content'
                    ).first()

                    if existing:
                        # Update existing record
                        existing.active = True
                        existing.last_updated_at = DateTimeHelper.now_default()
                        existing.qdrant_point_id = point_id
                    else:
                        # Create new record
                        new_vector = QdrantVector(
                            source_type=source_type,
                            table_name=entity_type,
                            record_id=entity_id,
                            qdrant_collection=f"tenant_{tenant_id}_{entity_type}",
                            qdrant_point_id=point_id,
                            vector_type='content',
                            integration_id=integration_id,
                            tenant_id=tenant_id,
                            active=True,
                            created_at=DateTimeHelper.now_default(),
                            last_updated_at=DateTimeHelper.now_default()
                        )
                        session.add(new_vector)

                session.commit()
                logger.info(f"✅ [BATCH-BRIDGE] Updated {batch_size} bridge table records")
                return True

        except Exception as e:
            logger.error(f"❌ [BATCH-BRIDGE] Error updating bridge table batch: {e}")
            import traceback
            logger.error(f"❌ [BATCH-BRIDGE] Full traceback: {traceback.format_exc()}")
            return False

    async def _get_integration_id_for_source_type(self, tenant_id: int, source_type: str) -> Optional[int]:
        """Get the integration_id for a given source_type (JIRA or GITHUB)."""
        try:
            from app.models.unified_models import Integration
            database = get_database()

            with database.get_read_session_context() as session:
                # Map source_type to provider name
                provider_mapping = {
                    'JIRA': 'Jira',
                    'GITHUB': 'GitHub'
                }
                provider_name = provider_mapping.get(source_type)

                if not provider_name:
                    logger.error(f"❌ [JIRA EMBEDDING] Unknown source_type: {source_type}")
                    return None

                # Find the integration for this tenant and provider
                integration = session.query(Integration).filter(
                    Integration.tenant_id == tenant_id,
                    Integration.provider == provider_name,
                    Integration.active == True
                ).first()

                if integration:
                    return integration.id
                else:
                    logger.error(f"❌ [JIRA EMBEDDING] No active {provider_name} integration found for tenant {tenant_id}")
                    return None

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error getting integration_id: {e}")
            return None

    async def _process_mapping_table(self, tenant_id: int, table_name: str) -> bool:
        """Process an entire Jira mapping table for embedding."""
        try:
            # Initialize providers for this tenant if not already done
            if not self.hybrid_provider:
                from app.ai.hybrid_provider_manager import HybridProviderManager
                self.hybrid_provider = HybridProviderManager()

            if not self.hybrid_provider.providers:
                if not await self.hybrid_provider.initialize_providers(tenant_id):
                    logger.error(f"❌ [JIRA EMBEDDING] Failed to initialize providers for tenant {tenant_id}")
                    return False

            database = get_database()

            # Map table names to model classes
            table_models = {
                'statuses_mappings': StatusMapping,
                'wits_mappings': WitMapping,
                'wits_hierarchies': WitHierarchy,
                'workflows': Workflow
            }

            if table_name not in table_models:
                logger.error(f"❌ [JIRA EMBEDDING] Unknown mapping table: {table_name}")
                return False

            model_class = table_models[table_name]

            # 🔑 Use WRITE session for mapping tables
            with database.get_write_session_context() as session:
                # Get all records from the table for this tenant
                records = session.query(model_class).filter(
                    model_class.tenant_id == tenant_id
                ).all()

                logger.debug(f"🔄 [JIRA EMBEDDING] Found {len(records)} records in {table_name} for tenant {tenant_id}")

                if not records:
                    logger.debug(f"✅ [JIRA EMBEDDING] No records to process in {table_name}")
                    return True

                # Process each record with rate limiting
                success_count = 0
                for i, record in enumerate(records):
                    try:
                        # Add rate limiting - delay every 5 records
                        if i > 0 and i % 5 == 0:
                            logger.debug(f"🔄 [JIRA EMBEDDING] Rate limiting - processed {i}/{len(records)} records, pausing...")
                            await asyncio.sleep(5)

                        # Create entity data based on table type
                        entity_data = self._create_mapping_entity_data(record, table_name)

                        # Generate embedding
                        text_content = self._extract_text_content(entity_data, table_name)
                        if not text_content:
                            logger.debug(f"🔍 [JIRA EMBEDDING] No text content for {table_name} ID {record.id}")
                            continue

                        embedding_result = await self.hybrid_provider.generate_embeddings(
                            texts=[text_content],
                            tenant_id=tenant_id
                        )
                        if not embedding_result.success or not embedding_result.data:
                            logger.warning(f"⚠️ [JIRA EMBEDDING] Failed to generate embedding for {table_name} ID {record.id}")
                            continue

                        embedding_vector = embedding_result.data[0]

                        # Store embedding
                        success = await self._store_embedding(
                            tenant_id=tenant_id,
                            entity_type=table_name,
                            entity_id=record.id,
                            embedding_vector=embedding_vector,
                            entity_data=entity_data,
                            message={'tenant_id': tenant_id, 'table_name': table_name, 'type': 'mappings'}
                        )

                        if success:
                            success_count += 1
                            if success_count % 20 == 0:
                                logger.debug(f"🔄 [JIRA EMBEDDING] Progress {success_count}/{len(records)} records embedded for {table_name}")
                        else:
                            logger.warning(f"⚠️ [JIRA EMBEDDING] Failed to embed {table_name} ID {record.id}")

                    except Exception as e:
                        logger.error(f"❌ [JIRA EMBEDDING] Error processing {table_name} ID {record.id}: {e}")

                logger.info(f"✅ [JIRA EMBEDDING] Successfully embedded {success_count}/{len(records)} records from {table_name}")
                return success_count > 0

        except Exception as e:
            logger.error(f"❌ [JIRA EMBEDDING] Error processing mapping table {table_name}: {e}")
            return False

    def _create_mapping_entity_data(self, record, table_name: str) -> Dict[str, Any]:
        """Create entity data dictionary from mapping table record."""
        base_data = {
            'id': record.id,
            'tenant_id': record.tenant_id,
            'entity_type': table_name
        }

        if table_name == 'wits_hierarchies':
            base_data.update({
                'name': record.name,
                'level': record.level,
                'description': record.description
            })
        elif table_name == 'wits_mappings':
            base_data.update({
                'wit_from': record.wit_from,
                'wit_to': record.wit_to
            })
        elif table_name == 'statuses_mappings':
            base_data.update({
                'status_from': record.status_from,
                'status_to': record.status_to,
                'status_category': record.status_category.name if record.status_category else None
            })
        elif table_name == 'workflows':
            base_data.update({
                'name': record.name
            })
        elif table_name == 'workflows_steps':
            # Get workflow and status names via relationships
            workflow_name = record.workflow.name if record.workflow else None
            status_name = record.status.name if record.status else None

            base_data.update({
                'workflow_id': record.workflow_id,
                'workflow_name': workflow_name,
                'name': record.name,
                'order': record.order,
                'status_id': record.status_id,
                'status_name': status_name,
                'is_commitment_point': record.is_commitment_point
            })

        return base_data