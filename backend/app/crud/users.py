from sqlalchemy.orm import Session
from app.db.models.user import User
from app.core.security import hash_password
from app.schemas.admin import UserCreateIn

def get_user_by_login(db: Session, login: str) -> User | None:
    return db.query(User).filter(User.login == login).one_or_none()

def list_users(db: Session):
    return db.query(User).order_by(User.id).all()

def create_user(db: Session, data: UserCreateIn) -> User:
    u = User(login=data.login, password_hash=hash_password(data.password), role=data.role, full_name=data.full_name)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
