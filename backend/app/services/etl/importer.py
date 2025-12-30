from __future__ import annotations

from pathlib import Path
import datetime as dt
import re
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.logging import logger
from app.db.models.import_run import ImportRun
from app.db.models.baseline import BaselineVolume
from app.db.models.facts import (
    FactVolumeDaily,
    FactResourceDaily,
    PlanVolumeMonthly,
    FactPnLMonthly,
    FactCashflowMonthly,
)
from app.db.models.operation import Operation
from app.db.models.wbs import WBS
from app.db.models.resource import Resource
from app.db.models.fin_account import FinAccount
from app.db.models.sales import SalesMonthly

from app.services.etl.validators import ValidationError
from app.services.etl.parsers.vdc import parse_vdc
from app.services.etl.parsers.gpr import parse_gpr
from app.services.etl.parsers.people import parse_people_tech
from app.services.etl.parsers.finance import parse_bdr, parse_bdds
from app.services.etl.parsers.sales import parse_sales


# -----------------------------
# Helpers: safe strings / floats
# -----------------------------
def _is_nan(v: Any) -> bool:
    return isinstance(v, float) and (v != v)


def _s(v: Any) -> Optional[str]:
    if v is None or _is_nan(v):
        return None
    s = str(v).strip()
    return s if s else None


def _trunc(v: Any, max_len: int) -> Optional[str]:
    s = _s(v)
    if s is None:
        return None
    return s[:max_len]


def _to_float(v: Any, default: float = 0.0) -> float:
    if v is None or _is_nan(v):
        return default
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(" ", "").replace(",", ".")
        if not s or s.lower() in ("nan", "none", "-", "—"):
            return default
        return float(s)
    except Exception:
        return default


def _to_float_nullable(v: Any) -> Optional[float]:
    if v is None or _is_nan(v):
        return None
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(" ", "").replace(",", ".")
        if not s or s.lower() in ("nan", "none", "-", "—"):
            return None
        return float(s)
    except Exception:
        return None


def _table_cols(model) -> set[str]:
    # model can be ORM class
    return set(getattr(model, "__table__").columns.keys())


def _filter_values(model, values: dict) -> dict:
    cols = _table_cols(model)
    return {k: v for k, v in values.items() if k in cols}


def _has_index(db: Session, index_name: str) -> bool:
    return db.execute(
        text("select 1 from pg_indexes where indexname=:name limit 1"),
        {"name": index_name},
    ).scalar() is not None


# -----------------------------
# Normalize unit/date
# -----------------------------
_UNIT_MAP = {
    "м2": "м2",
    "м²": "м2",
    "м3": "м3",
    "м³": "м3",
    "т": "тн",
    "тн": "тн",
    "тонн": "тн",
    "тонна": "тн",
    "тонны": "тн",
    "кг": "кг",
    "шт": "шт",
    "ед": "ед",
    "час": "час",
    "ч": "час",
    "п.м": "п.м",
    "пог.м": "п.м",
    "м.п": "п.м",
    "м": "м",
}

_UNIT_RE = re.compile(
    r"(?i)\b(м²|м2|м³|м3|тн|тонн(?:а|ы)?|т\b|кг|шт|ед|час|ч\b|п\.?\s?м|пог\.?\s?м|м\.?\s?п|м\b)\b"
)


def normalize_unit(raw: Any) -> Optional[str]:
    s = _s(raw)
    if not s:
        return None

    s0 = s.lower().replace(",", ".")
    m = _UNIT_RE.search(s0)
    if not m:
        # В Excel в "ед.изм" иногда попадает описание работ -> НЕ ПИШЕМ в unit (varchar32)
        return None

    token = m.group(1).lower().replace(" ", "")
    token = token.replace("пог.м", "п.м").replace("пм", "п.м").replace("м.п", "п.м")
    token = token.replace("тонна", "тн").replace("тонны", "тн").replace("тонн", "тн")
    token = "м2" if token in ("м²",) else token
    token = "м3" if token in ("м³",) else token
    token = "час" if token in ("ч",) else token
    token = "тн" if token in ("т",) else token
    return _UNIT_MAP.get(token, token)


def normalize_date(raw: Any) -> Optional[dt.date]:
    if raw is None or _is_nan(raw) or raw in (0, 0.0, "0", "0.0"):
        return None

    if isinstance(raw, dt.datetime):
        d = raw.date()
    elif isinstance(raw, dt.date):
        d = raw
    else:
        try:
            d = dt.datetime.fromisoformat(str(raw)).date()
        except Exception:
            return None

    if d == dt.date(1970, 1, 1):
        return None
    if d.year < 1990:
        return None
    return d


# -----------------------------
# ETL core
# -----------------------------
def _file_path(run: ImportRun) -> Path:
    return Path(settings.UPLOAD_DIR) / f"{run.project_id}_{run.file_hash}.xlsx"


def _cleanup_imported(db: Session, project_id: int, import_run_id: int) -> None:
    # remove previously imported rows for this run, keep other versions and manual rows
    for model in (
        FactVolumeDaily,
        FactResourceDaily,
        PlanVolumeMonthly,
        FactPnLMonthly,
        FactCashflowMonthly,
        BaselineVolume,
        SalesMonthly,
    ):
        db.query(model).filter(
            model.project_id == project_id,
            model.import_run_id == import_run_id,
        ).delete(synchronize_session=False)
    db.commit()


def _upsert_wbs(db: Session, project_id: int, paths: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in sorted(set([x for x in paths if x])):
        p2 = _trunc(p, 512)
        if not p2:
            continue
        stmt = (
            insert(WBS)
            .values(project_id=project_id, path=p2)
            .on_conflict_do_update(
                constraint="uq_wbs_project_path",
                set_=dict(path=p2),
            )
            .returning(WBS.id)
        )
        res = db.execute(stmt).first()
        if res:
            out[p2] = res[0]
    db.commit()
    return out


def _upsert_operations(db: Session, project_id: int, gpr_df) -> dict[str, int]:
    wbs_map = _upsert_wbs(
        db,
        project_id,
        gpr_df["wbs_path"].dropna().astype(str).tolist()
        if "wbs_path" in gpr_df.columns
        else [],
    )
    op_ids: dict[str, int] = {}

    for _, r in gpr_df.iterrows():
        code = _trunc(r.get("operation_code"), 128)
        if not code:
            continue

        wbs_id = None
        wbs_path = _s(r.get("wbs_path"))
        if wbs_path and wbs_path in wbs_map:
            wbs_id = wbs_map[wbs_path]

        raw_unit = r.get("unit")
        unit = normalize_unit(raw_unit)
        if unit is None:
            short = _s(raw_unit)
            if short and len(short) <= 32:
                unit = short
        if unit is None:
            unit = "ед"

        op_name = _trunc(r.get("operation_name"), 512) or code
        block = _trunc(r.get("block"), 128)
        ugpr = _trunc(r.get("ugpr"), 128)

        plan_start = normalize_date(r.get("start_date"))
        plan_finish = normalize_date(r.get("finish_date"))

        stmt = (
            insert(Operation)
            .values(
                project_id=project_id,
                wbs_id=wbs_id,
                code=code,
                name=op_name,
                discipline=None,
                block=block,
                floor=None,
                ugpr=ugpr,
                plan_qty_total=_to_float(r.get("plan_qty_total"), 0.0),
                unit=_trunc(unit, 32),
                plan_start=plan_start,
                plan_finish=plan_finish,
            )
            .on_conflict_do_update(
                constraint="uq_operation_project_code",
                set_=dict(
                    wbs_id=wbs_id,
                    name=op_name,
                    block=block,
                    ugpr=ugpr,
                    plan_qty_total=_to_float(r.get("plan_qty_total"), 0.0),
                    unit=_trunc(unit, 32),
                    plan_start=plan_start,
                    plan_finish=plan_finish,
                ),
            )
            .returning(Operation.id)
        )
        res = db.execute(stmt).first()
        if res:
            op_ids[code] = res[0]

    db.commit()
    return op_ids


def _distribute_qty_to_months(
    start: dt.date, finish: dt.date, qty_total: float
) -> list[tuple[dt.date, float]]:
    if not start or not finish:
        return []
    if finish < start:
        start, finish = finish, start
    days = (finish - start).days + 1
    if days <= 0:
        return []
    per_day = qty_total / days if qty_total else 0.0
    out: dict[dt.date, float] = {}
    d = start
    while d <= finish:
        m = dt.date(d.year, d.month, 1)
        out[m] = out.get(m, 0.0) + per_day
        d += dt.timedelta(days=1)
    return [(m, out[m]) for m in sorted(out.keys())]


def _load_plan_monthly(db: Session, project_id: int, import_run_id: int, gpr_df) -> int:
    """
    ВАЖНО: раньше было ON CONFLICT ON CONSTRAINT uq_plan_month — у тебя этого constraint нет.
    Здесь это не нужно: перед импортом мы делаем _cleanup_imported(), т.е. импортируемые строки уже удалены.
    Поэтому просто INSERT. Если есть "manual" строки (import_run_id IS NULL) — мы их НЕ трогаем и пропускаем.
    """
    rows: list[tuple[str, dt.date, float]] = []

    for _, r in gpr_df.iterrows():
        code = _trunc(r.get("operation_code"), 128)
        if not code:
            continue

        start = normalize_date(r.get("start_date"))
        finish = normalize_date(r.get("finish_date"))
        qty = _to_float(r.get("plan_qty_total"), 0.0)

        if not start or not finish or qty == 0:
            continue

        for m, q in _distribute_qty_to_months(start, finish, qty):
            rows.append((code, m, q))

    if not rows:
        return 0

    agg: dict[tuple[str, dt.date], float] = {}
    for code, m, q in rows:
        agg[(code, m)] = agg.get((code, m), 0.0) + q

    cols = _table_cols(PlanVolumeMonthly)
    has_import_run = "import_run_id" in cols
    has_scenario = "scenario" in cols
    supports_versions = _has_index(db, "uq_plan_volume_month_run")

    inserted = 0
    for (code, m), q in agg.items():
        # если есть manual строка (import_run_id NULL) — не перезаписываем
        if has_import_run:
            q_manual = db.query(PlanVolumeMonthly).filter(
                PlanVolumeMonthly.project_id == project_id,
                PlanVolumeMonthly.operation_code == code,
                PlanVolumeMonthly.month == m,
                (PlanVolumeMonthly.scenario == "plan") if has_scenario else True,
                PlanVolumeMonthly.import_run_id.is_(None),
            )
            if q_manual.first() is not None:
                continue

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            operation_code=code,
            month=m,
            scenario="plan",
            qty=float(q),
            amount=None,  # если колонки нет — отфильтруется
        )
        values = _filter_values(PlanVolumeMonthly, values)
        if supports_versions:
            db.execute(insert(PlanVolumeMonthly.__table__).values(**values))
        else:
            existing = db.query(PlanVolumeMonthly).filter(
                PlanVolumeMonthly.project_id == project_id,
                PlanVolumeMonthly.operation_code == code,
                PlanVolumeMonthly.month == m,
                (PlanVolumeMonthly.scenario == "plan") if has_scenario else True,
            ).first()
            if existing:
                if existing.import_run_id is None:
                    continue
                existing.import_run_id = import_run_id
                existing.qty = values.get("qty")
                existing.amount = values.get("amount")
            else:
                db.add(PlanVolumeMonthly(**values))
        inserted += 1

    db.commit()
    return inserted


def _load_baseline(db: Session, project_id: int, import_run_id: int, baseline_df) -> int:
    supports_versions = _has_index(db, "uq_baseline_row_run")
    agg: dict[tuple[str | None, str | None, str | None], dict[str, Any]] = {}

    for _, r in baseline_df.iterrows():
        unit = normalize_unit(r.get("unit")) or _trunc(r.get("unit"), 32)
        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            operation_code=_trunc(r.get("operation_code"), 128),
            operation_name=_trunc(r.get("operation_name"), 512),
            wbs=_trunc(r.get("wbs"), 512),
            discipline=_trunc(r.get("discipline"), 128),
            block=_trunc(r.get("block"), 128),
            floor=_trunc(r.get("floor"), 64),
            ugpr=_trunc(r.get("ugpr"), 128),
            category=_trunc(r.get("category"), 128),
            item_name=_trunc(r.get("item_name"), 512),
            unit=_trunc(unit, 32),
            plan_qty_total=_to_float_nullable(r.get("plan_qty_total")),
            price=_to_float_nullable(r.get("price")),
            amount_total=_to_float_nullable(r.get("amount_total")),
        )
        key = (values.get("operation_code"), values.get("category"), values.get("item_name"))
        if key not in agg:
            agg[key] = values
            continue

        cur = agg[key]
        for f in ("operation_name", "wbs", "discipline", "block", "floor", "ugpr", "unit"):
            if values.get(f) not in (None, ""):
                cur[f] = values.get(f)
        if values.get("plan_qty_total") is not None:
            cur["plan_qty_total"] = (cur.get("plan_qty_total") or 0.0) + float(values.get("plan_qty_total") or 0.0)
        if values.get("amount_total") is not None:
            cur["amount_total"] = (cur.get("amount_total") or 0.0) + float(values.get("amount_total") or 0.0)
        if values.get("price") is not None:
            cur["price"] = values.get("price")

    n = 0
    for values in agg.values():
        if supports_versions:
            stmt = (
                insert(BaselineVolume)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[
                        BaselineVolume.project_id,
                        BaselineVolume.import_run_id,
                        BaselineVolume.operation_code,
                        BaselineVolume.category,
                        BaselineVolume.item_name,
                    ],
                    index_where=BaselineVolume.import_run_id.isnot(None),
                    set_=dict(
                        plan_qty_total=values.get("plan_qty_total"),
                        price=values.get("price"),
                        amount_total=values.get("amount_total"),
                    ),
                )
            )
            db.execute(stmt)
        else:
            existing = db.query(BaselineVolume).filter(
                BaselineVolume.project_id == project_id,
                BaselineVolume.operation_code == values.get("operation_code"),
                BaselineVolume.category == values.get("category"),
                BaselineVolume.item_name == values.get("item_name"),
            ).first()
            if existing:
                if existing.import_run_id is None:
                    continue
                existing.import_run_id = import_run_id
                existing.operation_name = values.get("operation_name")
                existing.wbs = values.get("wbs")
                existing.discipline = values.get("discipline")
                existing.block = values.get("block")
                existing.floor = values.get("floor")
                existing.ugpr = values.get("ugpr")
                existing.unit = values.get("unit")
                existing.plan_qty_total = values.get("plan_qty_total")
                existing.price = values.get("price")
                existing.amount_total = values.get("amount_total")
            else:
                db.add(BaselineVolume(**values))
        n += 1

    db.commit()
    return n


def _load_fact_volume(db: Session, project_id: int, import_run_id: int, fact_df) -> int:
    n = 0
    supports_versions = _has_index(db, "uq_fact_volume_day_run")
    for _, r in fact_df.iterrows():
        unit = normalize_unit(r.get("unit")) or _trunc(r.get("unit"), 32)

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            operation_code=_trunc(r.get("operation_code"), 128),
            operation_name=_trunc(r.get("operation_name"), 512),
            wbs=_trunc(r.get("wbs"), 512),
            discipline=_trunc(r.get("discipline"), 128),
            block=_trunc(r.get("block"), 128),
            floor=_trunc(r.get("floor"), 64),
            ugpr=_trunc(r.get("ugpr"), 128),
            category=_trunc(r.get("category"), 128),
            item_name=_trunc(r.get("item_name"), 512),
            unit=_trunc(unit, 32),
            date=normalize_date(r.get("date")) or r.get("date"),
            qty=_to_float(r.get("qty"), 0.0),
            amount=_to_float_nullable(r.get("amount")),
        )

        if supports_versions:
            stmt = (
                insert(FactVolumeDaily)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[
                        FactVolumeDaily.project_id,
                        FactVolumeDaily.import_run_id,
                        FactVolumeDaily.operation_code,
                        FactVolumeDaily.category,
                        FactVolumeDaily.item_name,
                        FactVolumeDaily.date,
                    ],
                    index_where=FactVolumeDaily.import_run_id.isnot(None),
                    set_=dict(
                        qty=values.get("qty"),
                        amount=values.get("amount"),
                    ),
                )
            )
            db.execute(stmt)
        else:
            existing = db.query(FactVolumeDaily).filter(
                FactVolumeDaily.project_id == project_id,
                FactVolumeDaily.operation_code == values.get("operation_code"),
                FactVolumeDaily.category == values.get("category"),
                FactVolumeDaily.item_name == values.get("item_name"),
                FactVolumeDaily.date == values.get("date"),
            ).first()
            if existing:
                if existing.import_run_id is None:
                    continue
                existing.import_run_id = import_run_id
                existing.operation_name = values.get("operation_name")
                existing.wbs = values.get("wbs")
                existing.discipline = values.get("discipline")
                existing.block = values.get("block")
                existing.floor = values.get("floor")
                existing.ugpr = values.get("ugpr")
                existing.unit = values.get("unit")
                existing.qty = values.get("qty")
                existing.amount = values.get("amount")
            else:
                db.add(FactVolumeDaily(**values))
        n += 1

    db.commit()
    return n


def _upsert_resources(db: Session, project_id: int, people_df) -> dict[str, int]:
    """
    FIX: раньше падало 'Unconsumed column names: unit' — потому что в таблице resource у тебя нет unit.
    Решение: пишем unit только если колонка реально существует.
    + не привязываемся к constraint-именам (они могут отличаться).
    """
    res_ids: dict[str, int] = {}

    if "resource_name" not in people_df.columns:
        return res_ids

    cols_db = _table_cols(Resource)
    has_unit = "unit" in cols_db
    has_cat_col_db = "category" in cols_db  # в таблице Resource обычно 'category'
    has_cat_in_df = "resource_category" in people_df.columns
    has_unit_in_df = "unit" in people_df.columns

    # готовим dataframe только с тем, что реально есть
    use_cols = ["resource_name"]
    if has_cat_in_df:
        use_cols.append("resource_category")
    if has_unit_in_df:
        use_cols.append("unit")

    df = people_df[use_cols].drop_duplicates()

    for row in df.itertuples(index=False):
        name = row[0] if len(row) > 0 else None
        cat = row[1] if len(row) > 1 else None
        unit = row[2] if len(row) > 2 else None

        nm = _trunc(name, 256)
        if not nm:
            continue

        values = {"project_id": project_id, "name": nm}
        if has_cat_col_db:
            values["category"] = _trunc(cat, 128) if has_cat_in_df else None
        if has_unit:
            unit2 = normalize_unit(unit) or _trunc(unit, 32)
            values["unit"] = _trunc(unit2, 32)

        values = _filter_values(Resource, values)

        # простая идемпотентность: если уже есть (project_id, name) — обновим, иначе вставим
        existing = db.query(Resource).filter(
            Resource.project_id == project_id,
            Resource.name == nm,
        ).first()

        if existing is None:
            db.execute(insert(Resource.__table__).values(**values))
            existing = db.query(Resource).filter(
                Resource.project_id == project_id,
                Resource.name == nm,
            ).first()
        else:
            # update только по существующим колонкам
            for k, v in values.items():
                if k in ("project_id", "name"):
                    continue
                setattr(existing, k, v)

        if existing is not None:
            res_ids[nm] = existing.id

    db.commit()
    return res_ids


def _load_manhours(db: Session, project_id: int, import_run_id: int, people_df) -> int:
    """
    Вставка manhours/ресурсов по дням.
    Важно: колонки в FactResourceDaily могут отличаться => фильтруем values по реальным колонкам таблицы.
    """
    _upsert_resources(db, project_id, people_df)

    cols_db = _table_cols(FactResourceDaily)
    has_import_run = "import_run_id" in cols_db
    has_manhours = "manhours" in cols_db

    supports_versions = _has_index(db, "uq_res_day_run")
    n = 0
    for _, r in people_df.iterrows():
        qty = _to_float(r.get("qty"), 0.0)
        scenario = (_s(r.get("scenario")) or "fact").strip()
        cat_raw = (_s(r.get("resource_category")) or "").strip().lower()

        manhours: Optional[float] = None
        if has_manhours and cat_raw in ("manpower", "люди", "рабочие", "персонал") and scenario == "fact":
            manhours = qty * float(getattr(settings, "SHIFT_HOURS", 8))

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            resource_name=_trunc(r.get("resource_name"), 256) or "",
            category=_trunc(r.get("resource_category"), 128) or "",
            date=normalize_date(r.get("date")) or r.get("date"),
            scenario=_trunc(scenario, 32),
            qty=qty,
            manhours=manhours,
        )
        if not has_import_run:
            values.pop("import_run_id", None)

        values = _filter_values(FactResourceDaily, values)

        if supports_versions:
            stmt = (
                insert(FactResourceDaily)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[
                        FactResourceDaily.project_id,
                        FactResourceDaily.import_run_id,
                        FactResourceDaily.resource_name,
                        FactResourceDaily.category,
                        FactResourceDaily.date,
                        FactResourceDaily.scenario,
                    ],
                    index_where=FactResourceDaily.import_run_id.isnot(None),
                    set_=dict(
                        qty=values.get("qty"),
                        manhours=values.get("manhours"),
                    ),
                )
            )
            db.execute(stmt)
        else:
            existing = db.query(FactResourceDaily).filter(
                FactResourceDaily.project_id == project_id,
                FactResourceDaily.resource_name == values.get("resource_name"),
                FactResourceDaily.category == values.get("category"),
                FactResourceDaily.date == values.get("date"),
                FactResourceDaily.scenario == values.get("scenario"),
            ).first()
            if existing:
                if existing.import_run_id is None:
                    continue
                existing.import_run_id = import_run_id
                existing.qty = values.get("qty")
                if has_manhours:
                    existing.manhours = values.get("manhours")
            else:
                db.add(FactResourceDaily(**values))
        n += 1

    db.commit()
    return n

def _upsert_fin_accounts(db: Session, project_id: int, names: list[str], kind: str) -> None:
    """
    FIX: не используем constraint="uq_fin_account", т.к. его нет в БД.
    Делаем идемпотентно: если (project_id, kind, name) уже есть — пропускаем.
    """
    if not names:
        return

    kind2 = _trunc(kind, 32) or kind
    cols_db = _table_cols(FinAccount)

    for nm in sorted(set([n for n in names if n])):
        nm2 = _trunc(nm, 256)
        if not nm2:
            continue

        q = db.query(FinAccount)
        if "project_id" in cols_db:
            q = q.filter(FinAccount.project_id == project_id)
        if "kind" in cols_db:
            q = q.filter(FinAccount.kind == kind2)
        if "name" in cols_db:
            q = q.filter(FinAccount.name == nm2)

        if q.first() is not None:
            continue

        values = _filter_values(FinAccount, {"project_id": project_id, "kind": kind2, "name": nm2})
        db.execute(insert(FinAccount.__table__).values(**values))

    db.commit()


def _load_bdr(db: Session, project_id: int, import_run_id: int, bdr_df) -> int:
    """
    FIX: убрали constraint="uq_pnl_month" (может не существовать).
    Мы и так делаем _cleanup_imported(), поэтому просто вставляем, но:
    - агрегируем дубли внутри файла
    - не трогаем manual строки (import_run_id IS NULL), если такие есть
    """
    if bdr_df.empty:
        return 0

    _upsert_fin_accounts(db, project_id, bdr_df["account_name"].tolist(), "pnl")

    cols_db = _table_cols(FactPnLMonthly)
    has_import_run = "import_run_id" in cols_db

    agg: dict[tuple[str, dt.date, str], dict[str, Any]] = {}

    for _, r in bdr_df.iterrows():
        account = _trunc(r.get("account_name"), 256)
        if not account:
            continue

        month = normalize_date(r.get("month")) or r.get("month")
        if not isinstance(month, dt.date):
            continue

        scenario = _trunc(r.get("scenario") or "plan", 32) or "plan"
        parent = _trunc(r.get("parent_name"), 256)
        amount = _to_float(r.get("amount"), 0.0)

        key = (account, month, scenario)
        if key not in agg:
            agg[key] = {"parent_name": parent, "amount": amount}
        else:
            agg[key]["amount"] = float(agg[key]["amount"]) + amount
            if parent and not agg[key].get("parent_name"):
                agg[key]["parent_name"] = parent

    inserted = 0
    for (account, month, scenario), payload in agg.items():
        # manual строки не перезаписываем
        if has_import_run:
            manual = db.query(FactPnLMonthly).filter(
                FactPnLMonthly.project_id == project_id,
                FactPnLMonthly.account_name == account,
                FactPnLMonthly.month == month,
                FactPnLMonthly.scenario == scenario,
                FactPnLMonthly.import_run_id.is_(None),
            ).first()
            if manual is not None:
                continue

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            account_name=account,
            parent_name=payload.get("parent_name"),
            month=month,
            scenario=scenario,
            amount=float(payload.get("amount") or 0.0),
        )
        if not has_import_run:
            values.pop("import_run_id", None)

        values = _filter_values(FactPnLMonthly, values)
        db.execute(insert(FactPnLMonthly.__table__).values(**values))
        inserted += 1

    db.commit()
    return inserted


def _load_bdds(db: Session, project_id: int, import_run_id: int, bdds_df) -> int:
    """
    FIX: убрали constraint="uq_cf_month" (может не существовать).
    Аналогично: агрегируем, вставляем, manual не трогаем.
    """
    if bdds_df.empty:
        return 0

    _upsert_fin_accounts(db, project_id, bdds_df["account_name"].tolist(), "cashflow")

    cols_db = _table_cols(FactCashflowMonthly)
    has_import_run = "import_run_id" in cols_db

    agg: dict[tuple[str, dt.date, str, str], dict[str, Any]] = {}

    for _, r in bdds_df.iterrows():
        account = _trunc(r.get("account_name"), 256)
        if not account:
            continue

        month = normalize_date(r.get("month")) or r.get("month")
        if not isinstance(month, dt.date):
            continue

        scenario = _trunc(r.get("scenario") or "plan", 32) or "plan"
        direction = _trunc(r.get("direction"), 32) or ""
        parent = _trunc(r.get("parent_name"), 256)
        amount = _to_float(r.get("amount"), 0.0)

        key = (account, month, scenario, direction)
        if key not in agg:
            agg[key] = {"parent_name": parent, "amount": amount}
        else:
            agg[key]["amount"] = float(agg[key]["amount"]) + amount
            if parent and not agg[key].get("parent_name"):
                agg[key]["parent_name"] = parent

    inserted = 0
    for (account, month, scenario, direction), payload in agg.items():
        if has_import_run:
            manual = db.query(FactCashflowMonthly).filter(
                FactCashflowMonthly.project_id == project_id,
                FactCashflowMonthly.account_name == account,
                FactCashflowMonthly.month == month,
                FactCashflowMonthly.scenario == scenario,
                FactCashflowMonthly.direction == direction,
                FactCashflowMonthly.import_run_id.is_(None),
            ).first()
            if manual is not None:
                continue

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            account_name=account,
            parent_name=payload.get("parent_name"),
            month=month,
            scenario=scenario,
            direction=direction,
            amount=float(payload.get("amount") or 0.0),
        )
        if not has_import_run:
            values.pop("import_run_id", None)

        values = _filter_values(FactCashflowMonthly, values)
        db.execute(insert(FactCashflowMonthly.__table__).values(**values))
        inserted += 1

    db.commit()
    return inserted


def _load_sales_monthly(db: Session, project_id: int, import_run_id: int, sales_df) -> int:
    if sales_df.empty:
        return 0

    cols_db = _table_cols(SalesMonthly)
    has_import_run = "import_run_id" in cols_db

    agg: dict[tuple[str, dt.date, str], float] = {}

    for _, r in sales_df.iterrows():
        item = _trunc(r.get("item_name"), 256)
        if not item:
            continue

        month = normalize_date(r.get("month")) or r.get("month")
        if not isinstance(month, dt.date):
            continue

        scenario = _trunc(r.get("scenario") or "plan", 16) or "plan"
        area = _to_float(r.get("area_m2"), 0.0)
        key = (item, month, scenario)
        agg[key] = float(agg.get(key, 0.0)) + area

    inserted = 0
    for (item, month, scenario), area in agg.items():
        if has_import_run:
            manual = db.query(SalesMonthly).filter(
                SalesMonthly.project_id == project_id,
                SalesMonthly.item_name == item,
                SalesMonthly.month == month,
                SalesMonthly.scenario == scenario,
                SalesMonthly.import_run_id.is_(None),
            ).first()
            if manual is not None:
                continue

        values = dict(
            project_id=project_id,
            import_run_id=import_run_id,
            item_name=item,
            month=month,
            scenario=scenario,
            area_m2=float(area),
        )
        if not has_import_run:
            values.pop("import_run_id", None)

        values = _filter_values(SalesMonthly, values)
        db.execute(insert(SalesMonthly.__table__).values(**values))
        inserted += 1

    db.commit()
    return inserted


def run_import(db: Session, run: ImportRun) -> tuple[list[ValidationError], int]:
    """Main import. Returns (errors, rows_loaded)."""
    errors: list[ValidationError] = []
    path = _file_path(run)
    if not path.exists():
        return [ValidationError(f"Файл не найден: {path}")], 0

    logger.info("import_start", import_run_id=run.id, path=str(path))

    # Cleanup old imported snapshot for this project
    _cleanup_imported(db, run.project_id, run.id)

    baseline_df, fact_df, e1 = parse_vdc(str(path))
    gpr_df, e2 = parse_gpr(str(path))
    people_df, e3 = parse_people_tech(str(path))
    bdr_df, e4 = parse_bdr(str(path))
    bdds_df, e5 = parse_bdds(str(path))
    sales_df, e6 = parse_sales(str(path))

    errors.extend(e1)
    errors.extend(e2)
    errors.extend(e3)
    errors.extend(e4)
    errors.extend(e5)
    errors.extend(e6)

    # Upsert dims first
    if not gpr_df.empty:
        _upsert_operations(db, run.project_id, gpr_df)

    rows_loaded = 0
    if not baseline_df.empty:
        rows_loaded += _load_baseline(db, run.project_id, run.id, baseline_df)
    if not fact_df.empty:
        rows_loaded += _load_fact_volume(db, run.project_id, run.id, fact_df)
    if not gpr_df.empty:
        rows_loaded += _load_plan_monthly(db, run.project_id, run.id, gpr_df)
    if not people_df.empty:
        rows_loaded += _load_manhours(db, run.project_id, run.id, people_df)
    if not bdr_df.empty:
        rows_loaded += _load_bdr(db, run.project_id, run.id, bdr_df)
    if not bdds_df.empty:
        rows_loaded += _load_bdds(db, run.project_id, run.id, bdds_df)
    if not sales_df.empty:
        rows_loaded += _load_sales_monthly(db, run.project_id, run.id, sales_df)

    return errors, rows_loaded
