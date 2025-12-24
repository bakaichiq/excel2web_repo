from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import uuid

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.db.models.import_run import ImportRun
from app.db.models.import_error import ImportError
from app.db.models.baseline import BaselineVolume
from app.db.models.facts import (
    FactVolumeDaily,
    FactResourceDaily,
    PlanVolumeMonthly,
    FactPnLMonthly,
    FactCashflowMonthly,
)
from app.schemas.imports import ImportRunOut, ImportErrorOut
from app.services.etl.utils import file_sha256
from app.services.files import ensure_dirs, save_upload
from app.crud.imports import get_or_create_import_run, list_imports, list_import_errors
from app.worker.tasks import run_import_task
from app.core.config import settings

router = APIRouter()

ALLOWED_ROLES_VIEW = (Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)
ALLOWED_ROLES_EDIT = (Role.admin, Role.pto, Role.finance, Role.manager)


def _ensure_project_exists(db: Session, project_id: int):
    ok = db.execute(text("select 1 from project where id = :pid"), {"pid": project_id}).first()
    if not ok:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")


@router.get("", response_model=list[ImportRunOut])
def get_imports(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    _ensure_project_exists(db, project_id)
    return list_imports(db, project_id)


@router.get("/{import_run_id}/errors", response_model=list[ImportErrorOut])
def get_errors(
    import_run_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    return list_import_errors(db, import_run_id)


@router.delete("/{import_run_id}")
def delete_import_run(
    import_run_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    run = db.query(ImportRun).filter(ImportRun.id == import_run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Import run not found")
    if run.status in ("queued", "running"):
        raise HTTPException(status_code=409, detail="Import is running; cannot delete")

    # delete imported rows for this run
    for model in (
        FactVolumeDaily,
        FactResourceDaily,
        PlanVolumeMonthly,
        FactPnLMonthly,
        FactCashflowMonthly,
        BaselineVolume,
    ):
        db.query(model).filter(model.import_run_id == run.id).delete(synchronize_session=False)

    db.query(ImportError).filter(ImportError.import_run_id == run.id).delete(synchronize_session=False)
    db.query(ImportRun).filter(ImportRun.id == run.id).delete(synchronize_session=False)
    db.commit()

    file_path = Path(settings.UPLOAD_DIR) / f"{run.project_id}_{run.file_hash}.xlsx"
    if file_path.exists():
        file_path.unlink()

    return {"status": "ok"}


@router.post("/upload", response_model=ImportRunOut)
def upload_excel(
    project_id: int = Query(..., description="Project ID (1 file = 1 project)"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    _ensure_project_exists(db, project_id)

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx supported")

    ensure_dirs()

    # уникальный tmp, чтобы параллельные загрузки не перетирали друг друга
    tmp_name = f"tmp_{project_id}_{uuid.uuid4().hex}_{Path(file.filename).name}"
    tmp_path = Path(settings.UPLOAD_DIR) / tmp_name
    save_upload(file, tmp_path)

    file_hash = file_sha256(str(tmp_path))
    final_path = Path(settings.UPLOAD_DIR) / f"{project_id}_{file_hash}.xlsx"

    # если такой файл уже лежит — заменим, но аккуратно
    if final_path.exists():
        final_path.unlink()
    tmp_path.replace(final_path)

    run, created = get_or_create_import_run(db, project_id, file.filename, file_hash)

    # idempotent: тот же файл уже импортировали
    if run.status in ("success", "success_with_errors") and not created:
        return run

    # enqueue celery task
    run_import_task.delay(run.id)
    return run
