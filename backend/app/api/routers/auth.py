from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.auth import LoginIn, TokenOut, UserOut
from app.crud.users import get_user_by_login
from app.core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = get_user_by_login(db, data.login)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(sub=user.login, role=role)
    return TokenOut(access_token=token)

@router.get("/me", response_model=UserOut)
def me(user = Depends(get_current_user)):
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return UserOut(id=user.id, login=user.login, full_name=user.full_name, role=role)
