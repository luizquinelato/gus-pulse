"""
Work Item Types (WITs) ETL Management API
Handles work item type mappings and hierarchies
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.auth_middleware import require_authentication
from app.core.database import get_database
from app.models.unified_models import Wit, WitMapping, WitHierarchy, Integration, User, QdrantVector

router = APIRouter()


class WitResponse(BaseModel):
    id: int
    external_id: Optional[str]
    name: str
    original_name: str
    description: Optional[str]
    hierarchy_level: Optional[int]
    original_hierarchy_level: Optional[int]
    workflow_id: Optional[int]
    integration_id: Optional[int]
    active: bool


class WitMappingResponse(BaseModel):
    id: int
    wit_from: str
    wit_to: str
    hierarchy_level: Optional[int]
    integration_id: Optional[int]
    integration_name: Optional[str]
    integration_logo: Optional[str]
    active: bool


class WitHierarchyResponse(BaseModel):
    id: int
    level: int
    name: str
    description: Optional[str]
    integration_id: Optional[int]
    integration_name: Optional[str]
    integration_logo: Optional[str]
    active: bool


class HierarchyDeletionRequest(BaseModel):
    target_hierarchy_id: Optional[int] = None


class HierarchyUpdateRequest(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    description: Optional[str] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None
    target_hierarchy_id: Optional[int] = None


class HierarchyBulkUpdateRequest(BaseModel):
    hierarchy_ids: List[int]
    updates: HierarchyUpdateRequest


class HierarchyBulkDeleteRequest(BaseModel):
    hierarchy_ids: List[int]


class HierarchyCreateRequest(BaseModel):
    name: str
    level: int
    description: Optional[str] = None
    integration_id: Optional[int] = None


class WitMappingCreateRequest(BaseModel):
    wit_from: str
    wit_to: str
    hierarchy_level: int
    integration_id: Optional[int] = None
    apply_to_existing_wits: Optional[bool] = False


class WitMappingUpdateRequest(BaseModel):
    wit_from: Optional[str] = None
    wit_to: Optional[str] = None
    hierarchy_level: Optional[int] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None
    apply_to_existing_wits: Optional[bool] = False


class WitMappingBulkUpdateRequest(BaseModel):
    mapping_ids: List[int]
    updates: WitMappingUpdateRequest


class WitMappingBulkDeleteRequest(BaseModel):
    mapping_ids: List[int]


class RemapWitsResponse(BaseModel):
    total_wits_scanned: int
    wits_updated: int
    mappings_applied: int
    message: str


@router.get("/wits", response_model=List[WitResponse])
async def get_wits(
    user: User = Depends(require_authentication)
):
    """Get all work item types for current user's tenant"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            # Join with WitHierarchy to get the hierarchy level
            wits = session.query(Wit, WitHierarchy).outerjoin(
                WitHierarchy, Wit.wits_hierarchy_id == WitHierarchy.id
            ).filter(
                Wit.tenant_id == user.tenant_id,
                Wit.active == True
            ).order_by(Wit.original_name).all()

            return [
                WitResponse(
                    id=wit.id,  # type: ignore
                    external_id=wit.external_id,  # type: ignore
                    name=wit.name,  # type: ignore
                    original_name=wit.original_name,  # type: ignore
                    description=wit.description,  # type: ignore
                    hierarchy_level=hierarchy.level if hierarchy else None,  # type: ignore
                    original_hierarchy_level=wit.original_hierarchy_level,  # type: ignore
                    workflow_id=wit.workflow_id,  # type: ignore
                    integration_id=wit.integration_id,  # type: ignore
                    active=wit.active
                )
                for wit, hierarchy in wits
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch work item types: {str(e)}"
        )


@router.get("/wit-mappings", response_model=List[WitMappingResponse])
async def get_wit_mappings(
    user: User = Depends(require_authentication)
):
    """Get all work item type mappings for current user's tenant"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            # Query mappings with hierarchy and integration information, filtered by tenant
            # Use LEFT JOIN to include mappings even if hierarchy was deleted (NULL hierarchy_id)
            mappings = session.query(WitMapping, WitHierarchy, Integration).outerjoin(
                WitHierarchy, WitMapping.wits_hierarchy_id == WitHierarchy.id
            ).outerjoin(
                Integration, WitMapping.integration_id == Integration.id
            ).filter(
                WitMapping.tenant_id == user.tenant_id,
                WitMapping.active == True
            ).all()

            result = []
            for mapping, hierarchy, integration in mappings:
                result.append(WitMappingResponse(
                    id=mapping.id,
                    wit_from=mapping.wit_from,
                    wit_to=mapping.wit_to,
                    hierarchy_level=hierarchy.level if hierarchy else None,  # Handle NULL hierarchy
                    integration_id=mapping.integration_id,
                    integration_name=integration.provider if integration else None,
                    integration_logo=integration.logo_filename if integration else None,
                    active=mapping.active
                ))

            return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch work item type mappings: {str(e)}"
        )


@router.get("/wits-hierarchies", response_model=List[WitHierarchyResponse])
async def get_wits_hierarchies(
    user: User = Depends(require_authentication)
):
    """Get all work item type hierarchies"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            hierarchies = session.query(
                WitHierarchy,
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).outerjoin(
                Integration, WitHierarchy.integration_id == Integration.id
            ).filter(
                WitHierarchy.tenant_id == user.tenant_id
            ).order_by(WitHierarchy.level.desc()).all()

            return [
                WitHierarchyResponse(
                    id=hierarchy.WitHierarchy.id,
                    level=hierarchy.WitHierarchy.level,
                    name=hierarchy.WitHierarchy.name,
                    description=hierarchy.WitHierarchy.description,
                    integration_id=hierarchy.WitHierarchy.integration_id,
                    integration_name=hierarchy.integration_name,
                    integration_logo=hierarchy.integration_logo,
                    active=hierarchy.WitHierarchy.active
                )
                for hierarchy in hierarchies
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch work item type hierarchies: {str(e)}"
        )


@router.put("/wits-hierarchies/{hierarchy_id}", response_model=WitHierarchyResponse)
async def update_wit_hierarchy(
    hierarchy_id: int,
    hierarchy_update: HierarchyUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a WIT hierarchy with optional reassignment for deactivation"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the hierarchy
            hierarchy = session.query(WitHierarchy).filter(
                WitHierarchy.id == hierarchy_id,
                WitHierarchy.tenant_id == user.tenant_id
            ).first()

            if not hierarchy:
                raise HTTPException(status_code=404, detail="Hierarchy not found")

            # Handle deactivation with potential reassignment
            if hierarchy_update.active is False and hierarchy.active is True:
                # Check for dependent mappings
                dependent_mappings = session.query(WitMapping).filter(
                    WitMapping.wits_hierarchy_id == hierarchy_id,
                    WitMapping.tenant_id == user.tenant_id
                ).all()

                # If there are dependencies and a target is specified, reassign them
                if dependent_mappings and hierarchy_update.target_hierarchy_id:
                    # Verify target hierarchy exists and is active
                    target_hierarchy = session.query(WitHierarchy).filter(
                        WitHierarchy.id == hierarchy_update.target_hierarchy_id,
                        WitHierarchy.active == True,
                        WitHierarchy.tenant_id == user.tenant_id
                    ).first()

                    if not target_hierarchy:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Target hierarchy (ID: {hierarchy_update.target_hierarchy_id}) not found or is inactive"
                        )

                    # Reassign all dependent mappings to the target hierarchy
                    for mapping in dependent_mappings:
                        mapping.wits_hierarchy_id = hierarchy_update.target_hierarchy_id  # type: ignore
                        # Note: wit_to is not automatically updated - it's a configuration value

            # Update fields if provided
            if hierarchy_update.name is not None:
                hierarchy.name = hierarchy_update.name  # type: ignore
            if hierarchy_update.level is not None:
                hierarchy.level = hierarchy_update.level  # type: ignore
            if hierarchy_update.description is not None:
                hierarchy.description = hierarchy_update.description  # type: ignore

            # Handle integration_id - check if field was provided in request
            if 'integration_id' in hierarchy_update.model_dump(exclude_unset=True):
                if hierarchy_update.integration_id is not None:
                    hierarchy.integration_id = hierarchy_update.integration_id
                else:
                    # Explicitly set to None to clear the integration
                    hierarchy.integration_id = None

            if hierarchy_update.active is not None:
                hierarchy.active = hierarchy_update.active

                # Update corresponding vectors in qdrant_vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'wits_hierarchies',
                    QdrantVector.record_id == hierarchy_id
                ).update({
                    'active': hierarchy_update.active,
                    'last_updated_at': DateTimeHelper.now_default()
                })

            # Update the last_updated_at timestamp using configured timezone
            hierarchy.last_updated_at = DateTimeHelper.now_default()
            session.commit()

            # Get integration info for response
            integration = session.query(Integration).filter(
                Integration.id == hierarchy.integration_id
            ).first() if hierarchy.integration_id else None

            # Return updated hierarchy data with integration info
            return WitHierarchyResponse(
                id=hierarchy.id,  # type: ignore
                level=hierarchy.level,  # type: ignore
                name=hierarchy.name,  # type: ignore
                description=hierarchy.description,  # type: ignore
                integration_id=hierarchy.integration_id,  # type: ignore
                integration_name=integration.provider if integration else None,  # type: ignore
                integration_logo=integration.logo_filename if integration else None,  # type: ignore
                active=hierarchy.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating hierarchy: {str(e)}")


@router.get("/wits-hierarchies/{hierarchy_id}/dependencies")
async def get_wit_hierarchy_dependencies(
    hierarchy_id: int,
    user: User = Depends(require_authentication)
):
    """Get dependencies for a WIT hierarchy before deletion/deactivation"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            # Get the hierarchy
            hierarchy = session.query(WitHierarchy).filter(
                WitHierarchy.id == hierarchy_id,
                WitHierarchy.tenant_id == user.tenant_id
            ).first()

            if not hierarchy:
                raise HTTPException(status_code=404, detail="Hierarchy not found")

            # Get dependent mappings
            dependent_mappings = session.query(WitMapping).filter(
                WitMapping.wits_hierarchy_id == hierarchy_id,
                WitMapping.tenant_id == user.tenant_id
            ).all()

            # Get other active hierarchies for reassignment targets
            reassignment_targets = session.query(WitHierarchy).filter(
                WitHierarchy.id != hierarchy_id,
                WitHierarchy.active == True,
                WitHierarchy.tenant_id == user.tenant_id
            ).all()

            # Count affected work items - NOTE: wits table no longer has wits_mapping_id FK
            # In new architecture, wits store standardized values directly
            total_affected_wits = 0
            mapping_details = []
            for mapping in dependent_mappings:
                # Count wits that would be affected by this hierarchy
                # (wits with matching wits_hierarchy_id)
                wit_count = session.query(Wit).filter(
                    Wit.wits_hierarchy_id == hierarchy.id,
                    Wit.tenant_id == user.tenant_id,
                    Wit.active == True
                ).count()
                total_affected_wits += wit_count

                mapping_details.append({
                    "id": mapping.id,
                    "wit_from": mapping.wit_from,
                    "wit_to": mapping.wit_to,
                    "affected_wits_count": wit_count
                })

            return {
                "hierarchy": {
                    "id": hierarchy.id,
                    "name": hierarchy.name,
                    "level": hierarchy.level
                },
                "has_dependencies": len(dependent_mappings) > 0,
                "dependency_count": len(dependent_mappings),
                "affected_wits_count": total_affected_wits,
                "dependent_mappings": mapping_details,
                "reassignment_targets": [
                    {
                        "id": target.id,
                        "name": target.name,
                        "level": target.level,
                        "description": target.description
                    }
                    for target in reassignment_targets
                ]
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking dependencies: {str(e)}")


@router.delete("/wits-hierarchies/{hierarchy_id}")
async def delete_wit_hierarchy(
    hierarchy_id: int,
    deletion_data: Optional[HierarchyDeletionRequest] = None,
    user: User = Depends(require_authentication)
):
    """Delete a WIT hierarchy with optional reassignment"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the hierarchy
            hierarchy = session.query(WitHierarchy).filter(
                WitHierarchy.id == hierarchy_id,
                WitHierarchy.tenant_id == user.tenant_id
            ).first()

            if not hierarchy:
                raise HTTPException(status_code=404, detail="Hierarchy not found")

            # Get dependent mappings
            dependent_mappings = session.query(WitMapping).filter(
                WitMapping.wits_hierarchy_id == hierarchy_id,
                WitMapping.tenant_id == user.tenant_id
            ).all()

            # Clean up dependent mappings by setting hierarchy_id to NULL
            from app.core.utils import DateTimeHelper
            for mapping in dependent_mappings:
                mapping.wits_hierarchy_id = None
                mapping.last_updated_at = DateTimeHelper.now_default()

            # Delete the hierarchy
            session.delete(hierarchy)
            session.commit()

            return {
                "message": "Hierarchy deleted successfully",
                "id": hierarchy_id,
                "cleaned_mappings": len(dependent_mappings)
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting hierarchy: {str(e)}")


@router.post("/wits-hierarchies/bulk-update", response_model=List[WitHierarchyResponse])
async def bulk_update_wit_hierarchies(
    bulk_data: HierarchyBulkUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Bulk update multiple WIT hierarchies in a single transaction"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 BULK UPDATE - {len(bulk_data.hierarchy_ids)} hierarchies - Updates: {bulk_data.updates.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all hierarchies to update
            hierarchies = session.query(WitHierarchy).filter(
                WitHierarchy.id.in_(bulk_data.hierarchy_ids),
                WitHierarchy.tenant_id == user.tenant_id
            ).all()

            if not hierarchies:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No hierarchies found to update"
                )

            # Validate level if being updated
            if bulk_data.updates.level is not None:
                # Check if level already exists (excluding current hierarchies)
                existing_level = session.query(WitHierarchy).filter(
                    WitHierarchy.level == bulk_data.updates.level,
                    WitHierarchy.tenant_id == user.tenant_id,
                    ~WitHierarchy.id.in_(bulk_data.hierarchy_ids)
                ).first()

                if existing_level:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Level {bulk_data.updates.level} is already in use by hierarchy '{existing_level.name}'"
                    )

            # Update all hierarchies
            updated_hierarchies = []
            for hierarchy in hierarchies:
                if bulk_data.updates.name is not None:
                    hierarchy.name = bulk_data.updates.name  # type: ignore
                if bulk_data.updates.level is not None:
                    hierarchy.level = bulk_data.updates.level
                if bulk_data.updates.description is not None:
                    hierarchy.description = bulk_data.updates.description  # type: ignore

                # Handle integration_id - check if field was provided in request
                if 'integration_id' in bulk_data.updates.model_dump(exclude_unset=True):
                    if bulk_data.updates.integration_id is not None:
                        hierarchy.integration_id = bulk_data.updates.integration_id
                    else:
                        # Explicitly set to None to clear the integration
                        hierarchy.integration_id = None

                if bulk_data.updates.active is not None:
                    hierarchy.active = bulk_data.updates.active

                hierarchy.last_updated_at = DateTimeHelper.now_default()
                updated_hierarchies.append(hierarchy)

            session.commit()

            # Refresh to get updated data with relationships
            for hierarchy in updated_hierarchies:
                session.refresh(hierarchy)

            # Build response with integration info
            result = []
            for hierarchy in updated_hierarchies:
                integration_name = None
                integration_logo = None
                if hierarchy.integration_id:
                    integration = session.query(Integration).filter(
                        Integration.id == hierarchy.integration_id
                    ).first()
                    if integration:
                        integration_name = integration.provider
                        integration_logo = integration.logo_filename

                result.append(WitHierarchyResponse(
                    id=hierarchy.id,
                    level=hierarchy.level,
                    name=hierarchy.name,
                    description=hierarchy.description,
                    integration_id=hierarchy.integration_id,
                    integration_name=integration_name,
                    integration_logo=integration_logo,
                    active=hierarchy.active
                ))

            logger.info(f"✅ Successfully bulk updated {len(result)} hierarchies")
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk updating hierarchies: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update hierarchies: {str(e)}"
        )


@router.post("/wits-hierarchies/bulk-delete")
async def bulk_delete_wit_hierarchies(
    bulk_data: HierarchyBulkDeleteRequest,
    user: User = Depends(require_authentication)
):
    """Bulk delete multiple WIT hierarchies"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ BULK DELETE - {len(bulk_data.hierarchy_ids)} hierarchies")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get all hierarchies to delete
            hierarchies = session.query(WitHierarchy).filter(
                WitHierarchy.id.in_(bulk_data.hierarchy_ids),
                WitHierarchy.tenant_id == user.tenant_id
            ).all()

            if not hierarchies:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No hierarchies found to delete"
                )

            # Clean up dependent mappings by setting hierarchy_id to NULL
            from app.core.utils import DateTimeHelper
            total_cleaned = 0
            for hierarchy in hierarchies:
                dependent_mappings = session.query(WitMapping).filter(
                    WitMapping.wits_hierarchy_id == hierarchy.id,
                    WitMapping.tenant_id == user.tenant_id
                ).all()

                for mapping in dependent_mappings:
                    mapping.wits_hierarchy_id = None
                    mapping.last_updated_at = DateTimeHelper.now_default()
                    total_cleaned += 1

            # Delete all hierarchies
            for hierarchy in hierarchies:
                session.delete(hierarchy)

            session.commit()

            logger.info(f"✅ Successfully bulk deleted {len(hierarchies)} hierarchies, cleaned {total_cleaned} mappings")
            return {
                "message": f"Successfully deleted {len(hierarchies)} hierarchies",
                "deleted_count": len(hierarchies),
                "cleaned_mappings": total_cleaned
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk deleting hierarchies: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete hierarchies: {str(e)}"
        )


@router.post("/wits-hierarchies", response_model=WitHierarchyResponse)
async def create_wit_hierarchy(
    hierarchy_data: HierarchyCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new work item type hierarchy"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Create new hierarchy
            new_hierarchy = WitHierarchy(
                name=hierarchy_data.name,
                level=hierarchy_data.level,
                description=hierarchy_data.description,
                integration_id=hierarchy_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_hierarchy)
            session.flush()  # Get the ID

            # Get integration info if exists
            integration_name = None
            integration_logo = None
            if new_hierarchy.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == new_hierarchy.integration_id,
                    Integration.tenant_id == user.tenant_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return WitHierarchyResponse(
                id=new_hierarchy.id,  # type: ignore
                level=new_hierarchy.level,  # type: ignore
                name=new_hierarchy.name,  # type: ignore
                description=new_hierarchy.description,  # type: ignore
                integration_id=new_hierarchy.integration_id,  # type: ignore
                integration_name=integration_name,  # type: ignore
                integration_logo=integration_logo,  # type: ignore
                active=new_hierarchy.active
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create hierarchy: {str(e)}"
        )


@router.post("/wit-mappings", response_model=WitMappingResponse)
async def create_wit_mapping(
    mapping_data: WitMappingCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new work item type mapping"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Validate hierarchy level exists and is active
            hierarchy = session.query(WitHierarchy).filter(
                WitHierarchy.level == mapping_data.hierarchy_level,
                WitHierarchy.tenant_id == user.tenant_id,
                WitHierarchy.active == True
            ).first()

            if not hierarchy:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Active hierarchy level {mapping_data.hierarchy_level} not found"
                )

            # Create new mapping
            new_mapping = WitMapping(
                wit_from=mapping_data.wit_from,
                wit_to=mapping_data.wit_to,
                wits_hierarchy_id=hierarchy.id,
                integration_id=mapping_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_mapping)
            session.flush()  # Get the ID

            # Apply to existing WITs if requested
            wits_updated = 0
            if mapping_data.apply_to_existing_wits:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"🔄 Applying new mapping to existing WITs: '{mapping_data.wit_from}' -> '{mapping_data.wit_to}'")

                # Find all WITs with matching original_name (case-insensitive)
                from sqlalchemy import func
                wits_to_update = session.query(Wit).filter(
                    Wit.tenant_id == user.tenant_id,
                    func.lower(Wit.original_name) == func.lower(mapping_data.wit_from),
                    Wit.active == True
                ).all()

                for wit in wits_to_update:
                    if wit.name != mapping_data.wit_to or wit.wits_hierarchy_id != hierarchy.id:
                        logger.info(f"  📝 Updating WIT '{wit.original_name}': '{wit.name}' -> '{mapping_data.wit_to}', hierarchy_id: {wit.wits_hierarchy_id} -> {hierarchy.id}")
                        wit.name = mapping_data.wit_to
                        wit.wits_hierarchy_id = hierarchy.id
                        wit.last_updated_at = DateTimeHelper.now_default()
                        wits_updated += 1

                logger.info(f"✅ Updated {wits_updated} existing WITs")

            session.commit()

            # Get integration info if exists
            integration_name = None
            integration_logo = None
            if new_mapping.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == new_mapping.integration_id,
                    Integration.tenant_id == user.tenant_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return WitMappingResponse(
                id=new_mapping.id,  # type: ignore
                wit_from=new_mapping.wit_from,  # type: ignore
                wit_to=new_mapping.wit_to,  # type: ignore
                hierarchy_level=hierarchy.level,  # type: ignore
                integration_id=new_mapping.integration_id,  # type: ignore
                integration_name=integration_name,  # type: ignore
                integration_logo=integration_logo,  # type: ignore
                active=new_mapping.active
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create mapping: {str(e)}"
        )


@router.put("/wit-mappings/{mapping_id}", response_model=WitMappingResponse)
async def update_wit_mapping(
    mapping_id: int,
    mapping_data: WitMappingUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a work item type mapping"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the existing mapping
            mapping = session.query(WitMapping).filter(
                WitMapping.id == mapping_id,
                WitMapping.tenant_id == user.tenant_id
            ).first()

            if not mapping:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Mapping not found"
                )

            # Store original values for comparison
            original_wit_from = mapping.wit_from
            original_wit_to = mapping.wit_to

            # Update fields if provided
            if mapping_data.wit_from is not None:
                mapping.wit_from = mapping_data.wit_from  # type: ignore
            if mapping_data.wit_to is not None:
                mapping.wit_to = mapping_data.wit_to  # type: ignore

            # Handle integration_id - check if field was provided in request
            if 'integration_id' in mapping_data.model_dump(exclude_unset=True):
                if mapping_data.integration_id is not None:
                    mapping.integration_id = mapping_data.integration_id
                else:
                    # Explicitly set to None to clear the integration
                    mapping.integration_id = None

            if mapping_data.active is not None:
                mapping.active = mapping_data.active

                # Update corresponding vectors in qdrant_vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'wits_mappings',
                    QdrantVector.record_id == mapping_id
                ).update({
                    'active': mapping_data.active,
                    'last_updated_at': DateTimeHelper.now_default()
                })

            # Handle hierarchy level update
            if mapping_data.hierarchy_level is not None:
                # Validate hierarchy level exists and is active
                hierarchy = session.query(WitHierarchy).filter(
                    WitHierarchy.level == mapping_data.hierarchy_level,
                    WitHierarchy.tenant_id == user.tenant_id,
                    WitHierarchy.active == True
                ).first()

                if not hierarchy:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Active hierarchy level {mapping_data.hierarchy_level} not found"
                    )

                mapping.wits_hierarchy_id = hierarchy.id

            mapping.last_updated_at = DateTimeHelper.now_default()

            # Apply to existing WITs if requested and if wit_from or wit_to changed
            wits_updated = 0
            if mapping_data.apply_to_existing_wits:
                import logging
                logger = logging.getLogger(__name__)

                # Determine which original_name to search for
                # If wit_from changed, we need to update WITs with the OLD wit_from value
                # If wit_from didn't change, use the current wit_from
                search_original_name = original_wit_from if mapping_data.wit_from is None else mapping_data.wit_from
                new_mapped_name = mapping.wit_to
                new_hierarchy_id = mapping.wits_hierarchy_id

                logger.info(f"🔄 Applying mapping update to existing WITs: original_name='{search_original_name}' -> name='{new_mapped_name}', hierarchy_id={new_hierarchy_id}")

                # Find all WITs with matching original_name (case-insensitive)
                from sqlalchemy import func
                wits_to_update = session.query(Wit).filter(
                    Wit.tenant_id == user.tenant_id,
                    func.lower(Wit.original_name) == func.lower(search_original_name),
                    Wit.active == True
                ).all()

                for wit in wits_to_update:
                    if wit.name != new_mapped_name or wit.wits_hierarchy_id != new_hierarchy_id:
                        logger.info(f"  📝 Updating WIT '{wit.original_name}': '{wit.name}' -> '{new_mapped_name}', hierarchy_id: {wit.wits_hierarchy_id} -> {new_hierarchy_id}")
                        wit.name = new_mapped_name
                        wit.wits_hierarchy_id = new_hierarchy_id
                        wit.last_updated_at = DateTimeHelper.now_default()
                        wits_updated += 1

                logger.info(f"✅ Updated {wits_updated} existing WITs")

            session.commit()

            # Get updated hierarchy and integration info for response
            hierarchy = session.query(WitHierarchy).filter(
                WitHierarchy.id == mapping.wits_hierarchy_id
            ).first()

            integration = session.query(Integration).filter(
                Integration.id == mapping.integration_id
            ).first() if mapping.integration_id else None

            return WitMappingResponse(
                id=mapping.id,  # type: ignore
                wit_from=mapping.wit_from,  # type: ignore
                wit_to=mapping.wit_to,  # type: ignore
                hierarchy_level=hierarchy.level if hierarchy else None,  # type: ignore
                integration_id=mapping.integration_id,  # type: ignore
                integration_name=integration.provider if integration else None,  # type: ignore
                integration_logo=integration.logo_filename if integration else None,  # type: ignore
                active=mapping.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update mapping: {str(e)}"
        )


@router.delete("/wit-mappings/{mapping_id}")
async def delete_wit_mapping(
    mapping_id: int,
    user: User = Depends(require_authentication)
):
    """Delete a work item type mapping (translation rule only - doesn't affect existing WITs)"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the existing mapping
            mapping = session.query(WitMapping).filter(
                WitMapping.id == mapping_id,
                WitMapping.tenant_id == user.tenant_id
            ).first()

            if not mapping:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Mapping not found"
                )

            # Delete the mapping - it's just a translation rule
            # Existing WITs in the wits table are not affected
            session.delete(mapping)
            session.commit()
            return {"message": "Mapping deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete mapping: {str(e)}"
        )


@router.post("/wit-mappings/bulk-update", response_model=List[WitMappingResponse])
async def bulk_update_wit_mappings(
    bulk_data: WitMappingBulkUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Bulk update multiple WIT mappings in a single transaction"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 BULK UPDATE - {len(bulk_data.mapping_ids)} WIT mappings - Updates: {bulk_data.updates.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all mappings to update
            mappings = session.query(WitMapping).filter(
                WitMapping.id.in_(bulk_data.mapping_ids),
                WitMapping.tenant_id == user.tenant_id
            ).all()

            if not mappings:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No mappings found to update"
                )

            # Validate hierarchy level if being updated
            if bulk_data.updates.hierarchy_level is not None:
                hierarchy = session.query(WitHierarchy).filter(
                    WitHierarchy.level == bulk_data.updates.hierarchy_level,
                    WitHierarchy.tenant_id == user.tenant_id,
                    WitHierarchy.active == True
                ).first()

                if not hierarchy:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Active hierarchy level {bulk_data.updates.hierarchy_level} not found"
                    )

            # Update all mappings
            updated_mappings = []
            for mapping in mappings:
                if bulk_data.updates.wit_from is not None:
                    mapping.wit_from = bulk_data.updates.wit_from
                if bulk_data.updates.wit_to is not None:
                    mapping.wit_to = bulk_data.updates.wit_to
                if bulk_data.updates.hierarchy_level is not None:
                    # Find the hierarchy ID for this level
                    hierarchy = session.query(WitHierarchy).filter(
                        WitHierarchy.level == bulk_data.updates.hierarchy_level,
                        WitHierarchy.tenant_id == user.tenant_id
                    ).first()
                    if hierarchy:
                        mapping.wits_hierarchy_id = hierarchy.id
                # Handle integration_id - check if field was provided in request
                if 'integration_id' in bulk_data.updates.model_dump(exclude_unset=True):
                    if bulk_data.updates.integration_id is not None:
                        mapping.integration_id = bulk_data.updates.integration_id
                    else:
                        # Explicitly set to None to clear the integration
                        mapping.integration_id = None

                if bulk_data.updates.active is not None:
                    mapping.active = bulk_data.updates.active

                mapping.last_updated_at = DateTimeHelper.now_default()
                updated_mappings.append(mapping)

            # Apply changes to existing WITs if requested
            if bulk_data.updates.apply_to_existing_wits:
                logger.info(f"🔄 Applying bulk mapping updates to existing WITs...")
                total_wits_updated = 0

                for mapping in updated_mappings:
                    # Only apply if wit_to or hierarchy_level was changed
                    if bulk_data.updates.wit_to is not None or bulk_data.updates.hierarchy_level is not None:
                        # Find all WITs with matching original_name (case-insensitive)
                        from sqlalchemy import func
                        wits_to_update = session.query(Wit).filter(
                            Wit.tenant_id == user.tenant_id,
                            func.lower(Wit.original_name) == func.lower(mapping.wit_from),
                            Wit.active == True
                        ).all()

                        new_mapped_name = mapping.wit_to
                        new_hierarchy_id = mapping.wits_hierarchy_id

                        for wit in wits_to_update:
                            if wit.name != new_mapped_name or wit.wits_hierarchy_id != new_hierarchy_id:
                                logger.info(f"  📝 Updating WIT '{wit.original_name}': '{wit.name}' -> '{new_mapped_name}', hierarchy_id: {wit.wits_hierarchy_id} -> {new_hierarchy_id}")
                                wit.name = new_mapped_name
                                wit.wits_hierarchy_id = new_hierarchy_id
                                wit.last_updated_at = DateTimeHelper.now_default()
                                total_wits_updated += 1

                logger.info(f"✅ Updated {total_wits_updated} existing WITs across {len(updated_mappings)} mappings")

            session.commit()

            # Refresh to get updated data with relationships
            for mapping in updated_mappings:
                session.refresh(mapping)

            # Build response with integration info
            result = []
            for mapping in updated_mappings:
                integration_name = None
                integration_logo = None
                if mapping.integration_id:
                    integration = session.query(Integration).filter(
                        Integration.id == mapping.integration_id
                    ).first()
                    if integration:
                        integration_name = integration.provider  # ✅ FIXED: Use 'provider' not 'name'
                        integration_logo = integration.logo_filename

                # Get hierarchy level from the relationship
                hierarchy_level = None
                if mapping.wits_hierarchy_id:
                    hierarchy = session.query(WitHierarchy).filter(
                        WitHierarchy.id == mapping.wits_hierarchy_id
                    ).first()
                    if hierarchy:
                        hierarchy_level = hierarchy.level

                result.append(WitMappingResponse(
                    id=mapping.id,
                    wit_from=mapping.wit_from,
                    wit_to=mapping.wit_to,
                    hierarchy_level=hierarchy_level,
                    integration_id=mapping.integration_id,
                    integration_name=integration_name,
                    integration_logo=integration_logo,
                    active=mapping.active
                ))

            logger.info(f"✅ Successfully bulk updated {len(result)} WIT mappings")
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk updating WIT mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk update WIT mappings: {str(e)}"
        )


@router.post("/wit-mappings/bulk-delete")
async def bulk_delete_wit_mappings(
    bulk_data: WitMappingBulkDeleteRequest,
    user: User = Depends(require_authentication)
):
    """Bulk delete multiple WIT mappings (translation rules only - doesn't affect existing WITs)"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ BULK DELETE - {len(bulk_data.mapping_ids)} WIT mappings")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get all mappings to delete
            mappings = session.query(WitMapping).filter(
                WitMapping.id.in_(bulk_data.mapping_ids),
                WitMapping.tenant_id == user.tenant_id
            ).all()

            if not mappings:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No mappings found to delete"
                )

            # Delete all mappings - they're just translation rules
            # Existing WITs in the wits table are not affected
            for mapping in mappings:
                session.delete(mapping)

            session.commit()

            message = f"Successfully deleted {len(mappings)} mapping(s)"
            logger.info(f"✅ {message}")
            return {"message": message, "deleted": len(mappings)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk deleting WIT mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk delete WIT mappings: {str(e)}"
        )


@router.post("/wit-mappings/remap-all-wits", response_model=RemapWitsResponse)
async def remap_all_wits(
    user: User = Depends(require_authentication)
):
    """
    Scan all WITs in the database and update their 'name' field based on current WIT mappings.
    Only updates WITs where the mapped name differs from the current name.
    Matches WIT.original_name with WitMapping.wit_from to find the correct mapping.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 REMAP ALL WITS - Starting full WIT remapping for tenant {user.tenant_id}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all active WIT mappings for this tenant
            mappings = session.query(WitMapping).filter(
                WitMapping.tenant_id == user.tenant_id,
                WitMapping.active == True
            ).all()

            # Create a lookup dictionary: original_name -> mapped_name
            mapping_dict = {m.wit_from: m.wit_to for m in mappings}

            logger.info(f"📋 Found {len(mapping_dict)} active WIT mappings")

            # Get all WITs for this tenant
            wits = session.query(Wit).filter(
                Wit.tenant_id == user.tenant_id,
                Wit.active == True
            ).all()

            total_wits = len(wits)
            wits_updated = 0
            mappings_applied = 0

            # Update WITs based on mappings
            for wit in wits:
                # Check if there's a mapping for this WIT's original name
                if wit.original_name in mapping_dict:
                    mapped_name = mapping_dict[wit.original_name]
                    mappings_applied += 1

                    # Only update if the name is different
                    if wit.name != mapped_name:
                        logger.info(f"  📝 Updating WIT '{wit.original_name}': '{wit.name}' -> '{mapped_name}'")
                        wit.name = mapped_name
                        wit.last_updated_at = DateTimeHelper.now_default()
                        wits_updated += 1

            session.commit()

            message = f"Scanned {total_wits} WITs, found {mappings_applied} with mappings, updated {wits_updated} WITs"
            logger.info(f"✅ {message}")

            return RemapWitsResponse(
                total_wits_scanned=total_wits,
                wits_updated=wits_updated,
                mappings_applied=mappings_applied,
                message=message
            )

    except Exception as e:
        logger.error(f"❌ Error remapping WITs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remap WITs: {str(e)}"
        )
