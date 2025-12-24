"""init

Revision ID: 0001_init
Revises: 
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=256), nullable=True),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_user_login", "user", ["login"], unique=True)

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_project_code", "project", ["code"], unique=True)

    op.create_table(
        "wbs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "path", name="uq_wbs_project_path"),
    )
    op.create_index("ix_wbs_project_id", "wbs", ["project_id"])
    op.create_index("ix_wbs_path", "wbs", ["path"])

    op.create_table(
        "operation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wbs_id", sa.Integer(), sa.ForeignKey("wbs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("discipline", sa.String(length=128), nullable=True),
        sa.Column("block", sa.String(length=128), nullable=True),
        sa.Column("floor", sa.String(length=64), nullable=True),
        sa.Column("ugpr", sa.String(length=128), nullable=True),
        sa.Column("plan_qty_total", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("plan_start", sa.Date(), nullable=True),
        sa.Column("plan_finish", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "code", name="uq_operation_project_code"),
    )
    op.create_index("ix_operation_project_id", "operation", ["project_id"])
    op.create_index("ix_operation_code", "operation", ["code"])

    op.create_table(
        "resource",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "name", "category", name="uq_resource_project_name_cat"),
    )
    op.create_index("ix_resource_project_id", "resource", ["project_id"])
    op.create_index("ix_resource_name", "resource", ["name"])

    op.create_table(
        "fin_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("parent_name", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "kind", "name", name="uq_fin_account_project_kind_name"),
    )
    op.create_index("ix_fin_account_project_id", "fin_account", ["project_id"])
    op.create_index("ix_fin_account_name", "fin_account", ["name"])

    op.create_table(
        "import_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "file_hash", name="uq_import_project_hash"),
    )
    op.create_index("ix_import_run_project_id", "import_run", ["project_id"])
    op.create_index("ix_import_run_file_hash", "import_run", ["file_hash"])

    op.create_table(
        "import_error",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet", sa.String(length=128), nullable=True),
        sa.Column("row_num", sa.Integer(), nullable=True),
        sa.Column("column", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_import_error_import_run_id", "import_error", ["import_run_id"])


    op.create_table(
        "baseline_volume",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation_code", sa.String(length=128), nullable=True),
        sa.Column("operation_name", sa.String(length=512), nullable=True),
        sa.Column("wbs", sa.String(length=256), nullable=True),
        sa.Column("discipline", sa.String(length=128), nullable=True),
        sa.Column("block", sa.String(length=128), nullable=True),
        sa.Column("floor", sa.String(length=64), nullable=True),
        sa.Column("ugpr", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=512), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("plan_qty_total", sa.Float(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("amount_total", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "operation_code", "category", "item_name", name="uq_baseline_row"),
    )
    op.create_index("ix_baseline_volume_project_id", "baseline_volume", ["project_id"])
    op.create_index("ix_baseline_volume_operation_code", "baseline_volume", ["operation_code"])

    op.create_table(
        "fact_volume_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation_code", sa.String(length=128), nullable=True),
        sa.Column("operation_name", sa.String(length=512), nullable=True),
        sa.Column("wbs", sa.String(length=256), nullable=True),
        sa.Column("discipline", sa.String(length=128), nullable=True),
        sa.Column("block", sa.String(length=128), nullable=True),
        sa.Column("floor", sa.String(length=64), nullable=True),
        sa.Column("ugpr", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=512), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "operation_code", "category", "item_name", "date", name="uq_fact_volume_day"),
    )
    op.create_index("ix_fact_volume_daily_project_id", "fact_volume_daily", ["project_id"])
    op.create_index("ix_fact_volume_daily_operation_code", "fact_volume_daily", ["operation_code"])
    op.create_index("ix_fact_volume_daily_date", "fact_volume_daily", ["date"])

    op.create_table(
        "plan_volume_monthly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation_code", sa.String(length=128), nullable=False),
        sa.Column("operation_name", sa.String(length=512), nullable=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "operation_code", "month", "scenario", name="uq_plan_volume_month"),
    )
    op.create_index("ix_plan_volume_monthly_project_id", "plan_volume_monthly", ["project_id"])
    op.create_index("ix_plan_volume_monthly_operation_code", "plan_volume_monthly", ["operation_code"])
    op.create_index("ix_plan_volume_monthly_month", "plan_volume_monthly", ["month"])

    op.create_table(
        "fact_resource_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_name", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("manhours", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "resource_name", "category", "date", "scenario", name="uq_res_day"),
    )
    op.create_index("ix_fact_resource_daily_project_id", "fact_resource_daily", ["project_id"])
    op.create_index("ix_fact_resource_daily_resource_name", "fact_resource_daily", ["resource_name"])
    op.create_index("ix_fact_resource_daily_date", "fact_resource_daily", ["date"])

    op.create_table(
        "fact_pnl_monthly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_name", sa.String(length=256), nullable=False),
        sa.Column("parent_name", sa.String(length=256), nullable=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "account_name", "month", "scenario", name="uq_pnl_month"),
    )
    op.create_index("ix_fact_pnl_monthly_project_id", "fact_pnl_monthly", ["project_id"])
    op.create_index("ix_fact_pnl_monthly_account_name", "fact_pnl_monthly", ["account_name"])
    op.create_index("ix_fact_pnl_monthly_month", "fact_pnl_monthly", ["month"])

    op.create_table(
        "fact_cashflow_monthly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_name", sa.String(length=256), nullable=False),
        sa.Column("parent_name", sa.String(length=256), nullable=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "account_name", "month", "scenario", name="uq_cf_month"),
    )
    op.create_index("ix_fact_cashflow_monthly_project_id", "fact_cashflow_monthly", ["project_id"])
    op.create_index("ix_fact_cashflow_monthly_account_name", "fact_cashflow_monthly", ["account_name"])
    op.create_index("ix_fact_cashflow_monthly_month", "fact_cashflow_monthly", ["month"])

def downgrade():
    op.drop_table("fact_cashflow_monthly")
    op.drop_table("fact_pnl_monthly")
    op.drop_table("fact_resource_daily")
    op.drop_table("plan_volume_monthly")
    op.drop_table("fact_volume_daily")
    op.drop_table("baseline_volume")
    op.drop_table("import_error")
    op.drop_table("import_run")
    op.drop_table("fin_account")
    op.drop_table("resource")
    op.drop_table("operation")
    op.drop_table("wbs")
    op.drop_table("project")
    op.drop_table("user")
