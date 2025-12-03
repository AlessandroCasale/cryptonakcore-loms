# services/cryptonakcore/app/api/positions.py
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Position as PositionModel
from app.core.config import settings
from app.services.oms import _normalize_side, _get_price_source
from app.services.pricing import select_price, PriceSourceError


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
    - calcola il PnL in base a entry_price, qty e side
    - aggiorna:
        status -> 'closed'
        closed_at, close_price, pnl
        auto_close_reason -> 'manual'
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
    now = datetime.utcnow()

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

    # Calcolo PnL (riusiamo la stessa normalizzazione del side di OMS)
    entry = float(position.entry_price)
    qty = float(position.qty)
    side = _normalize_side(position.side)

    if side == "long":
        pnl = (current_price - entry) * qty
    elif side == "short":
        pnl = (entry - current_price) * qty
    else:
        # side sconosciuto → chiudiamo comunque, ma logghiamo il problema
        logger.warning(
            {
                "event": "manual_close_unknown_side",
                "position_id": position_id,
                "symbol": position.symbol,
                "raw_side": position.side,
            }
        )
        # fallback: consideriamo long
        pnl = (current_price - entry) * qty

    position.pnl = pnl

    # Aggiorniamo stato e metadati di chiusura
    position.status = "closed"
    position.closed_at = now
    position.close_price = current_price
    position.auto_close_reason = "manual"

    db.commit()
    db.refresh(position)

    logger.info(
        {
            "event": "position_closed_manual",
            "position_id": position.id,
            "symbol": position.symbol,
            "side": side,
            "entry": entry,
            "exit": current_price,
            "pnl": float(position.pnl) if position.pnl is not None else None,
            "qty": qty,
            "price_source": price_source_label,
            "price_mode": str(price_mode),
        }
    )

    return position