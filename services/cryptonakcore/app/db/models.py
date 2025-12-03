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

    # Timestamp creazione ordine (server-side, UTC)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Position(Base):
    """
    Posizione gestita dall'OMS.

    - Aperta da un segnale / order
    - Chiusa da auto_close_positions (TP/SL) o manualmente

    Pensata per funzionare in:
    - paper puro (simulatore prezzi)
    - paper con prezzi reali (Real Price Engine)
    - live su exchange (via BrokerAdapter + external_order_id/ref)
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identità "live-ready" della posizione ---

    # Exchange di riferimento: es. "bitget", "bybit"
    exchange = Column(String, index=True, nullable=True)

    # Tipo di mercato / strumento: es. "linear_perp"
    market_type = Column(String, nullable=True)

    # Simbolo sull'exchange: es. "BTCUSDT"
    symbol = Column(String, index=True, nullable=False)

    # "long" / "short" (o equivalente BUY/SELL normalizzato)
    side = Column(String, nullable=False)

    # Quantità in coin (es. 0.01 BTC)
    qty = Column(Float, nullable=False)

    # Etichetta logica dell'account/profilo: es. "semi_live_100eur"
    account_label = Column(String, nullable=True)

    # Riferimenti lato exchange (per SHADOW / LIVE)
    external_order_id = Column(String(64), nullable=True, index=True)
    external_position_ref = Column(String(64), nullable=True)

    # --- Prezzi TP/SL e stato posizione ---

    # Prezzo di ingresso (entry) "effettivo" della posizione
    entry_price = Column(Float, nullable=False)

    # TP / SL della posizione (prezzi target)
    tp_price = Column(Float, nullable=True)
    sl_price = Column(Float, nullable=True)

    # Stato posizione: "open" / "closed" / "cancelled"
    status = Column(String, default="open", index=True, nullable=False)

    # Timestamp apertura (equivalente a "entry_timestamp")
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

    # --- Exit Engine (ExitPolicy / smart exit) ---

    # Strategia di uscita associata: es. "tp_sl_static", "tp_sl_trailing_v1"
    exit_strategy = Column(String, nullable=True)

    # TP/SL dinamici (se la policy li muove nel tempo)
    dynamic_tp_price = Column(Float, nullable=True)
    dynamic_sl_price = Column(Float, nullable=True)

    # Massimo movimento favorevole raggiunto (es. in % o in prezzo — TBD)
    max_favorable_move = Column(Float, nullable=True)

    # Extra info serializzata (JSON in stringa), per debug/diagnostica
    exit_meta = Column(String, nullable=True)

