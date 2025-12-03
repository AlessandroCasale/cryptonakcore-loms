from datetime import datetime
import logging
from typing import Optional, List

from sqlalchemy.orm import Session

from app.db.models import Position
from app.services.market_simulator import MarketSimulator
from app.core.config import settings
from app.services.pricing import (
    PriceSourceType,
    SimulatedPriceSource,
    select_price,
)
from app.services.exit_engine import (
    StaticTpSlPolicy,
    ExitContext,
    ExitActionType,
)
from app.services.exchange_client import (
    ExchangePriceSource,
    get_default_exchange_client,
)
from app.services.broker_adapter import (
    BrokerAdapterPaperSim,
    NewPositionParams,
)

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


def _get_price_source():
    """
    Risolve la sorgente prezzi da usare a runtime.

    - simulator: usa MarketSimulator incapsulato in SimulatedPriceSource
    - exchange:  usa ExchangePriceSource con il client di default (per ora dummy)
    - altri valori: warning + fallback al simulatore
    """

    source = settings.price_source

    if source == PriceSourceType.SIMULATOR:
        return SimulatedPriceSource(MarketSimulator)

    if source == PriceSourceType.EXCHANGE:
        client = get_default_exchange_client()
        return ExchangePriceSource(client)

    # Config non ancora supportata → fallback al simulatore
    logger.warning(
        {
            "event": "price_source_fallback_to_simulator",
            "configured_source": str(source),
        }
    )
    return SimulatedPriceSource(MarketSimulator)


def _get_broker_adapter() -> BrokerAdapterPaperSim:
    """
    Risolve il BrokerAdapter da usare a runtime.

    Per ora:
    - BROKER_MODE=paper -> BrokerAdapterPaperSim (gestione Position in DB)

    In futuro:
    - potremo aggiungere adapter diversi per SHADOW / LIVE e fare uno switch
      in base a settings.broker_mode / profilo di rischio.
    """
    # In questa fase abbiamo solo il profilo paper.
    return BrokerAdapterPaperSim()


def check_risk_limits(
    db: Session,
    symbol: str,
    entry_price: Optional[float] = None,
    qty: Optional[float] = None,
) -> tuple[bool, str | None]:
    """
    Controlla i limiti di rischio base (paper), letti da Settings/env:

    - MAX_OPEN_POSITIONS: massimo numero di posizioni aperte in totale
    - MAX_OPEN_POSITIONS_PER_SYMBOL: massimo numero di posizioni aperte per simbolo
    - MAX_SIZE_PER_POSITION_USDT: size massima (notional) per posizione in USDT

    Parametri opzionali:
    - entry_price, qty: se presenti, viene controllato anche il limite di size
      (entry_price * qty <= MAX_SIZE_PER_POSITION_USDT).

    Ritorna:
    - (True, None) se si può aprire una nuova posizione
    - (False, reason) se NON si può aprire (con motivo testuale)
    """

    max_total = settings.MAX_OPEN_POSITIONS
    max_per_symbol = settings.MAX_OPEN_POSITIONS_PER_SYMBOL
    max_size_usdt = settings.MAX_SIZE_PER_POSITION_USDT

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

    # Controllo limite di size (notional) per posizione, se abbiamo i dati necessari
    if (
        max_size_usdt is not None
        and max_size_usdt > 0
        and entry_price is not None
        and qty is not None
    ):
        notional = float(entry_price) * float(qty)

        if notional > max_size_usdt:
            reason = (
                "max_size_per_position_exceeded "
                f"(notional={notional:.4f}, limit={max_size_usdt:.4f})"
            )
            logger.info(
                {
                    "event": "risk_block",
                    "scope": "size",
                    "symbol": symbol,
                    "entry_price": float(entry_price),
                    "qty": float(qty),
                    "notional": notional,
                    "limit": float(max_size_usdt),
                    "reason": reason,
                }
            )
            return False, reason

    # Tutto ok, si può aprire
    return True, None


def handle_bounce_signal(db: Session, signal) -> dict:
    """
    Gestisce un segnale Bounce:

    - se OMS_ENABLED = False → ack ma non apre nulla
    - applica il risk engine
    - costruisce i parametri posizione
    - apre la posizione via BrokerAdapterPaperSim
    - restituisce info su posizione aperta (per ora order_id=None)
    """

    symbol = signal.symbol
    side_in = signal.side
    price = float(signal.price)

    # OMS disabilitato → solo ack
    if not settings.OMS_ENABLED:
        logger.info(
            {
                "event": "bounce_signal_ignored_oms_disabled",
                "symbol": symbol,
                "side": side_in,
                "price": price,
            }
        )
        return {
            "received": True,
            "oms_enabled": False,
        }

    side = _normalize_side(side_in)
    qty = 1.0  # TODO: parametrizzare in futuro

    # Risk check
    risk_ok, risk_reason = check_risk_limits(
        db,
        symbol=symbol,
        entry_price=price,
        qty=qty,
    )
    if not risk_ok:
        logger.info(
            {
                "event": "bounce_signal_risk_block",
                "symbol": symbol,
                "side": side,
                "price": price,
                "reason": risk_reason,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": False,
            "risk_reason": risk_reason,
        }

    # TP/SL da settings (stessa logica di prima)
    tp_pct = float(getattr(settings, "TP_PCT", 0.0) or 0.0)
    sl_pct = float(getattr(settings, "SL_PCT", 0.0) or 0.0)

    if side == "long":
        tp_price = price * (1.0 + tp_pct / 100.0) if tp_pct > 0 else None
        sl_price = price * (1.0 - sl_pct / 100.0) if sl_pct > 0 else None
    elif side == "short":
        tp_price = price * (1.0 - tp_pct / 100.0) if tp_pct > 0 else None
        sl_price = price * (1.0 + sl_pct / 100.0) if sl_pct > 0 else None
    else:
        # side non valido → non apriamo
        reason = f"invalid_side: {side_in}"
        logger.error(
            {
                "event": "bounce_signal_invalid_side",
                "symbol": symbol,
                "side": side_in,
                "price": price,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": False,
            "risk_reason": reason,
        }

    # Parametri "profilo LAB dev" (come negli altri test)
    exchange = getattr(signal, "exchange", None) or "bitget"
    market_type = "paper_sim"
    account_label = "lab_dev"

    adapter = _get_broker_adapter()

    params = NewPositionParams(
        symbol=symbol,
        side=side,
        qty=qty,
        entry_price=price,
        exchange=exchange,
        market_type=market_type,
        account_label=account_label,
        tp_price=tp_price,
        sl_price=sl_price,
    )

    result = adapter.open_position(db, params)

    if not result.ok or result.position is None:
        logger.error(
            {
                "event": "bounce_signal_open_failed",
                "symbol": symbol,
                "side": side,
                "price": price,
                "reason": result.reason,
            }
        )
        return {
            "received": True,
            "oms_enabled": True,
            "risk_ok": True,
            "open_ok": False,
            "reason": result.reason or "broker_open_failed",
        }

    pos = result.position

    logger.info(
        {
            "event": "bounce_signal_position_opened",
            "symbol": symbol,
            "side": side,
            "price": price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "pos_id": pos.id,
            "exchange": pos.exchange,
            "market_type": pos.market_type,
            "account_label": pos.account_label,
        }
    )

    # Nota: order_id per ora None (non abbiamo ancora adattato il modello Order)
    return {
        "received": True,
        "oms_enabled": True,
        "risk_ok": True,
        "order_id": None,
        "position_id": pos.id,
        "tp_price": pos.tp_price,
        "sl_price": pos.sl_price,
        "exit_strategy": pos.exit_strategy,
    }


def auto_close_positions(db: Session) -> None:
    """
    Controlla tutte le posizioni aperte e le chiude in modalità paper
    quando il prezzo raggiunge TP (tp_price) o SL (sl_price).
    Le posizioni più giovani di 7 secondi NON vengono chiuse.

    Orchestrazione:
    - legge il prezzo tramite PriceSource (simulator/exchange)
    - valuta la posizione con StaticTpSlPolicy (ExitPolicy)
    - applica le ExitAction di tipo CLOSE_POSITION aggiornando la Position
    """

    open_positions = db.query(Position).filter(Position.status == "open").all()
    now = datetime.utcnow()  # momento attuale, usato per calcolare l'età

    # Sorgente prezzi e modalità (last/bid/ask/...)
    price_source = _get_price_source()
    price_mode = settings.price_mode

    # Exit policy attuale (TP/SL statici)
    policy = StaticTpSlPolicy()

    for pos in open_positions:
        # ⏱️ NON chiudere posizioni create da meno di 7 secondi
        if pos.created_at is not None:
            age_sec = (now - pos.created_at).total_seconds()
            if age_sec < 7:
                continue

        # Se non ha né TP né SL non c'è nulla da fare
        if pos.tp_price is None and pos.sl_price is None:
            continue

        # Recupero prezzo & valutazione policy con hardening errori
        try:
            quote = price_source.get_quote(pos.symbol)
            current_price = float(select_price(quote, price_mode))

            # Costruiamo il contesto per la policy
            ctx = ExitContext(price=current_price, quote=quote, now=now)
            actions = policy.on_new_price(pos, ctx)
        except Exception as e:
            logger.error(
                {
                    "event": "exit_engine_error",
                    "symbol": pos.symbol,
                    "error_type": type(e).__name__,
                    "error": str(e),
                }
            )
            # Non chiude il watcher: salta solo questa posizione
            continue

        # Filtriamo solo le azioni di chiusura completa
        close_actions: List = [
            a for a in actions if a.type == ExitActionType.CLOSE_POSITION
        ]

        # Nessuna azione di chiusura → continua
        if not close_actions:
            continue

        action = close_actions[0]
        reason = action.close_reason or "tp_sl"

        # ✅ NIENTE Order di chiusura per ora, aggiorniamo solo la Position
        pos.status = "closed"
        pos.closed_at = now
        pos.close_price = current_price
        pos.auto_close_reason = reason

        # Calcolo PnL (stessa logica di prima)
        entry = float(pos.entry_price)
        qty = float(pos.qty)

        side = _normalize_side(pos.side)
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
