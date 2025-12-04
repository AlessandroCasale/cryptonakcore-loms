from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict  # per Pydantic v2

from app.services.pricing import PriceSourceType, PriceMode


# BASE_DIR = root del servizio cryptonakcore (dove ci sono app/, data/, ecc.)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Config Pydantic Settings v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignora eventuali env "in più" (come loms_max_size_per_position_usdt)
    )

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

    # NOTA: usiamo una env *namespaced* per evitare conflitti con variabili di sistema
    # tipo MAX_SIZE_PER_POSITION_USDT=10.0 lasciate in giro.
    # LOMS userà SOLO LOMS_MAX_SIZE_PER_POSITION_USDT.
    MAX_SIZE_PER_POSITION_USDT: float = Field(
        100000.0,
        env="LOMS_MAX_SIZE_PER_POSITION_USDT",
    )  # size massima per posizione (paper)

    # file dove salviamo i segnali di bounce in formato JSON Lines
    AUDIT_LOG_PATH: str = str(BASE_DIR / "data" / "bounce_signals.jsonl")

    # -----------------------------
    # Real Price Engine (PriceSource)
    # -----------------------------
    # Da dove arrivano i prezzi: simulator | exchange | replay
    PRICE_SOURCE: PriceSourceType = PriceSourceType.SIMULATOR
    # Quale campo del quote usare: last | bid | ask | mid | mark
    PRICE_MODE: PriceMode = PriceMode.LAST

    # Exchange HTTP client per il Real Price Engine
    # dummy  -> DummyExchangeHttpClient (test / dev)
    # bybit  -> BybitHttpClient reale (REST /v5/market/tickers)
    PRICE_EXCHANGE: str = "dummy"

    # Timeout HTTP (in secondi) per le chiamate all'exchange reale
    PRICE_HTTP_TIMEOUT: float = 3.0

    # Scheduler / auto-close watcher
    AUTO_CLOSE_INTERVAL_SEC: int = 1

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

    @property
    def price_source(self) -> PriceSourceType:
        """Alias per l'uso interno /health ecc."""
        return self.PRICE_SOURCE

    @property
    def price_mode(self) -> PriceMode:
        """Alias per l'uso interno /health ecc."""
        return self.PRICE_MODE

    @property
    def price_exchange(self) -> str:
        """Alias lower-case per scegliere il client HTTP (dummy / bybit)."""
        return self.PRICE_EXCHANGE

    @property
    def price_http_timeout(self) -> float:
        """Alias per il timeout HTTP (secondi)."""
        return self.PRICE_HTTP_TIMEOUT


settings = Settings()