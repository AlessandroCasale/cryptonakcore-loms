from datetime import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Position
from app.services.market_simulator import MarketSimulator
from app.core.config import settings

logger = logging.getLogger("oms")


def _normalize_side(side: str) -> str:
    """
    Normalizza il side della posizione:
    - "buy"  / "long"  → "long"
    - "sell" / "short" → "short"
    """
    s = (side or "").lower()
    if s in ("buy", "long"):
        return "long"
    if s in ("sell", "short"):
        return "short"
    return s


def check_risk_limits(db: Session, symbol: str) -> tuple[bool, str | None]:
    """
    Controlla i limiti di rischio base (paper), letti da Settings/env:

    - MAX_OPEN_POSITIONS: massimo numero di posizioni aperte in totale
    - MAX_OPEN_POSITIONS_PER_SYMBOL: massimo numero di posizioni aperte per simbolo

    Ritorna:
    - (True, None) se si può aprire una nuova posizione
    - (False, reason) se NON si può aprire (con motivo testuale)
    """

    max_total = settings.MAX_OPEN_POSITIONS
    max_per_symbol = settings.MAX_OPEN_POSITIONS_PER_SYMBOL

    # Tutte le posizioni aperte
    base_q = db.query(Position).filter(Position.status == "open")

    total_open = base_q.count()
    open_for_symbol = base_q.filter(Position.symbol == symbol).count()

    # Controllo limite totale
    if total_open >= max_total:
        reason = f"max_total_open_reached (total={total_open}, limit={max_total})"
        logger.info(
            {
                "event": "risk_block",
                "scope": "total",
                "symbol": symbol,
                "total_open": total_open,
                "limit": max_total,
                "reason": reason,
            }
        )
        return False, reason

    # Controllo limite per simbolo
    if open_for_symbol >= max_per_symbol:
        reason = (
            f"max_symbol_open_reached (symbol={symbol}, "
            f"count={open_for_symbol}, limit={max_per_symbol})"
        )
        logger.info(
            {
                "event": "risk_block",
                "scope": "symbol",
                "symbol": symbol,
                "open_for_symbol": open_for_symbol,
                "limit": max_per_symbol,
                "reason": reason,
            }
        )
        return False, reason

    # Tutto ok, si può aprire
    return True, None


def auto_close_positions(db: Session) -> None:
    """
    Controlla tutte le posizioni aperte e le chiude in modalità paper
    quando il prezzo simulato raggiunge TP (tp_price) o SL (sl_price).
    Le posizioni più giovani di 7 secondi NON vengono chiuse.
    """

    open_positions = db.query(Position).filter(Position.status == "open").all()
    now = datetime.utcnow()  # momento attuale, usato per calcolare l'età

    for pos in open_positions:
        # ⏱️ NON chiudere posizioni create da meno di 7 secondi
        if pos.created_at is not None:
            age_sec = (now - pos.created_at).total_seconds()
            if age_sec < 7:
                continue

        # Se non ha né TP né SL non c'è nulla da fare
        if pos.tp_price is None and pos.sl_price is None:
            continue

        # Prezzo corrente dal market simulator
        price = MarketSimulator.get_price(pos.symbol)
        current_price = float(price)

        # Converte TP/SL in float se presenti
        tp: Optional[float] = float(pos.tp_price) if pos.tp_price is not None else None
        sl: Optional[float] = float(pos.sl_price) if pos.sl_price is not None else None

        side = _normalize_side(pos.side)

        hit_tp = False
        hit_sl = False

        if tp is not None:
            if side == "long":
                hit_tp = current_price >= tp
            elif side == "short":
                hit_tp = current_price <= tp

        if sl is not None:
            if side == "long":
                hit_sl = current_price <= sl
            elif side == "short":
                hit_sl = current_price >= sl

        # Nessun trigger → continua
        if not (hit_tp or hit_sl):
            continue

        reason = "tp" if hit_tp else "sl"

        # ✅ NIENTE Order di chiusura per ora, aggiorniamo solo la Position
        pos.status = "closed"
        pos.closed_at = now
        pos.close_price = current_price
        pos.auto_close_reason = reason

        # Calcolo PnL
        entry = float(pos.entry_price)
        qty = float(pos.qty)

        if side == "long":
            pos.pnl = (current_price - entry) * qty
        else:  # short
            pos.pnl = (entry - current_price) * qty

        db.commit()

        logger.info(
            {
                "event": "position_closed",
                "reason": reason,
                "symbol": pos.symbol,
                "entry": entry,
                "exit": current_price,
                "pnl": float(pos.pnl),
                "qty": qty,
                "pos_id": pos.id,
            }
        )
