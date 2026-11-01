import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_duckdb_path
from app.core.dependencies import (
    verify_workspace_access,
    get_user_workspace_ids
)
from app.api.v1.auth import get_current_user
from app.core.security import decrypt_secret
from app.models.models import (
    User, Workspace, DataSource, BusinessTerm, MetricDefinition, QueryHistory, DatabaseConnection
)
from app.services.query.nl_resolver import resolve_nl_query_intent, execute_duckdb_query
from app.services.connections.postgres_connector import execute_readonly_postgres_query

router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(..., example="What is our total revenue by region?")
    source_id: str = Field(...)

class ExecuteRequest(BaseModel):
    query_id: str = Field(...)
    confirmed: bool = Field(True)

@router.post("/ask")
def ask_question(
    data: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve natural language question against approved metric definitions.
    Strictly prevents LLM hallucination: if term or formula is missing/ambiguous,
    clarification is requested.
    """
    source = db.query(DataSource).filter(DataSource.id == data.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Selected data source not found.")

    verify_workspace_access(source.workspace_id, current_user, db)

    workspace_id = source.workspace_id

    # Load approved metrics and terms
    terms = db.query(BusinessTerm).filter(BusinessTerm.workspace_id == workspace_id).all()
    metrics = db.query(MetricDefinition).filter(
        MetricDefinition.workspace_id == workspace_id,
        MetricDefinition.status == "approved"
    ).all()

    resolution = resolve_nl_query_intent(
        question=data.question,
        terms=terms,
        metrics=metrics,
        source=source
    )

    if resolution["status"] != "ready_to_execute":
        return resolution

    # Save prepared query to QueryHistory
    query_rec = QueryHistory(
        workspace_id=workspace_id,
        user_id=current_user.id,
        question=data.question,
        metric_def_id=resolution.get("metric_id"),
        source_id=source.id,
        generated_sql=resolution["sql"],
        validation_status="valid",
        status="ready",
        how_calculated_json=resolution["how_calculated"]
    )
    db.add(query_rec)
    db.commit()
    db.refresh(query_rec)

    resolution["query_id"] = query_rec.id
    return resolution

@router.post("/execute")
def execute_query(
    data: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute validated read-only SQL on DuckDB dataset or PostgreSQL connection.
    Saves full calculation lineage and result metadata for auditability.
    """
    query_rec = db.query(QueryHistory).filter(QueryHistory.id == data.query_id).first()
    if not query_rec:
        raise HTTPException(status_code=404, detail="Prepared query not found.")

    verify_workspace_access(query_rec.workspace_id, current_user, db)

    source = db.query(DataSource).filter(DataSource.id == query_rec.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Underlying data source not found.")

    if not data.confirmed:
        query_rec.status = "blocked"
        db.commit()
        return {"status": "blocked", "message": "Execution cancelled by user."}

    # Execute based on source type
    if source.file_type in ["csv", "xlsx"]:
        duckdb_path = get_duckdb_path(source.id)
        if not os.path.exists(duckdb_path):
            raise HTTPException(status_code=404, detail="DuckDB analytics file not found.")

        try:
            exec_res = execute_duckdb_query(duckdb_path, query_rec.generated_sql)
        except Exception as e:
            query_rec.status = "failed"
            query_rec.validation_errors_json = [str(e)]
            db.commit()
            raise HTTPException(status_code=422, detail=f"Execution error: {str(e)}")

    elif source.file_type == "postgresql":
        conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == source.connection_id).first()
        if not conn:
            raise HTTPException(status_code=404, detail="Associated PostgreSQL connection not found.")

        raw_pwd = decrypt_secret(conn.encrypted_password)
        try:
            exec_res = execute_readonly_postgres_query(
                host=conn.host,
                port=conn.port,
                database=conn.database,
                username=conn.username,
                password=raw_pwd,
                query_sql=query_rec.generated_sql
            )
        except Exception as e:
            query_rec.status = "failed"
            query_rec.validation_errors_json = [str(e)]
            db.commit()
            raise HTTPException(status_code=422, detail=f"PostgreSQL execution error: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source type: {source.file_type}")

    # Persist results in audit record
    query_rec.status = "executed"
    query_rec.result_rows_json = exec_res["rows"]
    query_rec.result_columns_json = exec_res["columns"]
    query_rec.execution_ms = exec_res["execution_ms"]
    query_rec.row_count = exec_res["row_count"]

    how_calc = query_rec.how_calculated_json or {}
    how_calc["execution_ms"] = exec_res["execution_ms"]
    how_calc["row_count"] = exec_res["row_count"]
    how_calc["executed_at"] = datetime.now(timezone.utc).isoformat()
    query_rec.how_calculated_json = how_calc

    db.commit()

    return {
        "query_id": query_rec.id,
        "status": "executed",
        "sql": query_rec.generated_sql,
        "columns": exec_res["columns"],
        "rows": exec_res["rows"],
        "row_count": exec_res["row_count"],
        "execution_ms": exec_res["execution_ms"],
        "how_calculated": how_calc
    }

@router.get("/history")
def get_query_history(
    source_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve verified query audit log filtered by user's authorized workspaces."""
    user_ws_ids = get_user_workspace_ids(current_user, db)
    query = db.query(QueryHistory)
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db)
        query = query.filter(QueryHistory.workspace_id == workspace_id)
    else:
        query = query.filter(QueryHistory.workspace_id.in_(user_ws_ids))

    if source_id:
        query = query.filter(QueryHistory.source_id == source_id)
    history = query.order_by(QueryHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "id": q.id,
            "question": q.question,
            "sql": q.generated_sql,
            "status": q.status,
            "execution_ms": q.execution_ms,
            "row_count": q.row_count,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "how_calculated": q.how_calculated_json
        }
        for q in history
    ]

@router.get("/{query_id}")
def get_query_detail(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query record not found.")
    verify_workspace_access(q.workspace_id, current_user, db)
    return {
        "id": q.id,
        "question": q.question,
        "sql": q.generated_sql,
        "status": q.status,
        "columns": q.result_columns_json,
        "rows": q.result_rows_json,
        "row_count": q.row_count,
        "execution_ms": q.execution_ms,
        "how_calculated": q.how_calculated_json,
        "created_at": q.created_at.isoformat() if q.created_at else None
    }
