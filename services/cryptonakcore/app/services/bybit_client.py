from __future__ import annotations

from typing import Any


class BybitClient:
    """
    Skeleton di ExchangeClient per Bybit.

    Responsabilità (future):

      - gestire configurazione (base_url, API key/secret, testnet/mainnet),
      - esporre get_ticker(symbol) -> dict[str, Any] compatibile
        con ExchangePriceSource.

    NOTE IMPORTANTI (per il futuro, NON implementato ora):

      - La chiamata tipica sarà un endpoint tipo:
          GET /v5/market/tickers
        con i parametri richiesti da Bybit per i perpetual linear.

      - Anche qui, il risultato grezzo andrà normalizzato in un dict:

          {
              "bid": <best bid>       # opzionale
              "ask": <best ask>       # opzionale
              "last": <last trade>    # oppure last_price / close
              "mark_price": <mark>    # opzionale
          }

      - L'implementazione reale dovrà gestire:
          * errori di rete,
          * codice di errore specifico dell'API,
          * rate-limit,
          * logging strutturato.
    """

    name: str = "bybit"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.bybit.com",
    ) -> None:
        """
        Costruttore "live-ready" ma ancora senza logica HTTP.

        Parametri:
          - api_key, api_secret: credenziali API Bybit
          - base_url: endpoint base (default mainnet). Per il testnet
            potremo usare un'altra URL letta dal config/env.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        """
        Restituisce le informazioni di prezzo per il simbolo richiesto.

        CONTRATTO LOGICO atteso da ExchangePriceSource:

          - Il dict deve contenere almeno UNO tra:
              * "last" / "last_price" / "close"
              * "bid", "ask"
              * "mark" / "mark_price"

          - I nomi dei campi dipenderanno dalla risposta Bybit, ma
            verranno normalizzati in questa forma standard.

        IMPLEMENTAZIONE FUTURA (TODO):

          - Costruire l'URL dell'endpoint di ticker Bybit.
          - Firmare/parametrizzare la request come richiesto dall'API.
          - Eseguire la GET (httpx/requests).
          - Normalizzare i campi.

        Per ora è solo uno scheletro: solleva NotImplementedError.
        """
        raise NotImplementedError("BybitClient.get_ticker is not implemented yet.")
