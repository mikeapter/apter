from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, twofa, bots, logs, system, dashboard, signals, insights
from app.routes import subscriptions
from app.db.init_db import init_db

app = FastAPI(
    title="BotTrader Control Plane",
    version="0.1.0",
    openapi_version="3.1.0",
)


@app.on_event("startup")
def _startup() -> None:
    # Ensure sqlite tables exist (users + future subscription fields)
    init_db()

# Allow Next.js dev server to call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(twofa.router)
app.include_router(bots.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(signals.router)
app.include_router(insights.router)
app.include_router(subscriptions.router)
