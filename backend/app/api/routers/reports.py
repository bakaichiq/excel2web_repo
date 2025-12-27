import datetime as dt
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.schemas.reports import KPIOut, PlanFactSeries, PlanFactTable, MoneySeriesOut
from app.services.reports.service import kpi as kpi_calc, plan_fact_series as pfs_calc, plan_fact_table_by as pft_calc, pnl as pnl_calc, cashflow as cf_calc, ugpr_series as ugpr_calc
from app.services.exports.exporter import export_plan_fact_xlsx, export_kpi_pdf, default_export_path
from app.core.config import settings

router = APIRouter()

def _parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()

@router.get("/kpi", response_model=KPIOut)
def kpi(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    wbs_path: str | None = Query(None),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)),
):
    return kpi_calc(db, project_id, date_from, date_to, wbs_path=wbs_path, import_run_id=import_run_id)

@router.get("/plan-fact/series", response_model=PlanFactSeries)
def plan_fact_series(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    wbs_path: str | None = Query(None),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)),
):
    return pfs_calc(db, project_id, date_from, date_to, granularity=granularity, wbs_path=wbs_path, import_run_id=import_run_id)

@router.get("/plan-fact/table", response_model=PlanFactTable)
def plan_fact_table(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    by: str = Query("wbs", pattern="^(wbs|discipline|block|floor|ugpr)$"),
    scenario: str = Query("plan", pattern="^(plan|forecast|actual)$"),
    wbs_path: str | None = Query(None),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)),
):
    return pft_calc(db, project_id, date_from, date_to, by=by, scenario=scenario, wbs_path=wbs_path, import_run_id=import_run_id)

@router.get("/pnl")
def pnl(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    scenario: str = Query("plan"),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.finance, Role.manager, Role.viewer)),
):
    return pnl_calc(db, project_id, date_from, date_to, scenario=scenario, import_run_id=import_run_id)

@router.get("/cashflow")
def cashflow(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    scenario: str = Query("plan"),
    opening_balance: float = Query(settings.OPENING_CASH_BALANCE),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.finance, Role.manager, Role.viewer)),
):
    return cf_calc(db, project_id, date_from, date_to, scenario=scenario, opening_balance=opening_balance, import_run_id=import_run_id)

@router.get("/ugpr/series", response_model=MoneySeriesOut)
def ugpr_series(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    wbs_path: str | None = Query(None),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)),
):
    return ugpr_calc(db, project_id, date_from, date_to, granularity=granularity, wbs_path=wbs_path, import_run_id=import_run_id)

@router.get("/export/plan-fact.xlsx")
def export_plan_fact(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager)),
):
    data = pfs_calc(db, project_id, date_from, date_to, granularity="month", import_run_id=import_run_id)
    out = default_export_path(f"plan_fact_{project_id}", "xlsx")
    export_plan_fact_xlsx(data, out)
    return FileResponse(str(out), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=out.name)

@router.get("/export/kpi.pdf")
def export_kpi(
    project_id: int = Query(...),
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(Role.admin, Role.pto, Role.finance, Role.manager)),
):
    data = kpi_calc(db, project_id, date_from, date_to, import_run_id=import_run_id)
    out = default_export_path(f"kpi_{project_id}", "pdf")
    export_kpi_pdf(data, out)
    return FileResponse(str(out), media_type="application/pdf", filename=out.name)
