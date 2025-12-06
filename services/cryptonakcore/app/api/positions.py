# services/cryptonakcore/app/api/positions.py
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Position as PositionModel
from app.core.config import settings
from app.services.oms import _get_price_source  # _normalize_side non serve più qui
from app.services.pricing import select_price, PriceSourceError
from app.services.broker_adapter import get_broker_adapter

router = APIRouter()
logger = logging.getLogger("api.positions")


# ------------ Pydantic ------------


class PositionResponse(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    entry_price: float | None
    tp_price: float | None
    sl_price: float | None
    status: str

    created_at: datetime | None = None
    closed_at: datetime | None = None
    close_price: float | None = None
    pnl: float | None = None
    auto_close_reason: str | None = None

    # Campi extra per Exit Engine / Real Price
    exchange: str | None = None
    market_type: str | None = None
    account_label: str | None = None
    exit_strategy: str | None = None
    dynamic_tp_price: float | None = None
    dynamic_sl_price: float | None = None
    max_favorable_move: float | None = None
    exit_meta: dict | None = None

    class Config:
        from_attributes = True


# ------------ Dependency DB ------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------ Endpoints ------------


@router.get("/", response_model=list[PositionResponse])
async def list_positions(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista le posizioni.

    - Se status NON è passato → tutte le posizioni (aperte + chiuse).
    - Se status = "open"  → solo posizioni aperte.
    - Se status = "closed" → solo posizioni chiuse.
    """
    query = db.query(PositionModel)

    if status is not None:
        status_norm = status.lower()
        if status_norm not in ("open", "closed"):
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Allowed values: 'open', 'closed'.",
            )
        query = query.filter(PositionModel.status == status_norm)

    positions = query.all()
    return positions


@router.post("/{position_id}/close", response_model=PositionResponse)
async def close_position(position_id: int, db: Session = Depends(get_db)):
    """
    Chiude una posizione manualmente:

    - legge il prezzo corrente dalla sorgente configurata (PriceSource)
      usando lo stesso resolver dell'OMS (_get_price_source + PRICE_MODE)
    - delega la chiusura al BrokerAdapter (close_price + reason="manual"),
      che aggiorna:
        status, closed_at, close_price, pnl, auto_close_reason
    """

    position = (
        db.query(PositionModel)
        .filter(PositionModel.id == position_id)
        .first()
    )

    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")

    # Se è già chiusa, restituiamo comunque l'oggetto attuale (idempotente)
    if position.status == "closed":
        return position

    # Prezzo corrente dal PriceSource configurato (simulator / exchange / ...)
    price_source = _get_price_source()
    price_mode = settings.price_mode
    price_source_label = str(settings.price_source)

    try:
        quote = price_source.get_quote(position.symbol)
        current_price = float(select_price(quote, price_mode))

    except PriceSourceError as e:
        # Errore specifico della sorgente prezzi (HTTP, timeout, dati invalidi, ecc.)
        logger.error(
            {
                "event": "price_source_error_manual_close",
                "position_id": position_id,
                "symbol": position.symbol,
                "error_type": type(e).__name__,
                "error": str(e),
                "price_source": price_source_label,
                "price_mode": str(price_mode),
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Price source unavailable for manual close",
        )

    except Exception as e:
        # Qualsiasi altro errore interno
        logger.error(
            {
                "event": "manual_close_unexpected_error",
                "position_id": position_id,
                "symbol": position.symbol,
                "error_type": type(e).__name__,
                "error": str(e),
                "price_source": price_source_label,
                "price_mode": str(price_mode),
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Internal error during manual close",
        )

    # Chiudiamo via BrokerAdapter (paper oggi, live domani)
    adapter = get_broker_adapter()
    broker_result = adapter.close_position(
        db,
        position=position,
        close_price=current_price,
        reason="manual",
    )

    if not broker_result.ok or broker_result.position is None:
        logger.error(
            {
                "event": "manual_close_broker_failed",
                "position_id": position_id,
                "symbol": position.symbol,
                "reason": broker_result.reason,
                "price_source": price_source_label,
                "price_mode": str(price_mode),
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Broker close failed",
        )

    closed_pos = broker_result.position

    logger.info(
        {
            "event": "position_closed_manual",
            "position_id": closed_pos.id,
            "symbol": closed_pos.symbol,
            "side": closed_pos.side,
            "entry": float(closed_pos.entry_price) if closed_pos.entry_price is not None else None,
            "exit": float(closed_pos.close_price) if closed_pos.close_price is not None else None,
            "pnl": float(closed_pos.pnl) if closed_pos.pnl is not None else None,
            "qty": float(closed_pos.qty),
            "price_source": price_source_label,
            "price_mode": str(price_mode),
        }
    )

    return closed_pos
