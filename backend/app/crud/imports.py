import datetime as dt
from sqlalchemy.orm import Session
from app.db.models.import_run import ImportRun
from app.db.models.import_error import ImportError
from app.services.etl.validators import ValidationError

def get_import_run(db: Session, import_run_id: int) -> ImportRun | None:
    return db.query(ImportRun).filter(ImportRun.id==import_run_id).one_or_none()

def get_or_create_import_run(db: Session, project_id: int, file_name: str, file_hash: str) -> tuple[ImportRun, bool]:
    run = db.query(ImportRun).filter(ImportRun.project_id==project_id, ImportRun.file_hash==file_hash).one_or_none()
    if run:
        return run, False
    run = ImportRun(project_id=project_id, file_name=file_name, file_hash=file_hash, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run, True

def set_import_status(
    db: Session,
    import_run_id: int,
    status: str,
    started_at: dt.datetime | None = None,
    finished_at: dt.datetime | None = None,
    rows_loaded: int | None = None,
):
    run = db.query(ImportRun).filter(ImportRun.id==import_run_id).one()
    run.status = status
    if started_at is not None:
        run.started_at = started_at
    if finished_at is not None:
        run.finished_at = finished_at
    if rows_loaded is not None:
        run.rows_loaded = rows_loaded
    db.commit()

def list_imports(db: Session, project_id: int):
    return db.query(ImportRun).filter(ImportRun.project_id==project_id).order_by(ImportRun.id.desc()).all()

def list_import_errors(db: Session, import_run_id: int):
    return db.query(ImportError).filter(ImportError.import_run_id==import_run_id).order_by(ImportError.id).all()

def clear_import_errors(db: Session, import_run_id: int):
    db.query(ImportError).filter(ImportError.import_run_id==import_run_id).delete()
    db.commit()

def add_import_errors(db: Session, import_run_id: int, errors: list[ValidationError]):
    for er in errors:
        db.add(ImportError(
            import_run_id=import_run_id,
            sheet=er.sheet,
            row_num=er.row_num,
            column=er.column,
            message=er.message
        ))
    db.commit()
