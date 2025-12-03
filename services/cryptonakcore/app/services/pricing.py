from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Protocol, Any


class PriceSourceError(Exception):
    """
    Errore di alto livello per le sorgenti prezzi.

    Viene usato da tutte le implementazioni di PriceSource per segnalare:
    - timeout / errori HTTP verso l'exchange
    - dati mancanti o non validi
    - qualunque situazione in cui NON è sicuro usare il prezzo.
    """

    def __init__(self, message: str, symbol: Optional[str] = None, source: Optional[str] = None) -> None:
        super().__init__(message)
        self.symbol = symbol
        self.source = source


class PriceSourceType(str, Enum):
    """
    Da dove arrivano i prezzi.

    - simulator: prezzo generato dal MarketSimulator (paper puro)
    - exchange: prezzo reale da exchange (Bybit/Bitget, ecc.)
    - replay:   prezzo da feed storico (backtest / replay)
    """

    SIMULATOR = "simulator"
    EXCHANGE = "exchange"
    REPLAY = "replay"


class PriceMode(str, Enum):
    """
    Quale campo del quote usare per TP/SL, PnL, ecc.

    - last: ultimo trade price
    - bid:  best bid
    - ask:  best ask
    - mid:  (bid+ask)/2 se disponibile
    - mark: mark price dell'exchange, se esiste
    """

    LAST = "last"
    BID = "bid"
    ASK = "ask"
    MID = "mid"
    MARK = "mark"


@dataclass
class PriceQuote:
    """
    Quote standardizzato per un simbolo.

    NOTA: per ora è solo modello dati; la logica di come
    ottenere questi campi rimane nel PriceSource concreto.
    """

    symbol: str
    ts: datetime  # timezone-aware (UTC)

    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mark: Optional[float] = None

    # Metadati utili per logging / debug
    source: PriceSourceType = PriceSourceType.SIMULATOR
    mode: PriceMode = PriceMode.LAST

    @property
    def mid(self) -> Optional[float]:
        """Restituisce (bid+ask)/2 se entrambi presenti, altrimenti None."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2.0
        return None


class PriceSource(Protocol):
    """
    Interfaccia logica che ogni sorgente prezzi deve implementare.

    Implementazioni previste:
    - SimulatedPriceSource: incapsula l'attuale MarketSimulator
    - ExchangePriceSource: usa le API reali dell'exchange
    - ReplayPriceSource:  riproduce prezzi da dati storici
    """

    source_type: PriceSourceType

    def get_quote(self, symbol: str) -> PriceQuote:
        """
        Restituisce un PriceQuote per il simbolo richiesto.

        In caso di problemi deve sollevare PriceSourceError:
        - errori rete / HTTP
        - dati mancanti o non numerici
        - qualsiasi situazione in cui non è sicuro usare il prezzo
        """
        ...


def select_price(quote: PriceQuote, mode: PriceMode) -> float:
    """
    Utility per estrarre un float dal PriceQuote in base al PriceMode.

    Usata da auto_close_positions, chiusure manuali e in generale
    ovunque serva un singolo prezzo da passare all'ExitEngine / PnL.
    """
    if mode is PriceMode.LAST:
        if quote.last is None:
            raise ValueError("PriceQuote.last is None")
        return quote.last

    if mode is PriceMode.BID:
        if quote.bid is None:
            raise ValueError("PriceQuote.bid is None")
        return quote.bid

    if mode is PriceMode.ASK:
        if quote.ask is None:
            raise ValueError("PriceQuote.ask is None")
        return quote.ask

    if mode is PriceMode.MARK:
        if quote.mark is None:
            raise ValueError("PriceQuote.mark is None")
        return quote.mark

    if mode is PriceMode.MID:
        mid = quote.mid
        if mid is None:
            raise ValueError("PriceQuote.mid is None (bid/ask mancanti)")
        return mid

    # Difesa extra: se arriva un mode sconosciuto (es. da env sbagliato)
    raise ValueError(f"Unsupported PriceMode: {mode!r}")


class SimulatedPriceSource:
    """
    Implementazione di PriceSource che incapsula un semplice
    oggetto "simulatore" che espone un metodo get_price(symbol) -> float.

    Attualmente è la sorgente prezzi utilizzata in:
    - auto_close_positions (OMS paper)
    - chiusura manuale delle posizioni (/positions/{id}/close)
    """

    source_type: PriceSourceType = PriceSourceType.SIMULATOR

    def __init__(self, simulator: Any) -> None:
        self._simulator = simulator

    def get_quote(self, symbol: str) -> PriceQuote:
        try:
            price = self._simulator.get_price(symbol)
        except Exception as exc:
            # qualsiasi problema nel simulatore → errore di sorgente
            raise PriceSourceError(
                f"SimulatedPriceSource failed for symbol={symbol}: {exc!r}",
                symbol=symbol,
                source=self.source_type.value,
            ) from exc

        if price is None:
            raise PriceSourceError(
                f"SimulatedPriceSource returned None for symbol={symbol}",
                symbol=symbol,
                source=self.source_type.value,
            )

        try:
            price_float = float(price)
        except (TypeError, ValueError) as exc:
            raise PriceSourceError(
                f"SimulatedPriceSource returned non-numeric price for symbol={symbol}: {price!r}",
                symbol=symbol,
                source=self.source_type.value,
            ) from exc

        return PriceQuote(
            symbol=symbol,
            ts=datetime.now(timezone.utc),
            last=price_float,
            source=self.source_type,
            mode=PriceMode.LAST,
        )


class ExchangePriceSource:
    """
    Scheletro di PriceSource basato su prezzo reale da exchange.

    L'idea è che `client` sia un adapter verso l'exchange (Bybit/Bitget, ecc.)
    che espone un metodo tipo:

        get_ticker(symbol: str) -> dict

    dove il dict contiene almeno uno dei seguenti campi:
    - "last" / "last_price" / "close"
    - "bid", "ask"
    - "mark" / "mark_price"

    Per ora questa classe NON è usata nel runtime: verrà istanziata
    solo quando collegheremo il Real Price Engine con un adapter reale.
    """

    source_type: PriceSourceType = PriceSourceType.EXCHANGE

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_quote(self, symbol: str) -> PriceQuote:
        exchange_name = getattr(self._client, "exchange_name", "exchange")

        try:
            data = self._client.get_ticker(symbol)
        except Exception as exc:
            # timeout / errori HTTP / ecc.
            raise PriceSourceError(
                f"ExchangePriceSource failed to fetch ticker for symbol={symbol}: {exc!r}",
                symbol=symbol,
                source=exchange_name,
            ) from exc

        if not isinstance(data, dict):
            raise PriceSourceError(
                f"ExchangePriceSource expected dict from get_ticker for symbol={symbol}, got {type(data)!r}",
                symbol=symbol,
                source=exchange_name,
            )

        # Estraggo i campi in modo difensivo, adattandomi a vari naming possibili.
        raw_bid = data.get("bid")
        raw_ask = data.get("ask")
        raw_last = (
            data.get("last")
            or data.get("last_price")
            or data.get("close")
        )
        raw_mark = (
            data.get("mark")
            or data.get("mark_price")
        )

        def _to_float_or_none(key: str, value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise PriceSourceError(
                    f"ExchangePriceSource: invalid numeric value for {key} in ticker for {symbol}: {value!r}",
                    symbol=symbol,
                    source=exchange_name,
                ) from exc

        bid = _to_float_or_none("bid", raw_bid)
        ask = _to_float_or_none("ask", raw_ask)
        last = _to_float_or_none("last", raw_last)
        mark = _to_float_or_none("mark", raw_mark)

        if last is None and bid is None and ask is None and mark is None:
            raise PriceSourceError(
                f"ExchangePriceSource: nessun prezzo valido nel ticker per {symbol}",
                symbol=symbol,
                source=exchange_name,
            )

        return PriceQuote(
            symbol=symbol,
            ts=datetime.now(timezone.utc),
            bid=bid,
            ask=ask,
            last=last,
            mark=mark,
            source=self.source_type,
            mode=PriceMode.LAST,
        )


class ReplayPriceSource:
    """
    Scheletro di PriceSource basato su dati storici (replay / backtest).

    L'idea è che `feed` sia un oggetto che fornisce, per ogni simbolo
    e "istante" di simulazione, un set di prezzi da cui costruire
    un PriceQuote (es. CSV, database, snapshot JSON, ecc.).

    Per ora è solo un placeholder e NON viene usato nel runtime.
    """

    source_type: PriceSourceType = PriceSourceType.REPLAY

    def __init__(self, feed: Any) -> None:
        self._feed = feed

    def get_quote(self, symbol: str) -> PriceQuote:
        """
        Da implementare quando attaccheremo un vero feed storico.

        Potrà ad esempio:
        - usare un indice temporale globale (tick),
        - o cercare per ts più vicino,
        - o riprodurre un log di prezzi già salvato.
        """
        raise NotImplementedError("ReplayPriceSource non è ancora implementata")