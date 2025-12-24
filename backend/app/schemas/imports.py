import datetime as dt
from pydantic import BaseModel

class ImportRunOut(BaseModel):
    id: int
    project_id: int
    file_name: str
    file_hash: str
    status: str
    rows_loaded: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None

class ImportErrorOut(BaseModel):
    id: int
    sheet: str | None
    row_num: int | None
    column: str | None
    message: str
