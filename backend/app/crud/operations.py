import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.models.operation import Operation
from app.db.models.operation_dependency import OperationDependency
from app.db.models.wbs import WBS
from app.schemas.operations import OperationCreate, OperationUpdate


def _get_or_create_wbs(db: Session, project_id: int, path: str | None) -> int | None:
    if not path:
        return None
    p = path.strip()
    if not p:
        return None
    existing = db.query(WBS).filter(WBS.project_id == project_id, WBS.path == p).one_or_none()
    if existing:
        return existing.id
    w = WBS(project_id=project_id, path=p)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w.id


def list_operations(
    db: Session,
    project_id: int,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
    include_undated: bool = True,
    limit: int = 500,
    offset: int = 0,
):
    qry = db.query(Operation, WBS.path).outerjoin(WBS, Operation.wbs_id == WBS.id)
    qry = qry.filter(Operation.project_id == project_id)

    if q:
        q_like = f"%{q.strip()}%"
        qry = qry.filter(or_(Operation.code.ilike(q_like), Operation.name.ilike(q_like)))

    if date_from and date_to:
        overlap = and_(Operation.plan_start <= date_to, Operation.plan_finish >= date_from)
        if include_undated:
            qry = qry.filter(or_(overlap, Operation.plan_start.is_(None), Operation.plan_finish.is_(None)))
        else:
            qry = qry.filter(overlap)

    qry = qry.order_by(Operation.plan_start.is_(None), Operation.plan_start, Operation.code)
    if offset:
        qry = qry.offset(offset)
    if limit:
        qry = qry.limit(limit)

    return qry.all()


def create_operation(db: Session, data: OperationCreate) -> Operation:
    existing = (
        db.query(Operation)
        .filter(Operation.project_id == data.project_id, Operation.code == data.code)
        .one_or_none()
    )
    if existing:
        raise ValueError("operation_code_exists")

    wbs_id = _get_or_create_wbs(db, data.project_id, data.wbs_path)
    op = Operation(
        project_id=data.project_id,
        wbs_id=wbs_id,
        code=data.code.strip(),
        name=data.name.strip(),
        discipline=data.discipline,
        block=data.block,
        floor=data.floor,
        ugpr=data.ugpr,
        plan_qty_total=data.plan_qty_total,
        unit=data.unit,
        plan_start=data.plan_start,
        plan_finish=data.plan_finish,
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def update_operation(db: Session, op: Operation, data: OperationUpdate) -> Operation:
    if data.project_id and data.project_id != op.project_id:
        op.project_id = data.project_id

    if data.code:
        op.code = data.code.strip()
    if data.name:
        op.name = data.name.strip()

    if data.wbs_path is not None:
        op.wbs_id = _get_or_create_wbs(db, op.project_id, data.wbs_path)

    for field in ("discipline", "block", "floor", "ugpr", "unit"):
        v = getattr(data, field)
        if v is not None:
            setattr(op, field, v)

    if data.plan_qty_total is not None:
        op.plan_qty_total = data.plan_qty_total
    if data.plan_start is not None:
        op.plan_start = data.plan_start
    if data.plan_finish is not None:
        op.plan_finish = data.plan_finish

    db.commit()
    db.refresh(op)
    return op


def delete_operation(db: Session, op: Operation) -> None:
    db.delete(op)
    db.commit()


def list_dependencies(db: Session, project_id: int):
    return (
        db.query(OperationDependency)
        .filter(OperationDependency.project_id == project_id)
        .order_by(OperationDependency.id)
        .all()
    )


def create_dependency(db: Session, project_id: int, predecessor_id: int, successor_id: int) -> OperationDependency:
    dep = OperationDependency(
        project_id=project_id,
        predecessor_id=predecessor_id,
        successor_id=successor_id,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


def delete_dependency(db: Session, dep: OperationDependency) -> None:
    db.delete(dep)
    db.commit()
