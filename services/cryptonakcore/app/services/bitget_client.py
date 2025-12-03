from __future__ import annotations

from typing import Any


class BitgetClient:
    """
    Skeleton di ExchangeClient per Bitget.

    Responsabilità (future):

      - mantenere la configurazione di connessione (base_url, API key, ecc.)
      - esporre un metodo get_ticker(symbol) -> dict[str, Any] compatibile
        con ExchangePriceSource.

    NOTE IMPORTANTI (per il futuro, NON implementato ora):

      - La chiamata tipica sarà qualcosa come:
          GET /api/v2/market/ticker
        oppure l'equivalente endpoint "ticker" aggiornato di Bitget.
      - Il risultato grezzo dell'API andrà mappato in un dict
        con i campi normalizzati per ExchangePriceSource:

          {
              "bid": <best bid>       # opzionale
              "ask": <best ask>       # opzionale
              "last": <last trade>    # oppure last_price / close
              "mark_price": <mark>    # opzionale
          }

      - L'error handling dovrà:
          * NON silenziare errori di rete / auth,
          * loggare in modo strutturato,
          * sollevare eccezioni chiare in caso di problemi.
    """

    name: str = "bitget"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        base_url: str = "https://api.bitget.com",
    ) -> None:
        """
        Costruttore "live-ready" ma ancora senza logica HTTP.

        Parametri:
          - api_key, api_secret, passphrase: credenziali API Bitget
          - base_url: endpoint base (default mainnet). In futuro potremo
            prevedere un flag/testnet o passare un URL diverso dal config.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = base_url

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        """
        Restituisce le informazioni di prezzo per il simbolo richiesto.

        CONTRATTO LOGICO atteso da ExchangePriceSource:

          - Il dict deve contenere almeno UNO tra:
              * "last" / "last_price" / "close"
              * "bid", "ask"
              * "mark" / "mark_price"

          - Campi aggiuntivi possono essere presenti (volumi, high/low, ecc.).

        IMPLEMENTAZIONE FUTURA (TODO):

          - Costruire l'URL dell'endpoint di ticker Bitget.
          - Firmare la richiesta se necessario (per il ticker spesso non serve).
          - Eseguire la GET (es. via httpx / requests).
          - Normalizzare i campi del JSON di risposta nel dict standard.

        Per ora è solo uno scheletro: solleva NotImplementedError.
        """
        raise NotImplementedError("BitgetClient.get_ticker is not implemented yet.")
