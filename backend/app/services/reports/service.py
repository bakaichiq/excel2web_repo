import datetime as dt
from typing import Literal

from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, Date, cast, and_

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


def _plan_month_rows(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    scenario: str,
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


def kpi(db: Session, project_id: int, date_from: dt.date, date_to: dt.date, wbs_path: str | None = None):
    fact_qty_q = (
        db.query(func.coalesce(func.sum(FactVolumeDaily.qty), 0.0))
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    fact_qty = _apply_wbs_fact_filter(fact_qty_q, wbs_path).scalar() or 0.0

    plan_rows = _plan_month_rows(db, project_id, date_from, date_to, "plan", wbs_path=wbs_path)

    plan_qty = 0.0
    for m, qty in plan_rows:
        m_start = m
        m_end = m_start + dt.timedelta(days=_month_days(m_start) - 1)
        overlap_start = max(date_from, m_start)
        overlap_end = min(date_to, m_end)
        if overlap_start <= overlap_end:
            overlap_days = (overlap_end - overlap_start).days + 1
            plan_qty += (qty / _month_days(m_start)) * overlap_days

    manhours = (
        db.query(func.coalesce(func.sum(FactResourceDaily.manhours), 0.0))
        .filter(
            FactResourceDaily.project_id == project_id,
            FactResourceDaily.date >= date_from,
            FactResourceDaily.date <= date_to,
        )
        .scalar()
        or 0.0
    )

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
):
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
        _apply_wbs_fact_filter(fact_rows_q, wbs_path)
        .group_by(period_expr)
        .order_by(period_expr)
        .all()
    )

    def _daily_rows_for_scenario(scenario: str):
        months = _daterange_month_starts(date_from, date_to)
        daily: dict[dt.date, float] = {}
        for m in months:
            qty = _plan_qty_for_month(db, project_id, m, scenario, wbs_path=wbs_path)
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
        plan_rows = _plan_month_rows(db, project_id, date_from, date_to, "plan", wbs_path=wbs_path)
        forecast_rows = _plan_month_rows(db, project_id, date_from, date_to, "forecast", wbs_path=wbs_path)
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
        for i, p in enumerate(periods):
            v = fact_map.get(p, 0.0)
            if v > 0:
                xs.append(float(i))
                ys.append(float(v))

        if not xs:
            return []

        if len(xs) == 1:
            # flat forecast from last known fact
            last_val = ys[0]
            return [(p, last_val) for p in periods]

        # simple linear regression y = a*x + b
        n = float(len(xs))
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xx = sum(x * x for x in xs)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        denom = (n * sum_xx - sum_x * sum_x)
        if denom == 0:
            last_val = ys[-1]
            return [(p, last_val) for p in periods]

        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n

        forecast = []
        for i, p in enumerate(periods):
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
    wbs_path: str | None = None,
):
    col = getattr(FactVolumeDaily, by)
    fact_rows_q = (
        db.query(col.label("k"), func.coalesce(func.sum(FactVolumeDaily.qty), 0.0).label("fact"))
        .filter(
            FactVolumeDaily.project_id == project_id,
            FactVolumeDaily.date >= date_from,
            FactVolumeDaily.date <= date_to,
        )
    )
    fact_rows = _apply_wbs_fact_filter(fact_rows_q, wbs_path).group_by(col).all()

    total_fact = sum(float(r.fact or 0.0) for r in fact_rows)
    plan_total = kpi(db, project_id, date_from, date_to, wbs_path=wbs_path)["plan_qty"]

    rows = []
    for r in fact_rows:
        k = r.k or "—"
        fact = float(r.fact or 0.0)
        plan = (plan_total * (fact / total_fact)) if total_fact > 0 else 0.0
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
):
    if granularity == "day":
        period_expr = FactVolumeDaily.date
    elif granularity == "week":
        period_expr = cast(func.date_trunc("week", FactVolumeDaily.date), Date)
    else:
        period_expr = cast(func.date_trunc("month", FactVolumeDaily.date), Date)

    baseline_exact = aliased(BaselineVolume)
    baseline_cat = (
        db.query(
            BaselineVolume.project_id.label("project_id"),
            BaselineVolume.operation_code.label("operation_code"),
            BaselineVolume.category.label("category"),
            func.coalesce(func.avg(BaselineVolume.price), 0.0).label("price"),
        )
        .filter(BaselineVolume.price.isnot(None))
        .group_by(BaselineVolume.project_id, BaselineVolume.operation_code, BaselineVolume.category)
        .subquery()
    )

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
    qry = _apply_wbs_fact_filter(qry, wbs_path)
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
        .group_by(BaselineVolume.project_id, BaselineVolume.operation_code)
        .subquery()
    )

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


def pnl(db: Session, project_id: int, date_from: dt.date, date_to: dt.date, scenario: str = "plan"):
    rows = (
        db.query(FactPnLMonthly.month, FactPnLMonthly.account_name, func.sum(FactPnLMonthly.amount))
        .filter(
            FactPnLMonthly.project_id == project_id,
            FactPnLMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            FactPnLMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            FactPnLMonthly.scenario == scenario,
        )
        .group_by(FactPnLMonthly.month, FactPnLMonthly.account_name)
        .order_by(FactPnLMonthly.month)
        .all()
    )
    return [{"month": m.isoformat(), "account": a, "amount": float(val or 0.0)} for m, a, val in rows]


def cashflow(
    db: Session,
    project_id: int,
    date_from: dt.date,
    date_to: dt.date,
    scenario: str = "plan",
    opening_balance: float = 0.0,
):
    rows = (
        db.query(FactCashflowMonthly.month, FactCashflowMonthly.account_name, func.sum(FactCashflowMonthly.amount))
        .filter(
            FactCashflowMonthly.project_id == project_id,
            FactCashflowMonthly.month >= dt.date(date_from.year, date_from.month, 1),
            FactCashflowMonthly.month <= dt.date(date_to.year, date_to.month, 1),
            FactCashflowMonthly.scenario == scenario,
        )
        .group_by(FactCashflowMonthly.month, FactCashflowMonthly.account_name)
        .order_by(FactCashflowMonthly.month)
        .all()
    )

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
