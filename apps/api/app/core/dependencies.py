from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import User, Workspace, WorkspaceMember

def get_user_workspace_ids(user: User, db: Session) -> List[str]:
    """Return all workspace IDs that the user owns or belongs to."""
    owned = db.query(Workspace.id).filter(Workspace.owner_id == user.id).all()
    member_of = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == user.id).all()
    all_ids = set([r[0] for r in owned] + [r[0] for r in member_of])
    return list(all_ids)

def get_user_workspace_role(user: User, workspace_id: str, db: Session) -> Optional[str]:
    """Return the user's role in the given workspace (owner, editor, viewer), or None if not a member."""
    # Check if user is workspace owner
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        return None
    if ws.owner_id == user.id:
        return "owner"
    
    # Check membership table
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()
    if membership:
        return membership.role
    return None

def verify_workspace_access(
    workspace_id: str,
    user: User,
    db: Session,
    required_roles: Optional[List[str]] = None
) -> str:
    """
    Verify user has access to the workspace.
    Raises 404 if workspace doesn't exist,
    Raises 403 if user is not a member or lacks required roles.
    Returns user's role.
    """
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found."
        )

    role = get_user_workspace_role(user, workspace_id, db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have access to this workspace."
        )

    if required_roles and role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Action requires one of {required_roles} roles. Your role is '{role}'."
        )

    return role

def get_default_user_workspace(user: User, db: Session) -> Workspace:
    """Resolve or auto-provision the user's primary workspace."""
    ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
    if not ws:
        member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
        if member:
            ws = db.query(Workspace).filter(Workspace.id == member.workspace_id).first()
    if not ws:
        ws = Workspace(
            name=f"{user.name}'s Workspace",
            slug=f"ws-{user.id[:8]}",
            owner_id=user.id
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)
        member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
        db.add(member)
        db.commit()
    return ws
