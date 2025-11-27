from fastapi import FastAPI

from app.api import health, signals, orders, positions, market, stats
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler  # ⬅️ nuovo import
from app.db.models import Base
from app.db.session import engine

# inizializza logging JSON
setup_logging()

# istanza FastAPI
app = FastAPI(title="CryptoNakCore LOMS", version="0.1.0")


# crea le tabelle al bootstrap dell'app
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# avvia lo scheduler per l'auto-close delle posizioni
start_scheduler(app)  # ⬅️ questa riga aggancia il task periodico all'app


# registra i router
app.include_router(health.router)
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(positions.router, prefix="/positions", tags=["positions"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/")
async def root():
    return {"status": "ok", "service": "CryptoNakCore LOMS"}
