import json
from datetime import datetime
from pathlib import Path

from app.core.config import settings

# Path del file JSONL dove salviamo i segnali di bounce
LOG_PATH = Path(settings.AUDIT_LOG_PATH)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_bounce_signal(signal: dict) -> None:
    """
    Salva un segnale di bounce come riga JSON nel file audit.
    """
    entry = {
        "type": "bounce_signal",
        "ts": datetime.utcnow().isoformat(),
        "payload": signal,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
