from sqlalchemy import ForeignKey, Date, Float, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._mixins import TimestampMixin


class SalesMonthly(Base, TimestampMixin):
    __tablename__ = "sales_monthly"
    __table_args__ = (
        Index(
            "uq_sales_month_manual",
            "project_id",
            "item_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_sales_month_run",
            "project_id",
            "import_run_id",
            "item_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    item_name: Mapped[str] = mapped_column(String(256))
    month: Mapped[object] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(16), default="plan")
    area_m2: Mapped[float] = mapped_column(Float, default=0.0)
