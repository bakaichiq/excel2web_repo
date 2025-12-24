from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum

from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class Role(str, Enum):
    admin = "Admin"
    pto = "ПТО"
    finance = "Финансы"
    manager = "Руководитель"
    viewer = "Просмотр"

class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default=Role.viewer.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
