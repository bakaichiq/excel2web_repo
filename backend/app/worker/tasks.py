import datetime as dt
from sqlalchemy.orm import Session

from app.worker.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.crud.imports import set_import_status, add_import_errors, get_import_run
from app.services.etl.importer import run_import


@celery_app.task(name="imports.run_import", bind=True)
def run_import_task(self, import_run_id: int):
    db: Session = SessionLocal()
    try:
        run = get_import_run(db, import_run_id)
        if not run:
            logger.error("import_run_missing", import_run_id=import_run_id)
            return

        # Старт
        set_import_status(db, import_run_id, "running", started_at=dt.datetime.utcnow())

        # Основной импорт
        errors, rows_loaded = run_import(db, run)

        # Ошибки импорта (если есть)
        if errors:
            add_import_errors(db, import_run_id, errors)

        status = "success" if not errors else "success_with_errors"
        set_import_status(
            db,
            import_run_id,
            status,
            finished_at=dt.datetime.utcnow(),
            rows_loaded=rows_loaded,
        )

        logger.info(
            "import_finished",
            import_run_id=import_run_id,
            status=status,
            rows_loaded=rows_loaded,
            errors=len(errors) if errors else 0,
        )

    except Exception as e:
        logger.exception("import_failed", import_run_id=import_run_id, error=str(e))

        # ВАЖНО: транзакция могла быть в aborted state -> сначала rollback
        try:
            db.rollback()
            set_import_status(db, import_run_id, "failed", finished_at=dt.datetime.utcnow())
        except Exception as e2:
            logger.exception(
                "import_failed_status_update_failed",
                import_run_id=import_run_id,
                error=str(e2),
            )
            # Фоллбек: пробуем другой сессией (на случай, если db полностью "сломана")
            try:
                db2: Session = SessionLocal()
                try:
                    set_import_status(db2, import_run_id, "failed", finished_at=dt.datetime.utcnow())
                finally:
                    db2.close()
            except Exception as e3:
                logger.exception(
                    "import_failed_status_update_failed_second_attempt",
                    import_run_id=import_run_id,
                    error=str(e3),
                )

        raise

    finally:
        db.close()
