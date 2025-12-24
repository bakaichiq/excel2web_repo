from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.schemas.project import ProjectCreate, ProjectOut
from app.crud.projects import create_project, list_projects

router = APIRouter()

@router.get("", response_model=list[ProjectOut])
def get_projects(db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer))):
    return list_projects(db)

@router.post("", response_model=ProjectOut)
def post_project(data: ProjectCreate, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.manager))):
    return create_project(db, data)
