"""
Portfolio Report API Routes
Handles portfolio reporting and analytics
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app.auth.auth_middleware import require_authentication
from app.core.database import get_database
from app.models.unified_models import User, WorkItem, Wit, WitMapping, WitHierarchy, Status, Project
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class WorkItemTreeNode(BaseModel):
    """Work item node in the tree structure"""
    id: int
    external_id: Optional[str]
    key: Optional[str]
    summary: Optional[str]
    wit_name: Optional[str]
    wit_to: Optional[str]
    level_name: Optional[str]
    level_number: Optional[int]
    status_name: Optional[str]
    priority: Optional[str]
    assignee: Optional[str]
    story_points: Optional[float]
    parent_external_id: Optional[str]
    children: List['WorkItemTreeNode'] = []


class PortfolioTreeResponse(BaseModel):
    """Response model for portfolio tree"""
    success: bool
    tree: List[WorkItemTreeNode]
    total_items: int


@router.get("/portfolio/tree", response_model=PortfolioTreeResponse)
async def get_portfolio_tree(
    user: User = Depends(require_authentication),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    team: Optional[str] = Query(None, description="Filter by team"),
    wit_type: Optional[str] = Query(None, description="Filter by work item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority")
):
    """
    Get work items in hierarchical tree structure.
    
    The hierarchy is built using:
    1. wits_hierarchies table - defines hierarchy levels (level_number)
    2. wits_mappings table - maps wit_from to wit_to and hierarchy level
    3. work_items.parent_external_id - links to work_items.external_id for parent-child relationships
    """
    try:
        database = get_database()
        with database.get_read_session_context() as session:
            # Build query with joins to get hierarchy information
            query = session.query(
                WorkItem.id,
                WorkItem.external_id,
                WorkItem.key,
                WorkItem.summary,
                WorkItem.parent_external_id,
                WorkItem.priority,
                WorkItem.assignee,
                WorkItem.story_points,
                Wit.original_name.label('wit_name'),
                WitMapping.wit_to,
                WitHierarchy.level_name,
                WitHierarchy.level_number,
                Status.original_name.label('status_name')
            ).join(
                Wit, WorkItem.wit_id == Wit.id
            ).outerjoin(
                WitMapping, Wit.wits_mapping_id == WitMapping.id
            ).outerjoin(
                WitHierarchy, WitMapping.wits_hierarchy_id == WitHierarchy.id
            ).outerjoin(
                Status, WorkItem.status_id == Status.id
            ).filter(
                WorkItem.tenant_id == user.tenant_id,
                WorkItem.active == True
            )

            # Apply filters
            if project_id:
                query = query.filter(WorkItem.project_id == project_id)
            if team:
                query = query.filter(WorkItem.team == team)
            if wit_type:
                query = query.filter(WitMapping.wit_to == wit_type)
            if status:
                query = query.filter(Status.original_name == status)
            if priority:
                query = query.filter(WorkItem.priority == priority)

            # Order by hierarchy level (highest first) and then by key
            query = query.order_by(
                WitHierarchy.level_number.desc().nullslast(),
                WorkItem.key
            )

            results = query.all()

            # Convert to dictionary for easier lookup
            items_dict: Dict[str, Dict[str, Any]] = {}
            for row in results:
                item_data = {
                    'id': row.id,
                    'external_id': row.external_id,
                    'key': row.key,
                    'summary': row.summary,
                    'wit_name': row.wit_name,
                    'wit_to': row.wit_to,
                    'level_name': row.level_name,
                    'level_number': row.level_number,
                    'status_name': row.status_name,
                    'priority': row.priority,
                    'assignee': row.assignee,
                    'story_points': row.story_points,
                    'parent_external_id': row.parent_external_id,
                    'children': []
                }
                if row.external_id:
                    items_dict[row.external_id] = item_data

            # Build tree structure
            root_items = []
            for external_id, item in items_dict.items():
                parent_ext_id = item['parent_external_id']
                if parent_ext_id and parent_ext_id in items_dict:
                    # Add as child to parent
                    items_dict[parent_ext_id]['children'].append(item)
                else:
                    # Root level item (no parent or parent not in filtered set)
                    root_items.append(item)

            # Sort root items by hierarchy level (highest first), then by key
            def sort_key(item):
                level = item.get('level_number')
                key = item.get('key') or ''
                # Use negative level for descending order, handle None
                return (-(level if level is not None else -999), key)

            root_items.sort(key=sort_key)

            # Recursively sort children at each level
            def sort_children(items):
                for item in items:
                    if item['children']:
                        item['children'].sort(key=sort_key)
                        sort_children(item['children'])

            sort_children(root_items)

            return PortfolioTreeResponse(
                success=True,
                tree=root_items,
                total_items=len(results)
            )

    except Exception as e:
        logger.error(f"Failed to fetch portfolio tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch portfolio tree: {str(e)}"
        )

