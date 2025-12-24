from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class FinKind(str):
    BDR = "BDR"
    BDDS = "BDDS"

class FinAccount(Base, TimestampMixin):
    __tablename__ = "fin_account"
    __table_args__ = (UniqueConstraint("project_id", "kind", "name", name="uq_fin_account_project_kind_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # BDR|BDDS
    name: Mapped[str] = mapped_column(String(256), index=True)
    parent_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    project = relationship("Project")
