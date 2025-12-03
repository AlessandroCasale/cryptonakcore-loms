# app/core/scheduler.py
import asyncio
import logging

from app.db.session import SessionLocal
from app.services.oms import auto_close_positions
from app.core.config import settings

logger = logging.getLogger("scheduler")


async def position_watcher() -> None:
    """
    Loop di background che chiama periodicamente auto_close_positions(db).

    L'intervallo è configurabile tramite Settings.AUTO_CLOSE_INTERVAL_SEC
    (env AUTO_CLOSE_INTERVAL_SEC). Se il valore è <= 0, viene forzato a 1.
    """
    raw_interval = getattr(settings, "AUTO_CLOSE_INTERVAL_SEC", 1) or 1

    if raw_interval <= 0:
        logger.warning(
            {
                "event": "position_watcher_invalid_interval",
                "configured_interval": raw_interval,
                "fallback_interval": 1,
            }
        )
        interval_sec = 1
    else:
        interval_sec = float(raw_interval)

    logger.info(
        {
            "event": "position_watcher_started",
            "interval_sec": interval_sec,
        }
    )

    while True:
        db = SessionLocal()
        try:
            auto_close_positions(db)
        except Exception as e:
            logger.error(
                {
                    "event": "position_watcher_error",
                    "error_type": type(e).__name__,
                    "error": str(e),
                }
            )
        finally:
            db.close()

        await asyncio.sleep(interval_sec)


def start_scheduler(app) -> None:
    """
    Registra il watcher come background task all'avvio di FastAPI.
    """
    @app.on_event("startup")
    async def _start_watcher() -> None:
        asyncio.create_task(position_watcher())

