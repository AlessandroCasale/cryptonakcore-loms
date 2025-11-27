from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Position as PositionModel
from datetime import datetime

from app.services.market_simulator import MarketSimulator


router = APIRouter()


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
async def list_positions(db: Session = Depends(get_db)):
    """
    Lista tutte le posizioni aperte (per ora lista completa).
    """
    positions = db.query(PositionModel).all()
    return positions

@router.post("/{position_id}/close", response_model=PositionResponse)
async def close_position(position_id: int, db: Session = Depends(get_db)):
    """
    Chiude una posizione manualmente:
    - status -> 'closed'
    - imposta closed_at, close_price, pnl
    - auto_close_reason -> 'manual'
    """
    position = db.query(PositionModel).filter(PositionModel.id == position_id).first()

    if position is None:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.status == "closed":
        # è già chiusa, restituiamo comunque l'oggetto
        return position

    # Prezzo corrente dal market simulator
    price = MarketSimulator.get_price(position.symbol)
    current_price = float(price)

    # Calcolo PnL
    entry = float(position.entry_price)
    qty = float(position.qty)
    side = (position.side or "").lower()

    if side in ("buy", "long"):
        is_long = True
    elif side in ("sell", "short"):
        is_long = False
    else:
        # fallback: consideriamo long
        is_long = True

    if is_long:
        position.pnl = (current_price - entry) * qty
    else:
        position.pnl = (entry - current_price) * qty

    # Aggiorniamo stato e metadati di chiusura
    position.status = "closed"
    position.closed_at = datetime.utcnow()
    position.close_price = current_price
    position.auto_close_reason = "manual"

    db.commit()
    db.refresh(position)
    return position

