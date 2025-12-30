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


class UgprTableRow(BaseModel):
    operation_code: str
    operation_name: str
    plan_lcp: float
    fact_lcp: float
    plan_period: float
    fact_period: float
    plan_month: float
    fact_month: float
    plan_week: float
    fact_week: float
    plan_day: float
    fact_day: float


class UgprTableOut(BaseModel):
    rows: list[UgprTableRow]


class SalesKPIOut(BaseModel):
    project_id: int
    date_from: dt.date
    date_to: dt.date
    plan_m2: float
    fact_m2: float
    sold_m2: float
    remaining_m2: float
    variance_m2: float
    progress_pct: float


class FloorSummaryRow(BaseModel):
    block: str | None = None
    floor: str
    progress_pct: float
    operations_count: int


class FloorSummaryOut(BaseModel):
    rows: list[FloorSummaryRow]


class FloorOperationRow(BaseModel):
    operation_code: str
    operation_name: str
    progress_pct: float


class FloorOperationOut(BaseModel):
    rows: list[FloorOperationRow]


class FloorSeriesOut(BaseModel):
    plan: list[SeriesPoint]
    fact: list[SeriesPoint]
    forecast: list[SeriesPoint] | None = None
