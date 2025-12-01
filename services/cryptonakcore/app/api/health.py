# services/cryptonakcore/app/api/health.py

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    """
    Endpoint di health check minimale.

    Usato da tools/check_health.py per verificare che il servizio
    sia su e risponda con uno stato semplice.
    """
    return {
        "ok": True,
        "service": "CryptoNakCore LOMS",
        "status": "ok",
        "environment": settings.environment,
        "broker_mode": settings.broker_mode,
        "oms_enabled": settings.oms_enabled,
    }
