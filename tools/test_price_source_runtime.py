from __future__ import annotations

import sys
from pathlib import Path

# -------------------------------------------------------------------
# Setup path per importare app.* (stesso trucco degli altri tool)
# -------------------------------------------------------------------
# Vai dalla cartella tools/ alla root del progetto, poi in services/cryptonakcore
ROOT = Path(__file__).resolve().parent.parent / "services" / "cryptonakcore"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.core.config import settings
from app.services.oms import _get_price_source
from app.services.pricing import select_price


def main() -> None:
    print("==============================================")
    print(" Runtime PriceSource test (LOMS)")
    print("==============================================")
    print(f"ENVIRONMENT   : {settings.environment}")
    print(f"BROKER_MODE   : {settings.broker_mode}")
    print(f"PRICE_SOURCE  : {settings.price_source}")
    print(f"PRICE_MODE    : {settings.price_mode}")
    print()

    # Usa lo stesso resolver dell'OMS
    price_source = _get_price_source()

    symbol = "BTCUSDT"
    print(f"Richiedo quote per symbol: {symbol}")
    quote = price_source.get_quote(symbol)

    print("\nRaw PriceQuote:")
    print(f"  symbol   : {quote.symbol}")
    print(f"  ts       : {quote.ts}")
    print(f"  source   : {quote.source}")
    print(f"  mode     : {quote.mode}")
    print(f"  bid      : {quote.bid}")
    print(f"  ask      : {quote.ask}")
    print(f"  last     : {quote.last}")
    print(f"  mark     : {quote.mark}")
    mid = getattr(quote, "mid", None)
    print(f"  mid      : {mid}")
    print()

    # Proviamo a usare select_price con il PRICE_MODE corrente
    try:
        selected = select_price(quote, settings.price_mode)
        print(f"select_price(mode={settings.price_mode!r}) -> {selected}")
    except Exception as e:
        print(f"ERROR in select_price: {type(e).__name__}: {e}")

    print("==============================================")
    print(" Fine test PriceSource runtime")
    print("==============================================")


if __name__ == "__main__":
    main()
