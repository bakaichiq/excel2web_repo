from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.db.models.facts import FactVolumeDaily, FactResourceDaily, FactPnLMonthly, FactCashflowMonthly, PlanVolumeMonthly
from app.schemas.entries import FactVolumeIn, ManhoursIn, PnLIn, CashflowIn

def upsert_fact_volume(db: Session, data: FactVolumeIn):
    stmt = insert(FactVolumeDaily).values(
        project_id=data.project_id,
        import_run_id=None,
        operation_code=data.operation_code,
        operation_name=data.operation_name,
        wbs=data.wbs,
        discipline=data.discipline,
        block=data.block,
        floor=data.floor,
        ugpr=data.ugpr,
        category=data.category,
        item_name=data.item_name,
        unit=data.unit,
        date=data.date,
        qty=data.qty,
        amount=data.amount,
    ).on_conflict_do_update(
        constraint="uq_fact_volume_day",
        set_=dict(qty=data.qty, amount=data.amount, operation_name=data.operation_name, wbs=data.wbs,
                  discipline=data.discipline, block=data.block, floor=data.floor, ugpr=data.ugpr, unit=data.unit),
    )
    db.execute(stmt)
    db.commit()

def upsert_manhours(db: Session, data: ManhoursIn):
    stmt = insert(FactResourceDaily).values(
        project_id=data.project_id,
        import_run_id=None,
        resource_name=data.resource_name,
        category=data.category,
        date=data.date,
        scenario=data.scenario,
        qty=data.qty,
        manhours=data.manhours,
    ).on_conflict_do_update(
        constraint="uq_res_day",
        set_=dict(qty=data.qty, manhours=data.manhours),
    )
    db.execute(stmt)
    db.commit()

def upsert_pnl(db: Session, data: PnLIn):
    stmt = insert(FactPnLMonthly).values(
        project_id=data.project_id,
        import_run_id=None,
        account_name=data.account_name,
        parent_name=data.parent_name,
        month=data.month,
        scenario=data.scenario,
        amount=data.amount,
    ).on_conflict_do_update(
        constraint="uq_pnl_month",
        set_=dict(amount=data.amount, parent_name=data.parent_name),
    )
    db.execute(stmt)
    db.commit()

def upsert_cashflow(db: Session, data: CashflowIn):
    stmt = insert(FactCashflowMonthly).values(
        project_id=data.project_id,
        import_run_id=None,
        account_name=data.account_name,
        parent_name=data.parent_name,
        month=data.month,
        scenario=data.scenario,
        direction=data.direction,
        amount=data.amount,
    ).on_conflict_do_update(
        constraint="uq_cf_month",
        set_=dict(amount=data.amount, parent_name=data.parent_name, direction=data.direction),
    )
    db.execute(stmt)
    db.commit()
