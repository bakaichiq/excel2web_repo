import datetime as dt
from dataclasses import dataclass
import pandas as pd
from app.services.etl.validators import ValidationError
from app.services.etl.utils import to_date

META_COLS = [
    "Идентификатор операции",
    "Категория",
    "Блок",
    "WBS",
    "Конструктив",
    "Дисциплина",
    "Этаж",
    "УГПР",
    "Название операции",
    "Тип",
    "Наименование работ и материалов",
    "Ед. изм",
    "Количество Защита",
    "Цена Защита",
    "Прогнозное Количество",
    "Цена Фактическая",
]

def _norm_cols(cols: list):
    out=[]
    for c in cols:
        if isinstance(c, dt.datetime):
            out.append(c.date())
        elif isinstance(c, dt.date):
            out.append(c)
        elif c is None:
            out.append(None)
        else:
            s = str(c).replace("\n", " ").strip()
            s = " ".join(s.split())
            # Header dates are often stored as text like "15.09.2025"
            d = to_date(s)
            out.append(d if d else s)
    return out

def _to_num(s: pd.Series) -> pd.Series:
    # Normalize numeric strings like "1 234,56" to 1234.56
    return pd.to_numeric(
        s.astype(str)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

def parse_vdc(path: str) -> tuple[pd.DataFrame, pd.DataFrame, list[ValidationError]]:
    """Return (baseline_df, fact_daily_df, errors)"""
    errors: list[ValidationError] = []
    df = pd.read_excel(path, sheet_name="ВДЦ", header=0, engine="openpyxl")
    df.columns = _norm_cols(list(df.columns))

    # Remove header/group rows: keep those with item name present
    item_col = "Наименование работ и материалов"
    if item_col not in df.columns:
        # fallback - try contains
        cand=[c for c in df.columns if isinstance(c,str) and "наименование" in c.lower()]
        if cand: item_col=cand[0]
        else:
            return pd.DataFrame(), pd.DataFrame(), [ValidationError("Не найдена колонка 'Наименование работ и материалов'", sheet="ВДЦ")]

    # Some Excel files use merged cells; forward-fill key columns so fact rows keep identifiers
    ffill_cols = [
        "Идентификатор операции",
        "Категория",
        "Блок",
        "WBS",
        "Конструктив",
        "Дисциплина",
        "Этаж",
        "УГПР",
        "Название операции",
        "Наименование работ и материалов",
        "Ед. изм",
    ]
    for c in ffill_cols:
        if c in df.columns:
            # Treat empty strings as missing before forward fill
            df[c] = df[c].replace(r"^\s*$", pd.NA, regex=True).ffill()

    # Keep full df for facts; baseline will use rows with item name present
    df_base = df[df[item_col].notna()].copy()

    # Map columns (some with trailing spaces)
    def col(name):
        # exact or partial
        if name in df.columns: return name
        for c in df.columns:
            if isinstance(c,str) and c.lower()==name.lower():
                return c
        # handle without spaces
        for c in df.columns:
            if isinstance(c,str) and c.replace(" ","").lower()==name.replace(" ","").lower():
                return c
        return None

    op_code = col("Идентификатор операции")
    category = col("Категория")
    block = col("Блок")
    wbs = col("WBS")
    discipline = col("Дисциплина")
    floor = col("Этаж")
    ugpr = col("УГПР")
    op_name = col("Название операции")
    item = item_col
    unit = col("Ед. изм")
    plan_qty = col("Количество Защита")
    plan_price = col("Цена Защита")
    forecast_qty = col("Прогнозное Количество")
    fact_price = col("Цена Фактическая")

    required=[("Идентификатор операции",op_code),("Категория",category),("Наименование",item)]
    for n,cname in required:
        if cname is None:
            errors.append(ValidationError(f"Не найдена колонка {n}", sheet="ВДЦ"))
    if errors:
        return pd.DataFrame(), pd.DataFrame(), errors

    # Baseline rows
    base_cols = {
        "operation_code": df_base[op_code].astype(str).str.strip(),
        "operation_name": df_base[op_name].astype(str).where(df_base[op_name].notna(), None) if op_name else None,
        "wbs": df_base[wbs].astype(str).where(df_base[wbs].notna(), None) if wbs else None,
        "discipline": df_base[discipline].astype(str).where(df_base[discipline].notna(), None) if discipline else None,
        "block": df_base[block].astype(str).where(df_base[block].notna(), None) if block else None,
        "floor": df_base[floor].astype(str).where(df_base[floor].notna(), None) if floor else None,
        "ugpr": df_base[ugpr].astype(str).where(df_base[ugpr].notna(), None) if ugpr else None,
        "category": df_base[category].astype(str).str.strip(),
        "item_name": df_base[item].astype(str).str.strip(),
        "unit": df_base[unit].astype(str).where(df_base[unit].notna(), None) if unit else None,
        "plan_qty_total": _to_num(df_base[plan_qty]) if plan_qty else None,
        "price": _to_num(df_base[plan_price]) if plan_price else None,
    }
    baseline = pd.DataFrame({k:v for k,v in base_cols.items() if v is not None})
    if "plan_qty_total" in baseline.columns and "price" in baseline.columns:
        baseline["amount_total"]=baseline["plan_qty_total"].fillna(0)*baseline["price"].fillna(0)

    # Daily facts from date columns (columns that are date objects)
    date_cols=[c for c in df.columns if isinstance(c, dt.date)]
    if not date_cols:
        errors.append(ValidationError("Не найдены датные колонки для факта (возможно, они пустые).", sheet="ВДЦ"))
        return baseline, pd.DataFrame(), errors

    facts = df[[op_code, category, item, unit, wbs if wbs else op_code, discipline if discipline else op_code, block if block else op_code, floor if floor else op_code, ugpr if ugpr else op_code]].copy()
    facts["operation_code"]=df[op_code].astype(str).str.strip()
    facts["category"]=df[category].astype(str).str.strip()
    item_series = df[item].astype(str).where(df[item].notna(), None)
    # Fallbacks for merged/blank item names
    if op_name:
        item_series = item_series.where(item_series.notna(), df[op_name].astype(str))
    item_series = item_series.where(item_series.notna(), facts["operation_code"])
    facts["item_name"]=item_series.astype(str).str.strip()
    facts["unit"]=df[unit].astype(str).where(df[unit].notna(), None) if unit else None
    if fact_price:
        facts["fact_price"] = _to_num(df[fact_price])
    if wbs: facts["wbs"]=df[wbs].astype(str).where(df[wbs].notna(), None)
    else: facts["wbs"]=None
    if discipline: facts["discipline"]=df[discipline].astype(str).where(df[discipline].notna(), None)
    else: facts["discipline"]=None
    if block: facts["block"]=df[block].astype(str).where(df[block].notna(), None)
    else: facts["block"]=None
    if floor: facts["floor"]=df[floor].astype(str).where(df[floor].notna(), None)
    else: facts["floor"]=None
    if ugpr: facts["ugpr"]=df[ugpr].astype(str).where(df[ugpr].notna(), None)
    else: facts["ugpr"]=None
    if op_name:
        facts["operation_name"]=df[op_name].astype(str).where(df[op_name].notna(), None)
    else:
        facts["operation_name"]=None

    wide = pd.concat([facts, df[date_cols]], axis=1)
    m = wide.melt(
        id_vars=["operation_code","operation_name","wbs","discipline","block","floor","ugpr","category","item_name","unit"] + (["fact_price"] if "fact_price" in facts.columns else []),
        value_vars=date_cols,
        var_name="date",
        value_name="qty",
    )
    m["qty"]=_to_num(m["qty"]).fillna(0.0)
    m = m[m["qty"]!=0].copy()
    m["date"]=pd.to_datetime(m["date"]).dt.date

    # Amount: if fact price present, compute amount = qty * price
    if "fact_price" in m.columns:
        m["amount"] = (m["qty"] * m["fact_price"]).where(m["fact_price"].notna(), None)
    else:
        m["amount"] = None

    # basic validations
    bad_keys = m[(m["operation_code"].isna()) | (m["category"].isna()) | (m["item_name"].isna())]
    if not bad_keys.empty:
        errors.append(ValidationError(f"В ВДЦ найдено {len(bad_keys)} строк с пустыми ключами (операция/категория/наименование)", sheet="ВДЦ"))

    return baseline, m[["operation_code","operation_name","wbs","discipline","block","floor","ugpr","category","item_name","unit","date","qty","amount"]], errors
