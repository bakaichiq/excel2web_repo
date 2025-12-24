from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.config import settings
from app.crud.users import get_user_by_login, create_user
from app.schemas.admin import UserCreateIn
from app.db.models.user import Role
from app.crud.projects import list_projects, create_project
from app.schemas.project import ProjectCreate

def seed_demo():
    db: Session = SessionLocal()
    try:
        if settings.DEMO_ADMIN_LOGIN and settings.DEMO_ADMIN_PASSWORD:
            u = get_user_by_login(db, settings.DEMO_ADMIN_LOGIN)
            if not u:
                create_user(db, UserCreateIn(
                    login=settings.DEMO_ADMIN_LOGIN,
                    password=settings.DEMO_ADMIN_PASSWORD,
                    role=Role.admin.value,
                    full_name="Demo Admin",
                ))
        # Create default project if none
        if not list_projects(db):
            create_project(db, ProjectCreate(code="PRJ-1", name="Demo Project", description="Seeded demo project"))
    finally:
        db.close()
