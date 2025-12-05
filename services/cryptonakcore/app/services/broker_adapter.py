from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional

from sqlalchemy.orm import Session

from app.db.models import Position
import logging

from app.core.config import settings




logger = logging.getLogger("broker_adapter")


@dataclass
class NewPositionParams:
    """
    Parametri “logici” per aprire una nuova posizione tramite BrokerAdapter.

    Questa struct è indipendente dall’API HTTP vera (Bitget/Bybit) e serve
    solo come contratto interno tra:

    - /signals/bounce  (o altri endpoint)
    - BrokerAdapter    (paper / exchange / live)
    """

    symbol: str
    side: str
    qty: float
    entry_price: float

    exchange: Optional[str] = None
    market_type: Optional[str] = None
    account_label: Optional[str] = None

    tp_price: Optional[float] = None
    sl_price: Optional[float] = None

    # Strategia di uscita da usare per questa posizione
    exit_strategy: str = "tp_sl_static"


@dataclass
class BrokerOrderResult:
    """
    Risultato di una richiesta di apertura posizione.

    Per ora è minimale e punta al modello Position interno.
    In futuro potremo aggiungere:

    - order (modello Order)
    - external_order_id / ref specifici dell’exchange
    """

    ok: bool
    reason: Optional[str] = None
    position: Optional[Position] = None


@dataclass
class BrokerCloseResult:
    """
    Risultato di una richiesta di chiusura posizione.
    """

    ok: bool
    reason: Optional[str] = None
    position: Optional[Position] = None


class BrokerAdapter(Protocol):
    """
    Interfaccia astratta per tutti i BrokerAdapter (paper / exchange / live).
    """

    def open_position(self, db: Session, params: NewPositionParams) -> BrokerOrderResult:
        ...

    def close_position(
        self,
        db: Session,
        position: Position,
        close_price: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> BrokerCloseResult:
        ...


class BrokerAdapterPaperSim:
    """
    Implementazione base “paper puro” che lavora solo sul DB locale.

    NOTA IMPORTANTE:
    - per ora NON è ancora usata da /signals/bounce
    - crea direttamente una Position senza passare per l’exchange
    - serve come primo mattoncino per migrare la logica esistente
      verso il pattern BrokerAdapter.
    """

    def open_position(self, db: Session, params: NewPositionParams) -> BrokerOrderResult:
        pos = Position(
            symbol=params.symbol,
            side=params.side,
            qty=params.qty,
            entry_price=params.entry_price,
            tp_price=params.tp_price,
            sl_price=params.sl_price,
            exchange=params.exchange,
            market_type=params.market_type,
            account_label=params.account_label,
            status="open",
            exit_strategy=params.exit_strategy,
        )

        db.add(pos)
        db.commit()
        db.refresh(pos)

        return BrokerOrderResult(ok=True, position=pos)

    def close_position(
        self,
        db: Session,
        position: Position,
        close_price: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> BrokerCloseResult:
        """
        Versione semplificata: chiude la posizione al prezzo passato.
        Per ora NON calcola il PnL (lo fa già auto_close_positions e
        l’endpoint /positions/{id}/close).

        La teniamo come hook per il futuro (live / exchange).
        """
        if position.status != "open":
            return BrokerCloseResult(
                ok=False,
                reason=f"position_not_open (id={position.id}, status={position.status})",
                position=position,
            )

        if close_price is not None:
            position.close_price = float(close_price)

        position.status = "closed"
        if reason:
            position.auto_close_reason = reason

        db.commit()
        db.refresh(position)

        return BrokerCloseResult(ok=True, position=position)
    
class BrokerAdapterExchangeStub:
    """
    Stub per BrokerAdapter "live" / exchange.

    ⚠️ IMPORTANTE:
    - Non manda NESSUN ordine reale.
    - Serve solo come placeholder architetturale per il futuro BrokerAdapterExchange
      che parlerà con Bybit/Bitget.
    - Se qualcuno imposta BROKER_MODE=live oggi, otterrà sempre ok=False e
      nessuna Position creata.
    """

    def open_position(self, db: Session, params: NewPositionParams) -> BrokerOrderResult:
        logger.error(
            {
                "event": "broker_exchange_stub_open_called",
                "symbol": params.symbol,
                "side": params.side,
                "qty": params.qty,
                "reason": "BROKER_MODE=live ma BrokerAdapterExchange non è ancora implementato",
            }
        )
        return BrokerOrderResult(
            ok=False,
            reason="broker_exchange_not_implemented",
            position=None,
        )

    def close_position(
        self,
        db: Session,
        position: Position,
        close_price: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> BrokerCloseResult:
        logger.error(
            {
                "event": "broker_exchange_stub_close_called",
                "position_id": position.id,
                "status": position.status,
                "reason": "BROKER_MODE=live ma BrokerAdapterExchange non è ancora implementato",
            }
        )
        return BrokerCloseResult(
            ok=False,
            reason="broker_exchange_not_implemented",
            position=position,
        )
    
def get_broker_adapter() -> BrokerAdapter:
    """
    Factory centrale per ottenere il BrokerAdapter corretto in base alle Settings.

    - BROKER_MODE=paper (default) -> BrokerAdapterPaperSim
    - BROKER_MODE=live            -> BrokerAdapterExchangeStub (per ora solo stub)
    - altri valori                -> ValueError
    """
    mode = (settings.broker_mode or "paper").lower()

    if mode == "paper":
        logger.info(
            {
                "event": "broker_adapter_selected",
                "mode": mode,
                "adapter": "BrokerAdapterPaperSim",
            }
        )
        return BrokerAdapterPaperSim()

    if mode == "live":
        logger.warning(
            {
                "event": "broker_adapter_selected",
                "mode": mode,
                "adapter": "BrokerAdapterExchangeStub",
                "note": "adapter live non ancora implementato, nessun ordine reale verrà inviato",
            }
        )
        return BrokerAdapterExchangeStub()

    # Difesa extra in caso di typo in BROKER_MODE
    logger.error(
        {
            "event": "broker_adapter_invalid_mode",
            "mode": mode,
        }
    )
    raise ValueError(f"Unsupported BROKER_MODE={mode!r}")


