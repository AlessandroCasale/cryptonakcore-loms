from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.db.session import Base


class Order(Base):
    """
    Ordine "logico" creato dal segnale.
    Per ora è una semplice traccia di cosa è stato chiesto all'OMS.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Es. "BTCUSDT"
    symbol = Column(String, index=True, nullable=False)

    # "long" / "short" (normalizzato dal notifier RickyBot → LOMS)
    side = Column(String, nullable=False)

    # Quantità in coin (es. 0.01 BTC)
    qty = Column(Float, nullable=False)

    # Per ora solo "market"
    order_type = Column(String, default="market", nullable=False)

    # TP / SL dell'ordine (prezzi target opzionali)
    tp_price = Column(Float, nullable=True)
    sl_price = Column(Float, nullable=True)

    # Stato ordine: "created", "filled", "canceled", ...
    status = Column(String, default="created", nullable=False)

    # Timestamp creazione ordine
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Position(Base):
    """
    Posizione paper gestita dal MarketSimulator.

    - Aperta da un segnale / order
    - Chiusa da auto_close_positions (TP/SL) o manualmente
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)  # "long" / "short"
    qty = Column(Float, nullable=False)

    # Prezzo di ingresso "paper"
    entry_price = Column(Float, nullable=False)

    # TP / SL della posizione (prezzi target)
    tp_price = Column(Float, nullable=True)
    sl_price = Column(Float, nullable=True)

    # Stato posizione: "open" / "closed" / "cancelled" (stringhe usate in oms.py)
    status = Column(String, default="open", index=True, nullable=False)

    # Timestamp apertura
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Dati chiusura (settati da auto_close_positions o manualmente)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    close_price = Column(Float, nullable=True)

    # PnL realizzato sulla posizione (in "quote", es. USDT)
    pnl = Column(Float, nullable=True)

    # Motivo di chiusura: "tp", "sl", "manual", "timeout", ecc.
    auto_close_reason = Column(String, nullable=True)
