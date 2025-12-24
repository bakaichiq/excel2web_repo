from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.models._mixins import TimestampMixin

class ImportError(Base, TimestampMixin):
    __tablename__ = "import_error"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_run.id", ondelete="CASCADE"), index=True)
    sheet: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message: Mapped[str] = mapped_column(Text)

    import_run = relationship("ImportRun", back_populates="errors")
