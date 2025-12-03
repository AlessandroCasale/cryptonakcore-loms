from __future__ import annotations

import sys
from pathlib import Path

# -------------------------------------------------------------------
# Setup path per importare app.* (stesso trucco degli altri tool)
# -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent / "services" / "cryptonakcore"
sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.db.models import Base
from app.services.broker_adapter import BrokerAdapterPaperSim, NewPositionParams


def main() -> None:
    print("==============================================")
    print(" BrokerAdapterPaperSim test (LOMS)")
    print("==============================================")
    print(f"ENVIRONMENT   : {settings.environment}")
    print(f"BROKER_MODE   : {settings.broker_mode}")
    print()

    # 💾 Assicuriamoci che il DB (loms_dev.db) abbia le tabelle
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        adapter = BrokerAdapterPaperSim()

        params = NewPositionParams(
            symbol="BTCUSDT",
            side="long",
            qty=1.0,
            entry_price=5.0,
            exchange="bitget",
            market_type="paper_sim",
            account_label="lab_dev",
            tp_price=5.225,
            sl_price=4.925,
        )

        print("Creo nuova posizione via BrokerAdapterPaperSim...")
        result = adapter.open_position(db, params)

        print(f"ok       : {result.ok}")
        print(f"reason   : {result.reason}")
        if result.position is not None:
            p = result.position
            print("Position :")
            print(f"  id           : {p.id}")
            print(f"  symbol       : {p.symbol}")
            print(f"  side         : {p.side}")
            print(f"  qty          : {p.qty}")
            print(f"  entry_price  : {p.entry_price}")
            print(f"  tp_price     : {p.tp_price}")
            print(f"  sl_price     : {p.sl_price}")
            print(f"  status       : {p.status}")
            print(f"  exchange     : {p.exchange}")
            print(f"  market_type  : {p.market_type}")
            print(f"  account_label: {p.account_label}")
            print(f"  exit_strategy: {p.exit_strategy}")
    finally:
        db.close()

    print("==============================================")
    print(" Fine test BrokerAdapterPaperSim")
    print("==============================================")


if __name__ == "__main__":
    main()
