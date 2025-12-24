import datetime as dt
from pydantic import BaseModel


class OperationBase(BaseModel):
    project_id: int | None = None
    code: str | None = None
    name: str | None = None
    wbs_path: str | None = None
    discipline: str | None = None
    block: str | None = None
    floor: str | None = None
    ugpr: str | None = None
    unit: str | None = None
    plan_qty_total: float | None = None
    plan_start: dt.date | None = None
    plan_finish: dt.date | None = None


class OperationCreate(OperationBase):
    project_id: int
    code: str
    name: str


class OperationUpdate(OperationBase):
    pass


class OperationOut(BaseModel):
    id: int
    project_id: int
    code: str
    name: str
    wbs_path: str | None = None
    discipline: str | None = None
    block: str | None = None
    floor: str | None = None
    ugpr: str | None = None
    unit: str | None = None
    plan_qty_total: float | None = None
    plan_start: dt.date | None = None
    plan_finish: dt.date | None = None
