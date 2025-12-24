import datetime as dt
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class ImportRun(Base, TimestampMixin):
    __tablename__ = "import_run"
    __table_args__ = (UniqueConstraint("project_id", "file_hash", name="uq_import_project_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)

    file_name: Mapped[str] = mapped_column(String(512))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|running|done|failed
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)

    project = relationship("Project")
    errors = relationship("ImportError", back_populates="import_run")
