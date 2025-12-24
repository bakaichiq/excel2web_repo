import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.db.models.operation import Operation
from app.schemas.operations import OperationOut, OperationCreate, OperationUpdate
from app.crud.operations import list_operations, create_operation, update_operation, delete_operation

router = APIRouter()

ALLOWED_ROLES_VIEW = (Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)
ALLOWED_ROLES_EDIT = (Role.admin, Role.pto, Role.manager)


@router.get("/operations", response_model=list[OperationOut])
def get_operations(
    project_id: int = Query(...),
    date_from: dt.date | None = Query(None),
    date_to: dt.date | None = Query(None),
    q: str | None = Query(None),
    include_undated: bool = Query(True),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    rows = list_operations(
        db,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
        include_undated=include_undated,
        limit=limit,
        offset=offset,
    )
    out: list[OperationOut] = []
    for op, wbs_path in rows:
        out.append(
            OperationOut(
                id=op.id,
                project_id=op.project_id,
                code=op.code,
                name=op.name,
                wbs_path=wbs_path,
                discipline=op.discipline,
                block=op.block,
                floor=op.floor,
                ugpr=op.ugpr,
                unit=op.unit,
                plan_qty_total=op.plan_qty_total,
                plan_start=op.plan_start,
                plan_finish=op.plan_finish,
            )
        )
    return out


@router.post("/operations", response_model=OperationOut)
def post_operation(
    data: OperationCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    try:
        op = create_operation(db, data)
    except ValueError as e:
        if str(e) == "operation_code_exists":
            raise HTTPException(status_code=409, detail="Operation code already exists")
        raise
    return OperationOut(
        id=op.id,
        project_id=op.project_id,
        code=op.code,
        name=op.name,
        wbs_path=op.wbs.path if op.wbs else None,
        discipline=op.discipline,
        block=op.block,
        floor=op.floor,
        ugpr=op.ugpr,
        unit=op.unit,
        plan_qty_total=op.plan_qty_total,
        plan_start=op.plan_start,
        plan_finish=op.plan_finish,
    )


@router.put("/operations/{operation_id}", response_model=OperationOut)
def put_operation(
    operation_id: int,
    data: OperationUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    op = db.query(Operation).filter(Operation.id == operation_id).one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    op = update_operation(db, op, data)
    return OperationOut(
        id=op.id,
        project_id=op.project_id,
        code=op.code,
        name=op.name,
        wbs_path=op.wbs.path if op.wbs else None,
        discipline=op.discipline,
        block=op.block,
        floor=op.floor,
        ugpr=op.ugpr,
        unit=op.unit,
        plan_qty_total=op.plan_qty_total,
        plan_start=op.plan_start,
        plan_finish=op.plan_finish,
    )


@router.delete("/operations/{operation_id}")
def delete_operation_endpoint(
    operation_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    op = db.query(Operation).filter(Operation.id == operation_id).one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    delete_operation(db, op)
    return {"status": "ok"}
