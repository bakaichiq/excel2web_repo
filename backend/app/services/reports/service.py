import datetime as dt
from typing import Literal

from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, Date, cast, and_, or_

from app.db.models.facts import (
    FactVolumeDaily,
    PlanVolumeMonthly,
    FactResourceDaily,
    FactPnLMonthly,
    FactCashflowMonthly,
)
from app.db.models.baseline import BaselineVolume
from app.db.models.operation import Operation
from app.db.models.wbs import WBS
from app.db.models.import_run import ImportRun

Granularity = Literal["day", "week", "month"]


def _daterange_month_starts(d1: dt.date, d2: dt.date) -> list[dt.date]:
    d = dt.date(d1.year, d1.month, 1)
    out = []
    while d <= d2:
        out.append(d)
        if d.month == 12:
            d = dt.date(d.year + 1, 1, 1)
        else:
            d = dt.date(d.year, d.month + 1, 1)
    return out


def _month_days(month_start: dt.date) -> int:
    if month_start.month == 12:
        next_m = dt.date(month_start.year + 1, 1, 1)
    else:
        next_m = dt.date(month_start.year, month_start.month + 1, 1)
    return (next_m - month_start).days


def _apply_wbs_fact_filter(q, wbs_path: str | None):
    if wbs_path:
        like = f"{wbs_path}%"
        return q.filter(FactVolumeDaily.wbs.ilike(like))
    return q


def _latest_import_run_id(db: Session, project_id: int) -> int | None:
    run = (
        db.query(ImportRun)
        .filter(
            ImportRun.project_id == project_id,
            ImportRun.status.in_(("success", "success_with_errors")),
        )
        .order_by(ImportRun.finished_at.desc().nullslast(), ImportRun.id.desc())
        .first()
    )
    return run.id if run else None


def _effective_import_run_id(db: Session, project_id: int, import_run_id: int | None) -> int | None:
    return import_run_id if import_run_id is not None else _latest_import_run_id(db, project_id)


def _apply_import_run_filter(q, model, import_run_id: int | None):
    if import_run_id is None:
        return q.filter(model.import_run_id.is_(None))
    return q.filter(or_(model.import_run_id == import_run_id, model.import_run_id.is_(None)))


def _plan_month_rows(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    scenario: str,
    import_run_id: int | None = None,
    wbs_path: str | None = None,
):
    qry = (
        db.query(PlanVolumeMonthly.month.label("period"), func.coalesce(func.sum(PlanVolumeMonthly.qty), 0.0).label("value"))
        .filter(
            PlanVolumeMonthly.project_id == project_id,
            PlanVolumeMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            PlanVolumeMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            PlanVolumeMonthly.scenario == scenario,
        )
    )
    qry = _apply_import_run_filter(qry, PlanVolumeMonthly, import_run_id)
    if wbs_path:
        qry = (
            qry.join(
                Operation,
                and_(
                    Operation.project_id == PlanVolumeMonthly.project_id,
                    Operation.code == PlanVolumeMonthly.operation_code,
                ),
            )
            .join(WBS, Operation.wbs_id == WBS.id)
            .filter(WBS.path.ilike(f"{wbs_path}%"))
        )
    return qry.group_by(PlanVolumeMonthly.month).order_by(PlanVolumeMonthly.month).all()


def _plan_qty_for_month(
    db: Session,
    project_id: int,
    month: dt.date,
    scenario: str,
    import_run_id: int | None = None,
    wbs_path: str | None = None,
):
    qry = (
        db.query(func.coalesce(func.sum(PlanVolumeMonthly.qty), 0.0))
        .filter(
            PlanVolumeMonthly.project_id == project_id,
            PlanVolumeMonthly.month == month,
            PlanVolumeMonthly.scenario == scenario,
        )
    )
    qry = _apply_import_run_filter(qry, PlanVolumeMonthly, import_run_id)
    if wbs_path:
        qry = (
            qry.join(
                Operation,
                and_(
                    Operation.project_id == PlanVolumeMonthly.project_id,
                    Operation.code == PlanVolumeMonthly.operation_code,
                ),
            )
            .join(WBS, Operation.wbs_id == WBS.id)
            .filter(WBS.path.ilike(f"{wbs_path}%"))
        )
    return qry.scalar() or 0.0


def kpi(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    wbs_path: str | None = None,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    fact_qty_q = (
        db.query(func.coalesce(func.sum(FactVolumeDaily.qty), 0.0))
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    fact_qty = _apply_import_run_filter(
        _apply_wbs_fact_filter(fact_qty_q, wbs_path),
        FactVolumeDaily,
        import_run_id,
    ).scalar() or 0.0

    plan_rows = _plan_month_rows(
        db,
        project_id,
        date_from,
        date_to,
        "plan",
        import_run_id=import_run_id,
        wbs_path=wbs_path,
    )

    plan_qty = 0.0
    for m, qty in plan_rows:
        m_start = m
        m_end = m_start + dt.timedelta(days=_month_days(m_start) - 1)
        overlap_start = max(date_from, m_start)
        overlap_end = min(date_to, m_end)
        if overlap_start <= overlap_end:
            overlap_days = (overlap_end - overlap_start).days + 1
            plan_qty += (qty / _month_days(m_start)) * overlap_days

    manhours_q = (
        db.query(func.coalesce(func.sum(FactResourceDaily.manhours), 0.0))
        .filter(
            FactResourceDaily.project_id == project_id,
            FactResourceDaily.date >= date_from,
            FactResourceDaily.date <= date_to,
        )
    )
    manhours = _apply_import_run_filter(manhours_q, FactResourceDaily, import_run_id).scalar() or 0.0

    progress_pct = (fact_qty / plan_qty * 100.0) if plan_qty > 0 else 0.0
    productivity = (fact_qty / manhours) if manhours > 0 else None

    return dict(
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
        fact_qty=float(fact_qty),
        plan_qty=float(plan_qty),
        progress_pct=float(progress_pct),
        manhours=float(manhours),
        productivity=float(productivity) if productivity is not None else None,
    )


def plan_fact_series(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity = "month",
    wbs_path: str | None = None,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    # ✅ ВАЖНО: кастим в sqlalchemy.Date
    if granularity == "day":
        period_expr = FactVolumeDaily.date
    elif granularity == "week":
        period_expr = cast(func.date_trunc("week", FactVolumeDaily.date), Date)
    else:
        period_expr = cast(func.date_trunc("month", FactVolumeDaily.date), Date)

    fact_rows_q = (
        db.query(period_expr.label("period"), func.coalesce(func.sum(FactVolumeDaily.qty), 0.0).label("value"))
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    fact_rows = (
        _apply_import_run_filter(_apply_wbs_fact_filter(fact_rows_q, wbs_path), FactVolumeDaily, import_run_id)
        .group_by(period_expr)
        .order_by(period_expr)
        .all()
    )

    def _daily_rows_for_scenario(scenario: str):
        months = _daterange_month_starts(date_from, date_to)
        daily: dict[dt.date, float] = {}
        for m in months:
            qty = _plan_qty_for_month(db, project_id, m, scenario, import_run_id=import_run_id, wbs_path=wbs_path)
            per_day = (qty / _month_days(m)) if qty else 0.0
            for i in range(_month_days(m)):
                d = m + dt.timedelta(days=i)
                if date_from <= d <= date_to:
                    daily[d] = daily.get(d, 0.0) + per_day

        out_map: dict[dt.date, float] = {}
        for d, v in daily.items():
            if granularity == "week":
                p = d - dt.timedelta(days=d.weekday())  # Monday start
            else:
                p = d
            out_map[p] = out_map.get(p, 0.0) + v

        return [(p, out_map[p]) for p in sorted(out_map.keys())]

    if granularity == "month":
        plan_rows = _plan_month_rows(
            db, project_id, date_from, date_to, "plan", import_run_id=import_run_id, wbs_path=wbs_path
        )
        forecast_rows = _plan_month_rows(
            db, project_id, date_from, date_to, "forecast", import_run_id=import_run_id, wbs_path=wbs_path
        )
    else:
        plan_rows = _daily_rows_for_scenario("plan")
        forecast_rows = _daily_rows_for_scenario("forecast")

    def to_points(rows):
        out = []
        for p, v in rows:
            # чтобы фронту было стабильно
            period = p.isoformat() if hasattr(p, "isoformat") else str(p)
            out.append({"period": period, "value": float(v or 0.0)})
        return out

    def _auto_forecast(rows, plan_rows, fact_rows):
        if rows:
            return rows

        # Build full period list
        periods = sorted({p for p, _ in plan_rows} | {p for p, _ in fact_rows})
        if not periods:
            return []

        fact_map = {p: float(v or 0.0) for p, v in fact_rows}
        # Use non-zero fact points for regression
        xs = []
        ys = []
        last_fact_idx = None
        for i, p in enumerate(periods):
            v = fact_map.get(p, 0.0)
            if v > 0:
                xs.append(float(i))
                ys.append(float(v))
                last_fact_idx = i

        if not xs:
            return []

        # Forecast only after last fact period
        if last_fact_idx is None or last_fact_idx >= len(periods) - 1:
            return []

        if len(xs) == 1:
            # flat forecast from last known fact
            last_val = ys[0]
            return [(p, last_val) for p in periods[last_fact_idx + 1 :]]

        # simple linear regression y = a*x + b
        n = float(len(xs))
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xx = sum(x * x for x in xs)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        denom = (n * sum_xx - sum_x * sum_x)
        if denom == 0:
            last_val = ys[-1]
            return [(p, last_val) for p in periods[last_fact_idx + 1 :]]

        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n

        forecast = []
        for i, p in enumerate(periods[last_fact_idx + 1 :], start=last_fact_idx + 1):
            v = a * float(i) + b
            forecast.append((p, float(v)))
        return forecast

    out = {"fact": to_points(fact_rows), "plan": to_points(plan_rows)}
    forecast_rows = _auto_forecast(forecast_rows, plan_rows, fact_rows)
    if forecast_rows:
        out["forecast"] = to_points(forecast_rows)
    return out


def plan_fact_table_by(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    by: Literal["wbs", "discipline", "block", "floor", "ugpr"] = "wbs",
    scenario: Literal["plan", "forecast", "actual"] = "plan",
    wbs_path: str | None = None,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    def _month_overlap_days(month_start: dt.date) -> int:
        m_start = month_start
        m_end = m_start + dt.timedelta(days=_month_days(m_start) - 1)
        overlap_start = max(date_from, m_start)
        overlap_end = min(date_to, m_end)
        if overlap_start > overlap_end:
            return 0
        return (overlap_end - overlap_start).days + 1

    def _k(v):
        return v if v not in (None, "") else "—"

    col = getattr(FactVolumeDaily, by)
    fact_rows_q = (
        db.query(col.label("k"), func.coalesce(func.sum(FactVolumeDaily.qty), 0.0).label("fact"))
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    fact_rows = (
        _apply_import_run_filter(_apply_wbs_fact_filter(fact_rows_q, wbs_path), FactVolumeDaily, import_run_id)
        .group_by(col)
        .all()
    )
    fact_map = {_k(r.k): float(r.fact or 0.0) for r in fact_rows}

    plan_map: dict[str, float] = {}

    if scenario == "actual":
        plan_map = dict(fact_map)
    else:
        plan_scenario = "forecast" if scenario == "forecast" else "plan"
        month_from = dt.date(date_from.year, date_from.month, 1)
        month_to = dt.date(date_to.year, date_to.month, 1)

        op_group_col = getattr(Operation, by) if by != "wbs" else None

        qry = db.query(
            PlanVolumeMonthly.month.label("month"),
            PlanVolumeMonthly.qty.label("qty"),
            (WBS.path.label("gk") if by == "wbs" else op_group_col.label("gk")),
        ).join(
            Operation,
            and_(
                Operation.project_id == PlanVolumeMonthly.project_id,
                Operation.code == PlanVolumeMonthly.operation_code,
            ),
        )
        if by == "wbs" or wbs_path:
            qry = qry.outerjoin(WBS, Operation.wbs_id == WBS.id)

        qry = qry.filter(
            PlanVolumeMonthly.project_id == project_id,
            PlanVolumeMonthly.scenario == plan_scenario,
            PlanVolumeMonthly.month >= month_from,
            PlanVolumeMonthly.month <= month_to,
        )
        qry = _apply_import_run_filter(qry, PlanVolumeMonthly, import_run_id)
        if wbs_path:
            qry = qry.filter(WBS.path.ilike(f"{wbs_path}%"))

        plan_rows = qry.all()
        if plan_rows:
            for r in plan_rows:
                key = _k(r.gk)
                days = _month_overlap_days(r.month)
                if days <= 0:
                    continue
                qty = float(r.qty or 0.0)
                plan_map[key] = plan_map.get(key, 0.0) + (qty / _month_days(r.month)) * days

        if scenario == "forecast" and not plan_map:
            period_expr = cast(func.date_trunc("month", FactVolumeDaily.date), Date)
            fact_month_q = (
                db.query(period_expr.label("period"), col.label("k"), func.coalesce(func.sum(FactVolumeDaily.qty), 0.0).label("fact"))
                .filter(
                    FactVolumeDaily.project_id == project_id,
                    FactVolumeDaily.date >= date_from,
                    FactVolumeDaily.date <= date_to,
                )
            )
            fact_month_rows = (
                _apply_import_run_filter(_apply_wbs_fact_filter(fact_month_q, wbs_path), FactVolumeDaily, import_run_id)
                .group_by(period_expr, col)
                .all()
            )
            months = _daterange_month_starts(date_from, date_to)
            fact_by_group: dict[str, dict[dt.date, float]] = {}
            for r in fact_month_rows:
                key = _k(r.k)
                fact_by_group.setdefault(key, {})
                fact_by_group[key][r.period] = float(r.fact or 0.0)

            def _auto_forecast(periods: list[dt.date], fact_map_per: dict[dt.date, float]) -> dict[dt.date, float]:
                if not periods:
                    return {}
                xs = []
                ys = []
                for i, p in enumerate(periods):
                    v = fact_map_per.get(p, 0.0)
                    if v > 0:
                        xs.append(float(i))
                        ys.append(float(v))
                if not xs:
                    return {}
                if len(xs) == 1:
                    last_val = ys[0]
                    return {p: last_val for p in periods}
                n = float(len(xs))
                sum_x = sum(xs)
                sum_y = sum(ys)
                sum_xx = sum(x * x for x in xs)
                sum_xy = sum(x * y for x, y in zip(xs, ys))
                denom = (n * sum_xx - sum_x * sum_x)
                if denom == 0:
                    last_val = ys[-1]
                    return {p: last_val for p in periods}
                a = (n * sum_xy - sum_x * sum_y) / denom
                b = (sum_y - a * sum_x) / n
                return {p: float(a * i + b) for i, p in enumerate(periods)}

            for key, fmap in fact_by_group.items():
                forecast_map = _auto_forecast(months, fmap)
                if not forecast_map:
                    continue
                for m in months:
                    days = _month_overlap_days(m)
                    if days <= 0:
                        continue
                    qty = forecast_map.get(m, 0.0)
                    plan_map[key] = plan_map.get(key, 0.0) + (qty / _month_days(m)) * days

    keys = set(fact_map.keys()) | set(plan_map.keys())
    rows = []
    for k in keys:
        fact = float(fact_map.get(k, 0.0))
        plan = float(plan_map.get(k, 0.0))
        variance = fact - plan
        progress = (fact / plan * 100.0) if plan > 0 else 0.0
        rows.append({"key": k, "fact": fact, "plan": plan, "variance": variance, "progress_pct": progress})

    rows.sort(key=lambda x: abs(x["variance"]), reverse=True)
    return {"rows": rows}


def ugpr_series(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity = "month",
    wbs_path: str | None = None,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    if granularity == "day":
        period_expr = FactVolumeDaily.date
    elif granularity == "week":
        period_expr = cast(func.date_trunc("week", FactVolumeDaily.date), Date)
    else:
        period_expr = cast(func.date_trunc("month", FactVolumeDaily.date), Date)

    baseline_exact = aliased(BaselineVolume)
    baseline_cat_q = (
        db.query(
            BaselineVolume.project_id.label("project_id"),
            BaselineVolume.operation_code.label("operation_code"),
            BaselineVolume.category.label("category"),
            func.coalesce(func.avg(BaselineVolume.price), 0.0).label("price"),
        )
        .filter(BaselineVolume.price.isnot(None))
    )
    baseline_cat_q = _apply_import_run_filter(baseline_cat_q, BaselineVolume, import_run_id)
    baseline_cat = baseline_cat_q.group_by(
        BaselineVolume.project_id,
        BaselineVolume.operation_code,
        BaselineVolume.category,
    ).subquery()

    amount_expr = func.coalesce(
        FactVolumeDaily.amount,
        FactVolumeDaily.qty
        * func.coalesce(
            baseline_exact.price,
            baseline_cat.c.price,
            0.0,
        ),
    )

    qry = (
        db.query(period_expr.label("period"), func.coalesce(func.sum(amount_expr), 0.0).label("value"))
        .outerjoin(
            baseline_exact,
            and_(
                FactVolumeDaily.project_id == baseline_exact.project_id,
                FactVolumeDaily.operation_code == baseline_exact.operation_code,
                FactVolumeDaily.category == baseline_exact.category,
                FactVolumeDaily.item_name == baseline_exact.item_name,
                (
                    baseline_exact.import_run_id.is_(None)
                    if import_run_id is None
                    else or_(
                        baseline_exact.import_run_id == import_run_id,
                        baseline_exact.import_run_id.is_(None),
                    )
                ),
            ),
        )
        .outerjoin(
            baseline_cat,
            and_(
                FactVolumeDaily.project_id == baseline_cat.c.project_id,
                FactVolumeDaily.operation_code == baseline_cat.c.operation_code,
                FactVolumeDaily.category == baseline_cat.c.category,
            ),
        )
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    qry = _apply_import_run_filter(_apply_wbs_fact_filter(qry, wbs_path), FactVolumeDaily, import_run_id)
    rows = qry.group_by(period_expr).order_by(period_expr).all()

    out = []
    for p, v in rows:
        period = p.isoformat() if hasattr(p, "isoformat") else str(p)
        out.append({"period": period, "value": float(v or 0.0)})

    # Plan money series: distribute monthly plan amounts by granularity
    price_by_op = (
        db.query(
            BaselineVolume.project_id.label("project_id"),
            BaselineVolume.operation_code.label("operation_code"),
            func.coalesce(func.avg(BaselineVolume.price), 0.0).label("price"),
        )
        .filter(BaselineVolume.price.isnot(None))
    )
    price_by_op = _apply_import_run_filter(price_by_op, BaselineVolume, import_run_id).group_by(
        BaselineVolume.project_id,
        BaselineVolume.operation_code,
    ).subquery()

    plan_month_q = (
        db.query(
            PlanVolumeMonthly.month.label("period"),
            func.coalesce(func.sum(PlanVolumeMonthly.qty * func.coalesce(price_by_op.c.price, 0.0)), 0.0).label("value"),
        )
        .outerjoin(
            price_by_op,
            and_(
                PlanVolumeMonthly.project_id == price_by_op.c.project_id,
                PlanVolumeMonthly.operation_code == price_by_op.c.operation_code,
            ),
        )
        .filter(
            PlanVolumeMonthly.project_id == project_id,
            PlanVolumeMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            PlanVolumeMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            PlanVolumeMonthly.scenario == "plan",
        )
    )
    plan_month_q = _apply_import_run_filter(plan_month_q, PlanVolumeMonthly, import_run_id)
    if wbs_path:
        plan_month_q = (
            plan_month_q.join(
                Operation,
                and_(
                    Operation.project_id == PlanVolumeMonthly.project_id,
                    Operation.code == PlanVolumeMonthly.operation_code,
                ),
            )
            .join(WBS, Operation.wbs_id == WBS.id)
            .filter(WBS.path.ilike(f"{wbs_path}%"))
        )

    plan_month_rows = plan_month_q.group_by(PlanVolumeMonthly.month).order_by(PlanVolumeMonthly.month).all()

    plan_out = []
    if granularity == "month":
        for p, v in plan_month_rows:
            plan_out.append({"period": p.isoformat(), "value": float(v or 0.0)})
    else:
        months = _daterange_month_starts(date_from, date_to)
        daily: dict[dt.date, float] = {}
        plan_map = {p: float(v or 0.0) for p, v in plan_month_rows}
        for m in months:
            qty = plan_map.get(m, 0.0)
            per_day = (qty / _month_days(m)) if qty else 0.0
            for i in range(_month_days(m)):
                d = m + dt.timedelta(days=i)
                if date_from <= d <= date_to:
                    daily[d] = daily.get(d, 0.0) + per_day
        out_map: dict[dt.date, float] = {}
        for d, v in daily.items():
            if granularity == "week":
                p = d - dt.timedelta(days=d.weekday())
            else:
                p = d
            out_map[p] = out_map.get(p, 0.0) + v
        for p in sorted(out_map.keys()):
            plan_out.append({"period": p.isoformat(), "value": float(out_map[p] or 0.0)})

    return {"series": out, "plan": plan_out}


def manhours_series(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    granularity: Granularity = "month",
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    if granularity == "day":
        period_expr = FactResourceDaily.date
    elif granularity == "week":
        period_expr = cast(func.date_trunc("week", FactResourceDaily.date), Date)
    else:
        period_expr = cast(func.date_trunc("month", FactResourceDaily.date), Date)

    value_expr = func.coalesce(FactResourceDaily.manhours, FactResourceDaily.qty)

    def _rows_for_scenario(scenario: str):
        qry = (
            db.query(period_expr.label("period"), func.coalesce(func.sum(value_expr), 0.0).label("value"))
            .filter(
                FactResourceDaily.project_id == project_id,
                FactResourceDaily.date >= date_from,
                FactResourceDaily.date <= date_to,
                FactResourceDaily.scenario == scenario,
            )
        )
        qry = _apply_import_run_filter(qry, FactResourceDaily, import_run_id)
        return qry.group_by(period_expr).order_by(period_expr).all()

    plan_rows = _rows_for_scenario("plan")
    fact_rows = _rows_for_scenario("fact")

    def to_points(rows):
        out = []
        for p, v in rows:
            period = p.isoformat() if hasattr(p, "isoformat") else str(p)
            out.append({"period": period, "value": float(v or 0.0)})
        return out

    return {"plan": to_points(plan_rows), "fact": to_points(fact_rows)}


def ugpr_operation_table(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    wbs_path: str | None = None,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    today = dt.date.today()
    month_start = dt.date(today.year, today.month, 1)
    month_end = month_start + dt.timedelta(days=_month_days(month_start) - 1)
    week_start = today - dt.timedelta(days=today.weekday())
    week_end = week_start + dt.timedelta(days=6)

    def _overlap_days(a_start: dt.date, a_end: dt.date, b_start: dt.date, b_end: dt.date) -> int:
        start = max(a_start, b_start)
        end = min(a_end, b_end)
        if start > end:
            return 0
        return (end - start).days + 1

    price_q = (
        db.query(
            BaselineVolume.operation_code,
            BaselineVolume.price,
            BaselineVolume.plan_qty_total,
            BaselineVolume.amount_total,
        )
        .filter(BaselineVolume.project_id == project_id)
    )
    price_q = _apply_import_run_filter(price_q, BaselineVolume, import_run_id)
    price_rows = price_q.all()
    price_map: dict[str, list[float]] = {}
    for code, price, qty_total, amount_total in price_rows:
        if not code:
            continue
        unit_price = None
        if price is not None:
            unit_price = float(price)
        elif qty_total and amount_total is not None:
            try:
                unit_price = float(amount_total) / float(qty_total)
            except Exception:
                unit_price = None
        if unit_price is None:
            continue
        price_map.setdefault(code, []).append(unit_price)
    price_by_op = {k: sum(v) / len(v) for k, v in price_map.items()}

    ops_q = db.query(Operation.code, Operation.name).filter(Operation.project_id == project_id)
    if wbs_path:
        ops_q = (
            ops_q.join(WBS, Operation.wbs_id == WBS.id)
            .filter(WBS.path.ilike(f"{wbs_path}%"))
        )
    ops = ops_q.all()
    op_name = {code: (name or code) for code, name in ops}

    plan_q = (
        db.query(PlanVolumeMonthly.operation_code, PlanVolumeMonthly.month, PlanVolumeMonthly.qty)
        .filter(
            PlanVolumeMonthly.project_id == project_id,
            PlanVolumeMonthly.scenario == "plan",
        )
    )
    plan_q = _apply_import_run_filter(plan_q, PlanVolumeMonthly, import_run_id)
    if wbs_path:
        plan_q = (
            plan_q.join(Operation, Operation.code == PlanVolumeMonthly.operation_code)
            .join(WBS, Operation.wbs_id == WBS.id)
            .filter(WBS.path.ilike(f"{wbs_path}%"))
        )
    plan_rows = plan_q.all()

    plan = {}
    for code, month, qty in plan_rows:
        price = price_by_op.get(code, 0.0)
        amount = float(qty or 0.0) * price
        m_start = month
        m_end = month + dt.timedelta(days=_month_days(month) - 1)
        plan.setdefault(code, {
            "lcp": 0.0,
            "period": 0.0,
            "month": 0.0,
            "week": 0.0,
            "day": 0.0,
        })
        plan[code]["lcp"] += amount

        period_days = _overlap_days(m_start, m_end, date_from, date_to)
        if period_days:
            plan[code]["period"] += (amount / _month_days(month)) * period_days

        if m_start == month_start:
            plan[code]["month"] += amount

        week_days = _overlap_days(m_start, m_end, week_start, week_end)
        if week_days:
            plan[code]["week"] += (amount / _month_days(month)) * week_days

        if today >= m_start and today <= m_end:
            plan[code]["day"] += amount / _month_days(month)

    fact_q = (
        db.query(
            FactVolumeDaily.operation_code,
            FactVolumeDaily.date,
            FactVolumeDaily.qty,
            FactVolumeDaily.amount,
        )
        .filter(FactVolumeDaily.project_id == project_id)
    )
    fact_q = _apply_import_run_filter(fact_q, FactVolumeDaily, import_run_id)
    if wbs_path:
        fact_q = fact_q.filter(FactVolumeDaily.wbs.ilike(f"{wbs_path}%"))
    fact_rows = fact_q.all()

    fact = {}
    for code, d, qty, amount in fact_rows:
        price = price_by_op.get(code, 0.0)
        amt = float(amount) if amount is not None else float(qty or 0.0) * price
        fact.setdefault(code, {
            "lcp": 0.0,
            "period": 0.0,
            "month": 0.0,
            "week": 0.0,
            "day": 0.0,
        })
        fact[code]["lcp"] += amt
        if date_from <= d <= date_to:
            fact[code]["period"] += amt
        if month_start <= d <= month_end:
            fact[code]["month"] += amt
        if week_start <= d <= week_end:
            fact[code]["week"] += amt
        if d == today:
            fact[code]["day"] += amt

    codes = sorted(set(op_name.keys()) | set(plan.keys()) | set(fact.keys()))
    rows = []
    for code in codes:
        p = plan.get(code, {})
        f = fact.get(code, {})
        rows.append({
            "operation_code": code,
            "operation_name": op_name.get(code, code),
            "plan_lcp": float(p.get("lcp", 0.0)),
            "fact_lcp": float(f.get("lcp", 0.0)),
            "plan_period": float(p.get("period", 0.0)),
            "fact_period": float(f.get("period", 0.0)),
            "plan_month": float(p.get("month", 0.0)),
            "fact_month": float(f.get("month", 0.0)),
            "plan_week": float(p.get("week", 0.0)),
            "fact_week": float(f.get("week", 0.0)),
            "plan_day": float(p.get("day", 0.0)),
            "fact_day": float(f.get("day", 0.0)),
        })

    rows.sort(key=lambda r: abs(r["fact_period"]), reverse=True)
    return {"rows": rows}


def pnl(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    scenario: str = "plan",
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    rows_q = (
        db.query(
            FactPnLMonthly.month,
            FactPnLMonthly.account_name,
            FactPnLMonthly.parent_name,
            func.sum(FactPnLMonthly.amount),
        )
        .filter(
            FactPnLMonthly.project_id == project_id,
            FactPnLMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            FactPnLMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            FactPnLMonthly.scenario == scenario,
        )
        .group_by(FactPnLMonthly.month, FactPnLMonthly.account_name, FactPnLMonthly.parent_name)
        .order_by(FactPnLMonthly.month)
    )
    rows = _apply_import_run_filter(rows_q, FactPnLMonthly, import_run_id).all()
    return [
        {
            "month": m.isoformat(),
            "account": a,
            "parent_name": p,
            "amount": float(val or 0.0),
        }
        for m, a, p, val in rows
    ]


def cashflow(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    scenario: str = "plan",
    opening_balance: float = 0.0,
    import_run_id: int | None = None,
):
    import_run_id = _effective_import_run_id(db, project_id, import_run_id)
    rows_q = (
        db.query(FactCashflowMonthly.month, FactCashflowMonthly.account_name, func.sum(FactCashflowMonthly.amount))
        .filter(
            FactCashflowMonthly.project_id == project_id,
            FactCashflowMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            FactCashflowMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            FactCashflowMonthly.scenario == scenario,
        )
        .group_by(FactCashflowMonthly.month, FactCashflowMonthly.account_name)
        .order_by(FactCashflowMonthly.month)
    )
    rows = _apply_import_run_filter(rows_q, FactCashflowMonthly, import_run_id).all()

    month_tot = {}
    by_acc = {}
    for m, a, val in rows:
        v = float(val or 0.0)
        month_tot[m] = month_tot.get(m, 0.0) + v
        by_acc.setdefault(m, []).append({"account": a, "amount": v})

    balance = opening_balance
    series = []
    for m in sorted(month_tot.keys()):
        balance += month_tot[m]
        series.append({"month": m.isoformat(), "net": month_tot[m], "balance": balance})

    by_account = {m.isoformat(): v for m, v in by_acc.items()}
    return {"series": series, "by_account": by_account}
