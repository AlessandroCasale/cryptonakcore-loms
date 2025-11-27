
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Float, func
from app.db.session import Base

# Base comune per tutti i modelli ORM


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(String, index=True, nullable=False)    # es. "BTCUSDT"
    side = Column(String, nullable=False)                  # "long" / "short"
    qty = Column(Float, nullable=False)
    order_type = Column(String, default="market")

    # TP / SL opzionali
    tp_price = Column(Float, nullable=True)
    sl_price = Column(Float, nullable=True)

    status = Column(String, default="created")             # "created", "filled", "canceled"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)  # "long" / "short"
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)

    # TP / SL della posizione (prezzi target)
    tp_price = Column(Float, nullable=True)
    sl_price = Column(Float, nullable=True)

    # Stato posizione: open / closed / cancelled
    status = Column(String, default="open")

    # Timestamp apertura
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Dati chiusura (settati da auto_close_positions o manualmente)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    close_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)

    # Motivo di chiusura: "tp", "sl", "manual", ecc.
    auto_close_reason = Column(String, nullable=True)

