from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import SessionLocal
from app.db.models import Position as PositionModel

router = APIRouter()


# ---------- Dependency DB ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Pydantic models ----------

class StatsResponse(BaseModel):
    total_positions: int
    open_positions: int
    closed_positions: int
    total_pnl: float
    winning_trades: int
    losing_trades: int
    tp_count: int
    sl_count: int

    # Nuove metriche derivate (per ora con default)
    winrate: float = 0.0                # percentuale tra 0 e 100
    avg_pnl_per_trade: float = 0.0      # PnL medio per trade chiuso
    avg_pnl_win: float | None = None    # PnL medio delle vincenti
    avg_pnl_loss: float | None = None   # PnL medio delle perdenti



# ---------- Endpoint ----------

@router.get("/", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """
    Statistiche base sulle posizioni paper.
    """

    total_positions = db.query(PositionModel).count()

    open_positions = (
        db.query(PositionModel)
        .filter(PositionModel.status == "open")
        .count()
    )

    closed_positions = (
        db.query(PositionModel)
        .filter(PositionModel.status == "closed")
        .count()
    )

    # Somma PnL (se None, trattiamo come 0)
    total_pnl = db.query(func.coalesce(func.sum(PositionModel.pnl), 0.0)).scalar() or 0.0

    # Trade chiusi vincenti / perdenti (pnl > 0 / pnl < 0)
    winning_trades = (
        db.query(PositionModel)
        .filter(PositionModel.status == "closed", PositionModel.pnl > 0)
        .count()
    )

    losing_trades = (
        db.query(PositionModel)
        .filter(PositionModel.status == "closed", PositionModel.pnl < 0)
        .count()
    )

    # Conteggio chiusure per TP/SL
    tp_count = (
        db.query(PositionModel)
        .filter(PositionModel.auto_close_reason == "tp")
        .count()
    )

    sl_count = (
        db.query(PositionModel)
        .filter(PositionModel.auto_close_reason == "sl")
        .count()
    )

    # ------- Metriche derivate -------

    # Winrate in percentuale (solo sui trade chiusi)
    if closed_positions > 0:
        winrate = (winning_trades / closed_positions) * 100.0
        avg_pnl_per_trade = total_pnl / closed_positions
    else:
        winrate = 0.0
        avg_pnl_per_trade = 0.0

    # PnL medio delle vincenti
    avg_pnl_win = (
        db.query(func.avg(PositionModel.pnl))
        .filter(PositionModel.status == "closed", PositionModel.pnl > 0)
        .scalar()
    )

    # PnL medio delle perdenti
    avg_pnl_loss = (
        db.query(func.avg(PositionModel.pnl))
        .filter(PositionModel.status == "closed", PositionModel.pnl < 0)
        .scalar()
    )

    return StatsResponse(
        total_positions=total_positions,
        open_positions=open_positions,
        closed_positions=closed_positions,
        total_pnl=float(total_pnl),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        tp_count=tp_count,
        sl_count=sl_count,
        winrate=winrate,
        avg_pnl_per_trade=avg_pnl_per_trade,
        avg_pnl_win=float(avg_pnl_win) if avg_pnl_win is not None else None,
        avg_pnl_loss=float(avg_pnl_loss) if avg_pnl_loss is not None else None,
    )

