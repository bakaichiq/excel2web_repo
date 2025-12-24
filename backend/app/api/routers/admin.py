from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.schemas.admin import UserCreateIn
from app.crud.users import create_user, list_users

router = APIRouter()

@router.get("/users")
def users(db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin))):
    return list_users(db)

@router.post("/users")
def create_user_endpoint(data: UserCreateIn, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin))):
    return create_user(db, data)
