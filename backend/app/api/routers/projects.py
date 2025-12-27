from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.crud.projects import create_project, list_projects, update_project
from app.db.models.project import Project

router = APIRouter()

@router.get("", response_model=list[ProjectOut])
def get_projects(db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer))):
    return list_projects(db)

@router.post("", response_model=ProjectOut)
def post_project(data: ProjectCreate, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.manager))):
    return create_project(db, data)


@router.put("/{project_id}", response_model=ProjectOut)
def put_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.manager)),
):
    p = db.query(Project).filter(Project.id == project_id).one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return update_project(db, p, data)
