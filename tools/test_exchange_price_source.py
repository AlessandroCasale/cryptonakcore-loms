# tools/test_exchange_price_source.py

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: aggiungi `services/cryptonakcore` al sys.path
# così il package `app` è importabile quando lanci da root del repo.
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent          # .../cryptonakcore-loms/tools
REPO_ROOT = ROOT_DIR.parent                         # .../cryptonakcore-loms
APP_DIR = REPO_ROOT / "services" / "cryptonakcore"  # .../services/cryptonakcore

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Ora possiamo importare `app.*` normalmente
from app.core.config import settings
from app.services.pricing import (
    PriceMode,
    PriceSourceType,
    PriceQuote,
    ExchangePriceSource,
    select_price,
)


class DummyExchangeClient:
    """
    Client finto che emula la risposta di un exchange HTTP.

    Serve solo per testare ExchangePriceSource senza dipendere
    da Bitget/Bybit reali.
    """

    def get_ticker(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "bid": 99.5,
            "ask": 100.5,
            "last": 100.0,
            "mark": 100.2,
        }


def print_header() -> None:
    print("==============================================")
    print(" ExchangePriceSource test (Dummy client)")
    print("==============================================")
    print(f"ENVIRONMENT   : {settings.environment}")
    print(f"BROKER_MODE   : {settings.broker_mode}")
    print(f"PRICE_SOURCE  : {settings.price_source}")
    print(f"PRICE_MODE    : {settings.price_mode}")
    print()


def print_quote(symbol: str, quote: PriceQuote) -> None:
    print(f"Quote for {symbol}:")
    print(f"  symbol   : {quote.symbol}")
    print(f"  ts       : {quote.ts}")
    print(f"  source   : {quote.source}")
    print(f"  mode     : {quote.mode}")
    print(f"  bid      : {quote.bid}")
    print(f"  ask      : {quote.ask}")
    print(f"  last     : {quote.last}")
    print(f"  mark     : {quote.mark}")
    print(f"  mid      : {quote.mid}")
    print()


def main() -> None:
    symbol = "BTCUSDT"

    print_header()

    client = DummyExchangeClient()
    src = ExchangePriceSource(client)

    quote: PriceQuote = src.get_quote(symbol)
    print_quote(symbol, quote)

    price = select_price(quote, settings.price_mode)
    print(f"select_price(mode={settings.price_mode!r}) -> {price}")
    print("==============================================")
    print(" Fine test ExchangePriceSource")
    print("==============================================")


if __name__ == "__main__":
    main()
