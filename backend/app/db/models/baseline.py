import datetime as dt
from sqlalchemy import ForeignKey, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class BaselineVolume(Base, TimestampMixin):
    __tablename__ = "baseline_volume"
    __table_args__ = (
        UniqueConstraint("project_id", "operation_code", "category", "item_name", name="uq_baseline_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    operation_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    operation_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    wbs: Mapped[str | None] = mapped_column(String(256), nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    block: Mapped[str | None] = mapped_column(String(128), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ugpr: Mapped[str | None] = mapped_column(String(128), nullable=True)

    category: Mapped[str] = mapped_column(String(64))
    item_name: Mapped[str] = mapped_column(String(512))
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    plan_qty_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_total: Mapped[float | None] = mapped_column(Float, nullable=True)
