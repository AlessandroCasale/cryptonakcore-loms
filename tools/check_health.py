# tools/check_health.py
#
# Mini-CLI per chiamare /health del servizio LOMS e stampare uno stato leggibile.

import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Modifica qui se il servizio gira su un host/porta diversi
BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    url = f"{BASE_URL}/health"
    req = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(req, timeout=5) as resp:
            status_code = resp.getcode()
            try:
                data = json.load(resp)
            except json.JSONDecodeError:
                data = None
    except HTTPError as e:
        print("===================================")
        print(" CryptoNakCore LOMS - Health check ")
        print("===================================\n")
        print(f"[HTTP ERROR] {e.code} {e.reason}")
        print(f"URL: {url}")
        return
    except URLError as e:
        print("===================================")
        print(" CryptoNakCore LOMS - Health check ")
        print("===================================\n")
        print(f"[CONNECTION ERROR] {e.reason}")
        print("Assicurati che il server LOMS sia avviato, ad esempio:")
        print("  uvicorn services.cryptonakcore.app.main:app --reload")
        return

    print("===================================")
    print(" CryptoNakCore LOMS - Health check ")
    print("===================================\n")

    print(f"HTTP status code : {status_code}")

    if data is None or not isinstance(data, dict):
        print("Body JSON       : <non valido / non parseable>")
        return

    status = data.get("status")
    environment = data.get("environment")
    broker_mode = data.get("broker_mode")
    oms_enabled = data.get("oms_enabled")
    database_url = data.get("database_url")
    audit_log_path = data.get("audit_log_path")
    price_source = data.get("price_source")
    price_mode = data.get("price_mode")

    if status is not None:
        print(f"Service status  : {status}")
    else:
        print("Service status  : <campo 'status' non presente>")

    if environment is not None:
        print(f"Environment     : {environment}")

    if broker_mode is not None:
        print(f"Broker mode     : {broker_mode}")

    if oms_enabled is not None:
        print(f"OMS enabled     : {oms_enabled}")

    if database_url is not None:
        print(f"Database URL    : {database_url}")

    if audit_log_path is not None:
        print(f"Audit log path  : {audit_log_path}")

    if price_source is not None:
        print(f"Price source    : {price_source}")

    if price_mode is not None:
        print(f"Price mode  : {price_mode}")

    print(f"Raw JSON        : {data}")


if __name__ == "__main__":
    main()
