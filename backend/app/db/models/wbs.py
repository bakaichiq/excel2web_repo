from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class WBS(Base, TimestampMixin):
    __tablename__ = "wbs"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_wbs_project_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(512), index=True)  # e.g. "Паркинг/Фундамент"

    project = relationship("Project", back_populates="wbs_items")
    operations = relationship("Operation", back_populates="wbs")
