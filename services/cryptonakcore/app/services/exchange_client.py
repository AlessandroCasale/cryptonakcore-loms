# services/cryptonakcore/app/services/exchange_client.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.services.pricing import (
    PriceSource,
    PriceSourceType,
    PriceMode,
    PriceQuote,
)


class ExchangeHttpClient(Protocol):
    """
    Interfaccia generica per un client HTTP verso un exchange.

    Le implementazioni reali (BitgetClient, BybitClient, ecc.) dovranno
    implementare almeno get_ticker(symbol) -> dict con campi:
      - bid
      - ask
      - last
      - mark (opzionale)
      - ts   (timestamp ISO8601 opzionale)
    """

    def get_ticker(self, symbol: str) -> dict:
        ...


class DummyExchangeHttpClient:
    """
    Client HTTP finto usato solo per test / dev.

    Ritorna valori hard-coded in modo da poter testare l'integrazione
    dell'ExchangePriceSource senza fare vere chiamate di rete.
    """

    def get_ticker(self, symbol: str) -> dict:
        now = datetime.now(timezone.utc)

        # Valori dummy: gli stessi del tool di test
        return {
            "symbol": "BTCUSDT",
            "ts": now.isoformat(),
            "bid": 99.5,
            "ask": 100.5,
            "last": 100.0,
            "mark": 100.2,
        }


class ExchangePriceSource(PriceSource):
    """
    Implementazione di PriceSource che usa un ExchangeHttpClient.

    Per ora viene usata solo con DummyExchangeHttpClient (dev / test),
    ma in futuro verrà istanziata con BitgetClient / BybitClient reali.
    """

    source_type: PriceSourceType = PriceSourceType.EXCHANGE

    def __init__(
        self,
        client: ExchangeHttpClient,
        default_mode: PriceMode = PriceMode.LAST,
    ) -> None:
        self._client = client
        self._default_mode = default_mode

    def get_quote(self, symbol: str) -> PriceQuote:
        data = self._client.get_ticker(symbol)

        ts_str = data.get("ts")
        try:
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(timezone.utc)
        except Exception:
            ts = datetime.now(timezone.utc)

        return PriceQuote(
            symbol=symbol,
            ts=ts,
            bid=data.get("bid"),
            ask=data.get("ask"),
            last=data.get("last"),
            mark=data.get("mark"),
            source=self.source_type,
            mode=self._default_mode,
        )


def get_default_exchange_client() -> ExchangeHttpClient:
    """
    Restituisce il client HTTP di default per PriceSourceType.EXCHANGE.

    Per ora, in ambiente dev, usiamo sempre DummyExchangeHttpClient.
    In futuro qui potremo scegliere BitgetClient / BybitClient in base
    alla config (es. DEFAULT_EXCHANGE).
    """
    return DummyExchangeHttpClient()
