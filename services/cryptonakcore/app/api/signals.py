from datetime import datetime
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Order as OrderModel, Position as PositionModel
from app.services.audit import log_bounce_signal
from app.core.config import settings
from app.services.oms import _normalize_side, check_risk_limits


router = APIRouter()
logger = logging.getLogger("signals")

# Default per TP/SL e quantità (paper)
DEFAULT_TP_PCT = 4.5
DEFAULT_SL_PCT = 1.5
DEFAULT_QTY = 1.0


class BounceSignal(BaseModel):
    symbol: str
    side: str  # "long" or "short"
    price: float
    timestamp: datetime

    # Nuovi campi per il contesto del segnale
    exchange: str = "bitget"           # es. "bitget", "bybit"
    timeframe_min: int = 5             # es. 1, 5, 15...
    strategy: str = "bounce_ema10_strict"

    # TP/SL suggeriti dalla strategia (in percentuale, es. 4.5 / 1.5)
    tp_pct: float | None = None
    sl_pct: float | None = None


# --------- Dependency DB ---------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- Endpoint ---------


@router.post("/bounce")
async def receive_bounce_signal(
    signal: BounceSignal,
    db: Session = Depends(get_db),
):
    """
    Riceve un segnale Bounce:
    - lo logga su file JSONL
    - se OMS_ENABLED=True e i limiti di rischio lo permettono,
      crea un ordine + posizione paper
    """

    # 1) Log su audit (sempre)
    payload = signal.model_dump(mode="json")
    log_bounce_signal(payload)

    logger.info(
        {
            "event": "bounce_received",
            "symbol": signal.symbol,
            "side": signal.side,
            "exchange": signal.exchange,
            "timeframe_min": signal.timeframe_min,
            "strategy": signal.strategy,
        }
    )

    # 2) Se l'OMS è disabilitato, ci fermiamo qui
    if not settings.OMS_ENABLED:
        logger.info(
            {
                "event": "bounce_ignored_oms_disabled",
                "symbol": signal.symbol,
                "side": signal.side,
            }
        )
        return {
            "received": True,
            "oms_enabled": False,
            "risk_ok": False,
            "reason": "OMS disabled via config",
        }

    # 3) Normalizza side e prezzo di ingresso
    entry_price = float(signal.price)
    side = _normalize_side(signal.side)

    if side not in ("long", "short"):
        # Per ora, se side non è valido, non apriamo nulla
        logger.info(
            {
                "event": "bounce_invalid_side",
                "symbol": signal.symbol,
                "raw_side": signal.side,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": False,
            "error": "invalid_side",
        }

    qty = DEFAULT_QTY
    notional_usdt = entry_price * qty

    # 4) Controllo limiti di rischio base (numero posizioni aperte + size per posizione)
    risk_ok, risk_reason = check_risk_limits(
        db,
        symbol=signal.symbol,
        entry_price=entry_price,
        qty=qty,
    )
    if not risk_ok:
        # NON apriamo ordine/posizione, ma segnaliamo il blocco
        logger.info(
            {
                "event": "bounce_risk_block",
                "symbol": signal.symbol,
                "side": side,
                "risk_reason": risk_reason,
                "entry_price": entry_price,
                "qty": qty,
                "notional_usdt": notional_usdt,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": False,
            "risk_reason": risk_reason,
        }

    # 5) Calcolo TP/SL in base a price e percentuali
    tp_pct = signal.tp_pct if signal.tp_pct is not None else DEFAULT_TP_PCT
    sl_pct = signal.sl_pct if signal.sl_pct is not None else DEFAULT_SL_PCT

    tp_price: float | None
    sl_price: float | None

    if side == "long":
        tp_price = entry_price * (1.0 + tp_pct / 100.0)
        sl_price = entry_price * (1.0 - sl_pct / 100.0) if sl_pct is not None else None
    elif side == "short":
        tp_price = entry_price * (1.0 - tp_pct / 100.0)
        sl_price = entry_price * (1.0 + sl_pct / 100.0) if sl_pct is not None else None
    else:
        # Questo blocco dovrebbe essere teoricamente irraggiungibile perché filtriamo sopra,
        # ma lo lasciamo per sicurezza.
        logger.info(
            {
                "event": "bounce_invalid_side_post_tp_sl",
                "symbol": signal.symbol,
                "raw_side": signal.side,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": False,
            "error": "invalid_side",
        }

    # 6) Crea ordine paper
    db_order = OrderModel(
        symbol=signal.symbol,
        side=side,
        qty=qty,
        order_type="market",
        tp_price=tp_price,
        sl_price=sl_price,
        status="created",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 7) Crea posizione paper associata
    db_position = PositionModel(
        symbol=signal.symbol,
        side=side,
        qty=qty,
        entry_price=entry_price,
        tp_price=tp_price,
        sl_price=sl_price,
        status="open",
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)

    logger.info(
        {
            "event": "bounce_order_created",
            "symbol": signal.symbol,
            "side": side,
            "order_id": db_order.id,
            "position_id": db_position.id,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "entry_price": entry_price,
            "qty": qty,
            "notional_usdt": notional_usdt,
        }
    )

    return {
        "received": True,
        "oms_enabled": True,
        "risk_ok": True,
        "order_id": db_order.id,
        "position_id": db_position.id,
        "tp_price": tp_price,
        "sl_price": sl_price,
    }
