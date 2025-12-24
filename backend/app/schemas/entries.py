import datetime as dt
from pydantic import BaseModel, Field

class FactVolumeIn(BaseModel):
    project_id: int
    date: dt.date
    operation_code: str | None = None
    operation_name: str | None = None
    wbs: str | None = None
    discipline: str | None = None
    block: str | None = None
    floor: str | None = None
    ugpr: str | None = None
    category: str = Field(..., min_length=1)
    item_name: str = Field(..., min_length=1)
    unit: str | None = None
    qty: float = 0.0
    amount: float | None = None

class ManhoursIn(BaseModel):
    project_id: int
    date: dt.date
    resource_name: str
    category: str  # Manpower / Equipment
    scenario: str = "fact"
    qty: float = 0.0
    manhours: float | None = None

class PnLIn(BaseModel):
    project_id: int
    month: dt.date  # month start
    account_name: str
    parent_name: str | None = None
    scenario: str = "plan"
    amount: float = 0.0

class CashflowIn(BaseModel):
    project_id: int
    month: dt.date
    account_name: str
    parent_name: str | None = None
    scenario: str = "plan"
    direction: str | None = None
    amount: float = 0.0
