"""
Status Mappings ETL Management API
Handles status mappings and workflows
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.auth_middleware import require_authentication
from app.core.database import get_database
from app.models.unified_models import Status, StatusMapping, StatusCategory, Workflow, WorkflowsStep, Integration, User, QdrantVector, Wit

router = APIRouter()


class StatusResponse(BaseModel):
    id: int
    external_id: Optional[str]
    name: str
    original_name: str
    description: Optional[str]
    category: Optional[str]
    original_category: Optional[str]
    integration_id: Optional[int]
    active: bool


class StatusMappingResponse(BaseModel):
    id: int
    status_from: str
    status_to: str
    category: Optional[str]
    integration_name: Optional[str]
    integration_id: Optional[int]
    integration_logo: Optional[str]
    active: bool


class WorkflowResponse(BaseModel):
    id: int
    name: str
    integration_id: Optional[int]
    integration_name: Optional[str]
    integration_logo: Optional[str]
    active: bool


class WorkflowStepResponse(BaseModel):
    id: int
    workflow_id: int
    workflow_name: Optional[str]
    name: str
    order: Optional[int]
    status_id: Optional[int]
    status_name: Optional[str]
    is_commitment_point: bool
    integration_id: Optional[int]
    integration_name: Optional[str]
    integration_logo: Optional[str]
    active: bool


class StatusMappingCreateRequest(BaseModel):
    status_from: str
    status_to: str
    category_id: int
    integration_id: Optional[int] = None
    apply_to_existing_statuses: Optional[bool] = False


class WorkflowCreateRequest(BaseModel):
    name: str
    integration_id: Optional[int] = None


class WorkflowStepCreateRequest(BaseModel):
    workflow_id: int
    name: str
    order: Optional[int] = None
    status_id: Optional[int] = None
    is_commitment_point: bool = False
    integration_id: Optional[int] = None


class StatusMappingUpdateRequest(BaseModel):
    status_from: Optional[str] = None
    status_to: Optional[str] = None
    category_id: Optional[int] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None
    apply_to_existing_statuses: Optional[bool] = False


class StatusMappingBulkUpdateRequest(BaseModel):
    mapping_ids: List[int]
    updates: StatusMappingUpdateRequest


class StatusMappingBulkDeleteRequest(BaseModel):
    mapping_ids: List[int]


class RemapStatusesResponse(BaseModel):
    total_statuses_scanned: int
    statuses_updated: int
    mappings_applied: int
    message: str


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None


class WorkflowStepUpdateRequest(BaseModel):
    workflow_id: Optional[int] = None
    name: Optional[str] = None
    order: Optional[int] = None
    status_id: Optional[int] = None
    status_mapping_id: Optional[int] = None
    is_commitment_point: Optional[bool] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None


class WorkflowBulkUpdateRequest(BaseModel):
    workflow_ids: List[int]
    updates: WorkflowUpdateRequest


class WorkflowBulkDeleteRequest(BaseModel):
    workflow_ids: List[int]


class StatusCategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_waiting: bool
    is_done: bool
    integration_id: Optional[int] = None
    integration_name: Optional[str] = None
    integration_logo: Optional[str] = None
    active: bool


class StatusCategoryCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_waiting: bool = False
    is_done: bool = False
    integration_id: Optional[int] = None


class StatusCategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_waiting: Optional[bool] = None
    is_done: Optional[bool] = None
    integration_id: Optional[int] = None
    active: Optional[bool] = None


class StatusCategoryBulkUpdateRequest(BaseModel):
    category_ids: List[int]
    updates: StatusCategoryUpdateRequest


class StatusCategoryBulkDeleteRequest(BaseModel):
    category_ids: List[int]


@router.get("/statuses", response_model=List[StatusResponse])
async def get_statuses(
    user: User = Depends(require_authentication)
):
    """Get all statuses for current user's tenant"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            statuses = session.query(Status).filter(
                Status.tenant_id == user.tenant_id,
                Status.active == True
            ).order_by(Status.original_name).all()

            return [
                StatusResponse(
                    id=status_obj.id,  # type: ignore
                    external_id=status_obj.external_id,  # type: ignore
                    name=status_obj.name,  # type: ignore
                    original_name=status_obj.original_name,  # type: ignore
                    description=status_obj.description,  # type: ignore
                    category=status_obj.status_category.name if status_obj.status_category else None,  # type: ignore
                    original_category=status_obj.original_category,  # type: ignore
                    integration_id=status_obj.integration_id,  # type: ignore
                    active=status_obj.active
                )
                for status_obj in statuses
            ]
    except Exception as e:
        import traceback
        print(f"❌ ERROR fetching statuses: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statuses: {str(e)}"
        )


@router.get("/status-mappings", response_model=List[StatusMappingResponse])
async def get_status_mappings(
    user: User = Depends(require_authentication)
):
    """Get all status mappings"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            status_mappings = session.query(
                StatusMapping,
                StatusCategory.name.label('category_name'),
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).outerjoin(
                StatusCategory, StatusMapping.status_category_id == StatusCategory.id
            ).outerjoin(
                Integration, StatusMapping.integration_id == Integration.id
            ).filter(
                StatusMapping.tenant_id == user.tenant_id
            ).order_by(StatusMapping.status_to).all()

            return [
                StatusMappingResponse(
                    id=mapping.StatusMapping.id,
                    status_from=mapping.StatusMapping.status_from,
                    status_to=mapping.StatusMapping.status_to,
                    category=mapping.category_name,
                    integration_name=mapping.integration_name,
                    integration_id=mapping.StatusMapping.integration_id,
                    integration_logo=mapping.integration_logo,
                    active=mapping.StatusMapping.active
                )
                for mapping in status_mappings
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch status mappings: {str(e)}"
        )


@router.get("/workflows", response_model=List[WorkflowResponse])
async def get_workflows(
    user: User = Depends(require_authentication)
):
    """Get all workflows (containers)"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            workflows = session.query(
                Workflow,
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).outerjoin(
                Integration, Workflow.integration_id == Integration.id
            ).filter(
                Workflow.tenant_id == user.tenant_id
            ).order_by(Workflow.name).all()

            return [
                WorkflowResponse(
                    id=workflow.Workflow.id,
                    name=workflow.Workflow.name,
                    integration_id=workflow.Workflow.integration_id,
                    integration_name=workflow.integration_name,
                    integration_logo=workflow.integration_logo,
                    active=workflow.Workflow.active
                )
                for workflow in workflows
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflows: {str(e)}"
        )


@router.get("/workflow-steps", response_model=List[WorkflowStepResponse])
async def get_workflow_steps(
    user: User = Depends(require_authentication)
):
    """Get all workflow steps"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            steps = session.query(
                WorkflowsStep,
                Workflow.name.label('workflow_name'),
                Status.name.label('status_name'),
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).join(
                Workflow, WorkflowsStep.workflow_id == Workflow.id
            ).outerjoin(
                Status, WorkflowsStep.status_id == Status.id
            ).outerjoin(
                Integration, WorkflowsStep.integration_id == Integration.id
            ).filter(
                WorkflowsStep.tenant_id == user.tenant_id
            ).order_by(WorkflowsStep.workflow_id, WorkflowsStep.order.nulls_last()).all()

            return [
                WorkflowStepResponse(
                    id=step.WorkflowsStep.id,
                    workflow_id=step.WorkflowsStep.workflow_id,
                    workflow_name=step.workflow_name,
                    name=step.WorkflowsStep.name,
                    order=step.WorkflowsStep.order,
                    status_id=step.WorkflowsStep.status_id,
                    status_name=step.status_name,
                    is_commitment_point=step.WorkflowsStep.is_commitment_point,
                    integration_id=step.WorkflowsStep.integration_id,
                    integration_name=step.integration_name,
                    integration_logo=step.integration_logo,
                    active=step.WorkflowsStep.active
                )
                for step in steps
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow steps: {str(e)}"
        )


@router.post("/status-mappings", response_model=StatusMappingResponse)
async def create_status_mapping(
    mapping_data: StatusMappingCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new status mapping"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Validate category exists
            category = session.query(StatusCategory).filter(
                StatusCategory.id == mapping_data.category_id,
                StatusCategory.tenant_id == user.tenant_id,
                StatusCategory.active == True
            ).first()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Active status category {mapping_data.category_id} not found"
                )

            # Create new status mapping
            new_mapping = StatusMapping(
                status_from=mapping_data.status_from,
                status_to=mapping_data.status_to,
                status_category_id=mapping_data.category_id,
                integration_id=mapping_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_mapping)
            session.flush()  # Get the ID

            # Apply to existing statuses if requested
            statuses_updated = 0
            if mapping_data.apply_to_existing_statuses:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"🔄 Applying new mapping to existing statuses: '{mapping_data.status_from}' -> '{mapping_data.status_to}', category_id={mapping_data.category_id}")

                # Find all statuses with matching original_name (case-insensitive)
                from sqlalchemy import func
                statuses_to_update = session.query(Status).filter(
                    Status.tenant_id == user.tenant_id,
                    func.lower(Status.original_name) == func.lower(mapping_data.status_from),
                    Status.active == True
                ).all()

                for status in statuses_to_update:
                    if status.name != mapping_data.status_to or status.status_category_id != mapping_data.category_id:
                        logger.info(f"  📝 Updating Status '{status.original_name}': '{status.name}' -> '{mapping_data.status_to}', category_id: {status.status_category_id} -> {mapping_data.category_id}")
                        status.name = mapping_data.status_to
                        status.status_category_id = mapping_data.category_id
                        status.last_updated_at = DateTimeHelper.now_default()
                        statuses_updated += 1

                logger.info(f"✅ Updated {statuses_updated} existing statuses")

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

            return StatusMappingResponse(
                id=new_mapping.id,  # type: ignore
                status_from=new_mapping.status_from,  # type: ignore
                status_to=new_mapping.status_to,  # type: ignore
                category=category.name,  # type: ignore
                integration_name=integration_name,  # type: ignore
                integration_id=new_mapping.integration_id,  # type: ignore
                integration_logo=integration_logo,  # type: ignore
                active=new_mapping.active
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create status mapping: {str(e)}"
        )


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new workflow (container)"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Create new workflow container
            new_workflow = Workflow(
                name=workflow_data.name,
                integration_id=workflow_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_workflow)
            session.flush()  # Get the ID

            # Get integration info if exists
            integration_name = None
            integration_logo = None
            if new_workflow.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == new_workflow.integration_id,
                    Integration.tenant_id == user.tenant_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return WorkflowResponse(
                id=new_workflow.id,  # type: ignore
                name=new_workflow.name,  # type: ignore
                integration_id=new_workflow.integration_id,  # type: ignore
                integration_name=integration_name,  # type: ignore
                integration_logo=integration_logo,  # type: ignore
                active=new_workflow.active
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.post("/workflow-steps", response_model=WorkflowStepResponse)
async def create_workflow_step(
    step_data: WorkflowStepCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new workflow step"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Validate: Only one commitment point per workflow
            # Note: Frontend handles toggling, so this is just a safety check
            if step_data.is_commitment_point:
                existing_commitment_count = session.query(WorkflowsStep).filter(
                    WorkflowsStep.workflow_id == step_data.workflow_id,
                    WorkflowsStep.tenant_id == user.tenant_id,
                    WorkflowsStep.is_commitment_point == True,
                    WorkflowsStep.active == True
                ).count()

                # Allow if there's 0 or 1 (the one being updated might already exist)
                if existing_commitment_count > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Workflow already has multiple commitment points. Only one commitment point is allowed per workflow."
                    )

            # Create new workflow step
            new_step = WorkflowsStep(
                workflow_id=step_data.workflow_id,
                name=step_data.name,
                order=step_data.order,
                status_id=step_data.status_id,
                is_commitment_point=step_data.is_commitment_point,
                integration_id=step_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_step)
            session.flush()  # Get the ID

            # Get workflow, status, and integration info
            workflow_name = None
            status_name = None
            integration_name = None
            integration_logo = None

            workflow = session.query(Workflow).filter(
                Workflow.id == new_step.workflow_id,
                Workflow.tenant_id == user.tenant_id
            ).first()
            if workflow:
                workflow_name = workflow.name

            if new_step.status_id:
                status_obj = session.query(Status).filter(
                    Status.id == new_step.status_id,
                    Status.tenant_id == user.tenant_id
                ).first()
                if status_obj:
                    status_name = status_obj.name

            if new_step.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == new_step.integration_id,
                    Integration.tenant_id == user.tenant_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return WorkflowStepResponse(
                id=new_step.id,  # type: ignore
                workflow_id=new_step.workflow_id,  # type: ignore
                workflow_name=workflow_name,  # type: ignore
                name=new_step.name,  # type: ignore
                order=new_step.order,  # type: ignore
                status_id=new_step.status_id,  # type: ignore
                status_name=status_name,  # type: ignore
                is_commitment_point=new_step.is_commitment_point,  # type: ignore
                integration_id=new_step.integration_id,  # type: ignore
                integration_name=integration_name,  # type: ignore
                integration_logo=integration_logo,  # type: ignore
                active=new_step.active
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow step: {str(e)}"
        )


@router.put("/status-mappings/{mapping_id}", response_model=StatusMappingResponse)
async def update_status_mapping(
    mapping_id: int,
    mapping_data: StatusMappingUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a status mapping"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 PUT /status-mappings/{mapping_id} - Request data: {mapping_data.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the existing mapping
            mapping = session.query(StatusMapping).filter(
                StatusMapping.id == mapping_id,
                StatusMapping.tenant_id == user.tenant_id
            ).first()

            if not mapping:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Status mapping not found"
                )

            # Store original values for comparison
            original_status_from = mapping.status_from
            original_status_to = mapping.status_to

            # Update fields if provided
            if mapping_data.status_from is not None:
                mapping.status_from = mapping_data.status_from  # type: ignore
            if mapping_data.status_to is not None:
                mapping.status_to = mapping_data.status_to  # type: ignore

            # Handle category_id - check if field was provided in request
            if 'category_id' in mapping_data.model_dump(exclude_unset=True):
                if mapping_data.category_id is not None:
                    # Validate category exists
                    category = session.query(StatusCategory).filter(
                        StatusCategory.id == mapping_data.category_id,
                        StatusCategory.tenant_id == user.tenant_id,
                        StatusCategory.active == True
                    ).first()
                    if not category:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Active status category {mapping_data.category_id} not found"
                        )
                    mapping.status_category_id = mapping_data.category_id  # type: ignore
                else:
                    # Explicitly set to None to clear the category
                    mapping.status_category_id = None  # type: ignore

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
                    QdrantVector.table_name == 'status_mappings',
                    QdrantVector.record_id == mapping_id
                ).update({
                    'active': mapping_data.active,
                    'last_updated_at': DateTimeHelper.now_default()
                })

            mapping.last_updated_at = DateTimeHelper.now_default()

            # Apply to existing statuses if requested and if status_from or status_to changed
            statuses_updated = 0
            if mapping_data.apply_to_existing_statuses:
                # Determine which original_name to search for
                # If status_from changed, we need to update statuses with the OLD status_from value
                # If status_from didn't change, use the current status_from
                search_original_name = original_status_from if mapping_data.status_from is None else mapping_data.status_from
                new_mapped_name = mapping.status_to
                new_category_id = mapping.status_category_id

                logger.info(f"🔄 Applying mapping update to existing statuses: original_name='{search_original_name}' -> name='{new_mapped_name}', category_id={new_category_id}")

                # Find all statuses with matching original_name (case-insensitive)
                from sqlalchemy import func
                statuses_to_update = session.query(Status).filter(
                    Status.tenant_id == user.tenant_id,
                    func.lower(Status.original_name) == func.lower(search_original_name),
                    Status.active == True
                ).all()

                for status in statuses_to_update:
                    if status.name != new_mapped_name or status.status_category_id != new_category_id:
                        logger.info(f"  📝 Updating Status '{status.original_name}': '{status.name}' -> '{new_mapped_name}', category_id: {status.status_category_id} -> {new_category_id}")
                        status.name = new_mapped_name
                        status.status_category_id = new_category_id
                        status.last_updated_at = DateTimeHelper.now_default()
                        statuses_updated += 1

                logger.info(f"✅ Updated {statuses_updated} existing statuses")

            session.commit()

            # Get category and integration info for response
            category = session.query(StatusCategory).filter(
                StatusCategory.id == mapping.status_category_id
            ).first()

            integration = session.query(Integration).filter(
                Integration.id == mapping.integration_id
            ).first() if mapping.integration_id else None

            return StatusMappingResponse(
                id=mapping.id,  # type: ignore
                status_from=mapping.status_from,  # type: ignore
                status_to=mapping.status_to,  # type: ignore
                category=category.name if category else None,  # type: ignore
                integration_name=integration.provider if integration else None,  # type: ignore
                integration_id=mapping.integration_id,  # type: ignore
                integration_logo=integration.logo_filename if integration else None,  # type: ignore
                active=mapping.active
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating status mapping {mapping_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update status mapping: {str(e)}"
        )


@router.post("/status-mappings/bulk-update", response_model=List[StatusMappingResponse])
async def bulk_update_status_mappings(
    bulk_data: StatusMappingBulkUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Bulk update multiple status mappings in a single transaction"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 BULK UPDATE - {len(bulk_data.mapping_ids)} mappings - Updates: {bulk_data.updates.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Validate all mappings exist and belong to the user's tenant
            mappings = session.query(StatusMapping).filter(
                StatusMapping.id.in_(bulk_data.mapping_ids),
                StatusMapping.tenant_id == user.tenant_id
            ).all()

            if len(mappings) != len(bulk_data.mapping_ids):
                found_ids = {m.id for m in mappings}
                missing_ids = set(bulk_data.mapping_ids) - found_ids
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Status mappings not found: {missing_ids}"
                )

            # If category_id is being updated, validate it exists
            if 'category_id' in bulk_data.updates.model_dump(exclude_unset=True):
                if bulk_data.updates.category_id is not None:
                    category = session.query(StatusCategory).filter(
                        StatusCategory.id == bulk_data.updates.category_id,
                        StatusCategory.tenant_id == user.tenant_id,
                        StatusCategory.active == True
                    ).first()
                    if not category:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Active status category {bulk_data.updates.category_id} not found"
                        )

            # Apply updates to all mappings
            for mapping in mappings:
                if bulk_data.updates.status_from is not None:
                    mapping.status_from = bulk_data.updates.status_from  # type: ignore
                if bulk_data.updates.status_to is not None:
                    mapping.status_to = bulk_data.updates.status_to  # type: ignore

                # Handle category_id - check if field was provided in request
                if 'category_id' in bulk_data.updates.model_dump(exclude_unset=True):
                    if bulk_data.updates.category_id is not None:
                        mapping.status_category_id = bulk_data.updates.category_id  # type: ignore
                    else:
                        # Explicitly set to None to clear the category
                        mapping.status_category_id = None  # type: ignore

                # Handle integration_id - check if field was provided in request
                if 'integration_id' in bulk_data.updates.model_dump(exclude_unset=True):
                    if bulk_data.updates.integration_id is not None:
                        mapping.integration_id = bulk_data.updates.integration_id
                    else:
                        # Explicitly set to None to clear the integration
                        mapping.integration_id = None

                if bulk_data.updates.active is not None:
                    mapping.active = bulk_data.updates.active

                    # Update corresponding vectors in qdrant_vectors
                    session.query(QdrantVector).filter(
                        QdrantVector.tenant_id == user.tenant_id,
                        QdrantVector.table_name == 'status_mappings',
                        QdrantVector.record_id == mapping.id
                    ).update({
                        'active': bulk_data.updates.active,
                        'last_updated_at': DateTimeHelper.now_default()
                    })

                mapping.last_updated_at = DateTimeHelper.now_default()

            # Apply changes to existing statuses if requested
            if bulk_data.updates.apply_to_existing_statuses:
                logger.info(f"🔄 Applying bulk mapping updates to existing statuses...")
                total_statuses_updated = 0

                for mapping in mappings:
                    # Only apply if status_to or category_id was changed
                    if bulk_data.updates.status_to is not None or bulk_data.updates.category_id is not None:
                        # Find all statuses with matching original_name (case-insensitive)
                        from sqlalchemy import func
                        statuses_to_update = session.query(Status).filter(
                            Status.tenant_id == user.tenant_id,
                            func.lower(Status.original_name) == func.lower(mapping.status_from),
                            Status.active == True
                        ).all()

                        new_mapped_name = mapping.status_to
                        new_category_id = mapping.status_category_id

                        for status in statuses_to_update:
                            if status.name != new_mapped_name or status.status_category_id != new_category_id:
                                logger.info(f"  📝 Updating Status '{status.original_name}': '{status.name}' -> '{new_mapped_name}', category_id: {status.status_category_id} -> {new_category_id}")
                                status.name = new_mapped_name
                                status.status_category_id = new_category_id
                                status.last_updated_at = DateTimeHelper.now_default()
                                total_statuses_updated += 1

                logger.info(f"✅ Updated {total_statuses_updated} existing statuses across {len(mappings)} mappings")

            session.commit()

            # Fetch updated mappings with category and integration info
            updated_mappings = session.query(
                StatusMapping,
                StatusCategory.name.label('category_name'),
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).outerjoin(
                StatusCategory, StatusMapping.status_category_id == StatusCategory.id
            ).outerjoin(
                Integration, StatusMapping.integration_id == Integration.id
            ).filter(
                StatusMapping.id.in_(bulk_data.mapping_ids),
                StatusMapping.tenant_id == user.tenant_id
            ).all()

            logger.info(f"✅ BULK UPDATE - Successfully updated {len(updated_mappings)} mappings")

            return [
                StatusMappingResponse(
                    id=mapping.StatusMapping.id,
                    status_from=mapping.StatusMapping.status_from,
                    status_to=mapping.StatusMapping.status_to,
                    category=mapping.category_name,
                    integration_name=mapping.integration_name,
                    integration_id=mapping.StatusMapping.integration_id,
                    integration_logo=mapping.integration_logo,
                    active=mapping.StatusMapping.active
                )
                for mapping in updated_mappings
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk updating status mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk update status mappings: {str(e)}"
        )


@router.post("/status-mappings/bulk-delete")
async def bulk_delete_status_mappings(
    bulk_data: StatusMappingBulkDeleteRequest,
    user: User = Depends(require_authentication)
):
    """Bulk delete multiple status mappings (translation rules only - doesn't affect existing statuses)"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ BULK DELETE - {len(bulk_data.mapping_ids)} status mappings")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all mappings to delete
            mappings = session.query(StatusMapping).filter(
                StatusMapping.id.in_(bulk_data.mapping_ids),
                StatusMapping.tenant_id == user.tenant_id
            ).all()

            if not mappings:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No mappings found to delete"
                )

            # Delete all mappings and their vectors - they're just translation rules
            # Existing statuses in the statuses table are not affected
            for mapping in mappings:
                # Delete from qdrant_vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'status_mappings',
                    QdrantVector.record_id == mapping.id
                ).delete()

                # Delete the mapping
                session.delete(mapping)

            session.commit()

            message = f"Successfully deleted {len(mappings)} mapping(s)"
            logger.info(f"✅ {message}")
            return {"message": message, "deleted": len(mappings)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk deleting status mappings: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk delete status mappings: {str(e)}"
        )


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    workflow_data: WorkflowUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a workflow (container)"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the existing workflow
            workflow = session.query(Workflow).filter(
                Workflow.id == workflow_id,
                Workflow.tenant_id == user.tenant_id
            ).first()

            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )

            # Update fields if provided
            if workflow_data.name is not None:
                workflow.name = workflow_data.name  # type: ignore

            # Handle integration_id - check if field was provided in request
            if 'integration_id' in workflow_data.model_dump(exclude_unset=True):
                if workflow_data.integration_id is not None:
                    workflow.integration_id = workflow_data.integration_id
                else:
                    # Explicitly set to None to clear the integration
                    workflow.integration_id = None

            if workflow_data.active is not None:
                workflow.active = workflow_data.active

                # Update corresponding vectors in qdrant_vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'workflows',
                    QdrantVector.record_id == workflow_id
                ).update({
                    'active': workflow_data.active,
                    'last_updated_at': DateTimeHelper.now_default()
                })

            workflow.last_updated_at = DateTimeHelper.now_default()
            session.commit()

            # Get integration info for response
            integration = session.query(Integration).filter(
                Integration.id == workflow.integration_id
            ).first() if workflow.integration_id else None

            return WorkflowResponse(
                id=workflow.id,  # type: ignore
                name=workflow.name,  # type: ignore
                integration_id=workflow.integration_id,  # type: ignore
                integration_name=integration.provider if integration else None,  # type: ignore
                integration_logo=integration.logo_filename if integration else None,  # type: ignore
                active=workflow.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.put("/workflow-steps/{step_id}", response_model=WorkflowStepResponse)
async def update_workflow_step(
    step_id: int,
    step_data: WorkflowStepUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a workflow step"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the existing workflow step
            step = session.query(WorkflowsStep).filter(
                WorkflowsStep.id == step_id,
                WorkflowsStep.tenant_id == user.tenant_id
            ).first()

            if not step:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow step not found"
                )

            # Validate: Only one commitment point per workflow
            # Note: Frontend handles toggling, so this is just a safety check
            if step_data.is_commitment_point is not None and step_data.is_commitment_point:
                existing_commitment_count = session.query(WorkflowsStep).filter(
                    WorkflowsStep.workflow_id == step.workflow_id,
                    WorkflowsStep.tenant_id == user.tenant_id,
                    WorkflowsStep.id != step_id,  # Exclude current step
                    WorkflowsStep.is_commitment_point == True,
                    WorkflowsStep.active == True
                ).count()

                # Allow if there's 0 or 1 other commitment point (will be toggled off by frontend)
                if existing_commitment_count > 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Workflow already has multiple commitment points. Only one commitment point is allowed per workflow."
                    )

            # Update fields if provided
            if step_data.workflow_id is not None:
                step.workflow_id = step_data.workflow_id  # type: ignore
            if step_data.name is not None:
                step.name = step_data.name  # type: ignore
            if step_data.order is not None:
                step.order = step_data.order  # type: ignore
            # Allow explicit null for status_id
            if hasattr(step_data, 'status_id'):
                step.status_id = step_data.status_id  # type: ignore
            if step_data.is_commitment_point is not None:
                step.is_commitment_point = step_data.is_commitment_point  # type: ignore
            if step_data.integration_id is not None:
                step.integration_id = step_data.integration_id
            if step_data.active is not None:
                step.active = step_data.active

                # Update corresponding vectors in qdrant_vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'workflows_steps',
                    QdrantVector.record_id == step_id
                ).update({
                    'active': step_data.active,
                    'last_updated_at': DateTimeHelper.now_default()
                })

            step.last_updated_at = DateTimeHelper.now_default()
            session.commit()

            # Get workflow, status, and integration info for response
            workflow = session.query(Workflow).filter(
                Workflow.id == step.workflow_id
            ).first()

            status_obj = session.query(Status).filter(
                Status.id == step.status_id
            ).first() if step.status_id else None

            integration = session.query(Integration).filter(
                Integration.id == step.integration_id
            ).first() if step.integration_id else None

            return WorkflowStepResponse(
                id=step.id,  # type: ignore
                workflow_id=step.workflow_id,  # type: ignore
                workflow_name=workflow.name if workflow else None,  # type: ignore
                name=step.name,  # type: ignore
                order=step.order,  # type: ignore
                status_id=step.status_id,  # type: ignore
                status_name=status_obj.name if status_obj else None,  # type: ignore
                is_commitment_point=step.is_commitment_point,  # type: ignore
                integration_id=step.integration_id,  # type: ignore
                integration_name=integration.provider if integration else None,  # type: ignore
                integration_logo=integration.logo_filename if integration else None,  # type: ignore
                active=step.active
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"❌ ERROR updating workflow step {step_id}: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update workflow step: {str(e)}"
        )


@router.delete("/workflow-steps/{step_id}")
async def delete_workflow_step(
    step_id: int,
    user: User = Depends(require_authentication)
):
    """Delete a workflow step (permanent deletion)"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the existing workflow step
            step = session.query(WorkflowsStep).filter(
                WorkflowsStep.id == step_id,
                WorkflowsStep.tenant_id == user.tenant_id
            ).first()

            if not step:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow step not found"
                )

            # Delete corresponding vectors in qdrant_vectors
            session.query(QdrantVector).filter(
                QdrantVector.tenant_id == user.tenant_id,
                QdrantVector.table_name == 'workflows_steps',
                QdrantVector.record_id == step_id
            ).delete(synchronize_session=False)

            # Permanently delete the workflow step
            session.delete(step)
            session.commit()

            return {"message": "Workflow step deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete workflow step: {str(e)}"
        )


@router.delete("/status-mappings/{mapping_id}")
async def delete_status_mapping(
    mapping_id: int,
    user: User = Depends(require_authentication)
):
    """Delete a status mapping (translation rule only - doesn't affect existing statuses)"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the existing mapping
            mapping = session.query(StatusMapping).filter(
                StatusMapping.id == mapping_id,
                StatusMapping.tenant_id == user.tenant_id
            ).first()

            if not mapping:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Status mapping not found"
                )

            # Delete from qdrant_vectors
            session.query(QdrantVector).filter(
                QdrantVector.tenant_id == user.tenant_id,
                QdrantVector.table_name == 'status_mappings',
                QdrantVector.record_id == mapping.id
            ).delete()

            # Delete the mapping - it's just a translation rule
            # Existing statuses in the statuses table are not affected
            session.delete(mapping)
            session.commit()
            return {"message": "Status mapping deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete status mapping: {str(e)}"
        )


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    user: User = Depends(require_authentication)
):
    """Delete a workflow"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the existing workflow
            workflow = session.query(Workflow).filter(
                Workflow.id == workflow_id,
                Workflow.tenant_id == user.tenant_id
            ).first()

            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )

            # Check for dependent WITs (work item types that reference this workflow)
            dependent_wits = session.query(Wit).filter(
                Wit.workflow_id == workflow_id,
                Wit.active == True
            ).count()

            if dependent_wits > 0:
                # Soft delete to preserve WIT references
                workflow.active = False
                from app.core.utils import DateTimeHelper
                workflow.last_updated_at = DateTimeHelper.now_default()
                session.commit()
                return {"message": f"Workflow deactivated successfully ({dependent_wits} WITs preserved)"}
            else:
                from app.core.utils import DateTimeHelper

                # Hard delete: Clean up FKs, delete workflow steps, then delete workflow
                # 1. Clean up workflow_id FK in wits table (including inactive WITs)
                wits_to_cleanup = session.query(Wit).filter(
                    Wit.workflow_id == workflow_id
                ).all()

                for wit in wits_to_cleanup:
                    wit.workflow_id = None  # type: ignore
                    wit.last_updated_at = DateTimeHelper.now_default()  # type: ignore

                # 2. Delete workflow steps and their vectors
                workflow_steps = session.query(WorkflowsStep).filter(
                    WorkflowsStep.workflow_id == workflow_id
                ).all()

                for step in workflow_steps:
                    # Delete step's vectors
                    session.query(QdrantVector).filter(
                        QdrantVector.tenant_id == user.tenant_id,
                        QdrantVector.table_name == 'workflows_steps',
                        QdrantVector.record_id == step.id
                    ).delete(synchronize_session=False)

                    # Delete the step
                    session.delete(step)

                # 3. Delete workflow's vectors
                session.query(QdrantVector).filter(
                    QdrantVector.tenant_id == user.tenant_id,
                    QdrantVector.table_name == 'workflows',
                    QdrantVector.record_id == workflow_id
                ).delete(synchronize_session=False)

                # 4. Finally delete the workflow
                session.delete(workflow)
                session.commit()

                steps_deleted = len(workflow_steps)
                wits_cleaned = len(wits_to_cleanup)
                return {"message": f"Workflow deleted successfully ({steps_deleted} steps removed, {wits_cleaned} WITs cleaned up)"}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"❌ ERROR deleting workflow {workflow_id}: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete workflow: {str(e)}"
        )


@router.post("/workflows/bulk-update", response_model=List[WorkflowResponse])
async def bulk_update_workflows(
    bulk_data: WorkflowBulkUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Bulk update multiple workflows in a single transaction"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 BULK UPDATE - {len(bulk_data.workflow_ids)} workflows - Updates: {bulk_data.updates.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all workflows to update
            workflows = session.query(Workflow).filter(
                Workflow.id.in_(bulk_data.workflow_ids),
                Workflow.tenant_id == user.tenant_id
            ).all()

            if not workflows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No workflows found to update"
                )

            # Get the fields that were explicitly provided in the request
            update_dict = bulk_data.updates.model_dump(exclude_unset=True)

            # Apply updates to each workflow
            for workflow in workflows:
                if 'name' in update_dict:
                    workflow.name = bulk_data.updates.name  # type: ignore
                if 'integration_id' in update_dict:
                    workflow.integration_id = bulk_data.updates.integration_id  # type: ignore
                if 'active' in update_dict:
                    workflow.active = bulk_data.updates.active  # type: ignore

                workflow.last_updated_at = DateTimeHelper.now_default()  # type: ignore

            session.commit()

            # Refresh to get updated data with integration info
            updated_workflows = session.query(
                Workflow,
                Integration.provider.label('integration_name'),
                Integration.logo_filename.label('integration_logo')
            ).outerjoin(
                Integration, Workflow.integration_id == Integration.id
            ).filter(
                Workflow.id.in_(bulk_data.workflow_ids),
                Workflow.tenant_id == user.tenant_id
            ).all()

            logger.info(f"✅ Successfully bulk updated {len(workflows)} workflows")

            return [
                WorkflowResponse(
                    id=workflow.id,
                    name=workflow.name,
                    integration_id=workflow.integration_id,
                    integration_name=integration_name,
                    integration_logo=integration_logo,
                    active=workflow.active
                )
                for workflow, integration_name, integration_logo in updated_workflows
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk updating workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update workflows: {str(e)}"
        )


@router.post("/workflows/bulk-delete")
async def bulk_delete_workflows(
    bulk_data: WorkflowBulkDeleteRequest,
    user: User = Depends(require_authentication)
):
    """Bulk delete multiple workflows"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ BULK DELETE - {len(bulk_data.workflow_ids)} workflows")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all workflows to delete
            workflows = session.query(Workflow).filter(
                Workflow.id.in_(bulk_data.workflow_ids),
                Workflow.tenant_id == user.tenant_id
            ).all()

            if not workflows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No workflows found to delete"
                )

            total_steps_deleted = 0
            total_deactivated = 0
            total_deleted = 0

            for workflow in workflows:
                # Check for dependent WITs
                dependent_wits = session.query(Wit).filter(
                    Wit.workflow_id == workflow.id,
                    Wit.active == True
                ).count()

                if dependent_wits > 0:
                    # Soft delete to preserve WIT references
                    workflow.active = False  # type: ignore
                    workflow.last_updated_at = DateTimeHelper.now_default()  # type: ignore
                    total_deactivated += 1
                else:
                    # Hard delete: Clean up FKs, delete workflow steps, then delete workflow
                    # 1. Clean up workflow_id FK in wits table (including inactive WITs)
                    wits_to_cleanup = session.query(Wit).filter(
                        Wit.workflow_id == workflow.id
                    ).all()

                    for wit in wits_to_cleanup:
                        wit.workflow_id = None  # type: ignore
                        wit.last_updated_at = DateTimeHelper.now_default()  # type: ignore

                    # 2. Delete workflow steps and their vectors
                    workflow_steps = session.query(WorkflowsStep).filter(
                        WorkflowsStep.workflow_id == workflow.id
                    ).all()

                    for step in workflow_steps:
                        # Delete step's vectors
                        session.query(QdrantVector).filter(
                            QdrantVector.tenant_id == user.tenant_id,
                            QdrantVector.table_name == 'workflows_steps',
                            QdrantVector.record_id == step.id
                        ).delete(synchronize_session=False)

                        # Delete the step
                        session.delete(step)
                        total_steps_deleted += 1

                    # 3. Delete workflow's vectors
                    session.query(QdrantVector).filter(
                        QdrantVector.tenant_id == user.tenant_id,
                        QdrantVector.table_name == 'workflows',
                        QdrantVector.record_id == workflow.id
                    ).delete(synchronize_session=False)

                    # 4. Delete the workflow
                    session.delete(workflow)
                    total_deleted += 1

            session.commit()

            logger.info(f"✅ Successfully bulk deleted {total_deleted} workflows, deactivated {total_deactivated}, removed {total_steps_deleted} steps")

            return {
                "message": "Bulk delete completed successfully",
                "deleted": total_deleted,
                "deactivated": total_deactivated,
                "steps_removed": total_steps_deleted
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error bulk deleting workflows: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete workflows: {str(e)}"
        )


@router.get("/status-categories", response_model=List[StatusCategoryResponse])
async def get_status_categories(
    user: User = Depends(require_authentication)
):
    """Get all status categories for current user's tenant"""
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            categories = session.query(StatusCategory).filter(
                StatusCategory.tenant_id == user.tenant_id
            ).order_by(StatusCategory.name).all()

            result = []
            for category in categories:
                integration_name = None
                integration_logo = None
                if category.integration_id:
                    integration = session.query(Integration).filter(
                        Integration.id == category.integration_id
                    ).first()
                    if integration:
                        integration_name = integration.provider
                        integration_logo = integration.logo_filename

                result.append(StatusCategoryResponse(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    is_waiting=category.is_waiting,
                    is_done=category.is_done,
                    integration_id=category.integration_id,
                    integration_name=integration_name,
                    integration_logo=integration_logo,
                    active=category.active
                ))

            return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch status categories: {str(e)}"
        )


@router.post("/status-categories", response_model=StatusCategoryResponse)
async def create_status_category(
    category_data: StatusCategoryCreateRequest,
    user: User = Depends(require_authentication)
):
    """Create a new status category"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Check if category with same name already exists
            existing = session.query(StatusCategory).filter(
                StatusCategory.name == category_data.name,
                StatusCategory.tenant_id == user.tenant_id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Status category '{category_data.name}' already exists"
                )

            # Create new category
            new_category = StatusCategory(
                name=category_data.name,
                description=category_data.description,
                is_waiting=category_data.is_waiting,
                is_done=category_data.is_done,
                integration_id=category_data.integration_id,
                tenant_id=user.tenant_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )

            session.add(new_category)
            session.commit()
            session.refresh(new_category)

            # Get integration info for response
            integration_name = None
            integration_logo = None
            if new_category.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == new_category.integration_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return StatusCategoryResponse(
                id=new_category.id,
                name=new_category.name,
                description=new_category.description,
                is_waiting=new_category.is_waiting,
                is_done=new_category.is_done,
                integration_id=new_category.integration_id,
                integration_name=integration_name,
                integration_logo=integration_logo,
                active=new_category.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create status category: {str(e)}"
        )


@router.put("/status-categories/{category_id}", response_model=StatusCategoryResponse)
async def update_status_category(
    category_id: int,
    category_data: StatusCategoryUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Update a status category"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get the existing category
            category = session.query(StatusCategory).filter(
                StatusCategory.id == category_id,
                StatusCategory.tenant_id == user.tenant_id
            ).first()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Status category not found"
                )

            # Update fields if provided
            if category_data.name is not None:
                # Check if new name conflicts with existing category
                existing = session.query(StatusCategory).filter(
                    StatusCategory.name == category_data.name,
                    StatusCategory.tenant_id == user.tenant_id,
                    StatusCategory.id != category_id
                ).first()

                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Status category '{category_data.name}' already exists"
                    )

                category.name = category_data.name

            if category_data.description is not None:
                category.description = category_data.description

            if category_data.is_waiting is not None:
                category.is_waiting = category_data.is_waiting

            if category_data.is_done is not None:
                category.is_done = category_data.is_done

            # Handle integration_id - check if field was provided in request
            if 'integration_id' in category_data.model_dump(exclude_unset=True):
                if category_data.integration_id is not None:
                    category.integration_id = category_data.integration_id
                else:
                    # Explicitly set to None to clear the integration
                    category.integration_id = None

            if category_data.active is not None:
                category.active = category_data.active

            category.last_updated_at = DateTimeHelper.now_default()

            session.commit()
            session.refresh(category)

            # Get integration info for response
            integration_name = None
            integration_logo = None
            if category.integration_id:
                integration = session.query(Integration).filter(
                    Integration.id == category.integration_id
                ).first()
                if integration:
                    integration_name = integration.provider
                    integration_logo = integration.logo_filename

            return StatusCategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                is_waiting=category.is_waiting,
                is_done=category.is_done,
                integration_id=category.integration_id,
                integration_name=integration_name,
                integration_logo=integration_logo,
                active=category.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update status category: {str(e)}"
        )


@router.delete("/status-categories/{category_id}")
async def delete_status_category(
    category_id: int,
    user: User = Depends(require_authentication)
):
    """Delete a status category"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get the existing category
            category = session.query(StatusCategory).filter(
                StatusCategory.id == category_id,
                StatusCategory.tenant_id == user.tenant_id
            ).first()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Status category not found"
                )

            # Clean up dependent status mappings by setting category_id to NULL
            from app.core.utils import DateTimeHelper
            dependent_mappings = session.query(StatusMapping).filter(
                StatusMapping.status_category_id == category_id
            ).all()

            for mapping in dependent_mappings:
                mapping.status_category_id = None
                mapping.last_updated_at = DateTimeHelper.now_default()

            # Delete the category
            session.delete(category)
            session.commit()
            return {
                "message": "Status category deleted successfully",
                "cleaned_mappings": len(dependent_mappings)
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete status category: {str(e)}"
        )


@router.put("/status-categories/{category_id}/toggle")
async def toggle_status_category(
    category_id: int,
    user: User = Depends(require_authentication)
):
    """Toggle active status of a status category"""
    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            category = session.query(StatusCategory).filter(
                StatusCategory.id == category_id,
                StatusCategory.tenant_id == user.tenant_id
            ).first()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Status category not found"
                )

            category.active = not category.active
            category.last_updated_at = DateTimeHelper.now_default()

            session.commit()
            session.refresh(category)

            return StatusCategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                is_waiting=category.is_waiting,
                is_done=category.is_done,
                active=category.active
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle status category: {str(e)}"
        )


@router.post("/status-categories/bulk-update", response_model=List[StatusCategoryResponse])
async def bulk_update_status_categories(
    bulk_data: StatusCategoryBulkUpdateRequest,
    user: User = Depends(require_authentication)
):
    """Bulk update multiple status categories in a single transaction"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📦 BULK UPDATE - {len(bulk_data.category_ids)} status categories - Updates: {bulk_data.updates.model_dump()}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all categories to update
            categories = session.query(StatusCategory).filter(
                StatusCategory.id.in_(bulk_data.category_ids),
                StatusCategory.tenant_id == user.tenant_id
            ).all()

            if not categories:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No categories found to update"
                )

            # Update all categories
            updated_categories = []
            for category in categories:
                if bulk_data.updates.name is not None:
                    category.name = bulk_data.updates.name  # type: ignore
                if bulk_data.updates.description is not None:
                    category.description = bulk_data.updates.description  # type: ignore
                if bulk_data.updates.is_waiting is not None:
                    category.is_waiting = bulk_data.updates.is_waiting
                if bulk_data.updates.is_done is not None:
                    category.is_done = bulk_data.updates.is_done

                # Handle integration_id - check if field was provided in request
                if 'integration_id' in bulk_data.updates.model_dump(exclude_unset=True):
                    if bulk_data.updates.integration_id is not None:
                        category.integration_id = bulk_data.updates.integration_id
                    else:
                        # Explicitly set to None to clear the integration
                        category.integration_id = None

                if bulk_data.updates.active is not None:
                    category.active = bulk_data.updates.active

                category.last_updated_at = DateTimeHelper.now_default()
                updated_categories.append(category)

            session.commit()

            # Refresh to get updated data with relationships
            for category in updated_categories:
                session.refresh(category)

            # Build response with integration info
            result = []
            for category in updated_categories:
                integration_name = None
                integration_logo = None
                if category.integration_id:
                    integration = session.query(Integration).filter(
                        Integration.id == category.integration_id
                    ).first()
                    if integration:
                        integration_name = integration.provider
                        integration_logo = integration.logo_filename

                result.append(StatusCategoryResponse(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    is_waiting=category.is_waiting,
                    is_done=category.is_done,
                    integration_id=category.integration_id,
                    integration_name=integration_name,
                    integration_logo=integration_logo,
                    active=category.active
                ))

            logger.info(f"✅ Successfully bulk updated {len(result)} status categories")
            return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update status categories: {str(e)}"
        )


@router.post("/status-categories/bulk-delete")
async def bulk_delete_status_categories(
    bulk_data: StatusCategoryBulkDeleteRequest,
    user: User = Depends(require_authentication)
):
    """Bulk delete multiple status categories"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🗑️ BULK DELETE - {len(bulk_data.category_ids)} status categories")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            # Get all categories to delete
            categories = session.query(StatusCategory).filter(
                StatusCategory.id.in_(bulk_data.category_ids),
                StatusCategory.tenant_id == user.tenant_id
            ).all()

            if not categories:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No categories found to delete"
                )

            # Clean up dependent status mappings by setting category_id to NULL
            from app.core.utils import DateTimeHelper
            total_cleaned = 0
            for category in categories:
                dependent_mappings = session.query(StatusMapping).filter(
                    StatusMapping.status_category_id == category.id
                ).all()

                for mapping in dependent_mappings:
                    mapping.status_category_id = None
                    mapping.last_updated_at = DateTimeHelper.now_default()
                    total_cleaned += 1

            # Delete all categories
            for category in categories:
                session.delete(category)

            session.commit()

            logger.info(f"✅ Successfully bulk deleted {len(categories)} status categories, cleaned {total_cleaned} mappings")
            return {
                "message": f"Successfully deleted {len(categories)} status categories",
                "deleted_count": len(categories),
                "cleaned_mappings": total_cleaned
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete status categories: {str(e)}"
        )


@router.post("/status-mappings/remap-all-statuses", response_model=RemapStatusesResponse)
async def remap_all_statuses(
    user: User = Depends(require_authentication)
):
    """
    Scan all Statuses in the database and update their 'name' field based on current status mappings.
    Only updates statuses where the mapped name differs from the current name.
    Matches Status.original_name with StatusMapping.status_from to find the correct mapping.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 REMAP ALL STATUSES - Starting full status remapping for tenant {user.tenant_id}")

    try:
        database = get_database()
        with database.get_write_session_context() as session:
            from app.core.utils import DateTimeHelper

            # Get all active status mappings for this tenant
            mappings = session.query(StatusMapping).filter(
                StatusMapping.tenant_id == user.tenant_id,
                StatusMapping.active == True
            ).all()

            # Create a lookup dictionary: original_name -> mapped_name
            mapping_dict = {m.status_from: m.status_to for m in mappings}

            logger.info(f"📋 Found {len(mapping_dict)} active status mappings")

            # Get all statuses for this tenant
            statuses = session.query(Status).filter(
                Status.tenant_id == user.tenant_id,
                Status.active == True
            ).all()

            total_statuses = len(statuses)
            statuses_updated = 0
            mappings_applied = 0

            # Update statuses based on mappings
            for status in statuses:
                # Check if there's a mapping for this status's original name
                if status.original_name in mapping_dict:
                    mapped_name = mapping_dict[status.original_name]
                    mappings_applied += 1

                    # Only update if the name is different
                    if status.name != mapped_name:
                        logger.info(f"  📝 Updating Status '{status.original_name}': '{status.name}' -> '{mapped_name}'")
                        status.name = mapped_name
                        status.last_updated_at = DateTimeHelper.now_default()
                        statuses_updated += 1

            session.commit()

            message = f"Scanned {total_statuses} statuses, found {mappings_applied} with mappings, updated {statuses_updated} statuses"
            logger.info(f"✅ {message}")

            return RemapStatusesResponse(
                total_statuses_scanned=total_statuses,
                statuses_updated=statuses_updated,
                mappings_applied=mappings_applied,
                message=message
            )

    except Exception as e:
        logger.error(f"❌ Error remapping statuses: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remap statuses: {str(e)}"
        )
