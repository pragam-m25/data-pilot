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
from app.models.models import User, Workspace, DashboardReport, ReportWidget, QueryHistory

router = APIRouter()

class ReportCreate(BaseModel):
    title: str = Field(..., example="Quarterly Revenue & Quality Report")
    description: Optional[str] = None
    workspace_id: Optional[str] = None

class WidgetAdd(BaseModel):
    widget_type: str = Field(..., example="bar")  # kpi, line, bar, table
    title: str = Field(...)
    query_id: str = Field(...)
    chart_config: Optional[Dict[str, Any]] = None

@router.get("")
def list_reports(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_ws_ids = get_user_workspace_ids(current_user, db)
    if not user_ws_ids:
        ws = get_default_user_workspace(current_user, db)
        user_ws_ids = [ws.id]

    query = db.query(DashboardReport)
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db)
        query = query.filter(DashboardReport.workspace_id == workspace_id)
    else:
        query = query.filter(DashboardReport.workspace_id.in_(user_ws_ids))

    reports = query.order_by(DashboardReport.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "widget_count": len(r.widgets),
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        }
        for r in reports
    ]

@router.post("")
def create_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace_id = data.workspace_id
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db, required_roles=["owner", "editor"])
    else:
        ws = get_default_user_workspace(current_user, db)
        workspace_id = ws.id

    report = DashboardReport(
        workspace_id=workspace_id,
        title=data.title,
        description=data.description,
        created_by=current_user.name
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": report.id, "title": report.title, "created_at": report.created_at.isoformat()}

@router.get("/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(DashboardReport).filter(DashboardReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    verify_workspace_access(report.workspace_id, current_user, db)

    widgets = []
    for w in report.widgets:
        # Load underlying verified query for full traceability
        q = db.query(QueryHistory).filter(QueryHistory.id == w.query_id).first() if w.query_id else None
        widgets.append({
            "id": w.id,
            "title": w.title,
            "widget_type": w.widget_type,
            "chart_config": w.chart_config_json,
            "position": w.position,
            "data": {
                "columns": q.result_columns_json if q else [],
                "rows": q.result_rows_json if q else [],
                "sql": q.generated_sql if q else None,
                "execution_ms": q.execution_ms if q else None,
                "how_calculated": q.how_calculated_json if q else {}
            }
        })

    return {
        "id": report.id,
        "title": report.title,
        "description": report.description,
        "created_by": report.created_by,
        "widgets": widgets,
        "created_at": report.created_at.isoformat() if report.created_at else None
    }

@router.post("/{report_id}/widgets")
def add_widget_to_report(
    report_id: str,
    data: WidgetAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(DashboardReport).filter(DashboardReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    verify_workspace_access(report.workspace_id, current_user, db, required_roles=["owner", "editor"])

    query = db.query(QueryHistory).filter(QueryHistory.id == data.query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Underlying verified query not found.")

    verify_workspace_access(query.workspace_id, current_user, db)

    widget = ReportWidget(
        report_id=report_id,
        title=data.title,
        widget_type=data.widget_type,
        query_id=query.id,
        metric_def_id=query.metric_def_id,
        chart_config_json=data.chart_config or {},
        position=len(report.widgets)
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return {"id": widget.id, "title": widget.title, "widget_type": widget.widget_type}

@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(DashboardReport).filter(DashboardReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    verify_workspace_access(report.workspace_id, current_user, db, required_roles=["owner", "editor"])
    db.delete(report)
    db.commit()
    return {"success": True, "deleted_id": report_id}
