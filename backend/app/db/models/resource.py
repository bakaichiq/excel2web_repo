from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class Resource(Base, TimestampMixin):
    __tablename__ = "resource"
    __table_args__ = (UniqueConstraint("project_id", "name", "category", name="uq_resource_project_name_cat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    category: Mapped[str] = mapped_column(String(64))  # люди/техника

    project = relationship("Project")
