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
    PriceSourceError,
    ExchangePriceSource,
)
from app.services.exit_engine import (
    StaticTpSlPolicy,
    ExitContext,
    ExitActionType,
)
from app.services.exchange_client import (
    get_default_exchange_client,
)
from app.services.broker_adapter import (
    NewPositionParams,
    get_broker_adapter,
    BrokerAdapter,
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


def _get_broker_adapter() -> BrokerAdapter:
    """
    Risolve il BrokerAdapter da usare a runtime.

    Usa la factory centrale get_broker_adapter(), che sceglie
    l'implementazione corretta in base a BROKER_MODE (paper/live/...).
    Oggi in pratica restituisce BrokerAdapterPaperSim.
    """
    return get_broker_adapter()


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

    # Valore “grezzo” letto da settings (quello che oggi ci sta dando 10.0 nel server)
    raw_max_size_usdt = settings.MAX_SIZE_PER_POSITION_USDT

    # Ambiente logico (dev / paper / live ...)
    env_name = getattr(settings, "ENVIRONMENT", "dev").lower()

    # 🔧 Decisione: in DEV non blocchiamo mai per notional.
    # Il limite di size resta valido solo per profili paper/live.
    if env_name == "dev":
        max_size_usdt = None
    else:
        max_size_usdt = raw_max_size_usdt

    # Log di diagnostica una volta per chiamata
    logger.info(
        {
            "event": "risk_limits_snapshot",
            "env": env_name,
            "max_total": max_total,
            "max_per_symbol": max_per_symbol,
            "max_size_usdt": max_size_usdt,
            "raw_max_size_usdt": raw_max_size_usdt,
        }
    )

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

    # Controllo limite di size (notional) per posizione, SOLO se il limite è attivo
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
    - apre la posizione via BrokerAdapter
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
    - applica le ExitAction di tipo CLOSE_POSITION via BrokerAdapter
    """

    open_positions = db.query(Position).filter(Position.status == "open").all()
    now = datetime.utcnow()  # momento attuale, usato per calcolare l'età

    # Sorgente prezzi e modalità (last/bid/ask/...)
    price_source = _get_price_source()
    price_mode = settings.price_mode
    price_source_label = str(settings.price_source)

    # Exit policy attuale (TP/SL statici)
    policy = StaticTpSlPolicy()

    # Broker adapter (paper / live, in futuro)
    adapter = _get_broker_adapter()

    for pos in open_positions:
        age_sec = None

        # ⏱️ NON chiudere posizioni create da meno di 7 secondi
        if pos.created_at is not None:
            age_sec = (now - pos.created_at).total_seconds()
            if age_sec < 7:
                continue

        # Se non ha né TP né SL non c'è nulla da fare
        if pos.tp_price is None and pos.sl_price is None:
            continue

        try:
            # Recupero prezzo & valutazione policy
            quote = price_source.get_quote(pos.symbol)
            current_price = float(select_price(quote, price_mode))

            ctx = ExitContext(price=current_price, quote=quote, now=now)
            actions = policy.on_new_price(pos, ctx)

        except PriceSourceError as e:
            # Problema specifico della sorgente prezzi (HTTP/timeout/dati invalidi)
            logger.error(
                {
                    "event": "price_source_error",
                    "symbol": pos.symbol,
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "price_source": price_source_label,
                    "price_mode": str(price_mode),
                }
            )
            # Non fermiamo il watcher, saltiamo solo questa posizione
            continue

        except Exception as e:
            # Qualsiasi altro errore a valle (ExitEngine, selezione prezzo, ecc.)
            logger.error(
                {
                    "event": "exit_engine_error",
                    "symbol": pos.symbol,
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "price_source": price_source_label,
                    "price_mode": str(price_mode),
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

        # Chiudiamo la posizione tramite BrokerAdapter (paper)
        broker_result = adapter.close_position(
            db,
            position=pos,
            close_price=current_price,
            reason=reason,
        )

        if not broker_result.ok or broker_result.position is None:
            logger.error(
                {
                    "event": "position_close_failed_via_broker",
                    "symbol": pos.symbol,
                    "pos_id": getattr(pos, "id", None),
                    "reason": broker_result.reason,
                    "price_source": price_source_label,
                    "price_mode": str(price_mode),
                }
            )
            # Non fermiamo il watcher: passiamo alla prossima posizione
            continue

        closed_pos = broker_result.position

        entry = float(closed_pos.entry_price)
        qty = float(closed_pos.qty)
        exit_price = float(closed_pos.close_price or current_price)
        pnl_val = float(closed_pos.pnl) if closed_pos.pnl is not None else None

        logger.info(
            {
                "event": "position_closed",
                "reason": closed_pos.auto_close_reason or reason,
                "symbol": closed_pos.symbol,
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl_val,
                "qty": qty,
                "pos_id": closed_pos.id,
                "age_sec": age_sec,
                "price_source": price_source_label,
                "price_mode": str(price_mode),
            }
        )
