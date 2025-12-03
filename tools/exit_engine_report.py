"""
Exit Engine Report (paper)

Legge le posizioni dall'API /positions e stampa:
- totale posizioni
- conteggio per status (open/closed)
- per le posizioni chiuse: conteggio e PnL medio per auto_close_reason
"""

import sys
import json
import statistics
from collections import defaultdict
from urllib import request, error


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def fetch_positions(base_url: str):
    url = f"{base_url.rstrip('/')}/positions/"
    try:
        with request.urlopen(url, timeout=5) as resp:
            status = resp.getcode()
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            data = resp.read()
    except error.URLError as e:
        raise RuntimeError(f"URLError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"HTTP error: {type(e).__name__}: {e}") from e

    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from /positions: {e}") from e


def main(base_url: str = DEFAULT_BASE_URL):
    try:
        positions = fetch_positions(base_url)
    except Exception as e:
        print("Errore nel chiamare /positions:", str(e))
        sys.exit(1)

    if not isinstance(positions, list):
        print("Risposta inattesa da /positions (non è una lista)")
        sys.exit(1)

    total = len(positions)
    print("Exit Engine Report")
    print("===================")
    print(f"Totale posizioni: {total}")
    print()

    if total == 0:
        print("Nessuna posizione trovata.")
        return

    status_counts = defaultdict(int)
    closed_by_reason = defaultdict(list)

    for p in positions:
        status = p.get("status", "unknown")
        status_counts[status] += 1

        if status == "closed":
            reason = p.get("auto_close_reason") or "unknown"
            pnl = p.get("pnl")
            try:
                pnl_f = float(pnl) if pnl is not None else 0.0
            except (TypeError, ValueError):
                pnl_f = 0.0
            closed_by_reason[reason].append(pnl_f)

    print("Per status:")
    for status, cnt in sorted(status_counts.items()):
        print(f"  - {status}: {cnt}")
    print()

    if not closed_by_reason:
        print("Nessuna posizione chiusa, niente da analizzare.")
        return

    print("Posizioni chiuse per auto_close_reason:")
    for reason, pnls in sorted(closed_by_reason.items()):
        count = len(pnls)
        avg_pnl = statistics.mean(pnls) if pnls else 0.0
        min_pnl = min(pnls) if pnls else 0.0
        max_pnl = max(pnls) if pnls else 0.0
        print(
            f"  - {reason}: n={count}, "
            f"avg_pnl={avg_pnl:.4f}, min={min_pnl:.4f}, max={max_pnl:.4f}"
        )


if __name__ == "__main__":
    base = DEFAULT_BASE_URL
    if len(sys.argv) > 1:
        base = sys.argv[1]
    main(base)
