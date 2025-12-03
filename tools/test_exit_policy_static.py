"""
Tool di test per StaticTpSlPolicy (ExitPolicy TP/SL statici).

Esegue alcuni scenari fittizi di posizione (long/short, diversi TP/SL)
e mostra quali ExitAction verrebbero suggerite a vari prezzi.
"""

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import sys

# -------------------------------------------------------------------
# Setup sys.path per usare i moduli di services/cryptonakcore (app.*)
# -------------------------------------------------------------------
# Struttura attesa:
#   cryptonakcore-loms/
#       tools/test_exit_policy_static.py  <-- questo file
#       services/cryptonakcore/app/...
#
# Aggiungiamo "services/cryptonakcore" a sys.path, così possiamo fare
# import app.services.exit_engine anche lanciando il tool dalla root.
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]  # .../cryptonakcore-loms
SERVICE_ROOT = ROOT_DIR / "services" / "cryptonakcore"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.services.exit_engine import (  # type: ignore[import]
    StaticTpSlPolicy,
    ExitContext,
    ExitAction,
    ExitActionType,
)


@dataclass
class FakePosition:
    """
    Posizione fittizia minima per testare la ExitPolicy.

    Campi usati da StaticTpSlPolicy:
    - symbol
    - side
    - tp_price
    - sl_price
    """

    symbol: str
    side: str
    tp_price: Optional[float]
    sl_price: Optional[float]


def run_scenario(
    name: str,
    position: FakePosition,
    prices: list[float],
) -> None:
    policy = StaticTpSlPolicy()

    print("=" * 60)
    print(f"Scenario: {name}")
    print(
        f"Position: symbol={position.symbol} side={position.side} "
        f"tp={position.tp_price} sl={position.sl_price}"
    )
    print("-" * 60)

    actions: List[ExitAction]

    for p in prices:
        ctx = ExitContext(price=p)
        actions = policy.on_new_price(position, ctx)

        if not actions:
            print(f"Price {p:.4f}: no action")
        else:
            for a in actions:
                if a.type == ExitActionType.CLOSE_POSITION:
                    print(
                        f"Price {p:.4f}: CLOSE_POSITION "
                        f"(reason={a.close_reason})"
                    )
                elif a.type == ExitActionType.ADJUST_STOP_LOSS:
                    print(
                        f"Price {p:.4f}: ADJUST_STOP_LOSS "
                        f"(new_sl={a.new_sl})"
                    )
                elif a.type == ExitActionType.ADJUST_TAKE_PROFIT:
                    print(
                        f"Price {p:.4f}: ADJUST_TAKE_PROFIT "
                        f"(new_tp={a.new_tp})"
                    )
                elif a.type == ExitActionType.PARTIAL_CLOSE:
                    print(
                        f"Price {p:.4f}: PARTIAL_CLOSE "
                        f"(qty={a.close_qty}, reason={a.close_reason})"
                    )
                else:
                    print(f"Price {p:.4f}: UNKNOWN ACTION {a}")


def main() -> None:
    # Scenario 1: long con TP sopra e SL sotto
    pos_long = FakePosition(
        symbol="BTCUSDT",
        side="long",
        tp_price=105.0,
        sl_price=95.0,
    )
    prices_long = [94.0, 96.0, 100.0, 104.9, 105.0, 106.0]

    run_scenario("LONG tp=105 sl=95", pos_long, prices_long)

    # Scenario 2: short con TP sotto e SL sopra
    pos_short = FakePosition(
        symbol="BTCUSDT",
        side="short",
        tp_price=95.0,   # per short: TP quando il prezzo SCENDE
        sl_price=105.0,  # SL quando il prezzo SALE
    )
    prices_short = [106.0, 104.0, 100.0, 95.1, 95.0, 94.0]

    run_scenario("SHORT tp=95 sl=105", pos_short, prices_short)

    # Scenario 3: solo TP, nessuno SL
    pos_only_tp = FakePosition(
        symbol="BTCUSDT",
        side="long",
        tp_price=110.0,
        sl_price=None,
    )
    prices_only_tp = [108.0, 109.9, 110.0, 111.0]

    run_scenario("LONG solo TP=110", pos_only_tp, prices_only_tp)

    # Scenario 4: niente TP/SL → nessuna azione mai
    pos_no_tp_sl = FakePosition(
        symbol="BTCUSDT",
        side="long",
        tp_price=None,
        sl_price=None,
    )
    prices_no_tp_sl = [90.0, 100.0, 110.0]

    run_scenario("LONG senza TP/SL", pos_no_tp_sl, prices_no_tp_sl)


if __name__ == "__main__":
    main()
