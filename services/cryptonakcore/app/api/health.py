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
        "environment": settings.ENVIRONMENT,
        "broker_mode": settings.BROKER_MODE,
        "oms_enabled": settings.OMS_ENABLED,
        "database_url": settings.DATABASE_URL,
        "audit_log_path": settings.AUDIT_LOG_PATH,
    }
