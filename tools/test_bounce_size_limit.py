from datetime import datetime, timezone
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://127.0.0.1:8000"


def send_bounce(price: float, symbol: str = "TESTUSDT") -> None:
    payload = {
        "symbol": symbol,
        "side": "long",
        "price": price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exchange": "bitget",
        "timeframe_min": 5,
        "strategy": "bounce_ema10_strict",
        "tp_pct": None,
        "sl_pct": None,
    }

    print("===================================")
    print(f" Invio segnale bounce (symbol={symbol}, price={price})")
    print("===================================\n")

    data = json.dumps(payload).encode("utf-8")
    url = f"{BASE_URL}/signals/bounce"
    req = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=5) as resp:
            status = resp.getcode()
            resp_body = resp.read().decode("utf-8")
    except HTTPError as e:
        print(f"[HTTP ERROR] {e.code} {e.reason}")
        try:
            body_err = e.read().decode("utf-8")
            print("Body errore:", body_err)
        except Exception:
            pass
        print()
        return
    except URLError as e:
        print(f"[CONNECTION ERROR] {e.reason}")
        print("Assicurati che il server LOMS sia avviato (uvicorn app.main:app --reload).")
        print()
        return

    print("HTTP status :", status)
    try:
        data_json = json.loads(resp_body)
    except Exception as ex:  # noqa: BLE001
        print("Errore nel parse JSON:", repr(ex))
        print("Raw text:", resp_body)
        print()
        return

    print("Risposta JSON:", data_json)
    print()


def main() -> None:
    # Caso 1: notional sotto il limite (es. 5 * qty=1 = 5 USDT)
    send_bounce(price=5.0, symbol="SIZEOKUSDT")

    # Caso 2: notional sopra il limite (es. 100 * qty=1 = 100 USDT)
    send_bounce(price=100.0, symbol="SIZEBLOCKUSDT")


if __name__ == "__main__":
    main()
