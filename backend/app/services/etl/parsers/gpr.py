import datetime as dt
from dataclasses import dataclass
import pandas as pd
from app.services.etl.validators import ValidationError

def _to_date(x):
    if pd.isna(x): return None
    if isinstance(x, dt.datetime): return x.date()
    if isinstance(x, dt.date): return x
    try:
        return pd.to_datetime(x).date()
    except Exception:
        return None

def parse_gpr(path: str) -> tuple[pd.DataFrame, list[ValidationError]]:
    errors: list[ValidationError]=[]
    df = pd.read_excel(path, sheet_name="ГПР", header=0, engine="openpyxl")
    # normalize col names
    df.columns=[str(c).replace("\n"," ").strip() if c is not None else "" for c in df.columns]
    # keep only rows with operation id
    op_col = "Идентификатор операции"
    if op_col not in df.columns:
        errors.append(ValidationError("Не найден лист/колонка 'Идентификатор операции' в ГПР", sheet="ГПР"))
        return pd.DataFrame(), errors
    df = df[df[op_col].notna()].copy()

    out=pd.DataFrame()
    out["operation_code"]=df[op_col].astype(str).str.strip()
    out["operation_name"]=df.get("Название операции")
    out["wbs_path"]=df.get("Название ИСР")
    out["block"]=df.get("Блок")
    out["ugpr"]=df.get("УГПР")
    out["start_date"]=df.get("Начало").apply(_to_date)
    out["finish_date"]=df.get("Окончание").apply(_to_date)
    out["unit"]=df.get("Ед. изм")
    qty_col="Плановое количество нетрудовых ресурсов"
    out["plan_qty_total"]=pd.to_numeric(df.get(qty_col), errors="coerce").fillna(0.0)
    out["price"]=pd.to_numeric(df.get("Цена"), errors="coerce")
    out["amount_total"]=pd.to_numeric(df.get("Стоимость"), errors="coerce")

    # validations
    miss = out[out["start_date"].isna() | out["finish_date"].isna()]
    if not miss.empty:
        errors.append(ValidationError(f"В ГПР {len(miss)} строк без дат начала/окончания", sheet="ГПР"))
    return out, errors
