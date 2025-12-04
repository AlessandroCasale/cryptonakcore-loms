# tools/test_exchange_price_source.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# --------------------------------------------------
# Setup sys.path per importare "app.*"
# --------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # C:\Projects\cryptonakcore-loms
SERVICE_ROOT = ROOT / "services" / "cryptonakcore"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import settings
from app.services.exchange_client import (
    ExchangePriceSource,
    DummyExchangeHttpClient,
    BybitHttpClient,
    BitgetHttpClient,
)
from app.services.pricing import PriceMode, PriceQuote


def _detect_client_name(src: ExchangePriceSource) -> str:
    client = getattr(src, "_client", None)
    if isinstance(client, BybitHttpClient):
        return "Bybit client"
    if isinstance(client, BitgetHttpClient):
        return "Bitget client"
    if isinstance(client, DummyExchangeHttpClient):
        return "Dummy client"
    return client.__class__.__name__ if client is not None else "Unknown client"


def _select_price_for_report(quote: PriceQuote) -> Optional[float]:
    """
    Mini helper solo per questo tool, per mostrare il prezzo scelto
    in base a settings.price_mode. Non tocca la logica reale dell'ExitEngine.
    """
    mode = settings.price_mode

    v_last = quote.last
    v_bid = quote.bid
    v_ask = quote.ask
    v_mark = quote.mark

    mv = getattr(mode, "value", str(mode))

    if mv == "last":
        return v_last
    if mv == "bid":
        return v_bid
    if mv == "ask":
        return v_ask
    if mv == "mark":
        return v_mark
    if mv == "mid":
        if v_bid is not None and v_ask is not None:
            return (v_bid + v_ask) / 2

    # Fallback ultra-semplice
    return v_last or v_mark or v_bid or v_ask


def main() -> None:
    symbol = "BTCUSDT"

    # Usa la factory interna: sceglie Dummy / Bybit / Bitget in base alle Settings
    src = ExchangePriceSource()
    client_name = _detect_client_name(src)

    print("==============================================")
    print(f" ExchangePriceSource test ({client_name})")
    print("==============================================")
    print(f"ENVIRONMENT        : {settings.environment}")
    print(f"BROKER_MODE        : {settings.broker_mode}")
    print(f"PRICE_SOURCE       : {settings.price_source}")
    print(f"PRICE_MODE         : {settings.price_mode}")
    print(f"PRICE_EXCHANGE     : {settings.price_exchange}")
    print(f"PRICE_HTTP_TIMEOUT : {settings.price_http_timeout}")
    print()

    quote = src.get_quote(symbol)

    mid = (
        (quote.bid + quote.ask) / 2
        if quote.bid is not None and quote.ask is not None
        else None
    )

    print(f"Quote for {symbol}:")
    print(f"  symbol   : {quote.symbol}")
    print(f"  ts       : {quote.ts}")
    print(f"  source   : {quote.source}")
    print(f"  mode     : {quote.mode}")
    print(f"  bid      : {quote.bid}")
    print(f"  ask      : {quote.ask}")
    print(f"  last     : {quote.last}")
    print(f"  mark     : {quote.mark}")
    print(f"  mid      : {mid}")
    print()

    selected = _select_price_for_report(quote)
    print(f"select_price(mode={settings.price_mode}) -> {selected}")
    print("==============================================")
    print(" Fine test ExchangePriceSource")
    print("==============================================")


if __name__ == "__main__":
    main()
