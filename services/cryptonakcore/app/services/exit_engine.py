from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Protocol, List

from app.services.pricing import PriceQuote


class ExitActionType(str, Enum):
    """
    Tipi di azioni che il motore di exit può suggerire.

    - adjust_stop_loss: sposta lo stop loss
    - adjust_take_profit: sposta il take profit
    - close_position: chiudi completamente la posizione
    - partial_close: chiudi solo una parte della posizione
    """

    ADJUST_STOP_LOSS = "adjust_stop_loss"
    ADJUST_TAKE_PROFIT = "adjust_take_profit"
    CLOSE_POSITION = "close_position"
    PARTIAL_CLOSE = "partial_close"


@dataclass
class ExitAction:
    """
    Azione di exit proposta dalla ExitPolicy.

    Campi usati in base al tipo:
    - CLOSE_POSITION:      type=CLOSE_POSITION, close_reason valorizzato
    - ADJUST_STOP_LOSS:    type=ADJUST_STOP_LOSS, new_sl valorizzato
    - ADJUST_TAKE_PROFIT:  type=ADJUST_TAKE_PROFIT, new_tp valorizzato
    - PARTIAL_CLOSE:       type=PARTIAL_CLOSE, close_qty valorizzato
    """

    type: ExitActionType

    # per adjust_stop_loss / adjust_take_profit
    new_sl: Optional[float] = None
    new_tp: Optional[float] = None

    # per close_position / partial_close
    close_reason: Optional[str] = None
    close_qty: Optional[float] = None


@dataclass
class ExitContext:
    """
    Contesto di valutazione della policy di exit.

    - price:  prezzo numerico usato per TP/SL/PnL
    - quote:  eventuale PriceQuote completo (bid/ask/mark/last)
    - now:    timestamp corrente (per timeout, aging, ecc.)
    """

    price: float
    quote: Optional[PriceQuote] = None
    now: Optional[datetime] = None


class ExitPolicy(Protocol):
    """
    Interfaccia base per tutte le ExitPolicy.

    Implementazioni tipiche:
    - StaticTpSlPolicy: replica TP/SL statici
    - TrailingV1Policy: applica trailing dopo una certa move
    """

    name: str

    def on_new_price(self, position: Any, context: ExitContext) -> List[ExitAction]:
        """
        Valuta la posizione alla luce di un nuovo prezzo e ritorna
        una lista di ExitAction da applicare (o lista vuota se niente da fare).
        """
        ...


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


class StaticTpSlPolicy:
    """
    Replica la logica TP/SL fissi attuale, ma in forma di ExitPolicy.

    NOTA IMPORTANTE:
    - Questa policy NON tocca il DB e NON calcola PnL.
      Si limita a dire "chiudi la posizione per TP/SL" tramite ExitAction.
    - L'applicazione concreta dell'azione (aggiornare Position, PnL, ecc.)
      sarà responsabilità dell'orchestratore (es. auto_close_positions).
    """

    name: str = "tp_sl_static"

    def on_new_price(self, position: Any, context: ExitContext) -> List[ExitAction]:
        # Se non abbiamo un prezzo valido, nessuna decisione
        if context.price is None:
            return []

        current_price = float(context.price)

        # Se non ha né TP né SL non c'è nulla da fare
        tp = getattr(position, "tp_price", None)
        sl = getattr(position, "sl_price", None)

        if tp is None and sl is None:
            return []

        # Normalizza side
        side = _normalize_side(getattr(position, "side", ""))

        hit_tp = False
        hit_sl = False

        # Converte TP/SL in float se presenti
        tp_f: Optional[float] = float(tp) if tp is not None else None
        sl_f: Optional[float] = float(sl) if sl is not None else None

        if tp_f is not None:
            if side == "long":
                hit_tp = current_price >= tp_f
            elif side == "short":
                hit_tp = current_price <= tp_f

        if sl_f is not None:
            if side == "long":
                hit_sl = current_price <= sl_f
            elif side == "short":
                hit_sl = current_price >= sl_f

        # Nessun trigger → nessuna azione
        if not (hit_tp or hit_sl):
            return []

        reason = "tp" if hit_tp else "sl"

        return [
            ExitAction(
                type=ExitActionType.CLOSE_POSITION,
                close_reason=reason,
            )
        ]
