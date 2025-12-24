from fastapi import APIRouter
from app.api.routers import auth, projects, imports, reports, entries, admin, gpr

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(gpr.router, prefix="/gpr", tags=["gpr"])
