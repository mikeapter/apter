from fastapi import APIRouter
from app.services.bot_runtime import (
    start_bot,
    stop_bot,
    get_status,
    get_logs,
)

router = APIRouter(prefix="/v1/bots", tags=["bots"])


@router.post("/{bot_id}/start")
def start(bot_id: str):
    return start_bot(bot_id)


@router.post("/{bot_id}/stop")
def stop(bot_id: str):
    return stop_bot(bot_id)


@router.get("/{bot_id}/status")
def status(bot_id: str):
    return get_status(bot_id)


@router.get("/{bot_id}/logs")
def logs(bot_id: str):
    return {"logs": get_logs()}
