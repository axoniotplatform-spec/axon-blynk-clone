from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
import hashlib
import secrets
from backend.database import get_db
from backend.models.entities import User, Organization
from backend.websocket_hub import hub

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/v1/users", tags=["users"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    organization_name: Optional[str] = None
    role: Optional[str] = "Admin"

class LoginRequest(BaseModel):
    email: str
    password: str

class UserCreateRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = "password123"
    role: Optional[str] = "User"
    org_id: Optional[int] = 1

# In-memory session token store (token -> user_id)
SESSION_TOKENS = {}

@router.post("/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Get or create organization
    org = None
    if payload.organization_name:
        org = Organization(
            name=payload.organization_name,
            plan_tier="FREE",
            timezone="UTC",
            server_region="ny3.blynk.cloud"
        )
        db.add(org)
        db.commit()
        db.refresh(org)
    else:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Default Organization", plan_tier="FREE")
            db.add(org)
            db.commit()
            db.refresh(org)

    new_user = User(
        org_id=org.id,
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role or "Admin",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = f"axon_tok_{secrets.token_urlsafe(32)}"
    SESSION_TOKENS[token] = new_user.id

    # Broadcast real-time user creation event to all connected Web & App clients
    await hub.broadcast_event("onUserCreated", {
        "userId": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "orgName": org.name
    })

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
            "orgId": org.id,
            "orgName": org.name
        }
    }

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    pw_hash = hash_password(payload.password)
    user = db.query(User).filter(User.email == email_clean).first()

    # Simple verify or fallback for test users
    if not user or (user.password_hash != pw_hash and user.password_hash != "argon2_hash_placeholder"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = f"axon_tok_{secrets.token_urlsafe(32)}"
    SESSION_TOKENS[token] = user.id

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "orgId": user.org_id,
            "orgName": user.organization.name if user.organization else "My Organization"
        }
    }

@router.get("/me")
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        tok = authorization.split(" ")[1]
        user_id = SESSION_TOKENS.get(tok)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "orgId": user.org_id,
                    "orgName": user.organization.name if user.organization else "My Organization"
                }

    # Default fallback to primary admin user
    user = db.query(User).first()
    return {
        "id": user.id if user else 1,
        "name": user.name if user else "Sam",
        "email": user.email if user else "samblynkk@gmail.com",
        "role": user.role if user else "Admin",
        "orgId": user.org_id if user else 1,
        "orgName": user.organization.name if user and user.organization else "My organization - 2257TU"
    }

# Team members / Users list endpoint (shared across Web and App)
@users_router.get("")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "organization": u.organization.name if u.organization else "My Organization",
            "status": "Active" if u.is_active else "Inactive",
            "registeredAt": u.created_at.strftime("%b %d, %Y") if u.created_at else "Just now"
        }
        for u in users
    ]

@users_router.post("")
async def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    org = db.query(Organization).filter(Organization.id == payload.org_id).first()
    if not org:
        org = db.query(Organization).first()

    new_user = User(
        org_id=org.id if org else 1,
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password or "password123"),
        name=payload.name,
        role=payload.role or "User",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await hub.broadcast_event("onUserCreated", {
        "userId": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "orgName": org.name if org else "My Organization"
    })

    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "organization": org.name if org else "My Organization",
        "status": "Active",
        "registeredAt": new_user.created_at.strftime("%b %d, %Y")
    }
