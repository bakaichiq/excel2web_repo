from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "excel2web",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    timezone=settings.TZ,
    enable_utc=True,
)
