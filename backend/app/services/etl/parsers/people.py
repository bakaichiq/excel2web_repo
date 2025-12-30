import datetime as dt
import pandas as pd
from app.services.etl.validators import ValidationError

def parse_people_tech(path: str, sheet: str = "Люди техника") -> tuple[pd.DataFrame, list[ValidationError]]:
    errors: list[ValidationError]=[]
    try:
        df = pd.read_excel(path, sheet_name=sheet, header=0, engine="openpyxl")
    except ValueError:
        errors.append(ValidationError(f"Не найден лист '{sheet}'", sheet=sheet))
        return pd.DataFrame(), errors
    df.columns=[str(c).strip() if c is not None else "" for c in df.columns]

    base_cols=["наименование","категория","ед. изм","план/факт"]
    for c in base_cols:
        if c not in df.columns:
            errors.append(ValidationError(f"Не найдена колонка '{c}'", sheet=sheet))
            return pd.DataFrame(), errors
    # date columns are those parsable to dates
    date_cols=[]
    for c in df.columns:
        if c in base_cols: continue
        try:
            d=pd.to_datetime(c, dayfirst=True).date()
            date_cols.append((c,d))
        except Exception:
            pass
    if not date_cols:
        errors.append(ValidationError("Не найдены датные колонки", sheet=sheet))
        return pd.DataFrame(), errors

    m = df.melt(id_vars=base_cols, value_vars=[c for c,_ in date_cols], var_name="date_col", value_name="qty")
    m["date"]=m["date_col"].apply(lambda x: pd.to_datetime(x, dayfirst=True).date())
    m["qty"]=pd.to_numeric(m["qty"], errors="coerce").fillna(0.0)
    m=m[m["qty"]!=0].copy()
    m.rename(columns={"наименование":"resource_name","категория":"resource_category","ед. изм":"unit","план/факт":"scenario"}, inplace=True)

    # Normalize scenario (split plan/fact rows)
    def _norm_scenario(v: str) -> str:
        s = str(v or "").strip().lower()
        if "факт" in s or "fact" in s:
            return "fact"
        if "план" in s or "plan" in s:
            return "plan"
        return "fact"

    m["scenario"] = m["scenario"].apply(_norm_scenario)
    return m[["resource_name","resource_category","unit","scenario","date","qty"]], errors
