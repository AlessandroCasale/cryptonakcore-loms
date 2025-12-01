from pathlib import Path

from pydantic_settings import BaseSettings  # per Pydantic v2


# BASE_DIR = root del servizio cryptonakcore (dove ci sono app/, data/, ecc.)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./cryptonakcore_loms.db"
    JWT_SECRET: str = "dev-secret"

    # Ambiente logico del servizio: dev / paper / live (per ora usiamo dev/paper)
    ENVIRONMENT: str = "dev"

    # Modalità broker: per ora supportato solo "paper".
    # "live" è riservato per il futuro, ma il flag serve già come kill-switch logico.
    BROKER_MODE: str = "paper"

    # Abilita/disabilita l’apertura automatica di ordini/posizioni dai segnali
    OMS_ENABLED: bool = True

    # Limiti base di rischio (paper)
    MAX_OPEN_POSITIONS: int = 10              # totale posizioni aperte
    MAX_OPEN_POSITIONS_PER_SYMBOL: int = 3    # per singolo symbol
    MAX_SIZE_PER_POSITION_USDT: float = 10.0  # size massima per posizione (paper)

    # file dove salviamo i segnali di bounce in formato JSON Lines
    AUDIT_LOG_PATH: str = str(BASE_DIR / "data" / "bounce_signals.jsonl")

    class Config:
        env_file = ".env"

    # Alias "comodi" in lower-case, usati da /health e da eventuali altri punti
    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    @property
    def broker_mode(self) -> str:
        return self.BROKER_MODE

    @property
    def oms_enabled(self) -> bool:
        return self.OMS_ENABLED


settings = Settings()
