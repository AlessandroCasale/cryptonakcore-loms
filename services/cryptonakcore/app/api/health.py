from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health():
    """
    Endpoint di health-check per CryptoNakCore LOMS.

    Ritorna info base di configurazione utili per capire
    in che modalità sta girando il servizio.
    """
    return {
        "ok": True,
        "service": "CryptoNakCore LOMS",
        "status": "ok",
        "environment": settings.environment,
        "broker_mode": settings.broker_mode,
        "oms_enabled": settings.oms_enabled,
        "database_url": settings.DATABASE_URL,
        "audit_log_path": settings.AUDIT_LOG_PATH,
        # Real Price Engine (nuovi campi)
        "price_source": settings.price_source.value,
        "price_mode": settings.price_mode.value,
    }
