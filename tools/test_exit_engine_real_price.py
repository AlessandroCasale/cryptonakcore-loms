from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# --------------------------------------------------
# Setup sys.path per usare i moduli di services/cryptonakcore (app.*)
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # .../cryptonakcore-loms
SERVICE_ROOT = ROOT_DIR / "services" / "cryptonakcore"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import settings  # type: ignore[import]
from app.services.exchange_client import ExchangePriceSource  # type: ignore[import]
from app.services.pricing import PriceQuote  # type: ignore[import]
from app.services.exit_engine import (  # type: ignore[import]
    StaticTpSlPolicy,
    ExitContext,
    ExitAction,
    ExitActionType,
)


@dataclass
class FakePosition:
    """
    Posizione fittizia minima per testare la ExitPolicy.

    Campi usati da StaticTpSlPolicy:
    - symbol
    - side
    - tp_price
    - sl_price
    """

    symbol: str
    side: str
    tp_price: Optional[float]
    sl_price: Optional[float]


def _pick_price_from_quote(q: PriceQuote) -> Optional[float]:
    """
    Sceglie un prezzo numerico da usare come "current_price"
    partendo dal quote reale.
    """
    if q.last is not None:
        return q.last
    if q.mark is not None:
        return q.mark
    if q.bid is not None and q.ask is not None:
        return (q.bid + q.ask) / 2
    if q.bid is not None:
        return q.bid
    if q.ask is not None:
        return q.ask
    return None


def _build_tp_sl(entry: float, side: str) -> tuple[float, float]:
    """
    Costruisce TP/SL a ±0.5% rispetto all'entry,
    giusto per avere soglie sensate.
    """
    delta = entry * 0.005  # 0.5%

    if side == "long":
        tp = entry + delta
        sl = entry - delta
    else:  # short
        tp = entry - delta
        sl = entry + delta

    return tp, sl


def _print_actions(label: str, price: float, actions: list[ExitAction]) -> None:
    if not actions:
        print(f"[{label}] price={price:.4f} -> no action")
        return

    for a in actions:
        if a.type == ExitActionType.CLOSE_POSITION:
            print(
                f"[{label}] price={price:.4f} -> "
                f"CLOSE_POSITION (reason={a.close_reason})"
            )
        elif a.type == ExitActionType.ADJUST_STOP_LOSS:
            print(
                f"[{label}] price={price:.4f} -> "
                f"ADJUST_STOP_LOSS (new_sl={a.new_sl})"
            )
        elif a.type == ExitActionType.ADJUST_TAKE_PROFIT:
            print(
                f"[{label}] price={price:.4f} -> "
                f"ADJUST_TAKE_PROFIT (new_tp={a.new_tp})"
            )
        elif a.type == ExitActionType.PARTIAL_CLOSE:
            print(
                f"[{label}] price={price:.4f} -> "
                f"PARTIAL_CLOSE (qty={a.close_qty}, reason={a.close_reason})"
            )
        else:
            print(f"[{label}] price={price:.4f} -> UNKNOWN ACTION {a}")


def main() -> None:
    symbol = "BTCUSDT"
    side = "long"  # per ora testiamo solo long
    qty = 1.0

    print("==============================================")
    print(" ExitEngine static TP/SL – Real Price test")
    print("==============================================")
    print(f"ENVIRONMENT        : {settings.environment}")
    print(f"BROKER_MODE        : {settings.broker_mode}")
    print(f"PRICE_SOURCE       : {settings.price_source}")
    print(f"PRICE_MODE         : {settings.price_mode}")
    print(f"PRICE_EXCHANGE     : {settings.price_exchange}")
    print(f"PRICE_HTTP_TIMEOUT : {settings.price_http_timeout}")
    print()

    # 1) Quote reale via ExchangePriceSource (Bybit/Bitget/Dummy in base alle Settings)
    price_src = ExchangePriceSource()
    quote = price_src.get_quote(symbol)

    print(f"Real price quote for {symbol}:")
    print(f"  ts    : {quote.ts}")
    print(f"  bid   : {quote.bid}")
    print(f"  ask   : {quote.ask}")
    print(f"  last  : {quote.last}")
    print(f"  mark  : {quote.mark}")
    mid = (
        (quote.bid + quote.ask) / 2
        if quote.bid is not None and quote.ask is not None
        else None
    )
    print(f"  mid   : {mid}")
    print()

    current_price = _pick_price_from_quote(quote)
    if current_price is None:
        print("❌ Nessun prezzo utilizzabile nel quote, abortisco il test.")
        return

    tp_price, sl_price = _build_tp_sl(current_price, side)

    # Posizione finta compatibile con StaticTpSlPolicy (uguale a FakePosition del test statico)
    position = FakePosition(
        symbol=symbol,
        side=side,
        tp_price=tp_price,
        sl_price=sl_price,
    )

    print("Test position context (finto):")
    print(f"  symbol      : {position.symbol}")
    print(f"  side        : {position.side}")
    print(f"  qty         : {qty}")
    print(f"  tp_price    : {position.tp_price}")
    print(f"  sl_price    : {position.sl_price}")
    print()

    policy = StaticTpSlPolicy()

    # 2) Tre scenari:
    #    - REAL: usa il prezzo reale dal quote
    #    - HIT_TP: prezzo fittizio esattamente sul TP
    #    - HIT_SL: prezzo fittizio esattamente sul SL
    scenarios: list[tuple[str, float]] = [
        ("REAL", current_price),
        ("HIT_TP", tp_price),
        ("HIT_SL", sl_price),
    ]

    for label, price in scenarios:
        ctx = ExitContext(
            price=price,
            quote=quote if label == "REAL" else None,
        )
        actions = policy.on_new_price(position, ctx)
        _print_actions(label, price, actions)

    print("==============================================")
    print(" Fine test ExitEngine (Real Price)")
    print("==============================================")


if __name__ == "__main__":
    main()
