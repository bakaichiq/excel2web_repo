from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._mixins import TimestampMixin


class OperationDependency(Base, TimestampMixin):
    __tablename__ = "operation_dependency"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "predecessor_id",
            "successor_id",
            name="uq_operation_dependency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    predecessor_id: Mapped[int] = mapped_column(ForeignKey("operation.id", ondelete="CASCADE"), index=True)
    successor_id: Mapped[int] = mapped_column(ForeignKey("operation.id", ondelete="CASCADE"), index=True)
