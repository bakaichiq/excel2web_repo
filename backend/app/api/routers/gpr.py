import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_db, require_roles
from app.db.models.user import Role
from app.db.models.operation import Operation
from app.db.models.operation_dependency import OperationDependency
from app.db.models.facts import FactVolumeDaily
from app.schemas.operations import (
    OperationOut,
    OperationCreate,
    OperationUpdate,
    OperationGanttOut,
    DependencyCreate,
    DependencyOut,
    GanttOut,
)
from app.crud.operations import (
    list_operations,
    create_operation,
    update_operation,
    delete_operation,
    list_dependencies,
    create_dependency,
    delete_dependency,
)
from app.services.reports.service import _effective_import_run_id, _apply_import_run_filter

router = APIRouter()

ALLOWED_ROLES_VIEW = (Role.admin, Role.pto, Role.finance, Role.manager, Role.viewer)
ALLOWED_ROLES_EDIT = (Role.admin, Role.pto, Role.manager)


def _is_valid_wbs(wbs_path: str | None, name: str | None) -> bool:
    if not wbs_path or not wbs_path.strip():
        return False
    nm = (name or "").strip().lower()
    if nm.startswith("иср"):
        return False
    return True


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
        if not _is_valid_wbs(wbs_path, op.name):
            continue
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


@router.get("/dependencies", response_model=list[DependencyOut])
def get_dependencies(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    return list_dependencies(db, project_id)


@router.post("/dependencies", response_model=DependencyOut)
def post_dependency(
    data: DependencyCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    if data.predecessor_id == data.successor_id:
        raise HTTPException(status_code=400, detail="predecessor_id and successor_id must differ")
    dep = create_dependency(db, data.project_id, data.predecessor_id, data.successor_id)
    return DependencyOut(
        id=dep.id,
        project_id=dep.project_id,
        predecessor_id=dep.predecessor_id,
        successor_id=dep.successor_id,
    )


@router.delete("/dependencies/{dependency_id}")
def delete_dependency_endpoint(
    dependency_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_EDIT)),
):
    dep = db.query(OperationDependency).filter(OperationDependency.id == dependency_id).one_or_none()
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    delete_dependency(db, dep)
    return {"status": "ok"}


@router.get("/gantt", response_model=GanttOut)
def gantt(
    project_id: int = Query(...),
    date_from: dt.date | None = Query(None),
    date_to: dt.date | None = Query(None),
    q: str | None = Query(None),
    include_undated: bool = Query(True),
    import_run_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ALLOWED_ROLES_VIEW)),
):
    ops_rows = list_operations(
        db,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
        include_undated=include_undated,
        limit=2000,
        offset=0,
    )
    ops: list[Operation] = []
    wbs_map: dict[int, str | None] = {}
    for op, wbs_path in ops_rows:
        if not _is_valid_wbs(wbs_path, op.name):
            continue
        ops.append(op)
        wbs_map[op.id] = wbs_path

    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    fact_q = (
        db.query(FactVolumeDaily.operation_code, func.coalesce(func.sum(FactVolumeDaily.qty), 0.0).label("qty"))
        .filter(FactVolumeDaily.project_id == project_id)
    )
    if date_from:
        fact_q = fact_q.filter(FactVolumeDaily.date >= date_from)
    if date_to:
        fact_q = fact_q.filter(FactVolumeDaily.date <= date_to)
    fact_q = _apply_import_run_filter(fact_q, FactVolumeDaily, import_run_id).group_by(FactVolumeDaily.operation_code)
    fact_rows = fact_q.all()
    fact_by_code = {r.operation_code: float(r.qty or 0.0) for r in fact_rows}

    deps = list_dependencies(db, project_id)
    deps_out = [
        DependencyOut(
            id=d.id,
            project_id=d.project_id,
            predecessor_id=d.predecessor_id,
            successor_id=d.successor_id,
        )
        for d in deps
    ]

    op_by_id = {op.id: op for op in ops}
    preds: dict[int, list[int]] = {}
    for d in deps:
        if d.predecessor_id not in op_by_id or d.successor_id not in op_by_id:
            continue
        preds.setdefault(d.successor_id, []).append(d.predecessor_id)

    # Critical path (simple longest path on DAG)
    nodes = [
        op.id
        for op in ops
        if op.plan_start is not None and op.plan_finish is not None
    ]
    if nodes:
        base_start = min(op_by_id[n].plan_start for n in nodes if op_by_id[n].plan_start is not None)
    else:
        base_start = None

    indeg = {n: 0 for n in nodes}
    succs: dict[int, list[int]] = {}
    for s, ps in preds.items():
        if s not in indeg:
            continue
        for p in ps:
            if p not in indeg:
                continue
            indeg[s] += 1
            succs.setdefault(p, []).append(s)

    queue = [n for n in nodes if indeg[n] == 0]
    topo = []
    while queue:
        n = queue.pop(0)
        topo.append(n)
        for s in succs.get(n, []):
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)

    critical_path: list[int] = []
    if len(topo) == len(nodes) and base_start:
        es: dict[int, int] = {}
        ef: dict[int, int] = {}
        prev: dict[int, int | None] = {}
        for n in topo:
            op = op_by_id[n]
            dur = (op.plan_finish - op.plan_start).days + 1 if op.plan_start and op.plan_finish else 0
            planned_offset = (op.plan_start - base_start).days if op.plan_start else 0
            best_pred = None
            best_ef = planned_offset
            for p in preds.get(n, []):
                if p not in ef:
                    continue
                if ef[p] > best_ef:
                    best_ef = ef[p]
                    best_pred = p
            es[n] = max(planned_offset, best_ef)
            ef[n] = es[n] + dur
            prev[n] = best_pred

        end = max(ef, key=lambda k: ef[k])
        while end is not None:
            critical_path.append(end)
            end = prev.get(end)
        critical_path.reverse()

    ops_out: list[OperationGanttOut] = []
    critical_set = set(critical_path)
    for op in ops:
        fact_qty = fact_by_code.get(op.code, 0.0)
        progress = None
        if op.plan_qty_total and op.plan_qty_total > 0:
            progress = float(fact_qty / op.plan_qty_total * 100.0)
        ops_out.append(
            OperationGanttOut(
                id=op.id,
                project_id=op.project_id,
                code=op.code,
                name=op.name,
                wbs_path=wbs_map.get(op.id),
                discipline=op.discipline,
                block=op.block,
                floor=op.floor,
                ugpr=op.ugpr,
                unit=op.unit,
                plan_qty_total=op.plan_qty_total,
                plan_start=op.plan_start,
                plan_finish=op.plan_finish,
                progress_pct=progress,
                critical=op.id in critical_set,
            )
        )

    return GanttOut(operations=ops_out, dependencies=deps_out, critical_path=critical_path)
