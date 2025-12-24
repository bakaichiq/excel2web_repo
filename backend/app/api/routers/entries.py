from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.schemas.entries import FactVolumeIn, ManhoursIn, PnLIn, CashflowIn
from app.crud.entries import upsert_fact_volume, upsert_manhours, upsert_pnl, upsert_cashflow

router = APIRouter()

@router.post("/fact-volume")
def post_fact_volume(data: FactVolumeIn, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.pto, Role.manager))):
    upsert_fact_volume(db, data)
    return {"status": "ok"}

@router.post("/manhours")
def post_manhours(data: ManhoursIn, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.pto, Role.manager))):
    upsert_manhours(db, data)
    return {"status": "ok"}

@router.post("/pnl")
def post_pnl(data: PnLIn, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.finance, Role.manager))):
    upsert_pnl(db, data)
    return {"status": "ok"}

@router.post("/cashflow")
def post_cashflow(data: CashflowIn, db: Session = Depends(get_db), _user=Depends(require_roles(Role.admin, Role.finance, Role.manager))):
    upsert_cashflow(db, data)
    return {"status": "ok"}
