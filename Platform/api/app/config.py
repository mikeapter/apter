from pathlib import Path
from dotenv import dotenv_values

# ==================================================
# HARD-LOCK REPO ROOT (KNOWN STRUCTURE)
# ==================================================
# config.py
# └── app
#     └── api
#         └── Platform
#             └── BotTrader  ← repo root (.env lives here)

REPO_ROOT = Path(__file__).resolve().parents[3]

# ==================================================
# LOAD .env EXPLICITLY
# ==================================================

ENV = dotenv_values(REPO_ROOT / ".env")

def _required(name: str) -> str:
    value = ENV.get(name)
    if value is None or str(value).strip() == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return str(value)

# ==================================================
# PLATFORM CONFIG (ENFORCED)
# ==================================================

BOT_ID = _required("BOT_ID")
BOT_DEFAULT_SCRIPT = _required("BOT_DEFAULT_SCRIPT")

API_PORT = int(_required("API_PORT"))
WEB_PORT = int(_required("WEB_PORT"))

RUNTIME_DIR = (REPO_ROOT / _required("RUNTIME_DIR")).resolve()

LOCAL_DEV_API_KEY = _required("LOCAL_DEV_API_KEY")
