"""operation dependency

Revision ID: 0003_operation_dependency
Revises: 0002_import_versions
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_operation_dependency"
down_revision = "0002_import_versions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operation_dependency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predecessor_id", sa.Integer(), sa.ForeignKey("operation.id", ondelete="CASCADE"), nullable=False),
        sa.Column("successor_id", sa.Integer(), sa.ForeignKey("operation.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "predecessor_id", "successor_id", name="uq_operation_dependency"),
    )
    op.create_index("ix_operation_dependency_project_id", "operation_dependency", ["project_id"])
    op.create_index("ix_operation_dependency_predecessor_id", "operation_dependency", ["predecessor_id"])
    op.create_index("ix_operation_dependency_successor_id", "operation_dependency", ["successor_id"])


def downgrade():
    op.drop_table("operation_dependency")
