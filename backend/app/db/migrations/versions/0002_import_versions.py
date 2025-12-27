"""import versions

Revision ID: 0002_import_versions
Revises: 0001_init
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_import_versions"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_baseline_row", "baseline_volume", type_="unique")
    op.drop_constraint("uq_fact_volume_day", "fact_volume_daily", type_="unique")
    op.drop_constraint("uq_plan_volume_month", "plan_volume_monthly", type_="unique")
    op.drop_constraint("uq_res_day", "fact_resource_daily", type_="unique")
    op.drop_constraint("uq_pnl_month", "fact_pnl_monthly", type_="unique")
    op.drop_constraint("uq_cf_month", "fact_cashflow_monthly", type_="unique")

    op.create_index(
        "uq_baseline_row_manual",
        "baseline_volume",
        ["project_id", "operation_code", "category", "item_name"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_baseline_row_run",
        "baseline_volume",
        ["project_id", "import_run_id", "operation_code", "category", "item_name"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )

    op.create_index(
        "uq_fact_volume_day_manual",
        "fact_volume_daily",
        ["project_id", "operation_code", "category", "item_name", "date"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_fact_volume_day_run",
        "fact_volume_daily",
        ["project_id", "import_run_id", "operation_code", "category", "item_name", "date"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )

    op.create_index(
        "uq_plan_volume_month_manual",
        "plan_volume_monthly",
        ["project_id", "operation_code", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_plan_volume_month_run",
        "plan_volume_monthly",
        ["project_id", "import_run_id", "operation_code", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )

    op.create_index(
        "uq_res_day_manual",
        "fact_resource_daily",
        ["project_id", "resource_name", "category", "date", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_res_day_run",
        "fact_resource_daily",
        ["project_id", "import_run_id", "resource_name", "category", "date", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )

    op.create_index(
        "uq_pnl_month_manual",
        "fact_pnl_monthly",
        ["project_id", "account_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_pnl_month_run",
        "fact_pnl_monthly",
        ["project_id", "import_run_id", "account_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )

    op.create_index(
        "uq_cf_month_manual",
        "fact_cashflow_monthly",
        ["project_id", "account_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_cf_month_run",
        "fact_cashflow_monthly",
        ["project_id", "import_run_id", "account_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_cf_month_run", table_name="fact_cashflow_monthly")
    op.drop_index("uq_cf_month_manual", table_name="fact_cashflow_monthly")
    op.drop_index("uq_pnl_month_run", table_name="fact_pnl_monthly")
    op.drop_index("uq_pnl_month_manual", table_name="fact_pnl_monthly")
    op.drop_index("uq_res_day_run", table_name="fact_resource_daily")
    op.drop_index("uq_res_day_manual", table_name="fact_resource_daily")
    op.drop_index("uq_plan_volume_month_run", table_name="plan_volume_monthly")
    op.drop_index("uq_plan_volume_month_manual", table_name="plan_volume_monthly")
    op.drop_index("uq_fact_volume_day_run", table_name="fact_volume_daily")
    op.drop_index("uq_fact_volume_day_manual", table_name="fact_volume_daily")
    op.drop_index("uq_baseline_row_run", table_name="baseline_volume")
    op.drop_index("uq_baseline_row_manual", table_name="baseline_volume")

    op.create_unique_constraint(
        "uq_baseline_row",
        "baseline_volume",
        ["project_id", "operation_code", "category", "item_name"],
    )
    op.create_unique_constraint(
        "uq_fact_volume_day",
        "fact_volume_daily",
        ["project_id", "operation_code", "category", "item_name", "date"],
    )
    op.create_unique_constraint(
        "uq_plan_volume_month",
        "plan_volume_monthly",
        ["project_id", "operation_code", "month", "scenario"],
    )
    op.create_unique_constraint(
        "uq_res_day",
        "fact_resource_daily",
        ["project_id", "resource_name", "category", "date", "scenario"],
    )
    op.create_unique_constraint(
        "uq_pnl_month",
        "fact_pnl_monthly",
        ["project_id", "account_name", "month", "scenario"],
    )
    op.create_unique_constraint(
        "uq_cf_month",
        "fact_cashflow_monthly",
        ["project_id", "account_name", "month", "scenario"],
    )
