from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.services.seed import seed_demo

def create_app() -> FastAPI:
    configure_logging(settings.ENV)
    app = FastAPI(title="Excel2Web ERP (MVP)", version="0.1.0")

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.on_event("startup")
    def _startup():
        # Ensure tables exist for dev-only convenience; in prod rely on alembic
        if settings.ENV == "dev":
            Base.metadata.create_all(bind=engine)
        if settings.SEED_DEMO and settings.ENV == "dev":
            seed_demo()

    app.include_router(api_router)
    logger.info("app_started", env=settings.ENV)
    return app

app = create_app()
