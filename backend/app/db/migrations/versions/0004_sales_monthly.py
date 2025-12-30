"""sales monthly

Revision ID: 0004_sales_monthly
Revises: 0003_operation_dependency
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_sales_monthly"
down_revision = "0003_operation_dependency"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sales_monthly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("import_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_name", sa.String(length=256), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_sales_monthly_project_id", "sales_monthly", ["project_id"])
    op.create_index("ix_sales_monthly_month", "sales_monthly", ["month"])
    op.create_index(
        "uq_sales_month_manual",
        "sales_monthly",
        ["project_id", "item_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NULL"),
    )
    op.create_index(
        "uq_sales_month_run",
        "sales_monthly",
        ["project_id", "import_run_id", "item_name", "month", "scenario"],
        unique=True,
        postgresql_where=sa.text("import_run_id IS NOT NULL"),
    )


def downgrade():
    op.drop_table("sales_monthly")
