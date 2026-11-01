from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.core.dependencies import (
    verify_workspace_access,
    get_user_workspace_ids,
    get_default_user_workspace
)
from app.core.security import encrypt_secret, decrypt_secret
from app.models.models import User, Workspace, DatabaseConnection
from app.services.connections.postgres_connector import (
    test_postgres_connection,
    introspect_postgres_schema
)

router = APIRouter()

class ConnectionCreate(BaseModel):
    name: str = Field(..., example="Production PostgreSQL")
    host: str = Field(..., example="localhost")
    port: int = Field(5432)
    database: str = Field(..., example="analytics_db")
    username: str = Field(..., example="read_only_user")
    password: str = Field(...)
    schema_name: Optional[str] = "public"
    workspace_id: Optional[str] = None

class ConnectionTestRequest(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str

@router.post("/test")
def test_connection_endpoint(data: ConnectionTestRequest):
    """
    Test real network connection to external PostgreSQL database.
    Never shows fake success.
    """
    res = test_postgres_connection(
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password=data.password,
        timeout_s=5
    )
    return res

@router.post("")
def create_connection(
    data: ConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test and save real PostgreSQL connection.
    Rejects and fails if server is unreachable.
    Encrypts password at rest with AES-256.
    """
    # 1. Test connectivity first
    test_res = test_postgres_connection(
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password=data.password,
        timeout_s=5
    )
    if not test_res["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Connection verification failed: {test_res['error']}"
        )

    # 2. Introspect schema
    try:
        schema_info = introspect_postgres_schema(
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password=data.password,
            target_schema=data.schema_name or "public"
        )
    except Exception as e:
        schema_info = {"error": str(e), "tables": []}

    # 3. Resolve and verify workspace
    workspace_id = data.workspace_id
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db, required_roles=["owner", "editor"])
    else:
        ws = get_default_user_workspace(current_user, db)
        workspace_id = ws.id

    conn_rec = DatabaseConnection(
        workspace_id=workspace_id,
        name=data.name,
        dialect="postgresql",
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        encrypted_password=encrypt_secret(data.password),
        schema_name=data.schema_name or "public",
        is_read_only=True,
        schema_cache_json=schema_info,
        last_tested_at=datetime.now(timezone.utc)
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    return {
        "id": conn_rec.id,
        "name": conn_rec.name,
        "dialect": conn_rec.dialect,
        "host": conn_rec.host,
        "database": conn_rec.database,
        "schema_name": conn_rec.schema_name,
        "table_count": schema_info.get("table_count", 0),
        "is_read_only": conn_rec.is_read_only,
        "latency_ms": test_res.get("latency_ms"),
        "created_at": conn_rec.created_at.isoformat()
    }

@router.get("")
def list_connections(
    workspace_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List only real saved connections belonging to user's authorized workspaces."""
    user_ws_ids = get_user_workspace_ids(current_user, db)
    if not user_ws_ids:
        ws = get_default_user_workspace(current_user, db)
        user_ws_ids = [ws.id]

    query = db.query(DatabaseConnection)
    if workspace_id:
        verify_workspace_access(workspace_id, current_user, db)
        query = query.filter(DatabaseConnection.workspace_id == workspace_id)
    else:
        query = query.filter(DatabaseConnection.workspace_id.in_(user_ws_ids))

    conns = query.all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "dialect": c.dialect,
            "host": c.host,
            "port": c.port,
            "database": c.database,
            "username": c.username,
            "schema_name": c.schema_name,
            "table_count": len(c.schema_cache_json.get("tables", [])) if isinstance(c.schema_cache_json, dict) else 0,
            "is_read_only": c.is_read_only,
            "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in conns
    ]

@router.get("/{connection_id}/schema")
def get_connection_schema(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    verify_workspace_access(conn.workspace_id, current_user, db)
    return conn.schema_cache_json

@router.delete("/{connection_id}")
def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    verify_workspace_access(conn.workspace_id, current_user, db, required_roles=["owner", "editor"])
    db.delete(conn)
    db.commit()
    return {"success": True, "deleted_id": connection_id}
