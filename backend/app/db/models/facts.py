import datetime as dt
from sqlalchemy import ForeignKey, Date, Float, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class FactVolumeDaily(Base, TimestampMixin):
    __tablename__ = "fact_volume_daily"
    __table_args__ = (
        Index(
            "uq_fact_volume_day_manual",
            "project_id",
            "operation_code",
            "category",
            "item_name",
            "date",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_fact_volume_day_run",
            "project_id",
            "import_run_id",
            "operation_code",
            "category",
            "item_name",
            "date",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
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

    date: Mapped[dt.date] = mapped_column(Date, index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

class PlanVolumeMonthly(Base, TimestampMixin):
    __tablename__ = "plan_volume_monthly"
    __table_args__ = (
        Index(
            "uq_plan_volume_month_manual",
            "project_id",
            "operation_code",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_plan_volume_month_run",
            "project_id",
            "import_run_id",
            "operation_code",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    operation_code: Mapped[str] = mapped_column(String(128), index=True)
    operation_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    month: Mapped[dt.date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(16), default="plan")
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)

class FactResourceDaily(Base, TimestampMixin):
    __tablename__ = "fact_resource_daily"
    __table_args__ = (
        Index(
            "uq_res_day_manual",
            "project_id",
            "resource_name",
            "category",
            "date",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_res_day_run",
            "project_id",
            "import_run_id",
            "resource_name",
            "category",
            "date",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    resource_name: Mapped[str] = mapped_column(String(256), index=True)
    category: Mapped[str] = mapped_column(String(64))
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(16), default="fact")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    manhours: Mapped[float | None] = mapped_column(Float, nullable=True)

class FactPnLMonthly(Base, TimestampMixin):
    __tablename__ = "fact_pnl_monthly"
    __table_args__ = (
        Index(
            "uq_pnl_month_manual",
            "project_id",
            "account_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_pnl_month_run",
            "project_id",
            "import_run_id",
            "account_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    account_name: Mapped[str] = mapped_column(String(256), index=True)
    parent_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    month: Mapped[dt.date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(16), default="plan")
    amount: Mapped[float] = mapped_column(Float, default=0.0)

class FactCashflowMonthly(Base, TimestampMixin):
    __tablename__ = "fact_cashflow_monthly"
    __table_args__ = (
        Index(
            "uq_cf_month_manual",
            "project_id",
            "account_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NULL",
        ),
        Index(
            "uq_cf_month_run",
            "project_id",
            "import_run_id",
            "account_name",
            "month",
            "scenario",
            unique=True,
            postgresql_where="import_run_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True)

    account_name: Mapped[str] = mapped_column(String(256), index=True)
    parent_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    month: Mapped[dt.date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(16), default="plan")
    direction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
