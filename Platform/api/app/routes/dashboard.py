from fastapi import APIRouter

from app.services.dashboard_service import build_dashboard_payload

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard():
    return build_dashboard_payload()
