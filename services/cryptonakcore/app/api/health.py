import logging

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger("health")


@router.get("/health")
async def health():
    """
    Endpoint di health-check semplice:
    - ok / status
    - nome servizio
    - ambiente logico (ENVIRONMENT)
    - modalità broker (BROKER_MODE)
    """

    payload = {
        "ok": True,
        "service": "CryptoNakCore LOMS",
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "broker_mode": settings.BROKER_MODE,
    }

    logger.info(
        {
            "event": "health_check",
            **payload,
        }
    )

    return payload
