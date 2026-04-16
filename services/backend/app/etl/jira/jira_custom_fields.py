"""
ETL Custom Fields API
Handles custom field mapping and discovery for Jira integrations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
import os

from app.core.database import get_db_session
from app.auth.auth_middleware import require_authentication, UserData
from app.models.unified_models import Integration

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class CustomFieldMappingResponse:
    """Response model for custom field mappings"""
    def __init__(self, custom_field_mappings: Dict[str, Any], available_columns: List[str], mapped_columns: List[str]):
        self.custom_field_mappings = custom_field_mappings
        self.available_columns = available_columns
        self.mapped_columns = mapped_columns


# ============================================================================
# Helper Functions
# ============================================================================

def get_available_custom_field_columns() -> List[str]:
    """Get list of available custom field columns (custom_field_01 through custom_field_20)"""
    return [f"custom_field_{i:02d}" for i in range(1, 21)]


def get_mapped_columns_from_config(custom_field_mappings: Dict[str, Any]) -> List[str]:
    """Extract mapped columns from custom field mappings configuration"""
    mapped_columns = []
    for field_id, config in custom_field_mappings.items():
        if isinstance(config, dict) and config.get('mapped_column'):
            mapped_columns.append(config['mapped_column'])
    return mapped_columns


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/custom-fields/mappings/{integration_id}")
async def get_custom_field_mappings(
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Get custom field mappings for a specific integration.
    Returns the current mappings configuration and available columns.
    """
    try:
        # Get integration and verify access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Get custom field mappings from integration configuration
        custom_field_mappings = integration.custom_field_mappings or {}

        # Ensure custom_field_mappings is a dict
        if not isinstance(custom_field_mappings, dict):
            custom_field_mappings = {}

        # Get available and mapped columns
        available_columns = get_available_custom_field_columns()
        mapped_columns = get_mapped_columns_from_config(custom_field_mappings)
        
        return {
            "success": True,
            "custom_field_mappings": custom_field_mappings,
            "available_columns": available_columns,
            "mapped_columns": mapped_columns,
            "integration_id": integration_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting custom field mappings for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get custom field mappings")


@router.put("/custom-fields/mappings/{integration_id}")
async def update_custom_field_mappings(
    integration_id: int,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Update custom field mappings for a specific integration.
    Saves the mappings configuration to the integration record.
    """
    try:
        # Get integration and verify access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Extract custom field mappings from request
        custom_field_mappings = request_data.get('custom_field_mappings', {})
        
        # Validate mappings format
        available_columns = get_available_custom_field_columns()
        for field_id, config in custom_field_mappings.items():
            if isinstance(config, dict):
                mapped_column = config.get('mapped_column')
                if mapped_column and mapped_column != 'overflow' and mapped_column not in available_columns:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid mapped column: {mapped_column}. Must be one of {available_columns} or 'overflow'"
                    )
        
        # Update integration with new mappings
        integration.custom_field_mappings = custom_field_mappings
        db.commit()
        
        logger.info(f"Updated custom field mappings for integration {integration_id}")
        
        return {
            "success": True,
            "message": "Custom field mappings updated successfully",
            "integration_id": integration_id,
            "mappings_count": len(custom_field_mappings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom field mappings for integration {integration_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update custom field mappings")


@router.get("/custom-fields/list/{integration_id}")
async def list_custom_fields(
    integration_id: int,
    only_available: bool = False,  # NEW: Filter to show only fields available in user's projects
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Get list of custom fields from custom_fields table for a specific integration.
    Returns all discovered custom fields with project availability information.

    Args:
        integration_id: Integration ID
        only_available: If True, only return fields that are available in at least one project
    """
    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Query custom_fields table with project relationships
        from app.models.unified_models import CustomField, CustomFieldProject, Project
        from sqlalchemy import func
        from sqlalchemy.orm import aliased

        # Build query with left join to get project availability
        query = db.query(
            CustomField.id,
            CustomField.external_id,
            CustomField.name,
            CustomField.field_type,
            CustomField.operations,
            func.count(CustomFieldProject.project_id).label('project_count')
        ).outerjoin(
            CustomFieldProject,
            CustomFieldProject.custom_field_id == CustomField.id
        ).filter(
            CustomField.integration_id == integration_id,
            CustomField.tenant_id == user.tenant_id,
            CustomField.active == True
        ).group_by(
            CustomField.id,
            CustomField.external_id,
            CustomField.name,
            CustomField.field_type,
            CustomField.operations
        )

        # Apply filter if only_available is True
        if only_available:
            query = query.having(func.count(CustomFieldProject.project_id) > 0)

        query = query.order_by(CustomField.name)
        results = query.all()

        # PERFORMANCE FIX: Fetch ALL project relationships in a single query
        # instead of N separate queries (one per custom field)
        field_ids = [result[0] for result in results]

        # Get all project relationships for all custom fields in one query
        all_project_relationships = db.query(
            CustomFieldProject.custom_field_id,
            Project.key,
            Project.name
        ).join(
            Project,
            CustomFieldProject.project_id == Project.id
        ).filter(
            CustomFieldProject.custom_field_id.in_(field_ids),
            Project.active == True
        ).all()

        # Group project relationships by custom_field_id
        from collections import defaultdict
        projects_by_field = defaultdict(list)
        for rel in all_project_relationships:
            projects_by_field[rel[0]].append({
                "project_key": rel[1],
                "project_name": rel[2],
                "issue_types": []  # Issue types info removed from junction table
            })

        # Build the final fields list
        fields_list = []
        for result in results:
            field_id = result[0]
            available_in_projects = projects_by_field.get(field_id, [])

            fields_list.append({
                "id": result[0],
                "external_id": result[1],
                "name": result[2],
                "field_type": result[3],
                "operations": result[4] or [],
                "project_count": result[5],
                "is_available": result[5] > 0,
                "available_in_projects": available_in_projects
            })

        return {
            "success": True,
            "custom_fields": fields_list,
            "total_count": len(fields_list),
            "integration_id": integration_id,
            "filters": {
                "only_available": only_available
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching custom fields for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch custom fields")


@router.get("/custom-fields/mappings-table/{integration_id}")
async def get_custom_field_mappings_table(
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Get custom field mappings from custom_fields_mappings table.
    Simple database read operation - returns raw values from the table.
    """
    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Query custom_fields_mapping table
        from app.models.unified_models import CustomFieldMapping

        mapping_record = db.query(CustomFieldMapping).filter(
            CustomFieldMapping.integration_id == integration_id,
            CustomFieldMapping.tenant_id == user.tenant_id,
            CustomFieldMapping.active == True
        ).first()

        # Build response with special fields + 20 custom field mappings
        # Simply return what's in the database, no auto-mapping logic
        mappings = {}
        if mapping_record:
            # Special fields
            mappings['team_field'] = mapping_record.team_field_id
            mappings['sprints_field'] = mapping_record.sprints_field_id
            mappings['development_field'] = mapping_record.development_field_id
            mappings['story_points_field'] = mapping_record.story_points_field_id
            mappings['acceptance_criteria_field'] = mapping_record.acceptance_criteria_field_id

            # 20 custom fields
            for i in range(1, 21):
                field_key = f"custom_field_{i:02d}"
                field_id_attr = f"custom_field_{i:02d}_id"
                field_id = getattr(mapping_record, field_id_attr, None)
                mappings[field_key] = field_id
        else:
            # No mapping record exists yet, return empty mappings
            mappings['team_field'] = None
            mappings['sprints_field'] = None
            mappings['development_field'] = None
            mappings['story_points_field'] = None
            mappings['acceptance_criteria_field'] = None

            for i in range(1, 21):
                field_key = f"custom_field_{i:02d}"
                mappings[field_key] = None

        return {
            "success": True,
            "mappings": mappings,
            "integration_id": integration_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching custom field mappings table for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch custom field mappings")


@router.put("/custom-fields/mappings-table/{integration_id}")
async def update_custom_field_mappings_table(
    integration_id: int,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Update custom field mappings in custom_fields_mappings table.
    Expects mappings in format: { "custom_field_01": 123, "custom_field_02": 456, ... }
    """
    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Get mappings from request
        mappings = request_data.get('mappings', {})

        # Query or create custom_fields_mappings record
        from app.models.unified_models import CustomFieldMapping

        mapping_record = db.query(CustomFieldMapping).filter(
            CustomFieldMapping.integration_id == integration_id,
            CustomFieldMapping.tenant_id == user.tenant_id
        ).first()

        if not mapping_record:
            # Create new mapping record
            mapping_record = CustomFieldMapping(
                integration_id=integration_id,
                tenant_id=user.tenant_id,
                active=True
            )
            db.add(mapping_record)

        # Update special fields
        mapping_record.team_field_id = mappings.get('team_field')
        mapping_record.sprints_field_id = mappings.get('sprints_field')
        mapping_record.development_field_id = mappings.get('development_field')
        mapping_record.story_points_field_id = mappings.get('story_points_field')
        mapping_record.acceptance_criteria_field_id = mappings.get('acceptance_criteria_field')

        # Update all 20 custom field mappings
        for i in range(1, 21):
            field_key = f"custom_field_{i:02d}"
            field_id_attr = f"custom_field_{i:02d}_id"
            field_id = mappings.get(field_key)
            setattr(mapping_record, field_id_attr, field_id)

        db.commit()

        logger.info(f"Updated custom field mappings table for integration {integration_id}")

        return {
            "success": True,
            "message": "Custom field mappings updated successfully",
            "integration_id": integration_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom field mappings table for integration {integration_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update custom field mappings")


@router.get("/custom-fields/version-check")
async def version_check():
    """Simple endpoint to verify the updated code is loaded"""
    return {"version": "fixed_single_record_v2", "message": "Updated code loaded successfully"}

@router.post("/custom-fields/sync/{integration_id}")
async def sync_custom_fields(
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Trigger custom field sync for an integration using Jira createmeta API.
    Similar to ETL jobs, this will request Jira data, extract custom fields, and queue for processing.
    """
    logger.info(f"Starting custom fields sync for integration {integration_id}, user: {user.user_id}, tenant: {user.tenant_id}")

    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Only support Jira integrations
        if integration.provider.lower() != 'jira':
            raise HTTPException(status_code=400, detail="Custom field sync only supported for Jira integrations")

        # Get project keys from integration settings
        settings = integration.settings or {}
        project_keys = settings.get('projects', [])

        if not project_keys:
            raise HTTPException(status_code=400, detail="No projects configured in integration settings")
        logger.info(f"Starting custom fields sync for integration {integration_id} with projects: {project_keys}")

        # Perform custom fields discovery using TWO-STEP approach:
        # 1. Get ALL custom fields from /rest/api/latest/field
        # 2. Get project-field relationships from /createmeta
        from app.etl.jira.jira_client import JiraAPIClient, extract_custom_fields_from_all_fields, extract_custom_fields_from_createmeta
        from datetime import datetime, timezone

        try:
            # Create Jira client from integration
            jira_client = JiraAPIClient.create_from_integration(integration)

            # STEP 1: Get ALL custom fields (global discovery)
            logger.info(f"Calling Jira /rest/api/latest/field to get ALL custom fields")
            all_fields_response = jira_client.get_all_fields()
            all_discovered_fields = extract_custom_fields_from_all_fields(all_fields_response)

            logger.info(f"Discovered {len(all_discovered_fields)} custom fields from all fields endpoint")

            # STEP 2: Get project-field relationships from createmeta
            logger.info(f"Calling Jira createmeta API for projects: {project_keys}")
            createmeta_response = jira_client.get_createmeta(
                project_keys=project_keys,
                issue_type_names=None,  # Get ALL issue types
                expand="projects.issuetypes.fields"
            )

            # 🔍 DEBUG: Log the size of the response for troubleshooting
            response_json = json.dumps(createmeta_response)
            response_size_bytes = len(response_json.encode('utf-8'))
            response_size_mb = response_size_bytes / 1024 / 1024
            projects_count = len(createmeta_response.get('projects', []))
            logger.info(f"🔍 DEBUG: Createmeta response size: {response_size_bytes:,} bytes ({response_size_mb:.2f} MB), projects: {projects_count}")

            # Store one record with all projects and queue single message
            projects_processed = 0
            total_custom_fields = 0

            if user.tenant_id is not None:
                projects = createmeta_response.get('projects', [])
                projects_processed = len(projects)
                total_custom_fields = len(all_discovered_fields)

                # Send WebSocket status update: extraction started
                try:
                    from app.api.websocket_routes import get_custom_fields_websocket_manager
                    cf_ws_manager = get_custom_fields_websocket_manager()
                    await cf_ws_manager.send_status_update(user.tenant_id, 'extraction', 'running')
                    logger.debug(f"✅ [CF-WS] Sent extraction 'running' status for custom fields")
                except Exception as e:
                    logger.warning(f"⚠️ [CF-WS] Failed to send extraction running status: {e}")

                # Queue STEP 1: All custom fields (global discovery)
                await queue_all_custom_fields_for_processing(
                    integration_id=integration_id,
                    tenant_id=user.tenant_id,
                    all_fields_response=all_fields_response
                )

                logger.info(f"Queued {total_custom_fields} custom fields for global processing")

                # Send WebSocket status update: extraction finished
                try:
                    from app.api.websocket_routes import get_custom_fields_websocket_manager
                    cf_ws_manager = get_custom_fields_websocket_manager()
                    await cf_ws_manager.send_status_update(user.tenant_id, 'extraction', 'finished')
                    logger.debug(f"✅ [CF-WS] Sent extraction 'finished' status for custom fields")
                except Exception as e:
                    logger.warning(f"⚠️ [CF-WS] Failed to send extraction finished status: {e}")

                # Queue STEP 2: Project-field relationships from createmeta
                await queue_custom_fields_for_processing(
                    integration_id=integration_id,
                    tenant_id=user.tenant_id,
                    project_key=None,  # No specific project - this is for all projects
                    project_name=None,
                    discovered_fields=extract_custom_fields_from_createmeta(createmeta_response),
                    createmeta_response=createmeta_response  # FULL original response with all projects
                )

                logger.info(f"Stored createmeta raw data and queued for processing: projects_count={projects_processed}, fields_count={total_custom_fields}")

                # NOTE: Special fields (development, sprints) are already included in the
                # /rest/api/latest/field response processed in Step 1, so no need to fetch separately.
                # The old approach of fetching them separately caused deadlocks when multiple workers
                # tried to UPSERT the same fields simultaneously.

                logger.info(f"Total custom fields sync completed: {total_custom_fields} fields")
            else:
                logger.warning("User tenant_id is None, skipping queue processing")

            etl_result = {
                "status": "completed",
                "projects_processed": projects_processed,
                "total_custom_fields": total_custom_fields,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to sync custom fields: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve custom fields: {str(e)}")

        return {
            "success": True,
            "message": f"Custom fields sync queued successfully for {etl_result.get('projects_processed', 0)} projects. Processing in background...",
            "integration_id": integration_id,
            "project_keys": project_keys,
            "sync_status": "queued",  # Changed from "completed" to "queued" since transform worker processes async
            "projects_processed": etl_result.get("projects_processed", 0),
            "discovered_fields_count": etl_result.get("total_custom_fields", 0),  # Add this for frontend
            "timestamp": etl_result.get("timestamp")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing custom fields for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync custom fields")


@router.get("/custom-fields/sync-status/{integration_id}")
async def get_sync_status(
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Check the status of custom field sync processing.
    Returns whether transform worker has completed processing.
    """
    try:
        from app.models.unified_models import RawExtractionData
        from sqlalchemy import desc, func
        from datetime import datetime, timedelta

        # Get all custom fields sync records from the last 5 minutes for this integration
        # This ensures we check jira_custom_field_single and jira_custom_fields records
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)

        sync_records = db.query(RawExtractionData).filter(
            RawExtractionData.integration_id == integration_id,
            RawExtractionData.tenant_id == user.tenant_id,
            RawExtractionData.type.in_(['jira_custom_field_single', 'jira_custom_fields']),
            RawExtractionData.created_at >= cutoff_time
        ).order_by(desc(RawExtractionData.created_at)).all()

        if not sync_records:
            return {
                "success": True,
                "status": "no_sync_found",
                "processing_complete": True
            }

        # Check if ALL recent sync records are completed
        all_completed = all(record.status == 'completed' for record in sync_records)

        # Get status summary
        statuses = [record.status for record in sync_records]
        latest_record = sync_records[0]  # Most recent

        logger.info(f"Sync status check: {len(sync_records)} records, statuses: {statuses}, all_completed: {all_completed}")

        return {
            "success": True,
            "status": latest_record.status,
            "processing_complete": all_completed,
            "records_count": len(sync_records),
            "all_statuses": statuses,
            "created_at": latest_record.created_at.isoformat() if latest_record.created_at else None
        }

    except Exception as e:
        logger.error(f"Error checking sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check sync status")


@router.post("/custom-fields/discover")
async def discover_custom_fields(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Trigger custom field discovery for a project.
    This is a placeholder for future implementation that would call Jira API.
    """
    try:
        project_id = request_data.get('project_id')
        integration_id = request_data.get('integration_id')
        force_refresh = request_data.get('force_refresh', False)

        if not project_id or not integration_id:
            raise HTTPException(status_code=400, detail="project_id and integration_id are required")

        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # TODO: Implement actual Jira API discovery
        # For now, return mock data
        discovered_fields = [
            {
                "jira_field_id": "customfield_10001",
                "jira_field_name": "Story Points",
                "jira_field_type": "number",
                "project_count": 1
            },
            {
                "jira_field_id": "customfield_10002",
                "jira_field_name": "Epic Link",
                "jira_field_type": "string",
                "project_count": 1
            }
        ]

        discovered_issue_types = [
            {
                "issue_type_id": "10001",
                "issue_type_name": "Story",
                "project_count": 1
            },
            {
                "issue_type_id": "10002",
                "issue_type_name": "Epic",
                "project_count": 1
            }
        ]

        return {
            "success": True,
            "project_id": project_id,
            "integration_id": integration_id,
            "discovered_fields": discovered_fields,
            "discovered_issue_types": discovered_issue_types,
            "discovery_timestamp": "2025-10-02T19:30:00Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering custom fields: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover custom fields")


@router.get("/custom-fields/discovered/{project_id}/{integration_id}")
async def get_discovered_custom_fields(
    project_id: int,
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Get previously discovered custom fields for a project.
    This is a placeholder for future implementation.
    """
    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # TODO: Implement actual database lookup
        # For now, return empty data
        return {
            "success": True,
            "data": []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting discovered custom fields: {e}")
        raise HTTPException(status_code=500, detail="Failed to get discovered custom fields")


async def queue_all_custom_fields_for_processing(
    integration_id: int,
    tenant_id: int,
    all_fields_response: List[Dict[str, Any]]
):
    """
    Queue individual custom fields for processing (one message per field).
    This is STEP 1 of the two-step custom fields extraction.

    NEW APPROACH: Instead of storing all fields in one record and processing in bulk,
    we break them into individual messages (like projects/WITs) to avoid deadlocks.

    Args:
        integration_id: Integration ID
        tenant_id: Tenant ID
        all_fields_response: Response from /rest/api/latest/field API (list of all fields)
    """
    try:
        from app.etl.workers.queue_manager import QueueManager
        from datetime import datetime, timezone
        from sqlalchemy import text
        import json
        from app.core.database import get_database

        database = get_database()
        queue_manager = QueueManager()

        # Filter to only custom fields
        custom_fields = [f for f in all_fields_response if f.get('custom', False)]

        logger.info(f"Queuing {len(custom_fields)} individual custom fields for processing")

        # Process each custom field individually
        for i, field in enumerate(custom_fields):
            field_id = field.get('id')
            field_name = field.get('name', 'Unknown')

            if not field_id:
                logger.warning(f"Skipping field without ID: {field_name}")
                continue

            # Store individual field in raw_extraction_data
            with database.get_write_session_context() as db:
                try:
                    insert_query = text("""
                        INSERT INTO raw_extraction_data (
                            type, raw_data, status, tenant_id, integration_id, created_at, last_updated_at, active
                        ) VALUES (
                            :type, CAST(:raw_data AS jsonb), 'pending', :tenant_id, :integration_id, NOW(), NOW(), TRUE
                        ) RETURNING id
                    """)

                    raw_data_json = json.dumps(field)

                    result = db.execute(insert_query, {
                        'type': 'jira_custom_field_single',  # NEW type for individual fields
                        'raw_data': raw_data_json,
                        'tenant_id': tenant_id,
                        'integration_id': integration_id
                    })

                    row = result.fetchone()
                    if row is None:
                        logger.error(f"Failed to insert field {field_id} - no ID returned")
                        continue

                    raw_data_id = row[0]
                    db.commit()

                except Exception as db_error:
                    db.rollback()
                    logger.error(f"Database error storing field {field_id}: {db_error}")
                    continue

            # Queue individual field for transform
            # STEP 1 flags: first_item=True for first, last_item=True for last, last_job_item=False for all
            is_first = (i == 0)
            is_last = (i == len(custom_fields) - 1)

            success = queue_manager.publish_transform_job(
                tenant_id=tenant_id,
                integration_id=integration_id,
                raw_data_id=raw_data_id,
                data_type='jira_custom_field_single',  # NEW type for individual fields
                provider='jira',
                first_item=is_first,
                last_item=is_last,
                last_job_item=False  # Step 2 follows, so never True in Step 1
            )

            if not success:
                logger.error(f"Failed to queue field {field_id} for processing")
            elif i % 100 == 0 or is_last:
                logger.info(f"Queued {i+1}/{len(custom_fields)} custom fields")

        logger.info(f"Successfully queued all {len(custom_fields)} custom fields for individual processing")

    except Exception as e:
        logger.error(f"Error queuing custom fields for processing: {e}")
        raise


async def queue_custom_fields_for_processing(
    integration_id: int,
    tenant_id: int,
    discovered_fields: List[Dict[str, Any]],
    createmeta_response: Dict[str, Any],
    project_key: Optional[str] = None,
    project_name: Optional[str] = None
):
    """
    STEP 2: Break createmeta response by project and queue each project separately.

    This follows the user's specification:
    - Break the response by project
    - Send first_item=False to all of them
    - Send last_item=True to all of them
    - Send last_job_item=True ONLY to the last project

    Args:
        integration_id: Integration ID
        tenant_id: Tenant ID
        discovered_fields: Extracted custom fields (not used in new approach)
        createmeta_response: Full createmeta response with all projects
        project_key: Not used (legacy parameter)
        project_name: Not used (legacy parameter)
    """
    try:
        from app.etl.workers.queue_manager import QueueManager
        from datetime import datetime, timezone
        from sqlalchemy import text
        import json
        from app.core.database import get_database

        database = get_database()
        queue_manager = QueueManager()

        # Extract projects from createmeta response
        # Handle both 'projects' (createmeta API) and 'values' (project search API)
        projects = createmeta_response.get('projects', createmeta_response.get('values', []))

        if not projects:
            logger.warning("No projects found in createmeta response")
            return

        logger.info(f"Breaking createmeta response into {len(projects)} project messages")

        # Process each project individually
        for i, project in enumerate(projects):
            project_key = project.get('key')
            project_name = project.get('name')

            if not project_key:
                logger.warning(f"Skipping project without key: {project_name}")
                continue

            # Create a single-project createmeta response
            single_project_response = {
                'projects': [project]
            }

            # Store individual project in raw_extraction_data
            with database.get_write_session_context() as db:
                try:
                    insert_query = text("""
                        INSERT INTO raw_extraction_data (
                            type, raw_data, status, tenant_id, integration_id, created_at, last_updated_at, active
                        ) VALUES (
                            :type, CAST(:raw_data AS jsonb), 'pending', :tenant_id, :integration_id, NOW(), NOW(), TRUE
                        ) RETURNING id
                    """)

                    raw_data_json = json.dumps(single_project_response)

                    result = db.execute(insert_query, {
                        'type': 'jira_custom_fields',
                        'raw_data': raw_data_json,
                        'tenant_id': tenant_id,
                        'integration_id': integration_id
                    })

                    row = result.fetchone()
                    if row is None:
                        logger.error(f"Failed to insert project {project_key} - no ID returned")
                        continue

                    raw_data_id = row[0]
                    db.commit()

                except Exception as db_error:
                    db.rollback()
                    logger.error(f"Database error storing project {project_key}: {db_error}")
                    continue

            # Queue individual project for transform
            # STEP 2 flags: first_item=False for all, last_item=True for all, last_job_item=True ONLY for last
            is_last = (i == len(projects) - 1)

            success = queue_manager.publish_transform_job(
                tenant_id=tenant_id,
                integration_id=integration_id,
                raw_data_id=raw_data_id,
                data_type='jira_custom_fields',
                provider='jira',
                first_item=False,  # Always False in Step 2
                last_item=True,    # Always True in Step 2
                last_job_item=is_last  # True ONLY for the last project
            )

            if not success:
                logger.error(f"Failed to queue project {project_key} for processing")
            elif i % 10 == 0 or is_last:
                logger.info(f"Queued {i+1}/{len(projects)} projects (last_job_item={is_last})")

        logger.info(f"Successfully queued all {len(projects)} projects for processing")

    except Exception as e:
        logger.error(f"Failed to store/queue custom fields data: {e}")
        # Don't raise exception here - the discovery was successful even if storage/queuing failed


async def queue_special_fields_for_processing(
    integration_id: int,
    tenant_id: int,
    field_search_response: Dict[str, Any]
):
    """
    Store special field response in raw_extraction_data and queue for processing.
    Uses type 'jira_special_fields' to differentiate from createmeta.

    Special fields are those not available in createmeta API (e.g., development field).
    This function can handle any field fetched via /rest/api/3/field/search API.

    Args:
        integration_id: Integration ID
        tenant_id: Tenant ID
        field_search_response: Response from /rest/api/3/field/search API
    """
    try:
        from app.etl.workers.queue_manager import QueueManager
        from sqlalchemy import text
        import json
        from app.core.database import get_database

        database = get_database()

        with database.get_write_session_context() as db:
            try:
                # Insert into raw_extraction_data with type 'jira_special_fields'
                insert_query = text("""
                    INSERT INTO raw_extraction_data (
                        type, raw_data, status, tenant_id, integration_id, created_at, last_updated_at, active
                    ) VALUES (
                        :type, CAST(:raw_data AS jsonb), 'pending', :tenant_id, :integration_id, NOW(), NOW(), TRUE
                    ) RETURNING id
                """)

                raw_data_json = json.dumps(field_search_response)
                logger.info(f"🔍 DEBUG: Storing special field in database")

                result = db.execute(insert_query, {
                    'type': 'jira_special_fields',  # Generic type for special fields
                    'raw_data': raw_data_json,
                    'tenant_id': tenant_id,
                    'integration_id': integration_id
                })

                row = result.fetchone()
                if row is None:
                    raise Exception("Failed to insert special field raw data - no ID returned")
                raw_data_id = row[0]
                db.commit()

                logger.info(f"🔍 DEBUG: Successfully stored special field raw_data with ID: {raw_data_id}")

            except Exception as db_error:
                db.rollback()
                logger.error(f"Database error storing special field raw data: {db_error}")
                raise

        # Queue message to tenant-specific transform queue
        queue_manager = QueueManager()

        success = queue_manager.publish_transform_job(
            tenant_id=tenant_id,
            integration_id=integration_id,
            raw_data_id=raw_data_id,
            data_type='jira_special_fields',  # Generic data type for worker routing
            provider='jira'  # 🔑 Required for router to route to JiraTransformHandler
        )

        if success:
            logger.info(f"✅ Queued special field for processing: raw_data_id={raw_data_id}, tenant={tenant_id}")
        else:
            logger.error(f"❌ Failed to queue special field for processing: raw_data_id={raw_data_id}, tenant={tenant_id}")
            raise Exception("Failed to queue special field for processing")

    except Exception as e:
        logger.error(f"Failed to store/queue special field data: {e}")
        # Don't raise exception here - the discovery was successful even if storage/queuing failed


@router.get("/issue-types/discovered/{project_id}/{integration_id}")
async def get_discovered_issue_types(
    project_id: int,
    integration_id: int,
    db: Session = Depends(get_db_session),
    user: UserData = Depends(require_authentication)
):
    """
    Get previously discovered issue types for a project.
    This is a placeholder for future implementation.
    """
    try:
        # Verify integration access
        integration = db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.tenant_id == user.tenant_id,
            Integration.active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # TODO: Implement actual database lookup
        # For now, return empty data
        return {
            "success": True,
            "data": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting discovered issue types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get discovered issue types")
