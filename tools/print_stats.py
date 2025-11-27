# tools/print_stats.py
#
# Mini-CLI per leggere /stats dal servizio LOMS e stamparli in modo leggibile.

import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


BASE_URL = "http://127.0.0.1:8000"  # modifica se il servizio gira altrove


def fetch_stats() -> dict:
    url = f"{BASE_URL}/stats"
    req = Request(url, headers={"Accept": "application/json"})

    with urlopen(req, timeout=5) as resp:
        data = json.load(resp)
    return data


def format_float(x) -> str:
    if x is None:
        return "-"
    return f"{x:.4f}"


def main():
    try:
        stats = fetch_stats()
    except HTTPError as e:
        print(f"[HTTP ERROR] {e.code} {e.reason}")
        return
    except URLError as e:
        print(f"[CONNECTION ERROR] {e.reason}")
        print("Assicurati che il server LOMS sia avviato (uvicorn app.main:app --reload).")
        return

    print("===================================")
    print(" CryptoNakCore LOMS - Stats snapshot")
    print("===================================\n")

    print(f"Total positions : {stats.get('total_positions', 0)}")
    print(f"Open positions  : {stats.get('open_positions', 0)}")
    print(f"Closed positions: {stats.get('closed_positions', 0)}\n")

    print(f"Winning trades  : {stats.get('winning_trades', 0)}")
    print(f"Losing trades   : {stats.get('losing_trades', 0)}")
    print(f"TP count        : {stats.get('tp_count', 0)}")
    print(f"SL count        : {stats.get('sl_count', 0)}\n")

    print(f"Total PnL       : {format_float(stats.get('total_pnl'))}")
    print(f"Winrate (%)     : {format_float(stats.get('winrate'))}")
    print(f"Avg PnL/trade   : {format_float(stats.get('avg_pnl_per_trade'))}")
    print(f"Avg PnL win     : {format_float(stats.get('avg_pnl_win'))}")
    print(f"Avg PnL loss    : {format_float(stats.get('avg_pnl_loss'))}")
    print()


if __name__ == "__main__":
    main()
