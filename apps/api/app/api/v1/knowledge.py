from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    verify_workspace_access,
    get_user_workspace_ids,
    get_default_user_workspace
)
from app.api.v1.auth import get_current_user
from app.models.models import User, Workspace, BusinessTerm, MetricDefinition, BusinessRule
from app.services.query.metric_validator import validate_metric_formula_and_schema, MetricValidationError

router = APIRouter()

# --- Request / Response Models ---

class TermCreate(BaseModel):
    name: str = Field(..., example="Paid Order")
    definition: str = Field(..., example="An order whose payment status is captured and not cancelled.")
    synonyms: List[str] = Field(default_factory=list, example=["successful order", "completed payment"])
    related_table: Optional[str] = "orders"
    related_column: Optional[str] = "status"
    owner: Optional[str] = "Operations"
    workspace_id: Optional[str] = None

class TermUpdate(BaseModel):
    definition: Optional[str] = None
    synonyms: Optional[List[str]] = None
    related_table: Optional[str] = None
    related_column: Optional[str] = None
    owner: Optional[str] = None

class MetricCreate(BaseModel):
    name: str = Field(..., example="Net Revenue")
    description: Optional[str] = "Total revenue from paid orders after promotional discounts."
    formula_sql: str = Field(..., example="SUM(amount)")
    source_tables: List[str] = Field(default_factory=lambda: ["orders"])
    grain: Optional[str] = "order"
    time_column: Optional[str] = "created_at"
    default_filters: List[Dict[str, Any]] = Field(default_factory=list)
    allowed_dimensions: List[str] = Field(default_factory=lambda: ["region", "plan", "channel"])
    unit: Optional[str] = "USD"
    currency: Optional[str] = "$"
    owner: Optional[str] = "Finance Team"
    status: Optional[str] = "draft"  # Must default to draft
    workspace_id: Optional[str] = None

class MetricUpdate(BaseModel):
    description: Optional[str] = None
    formula_sql: Optional[str] = None
    grain: Optional[str] = None
    time_column: Optional[str] = None
    default_filters: Optional[List[Dict[str, Any]]] = None
    allowed_dimensions: Optional[List[str]] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    owner: Optional[str] = None
    change_reason: Optional[str] = "Metric formula update"

# --- Business Terms (Glossary) ---

@router.get("/terms")
def list_terms(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_ws_ids = get_user_workspace_ids(current_user, db)
    if not user_ws_ids:
        ws = get_default_user_workspace(current_user, db)
        user_ws_ids = [ws.id]

    query = db.query(BusinessTerm)
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db)
        query = query.filter(BusinessTerm.workspace_id == workspace_id)
    else:
        query = query.filter(BusinessTerm.workspace_id.in_(user_ws_ids))

    terms = query.order_by(BusinessTerm.name).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "definition": t.definition,
            "synonyms": t.synonyms_json,
            "related_table": t.related_table,
            "related_column": t.related_column,
            "owner": t.owner,
            "status": t.status,
            "approved_by": t.approved_by,
            "approved_at": t.approved_at.isoformat() if t.approved_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in terms
    ]

@router.post("/terms")
def create_term(
    data: TermCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = data.workspace_id
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db, required_roles=["owner", "editor"])
    else:
        ws = get_default_user_workspace(current_user, db)
        workspace_id = ws.id

    term = BusinessTerm(
        workspace_id=workspace_id,
        name=data.name,
        definition=data.definition,
        synonyms_json=data.synonyms,
        related_table=data.related_table,
        related_column=data.related_column,
        owner=data.owner or current_user.name,
        status="draft"
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return {"id": term.id, "name": term.name, "status": term.status}

@router.post("/terms/{term_id}/approve")
def approve_term(
    term_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    term = db.query(BusinessTerm).filter(BusinessTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found.")
    verify_workspace_access(term.workspace_id, current_user, db, required_roles=["owner", "editor"])

    term.status = "approved"
    term.approved_by = current_user.name
    term.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "id": term.id, "status": term.status, "approved_by": term.approved_by}

@router.delete("/terms/{term_id}")
def delete_term(
    term_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    term = db.query(BusinessTerm).filter(BusinessTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found.")
    verify_workspace_access(term.workspace_id, current_user, db, required_roles=["owner", "editor"])
    db.delete(term)
    db.commit()
    return {"success": True, "deleted_id": term_id}

# --- Metric Definitions (Metrics Layer) ---

@router.get("/metrics")
def list_metrics(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_ws_ids = get_user_workspace_ids(current_user, db)
    if not user_ws_ids:
        ws = get_default_user_workspace(current_user, db)
        user_ws_ids = [ws.id]

    query = db.query(MetricDefinition)
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db)
        query = query.filter(MetricDefinition.workspace_id == workspace_id)
    else:
        query = query.filter(MetricDefinition.workspace_id.in_(user_ws_ids))

    if status:
        query = query.filter(MetricDefinition.status == status)

    metrics = query.order_by(MetricDefinition.name).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "formula_sql": m.formula_sql,
            "source_tables": m.source_tables_json,
            "grain": m.grain,
            "time_column": m.time_column,
            "default_filters": m.default_filters_json,
            "allowed_dimensions": m.allowed_dimensions_json,
            "unit": m.unit,
            "currency": m.currency,
            "owner": m.owner,
            "status": m.status,
            "version": m.version,
            "approved_by": m.approved_by,
            "approved_at": m.approved_at.isoformat() if m.approved_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in metrics
    ]

@router.post("/metrics")
def create_metric(
    data: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new metric definition.
    - Validates formula and schema against workspace tables.
    - Automatically enters 'draft' status (never auto-approved).
    """
    workspace_id = data.workspace_id
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db, required_roles=["owner", "editor"])
    else:
        ws = get_default_user_workspace(current_user, db)
        workspace_id = ws.id

    # Validate formula, aggregations, columns, and filters against schema
    try:
        validate_metric_formula_and_schema(
            formula_sql=data.formula_sql,
            source_tables=data.source_tables,
            default_filters=data.default_filters,
            allowed_dimensions=data.allowed_dimensions,
            workspace_id=workspace_id,
            db=db
        )
    except MetricValidationError as err:
        raise HTTPException(status_code=422, detail=f"Metric Schema Validation Error: {str(err)}")

    metric = MetricDefinition(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        formula_sql=data.formula_sql,
        source_tables_json=data.source_tables,
        grain=data.grain or "order",
        time_column=data.time_column,
        default_filters_json=data.default_filters,
        allowed_dimensions_json=data.allowed_dimensions,
        unit=data.unit,
        currency=data.currency,
        owner=data.owner or current_user.name,
        status="draft",  # Strictly draft upon creation
        version=1,
        approved_by=None,
        approved_at=None
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return {
        "id": metric.id,
        "name": metric.name,
        "formula_sql": metric.formula_sql,
        "version": metric.version,
        "status": metric.status
    }

@router.post("/metrics/{metric_id}/submit-review")
def submit_metric_for_review(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a draft metric for team review."""
    metric = db.query(MetricDefinition).filter(MetricDefinition.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found.")

    verify_workspace_access(metric.workspace_id, current_user, db)

    metric.status = "in_review"
    db.commit()
    return {"success": True, "id": metric.id, "status": metric.status}

@router.post("/metrics/{metric_id}/approve")
def approve_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a metric for live query execution in Ask Data.
    Requires workspace owner or editor role and validates schema.
    """
    metric = db.query(MetricDefinition).filter(MetricDefinition.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found.")

    verify_workspace_access(metric.workspace_id, current_user, db, required_roles=["owner", "editor"])

    # Strict pre-approval validation check
    try:
        validate_metric_formula_and_schema(
            formula_sql=metric.formula_sql,
            source_tables=metric.source_tables_json or [],
            default_filters=metric.default_filters_json or [],
            allowed_dimensions=metric.allowed_dimensions_json or [],
            workspace_id=metric.workspace_id,
            db=db
        )
    except MetricValidationError as err:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot approve invalid metric definition: {str(err)}"
        )

    metric.status = "approved"
    metric.approved_by = current_user.name
    metric.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "success": True,
        "id": metric.id,
        "status": metric.status,
        "approved_by": metric.approved_by,
        "approved_at": metric.approved_at.isoformat()
    }

@router.put("/metrics/{metric_id}")
def update_metric_version(
    metric_id: str,
    data: MetricUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifying a metric creates version v(N+1) to preserve audit history.
    """
    old_metric = db.query(MetricDefinition).filter(MetricDefinition.id == metric_id).first()
    if not old_metric:
        raise HTTPException(status_code=404, detail="Metric not found.")

    role = verify_workspace_access(old_metric.workspace_id, current_user, db, required_roles=["owner", "editor"])

    new_formula = data.formula_sql if data.formula_sql is not None else old_metric.formula_sql
    new_filters = data.default_filters if data.default_filters is not None else (old_metric.default_filters_json or [])
    new_dims = data.allowed_dimensions if data.allowed_dimensions is not None else (old_metric.allowed_dimensions_json or [])

    try:
        validate_metric_formula_and_schema(
            formula_sql=new_formula,
            source_tables=old_metric.source_tables_json or [],
            default_filters=new_filters,
            allowed_dimensions=new_dims,
            workspace_id=old_metric.workspace_id,
            db=db
        )
    except MetricValidationError as err:
        raise HTTPException(status_code=422, detail=f"Updated metric validation error: {str(err)}")

    new_version = old_metric.version + 1
    new_metric = MetricDefinition(
        workspace_id=old_metric.workspace_id,
        name=old_metric.name,
        description=data.description if data.description is not None else old_metric.description,
        formula_sql=new_formula,
        source_tables_json=old_metric.source_tables_json,
        grain=data.grain if data.grain is not None else old_metric.grain,
        time_column=data.time_column if data.time_column is not None else old_metric.time_column,
        default_filters_json=new_filters,
        allowed_dimensions_json=new_dims,
        unit=data.unit if data.unit is not None else old_metric.unit,
        currency=data.currency if data.currency is not None else old_metric.currency,
        owner=data.owner if data.owner is not None else old_metric.owner,
        status="approved" if role == "owner" else "in_review",
        version=new_version,
        parent_id=old_metric.id,
        approved_by=current_user.name if role == "owner" else None,
        approved_at=datetime.now(timezone.utc) if role == "owner" else None
    )
    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)

    return {
        "id": new_metric.id,
        "name": new_metric.name,
        "formula_sql": new_metric.formula_sql,
        "version": new_metric.version,
        "previous_version_id": old_metric.id,
        "status": new_metric.status
    }

@router.delete("/metrics/{metric_id}")
def delete_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    metric = db.query(MetricDefinition).filter(MetricDefinition.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found.")
    verify_workspace_access(metric.workspace_id, current_user, db, required_roles=["owner", "editor"])
    db.delete(metric)
    db.commit()
    return {"success": True, "deleted_id": metric_id}
