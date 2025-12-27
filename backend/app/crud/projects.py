from sqlalchemy.orm import Session
from app.db.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

def list_projects(db: Session):
    return db.query(Project).order_by(Project.id).all()

def get_project(db: Session, project_id: int) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).one_or_none()

def create_project(db: Session, data: ProjectCreate) -> Project:
    p = Project(
        code=data.code,
        name=data.name,
        description=data.description,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_project(db: Session, p: Project, data: ProjectUpdate) -> Project:
    if data.code is not None:
        p.code = data.code
    if data.name is not None:
        p.name = data.name
    if data.description is not None:
        p.description = data.description
    db.commit()
    db.refresh(p)
    return p
