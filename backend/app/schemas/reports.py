import datetime as dt
from pydantic import BaseModel

class KPIOut(BaseModel):
    project_id: int
    date_from: dt.date
    date_to: dt.date
    fact_qty: float
    plan_qty: float
    progress_pct: float
    manhours: float
    productivity: float | None

class SeriesPoint(BaseModel):
    period: dt.date
    value: float

class PlanFactSeries(BaseModel):
    fact: list[SeriesPoint]
    plan: list[SeriesPoint]
    forecast: list[SeriesPoint] | None = None

class TableRow(BaseModel):
    key: str
    fact: float
    plan: float
    variance: float
    progress_pct: float

class PlanFactTable(BaseModel):
    rows: list[TableRow]


class MoneySeriesPoint(BaseModel):
    period: dt.date
    value: float


class MoneySeriesOut(BaseModel):
    series: list[MoneySeriesPoint]
    plan: list[MoneySeriesPoint] | None = None
