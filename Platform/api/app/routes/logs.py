from fastapi import APIRouter
import os

router = APIRouter(prefix="/logs", tags=["logs"])

LOG_FILE = "Platform/runtime/opening.log"


@router.get("/")
def logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": "(no logs yet)"}

    with open(LOG_FILE, "r") as f:
        return {"logs": f.read()[-5000:]}
