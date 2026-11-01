from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, Workspace, WorkspaceMember

router = APIRouter()

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: str

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    role: Optional[str] = "owner"

@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    results = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if ws:
            results.append(WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
                owner_id=ws.owner_id,
                role=m.role
            ))
    return results

@router.post("", response_model=WorkspaceResponse)
def create_workspace(data: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    slug = data.name.lower().replace(" ", "-") + f"-{current_user.id[:4]}"
    ws = Workspace(
        name=data.name,
        slug=slug,
        owner_id=current_user.id
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    member = WorkspaceMember(workspace_id=ws.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()

    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        owner_id=ws.owner_id,
        role="owner"
    )

@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
def get_members(workspace_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    res = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            res.append(WorkspaceMemberResponse(
                user_id=user.id,
                email=user.email,
                name=user.name,
                role=m.role
            ))
    return res
