from fastapi import APIRouter

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
    }
