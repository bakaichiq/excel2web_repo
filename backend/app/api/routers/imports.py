from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import uuid
import datetime as dt

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
from app.services.reports.service import kpi as kpi_calc, plan_fact_table_by as pft_calc
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


@router.get("/compare")
def compare_imports(
    project_id: int = Query(...),
    run_a: int = Query(...),
    run_b: int = Query(...),
    date_from: str = Query(...),
    date_to: str = Query(...),
    by: str = Query("wbs", pattern="^(wbs|discipline|block|floor|ugpr)$"),
    scenario: str = Query("plan", pattern="^(plan|forecast|actual)$"),
    wbs_path: str | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    _ensure_project_exists(db, project_id)
    if run_a == run_b:
        raise HTTPException(status_code=400, detail="run_a and run_b must be different")

    dt_from = dt.datetime.strptime(date_from, "%Y-%m-%d").date()
    dt_to = dt.datetime.strptime(date_to, "%Y-%m-%d").date()

    def _check_run(run_id: int):
        run = db.query(ImportRun).filter(ImportRun.id == run_id, ImportRun.project_id == project_id).one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail=f"Import run {run_id} not found")
        return run

    _check_run(run_a)
    _check_run(run_b)

    kpi_a = kpi_calc(db, project_id, dt_from, dt_to, wbs_path=wbs_path, import_run_id=run_a)
    kpi_b = kpi_calc(db, project_id, dt_from, dt_to, wbs_path=wbs_path, import_run_id=run_b)

    table_a = pft_calc(
        db,
        project_id,
        dt_from,
        dt_to,
        by=by,
        scenario=scenario,
        wbs_path=wbs_path,
        import_run_id=run_a,
    )
    table_b = pft_calc(
        db,
        project_id,
        dt_from,
        dt_to,
        by=by,
        scenario=scenario,
        wbs_path=wbs_path,
        import_run_id=run_b,
    )

    map_a = {r["key"]: r for r in table_a.get("rows", [])}
    map_b = {r["key"]: r for r in table_b.get("rows", [])}
    keys = sorted(set(map_a.keys()) | set(map_b.keys()))
    rows = []
    for key in keys:
        a = map_a.get(key, {"fact": 0.0, "plan": 0.0, "variance": 0.0, "progress_pct": 0.0})
        b = map_b.get(key, {"fact": 0.0, "plan": 0.0, "variance": 0.0, "progress_pct": 0.0})
        rows.append(
            {
                "key": key,
                "a": a,
                "b": b,
                "delta": {
                    "fact": float(b["fact"]) - float(a["fact"]),
                    "plan": float(b["plan"]) - float(a["plan"]),
                    "variance": float(b["variance"]) - float(a["variance"]),
                    "progress_pct": float(b["progress_pct"]) - float(a["progress_pct"]),
                },
            }
        )

    return {
        "project_id": project_id,
        "run_a": run_a,
        "run_b": run_b,
        "period": {"date_from": dt_from.isoformat(), "date_to": dt_to.isoformat()},
        "kpi": {
            "a": kpi_a,
            "b": kpi_b,
            "delta": {
                "fact_qty": kpi_b["fact_qty"] - kpi_a["fact_qty"],
                "plan_qty": kpi_b["plan_qty"] - kpi_a["plan_qty"],
                "progress_pct": kpi_b["progress_pct"] - kpi_a["progress_pct"],
                "manhours": kpi_b["manhours"] - kpi_a["manhours"],
                "productivity": (
                    (kpi_b["productivity"] or 0.0) - (kpi_a["productivity"] or 0.0)
                ),
            },
        },
        "table": {"by": by, "scenario": scenario, "rows": rows},
    }
