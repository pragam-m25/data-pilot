from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from app.models.models import User, Workspace, WorkspaceMember

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = "DataPilot Pioneer"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # Strictly reject unauthenticated requests in production
    if not token:
        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # In local development mode only, fallback to demo user
        user = db.query(User).filter(User.email == "demo@datapilot.dev").first()
        if not user:
            user = User(
                email="demo@datapilot.dev",
                name="Alex Demo",
                password_hash=get_password_hash("datapilot123"),
                role="admin"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create default workspace
            workspace = Workspace(
                name="Default Workspace",
                slug="default-workspace",
                owner_id=user.id
            )
            db.add(workspace)
            db.commit()
            db.refresh(workspace)

            member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
            db.add(member)
            db.commit()

        return user

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/signup", response_model=TokenResponse)
def signup(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        name=data.name or "User",
        password_hash=get_password_hash(data.password),
        role="member"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Automatically provision primary workspace
    slug = f"ws-{user.id[:8]}"
    workspace = Workspace(
        name=f"{user.name}'s Workspace",
        slug=slug,
        owner_id=user.id
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
    db.add(member)
    db.commit()

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role)
    )

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role
    )
