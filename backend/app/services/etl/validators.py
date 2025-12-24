from dataclasses import dataclass
from typing import Any

@dataclass
class ValidationError:
    message: str
    sheet: str | None = None
    row_num: int | None = None
    column: str | None = None

def is_negative(v: Any) -> bool:
    try:
        return float(v) < 0
    except Exception:
        return False
