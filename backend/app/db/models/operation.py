import datetime as dt
from sqlalchemy import String, ForeignKey, Date, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class Operation(Base, TimestampMixin):
    __tablename__ = "operation"
    __table_args__ = (UniqueConstraint("project_id", "code", name="uq_operation_project_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    wbs_id: Mapped[int | None] = mapped_column(ForeignKey("wbs.id", ondelete="SET NULL"), nullable=True)

    code: Mapped[str] = mapped_column(String(128), index=True)  # Excel "Идентификатор операции"
    name: Mapped[str] = mapped_column(String(512))
    discipline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    block: Mapped[str | None] = mapped_column(String(128), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ugpr: Mapped[str | None] = mapped_column(String(128), nullable=True)

    plan_qty_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    plan_start: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    plan_finish: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    project = relationship("Project", back_populates="operations")
    wbs = relationship("WBS", back_populates="operations")
