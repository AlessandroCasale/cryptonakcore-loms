# services/cryptonakcore/app/services/exchange_client.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
import logging

import requests

from app.services.pricing import (
    PriceSource,
    PriceSourceType,
    PriceMode,
    PriceQuote,
)
from app.core.config import settings

logger = logging.getLogger("exchange_client")


class ExchangeHttpClient(Protocol):
    """
    Interfaccia generica per un client HTTP verso un exchange.

    Le implementazioni reali (BitgetClient, BybitClient, ecc.) devono
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

        # Valori dummy fissi
        return {
            "symbol": symbol,
            "ts": now.isoformat(),
            "bid": 99.5,
            "ask": 100.5,
            "last": 100.0,
            "mark": 100.2,
        }


class BybitHttpClient:
    """
    Client HTTP minimale verso Bybit (solo endpoint public /v5/market/tickers).

    - usa solo endpoint public (nessuna API key)
    - category di default: "linear" (per perp USDT)
    """

    def __init__(
        self,
        base_url: str | None = None,
        category: str = "linear",
        timeout_sec: float = 2.0,
    ) -> None:
        # Se non specificato, usiamo l'endpoint pubblico principale Bybit.
        self.base_url = base_url or "https://api.bybit.com"
        self.category = category
        self.timeout_sec = timeout_sec

    def get_ticker(self, symbol: str) -> dict:
        """
        Chiama GET /v5/market/tickers?category=linear&symbol=BTCUSDT

        Doc:
        - https://bybit-exchange.github.io/docs/v5/market/tickers
        """
        url = f"{self.base_url}/v5/market/tickers"
        params = {
            "category": self.category,
            "symbol": symbol,
        }

        resp = requests.get(url, params=params, timeout=self.timeout_sec)
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {payload}")

        result = payload.get("result") or {}
        items = result.get("list") or []
        if not items:
            raise RuntimeError(f"Bybit tickers empty for symbol={symbol}")

        item = items[0]

        def _maybe_float(key: str) -> float | None:
            v = item.get(key)
            if v is None:
                return None
            try:
                return float(v)
            except Exception:
                return None

        # Bybit non espone un ts diretto qui → usiamo "ora"
        now = datetime.now(timezone.utc)

        return {
            "symbol": item.get("symbol") or symbol,
            "ts": now.isoformat(),
            "bid": _maybe_float("bid1Price"),
            "ask": _maybe_float("ask1Price"),
            "last": _maybe_float("lastPrice"),
            "mark": _maybe_float("markPrice"),
        }


class BitgetHttpClient:
    """
    Client HTTP minimale verso Bitget.

    Per semplicità, in questa prima versione usiamo il Ticker SPOT V2:

      GET /api/v2/spot/market/tickers?symbol=BTCUSDT

    Doc:
    - GET /api/v2/spot/market/tickers (symbol opzionale, se vuoto ritorna tutti)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_sec: float = 2.0,
    ) -> None:
        # Endpoint pubblico principale Bitget.
        self.base_url = base_url or "https://api.bitget.com"
        self.timeout_sec = timeout_sec

    def get_ticker(self, symbol: str) -> dict:
        url = f"{self.base_url}/api/v2/spot/market/tickers"
        params = {
            "symbol": symbol,
        }

        resp = requests.get(url, params=params, timeout=self.timeout_sec)
        resp.raise_for_status()
        payload = resp.json()

        # V2: code == "00000" indica successo
        if payload.get("code") != "00000":
            raise RuntimeError(f"Bitget API error: {payload}")

        data = payload.get("data") or []
        if not data:
            raise RuntimeError(f"Bitget tickers empty for symbol={symbol}")

        item = data[0]

        def _maybe_float(key: str) -> float | None:
            v = item.get(key)
            if v is None:
                return None
            try:
                return float(v)
            except Exception:
                return None

        # ts è millisecondi Unix in stringa → convertiamo a datetime ISO UTC
        ts_raw = item.get("ts")
        ts_iso: str
        if ts_raw is not None:
            try:
                ts_ms = int(ts_raw)
                dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                ts_iso = dt.isoformat()
            except Exception:
                ts_iso = datetime.now(timezone.utc).isoformat()
        else:
            ts_iso = datetime.now(timezone.utc).isoformat()

        return {
            "symbol": item.get("symbol") or symbol,
            "ts": ts_iso,
            "bid": _maybe_float("bidPr"),
            "ask": _maybe_float("askPr"),
            "last": _maybe_float("lastPr"),
            # Spot ticker non espone mark price → lasciamo None
            "mark": None,
        }


class PriceExchange(str, Enum):
    """
    Selettore dell'exchange per PriceSource=EXCHANGE.

    Per ora:
    - dummy (default)
    - bybit
    - bitget
    """

    DUMMY = "dummy"
    BYBIT = "bybit"
    BITGET = "bitget"


def get_default_exchange_client() -> ExchangeHttpClient:
    """
    Restituisce il client HTTP di default per PriceSourceType.EXCHANGE.

    - PRICE_EXCHANGE=dummy (default) -> DummyExchangeHttpClient
    - PRICE_EXCHANGE=bybit           -> BybitHttpClient (REST reale)
    - PRICE_EXCHANGE=bitget          -> BitgetHttpClient (REST reale spot)
    """

    # Usiamo l'alias lower-case definito in config.py
    exchange_name = settings.price_exchange.lower()

    if exchange_name == PriceExchange.BYBIT.value:
        logger.info(
            {
                "event": "exchange_client_selected",
                "exchange": "bybit",
                "base_url": "https://api.bybit.com",
                "timeout_sec": settings.price_http_timeout,
            }
        )
        return BybitHttpClient(timeout_sec=settings.price_http_timeout)

    if exchange_name == PriceExchange.BITGET.value:
        logger.info(
            {
                "event": "exchange_client_selected",
                "exchange": "bitget",
                "base_url": "https://api.bitget.com",
                "timeout_sec": settings.price_http_timeout,
            }
        )
        return BitgetHttpClient(timeout_sec=settings.price_http_timeout)

    # Fallback: dummy
    logger.info(
        {
            "event": "exchange_client_selected",
            "exchange": "dummy",
        }
    )
    return DummyExchangeHttpClient()


class ExchangePriceSource(PriceSource):
    """
    Implementazione di PriceSource che usa un ExchangeHttpClient.

    Per ora viene usata con DummyExchangeHttpClient, BybitHttpClient, BitgetHttpClient.
    """

    source_type: PriceSourceType = PriceSourceType.EXCHANGE

    def __init__(
        self,
        client: ExchangeHttpClient | None = None,
        default_mode: PriceMode | None = None,
    ) -> None:
        # Se non viene passato un client esplicito, usiamo la factory basata sulle Settings
        self._client = client or get_default_exchange_client()
        # Se non viene passato un mode esplicito, usiamo quello dalle Settings (PRICE_MODE)
        self._default_mode = default_mode or settings.price_mode

    def get_quote(self, symbol: str) -> PriceQuote:
        data = self._client.get_ticker(symbol)

        ts_str = data.get("ts")
        try:
            ts = (
                datetime.fromisoformat(ts_str)
                if ts_str
                else datetime.now(timezone.utc)
            )
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