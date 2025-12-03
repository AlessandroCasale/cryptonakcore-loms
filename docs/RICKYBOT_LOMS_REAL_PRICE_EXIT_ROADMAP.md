RickyBot + LOMS – Real Price & Smart Exit Roadmap

(versione Jira-style – v0.4 – 2025-12-03)

Scope: percorso definitivo per arrivare a:

- prezzi reali nei trade (no MarketSimulator per la parte seria),
- 100€ semi-live sicuri (TP/SL),
- gestione avanzata dell’ordine in corso (smart exit, trailing, ecc.),
- mantenendo paper/shadow/backtest come laboratorio.

Legenda stato:  
✅ completato  
🟡 in corso / parzialmente completo  
⬜ da fare / idea futura  

---

## 0. Macro-obiettivo & principi

### 0.1 Obiettivo finale

⬜ Portare RickyBot + LOMS a:

- usare prezzi reali di mercato per PnL e TP/SL,  
- supportare un profilo semi-live 100€ su exchange reale con risk engine attivo,  
- integrare un motore di uscita smart (ExitPolicy) sopra il TP/SL fisso,  
- mantenere tre modalità operative chiare:

  - **LAB**: paper + simulator,  
  - **SHADOW**: paper + prezzi reali,  
  - **SEMI-LIVE**: ordini reali con capitale limitato.

### 0.2 Principi architetturali (no rework)

⬜ Nessuna logica di trading “seria” nei tool: tutto deve passare da RickyBot (pattern/segnali) + LOMS (OMS/esecuzione).  

⬜ Un’unica astrazione per i prezzi in LOMS (PriceSource / MarketDataService).  

⬜ Un’unica astrazione per l’esecuzione ordini (BrokerAdapter).  

⬜ Schema Position pensato da subito per convivere con:

- paper puro,  
- paper con prezzi reali,  
- live su exchange.

⬜ Ogni step lascia il sistema in uno stato eseguibile (mai “mezzo rotto”).

---

## 1. Real Price Engine (PriceSource / MarketDataService)

### 1.1 Definizione interfaccia prezzi

✅ Definire l’interfaccia concettuale PriceSource (in codice + docs), con:

- Struttura **PriceQuote** con almeno:
  - `symbol`,
  - `ts` (timestamp),
  - `bid`, `ask`, `last`, `mark` (opzionali),
  - `source` (es. `"simulator"`, `"bybit"`, `"bitget"`),
  - `mode` (es. `"last"`, `"bid"`, `"ask"`, `"mid"`, `"mark"`).

- Metodo base:
  - `get_quote(symbol) -> PriceQuote`

- Funzione helper:
  - `select_price(quote, mode)` per estrarre il prezzo giusto (last/bid/ask/mid/mark).

- LOMS ora consuma un `PriceQuote` e sceglie il campo corretto tramite `PRICE_MODE`.

✅ Modulo di appartenenza: `app.services.pricing`  
(definiti `PriceSourceType`, `PriceMode`, `PriceQuote`, `PriceSource` (Protocol), `select_price`, `SimulatedPriceSource`).

⬜ Definire in modo definitivo il contratto d’errore per tutte le sorgenti  
(eccezioni specifiche `PriceSourceError`, log strutturati, policy di retry).

---

### 1.2 Implementazioni previste

✅ **PriceSourceSimulator**

Incapsula l’attuale `MarketSimulator` (random ±10), usato per:

- dev offline,  
- test puramente tecnici,  
- LAB mode attuale.

🟡 **PriceSourceExchange**

✅ Scheletro definito:

- `ExchangeType` + `ExchangeClient` (Protocol) in `exchange_client.py`,  
- `ExchangePriceSource` che prende un `ExchangeClient` e lo trasforma in `PriceQuote`,  
- tool `tools/test_exchange_price_source.py` con `DummyExchangeClient` che verifica:
  - `bid/ask/last/mark`,
  - `select_price` per tutti i `PriceMode`.

⬜ Da fare:

- implementare davvero i client HTTP (`BitgetClient`, `BybitClient`) con le API vere,  
- adattare le response reali → `PriceQuote`,  
- gestione errori/retry/rate-limit.

⬜ **PriceSourceReplay** (fase successiva)

- `ReplayPriceSource` che usa dati storici (CSV, snapshot, klines) per simulare feed di prezzo,  
- fondamentale per testare ExitPolicy offline.

---

### 1.3 Integrazione PriceSource con LOMS

✅ Introdurre i flag in Settings:

- `PRICE_SOURCE = simulator|exchange|replay` (mappato in `PriceSourceType`)  
- `PRICE_MODE = last|bid|ask|mid|mark` (mappato in `PriceMode`)

con alias `settings.price_source`, `settings.price_mode` usati dal codice.

✅ Aggiornare `auto_close_positions(db)`:

invece di usare direttamente `MarketSimulator`, ora legge:

- `price_source = _get_price_source()`:

  - `simulator` → `SimulatedPriceSource(MarketSimulator)`  
  - `exchange` → `ExchangePriceSource(get_default_exchange_client())`  
    (attualmente `get_default_exchange_client()` restituisce un **DummyExchangeHttpClient** con quote finte).

- `quote = price_source.get_quote(pos.symbol)`,  
- `current_price = select_price(quote, settings.price_mode)`,  
- costruisce `ExitContext(price, quote, now)` e passa a `StaticTpSlPolicy`,  
- applica le `ExitAction` di tipo `CLOSE_POSITION` aggiornando `Position`
  (`status`, `closed_at`, `close_price`, `pnl`, `auto_close_reason`).

✅ Aggiornare `POST /positions/{id}/close` (chiusura manuale):

- usa lo stesso `_get_price_source()` di `auto_close_positions`,  
- calcola `current_price = select_price(quote, settings.price_mode)`,  
- chiude la posizione con:
  - `auto_close_reason = "manual"`,  
  - PnL calcolato con l’algoritmo standard long/short.

✅ Garantito:

- `PRICE_SOURCE=simulator` → comportamento LAB attuale (paper puro) invariato,  
- `PRICE_SOURCE=exchange` → testato in dev con `DummyExchangeHttpClient`:

  - `auto_close_positions` chiude a prezzi finti (last=100, ecc.),  
  - `/positions/{id}/close` usa gli stessi prezzi finti,  
  - **perfetta coerenza** fra auto-close e manual-close.

- Fallback sicuro: se viene configurato un sorgente non supportato → warning e fallback a `SimulatedPriceSource`.

---

## 2. Semi-live 100€ (Fase 1 – TP/SL semplici)

### 2.1 Preparazione schema dati “live-ready”

✅ Verificare/aggiungere in `Position`:

- `exchange` (es. `"bitget"`, `"bybit"`),  
- `market_type` / `instrument_type` (es. `"paper_sim"` in LAB; in futuro `"linear_perp"`),  
- `account_label` (es. `"lab_dev"`, in futuro `"semi_live_100eur"`),  
- `external_order_id` (ID ordine sull’exchange, indicizzato),  
- `external_position_ref` (riferimento posizione sull’exchange, se diverso da `order_id`),  
- chiarita semantica di `created_at` come **entry_timestamp** della posizione.

✅ Mantenere compatibilità completa con paper/shadow/live  
(tutti i nuovi campi nullable → nessuna rottura per i DB esistenti).

---

### 2.2 BrokerAdapter – separare logica da esecuzione

🟡 Stato: interfaccia paper pronta, exchange ancora da fare

✅ Definire concettualmente interfaccia BrokerAdapter (paper):

- `NewPositionParams` come comando interno (`symbol`, `side`, `qty`, `entry_price`, `exchange`, `market_type`, `account_label`, `tp_price`, `sl_price`, ecc.).  
- `BrokerAdapterPaperSim` con metodi:
  - `open_position(db, params) -> BrokerOpenResult` che crea una `Position` in DB
    (`exchange`, `market_type`, `account_label`, `exit_strategy = "tp_sl_static"`).

- Tool di test: `tools/test_broker_adapter_papersim.py` che:
  - crea il DB se manca (`Base.metadata.create_all(bind=engine)`),
  - apre una posizione di prova e stampa i campi principali.

⬜ Estendere l’interfaccia per profili exchange:

- `create_order(params) -> BrokerOrderResult` (per modalità SHADOW/LIVE).  
- `close_position(position) -> BrokerCloseResult`.  
- `sync_positions() -> list[ExternalPositionSnapshot]` (per futuri allineamenti con l’exchange).

⬜ Implementazioni target (non ancora fatte):

- `BrokerAdapterExchangePaper` (ordini finti su prezzi reali).  
- `BrokerAdapterExchangeLive` (ordini reali con size ultra-ridotte).

---

### 2.3 Flusso RickyBot → LOMS → BrokerAdapter

🟡 Stato: lato LOMS paper pronto, integrazione RickyBot reale rimane TODO

⬜ Verificare payload `BounceSignal` lato RickyBot (quando ri-agganciamo il client LOMS):

- `symbol, side, price, timestamp, exchange, timeframe_min, strategy, tp_pct, sl_pct`.  
- Allineare i nomi dei campi tra RickyBot e LOMS
  (oggi LOMS usa `signal.symbol`, `signal.side`, `signal.price`, `signal.exchange`,
  `signal.timeframe_min`, `signal.strategy` + `TP_PCT` / `SL_PCT` da settings).

✅ In `/signals/bounce` (profilo LAB / paper):

- Usa `oms.handle_bounce_signal(db, signal)` come entrypoint unico.  
- `handle_bounce_signal`:
  - verifica `OMS_ENABLED` (se false → ack senza aprire posizioni),  
  - normalizza `side` (buy/long, sell/short),  
  - esegue il **risk engine** via `check_risk_limits(...)`,  
  - costruisce un `NewPositionParams` con:
    - `symbol`, `side`, `qty = 1.0` (profilo LAB),  
    - `entry_price = signal.price`,  
    - `exchange = signal.exchange` (default `"bitget"` se mancante),  
    - `market_type = "paper_sim"`,  
    - `account_label = "lab_dev"`,  
    - `tp_price` / `sl_price` calcolati da `TP_PCT` / `SL_PCT` dei settings.
  - chiama il `BrokerAdapterPaperSim` per aprire la posizione.

- Risposta attuale (LAB paper):

  ```json
  {
    "received": true,
    "oms_enabled": true,
    "risk_ok": true,
    "order_id": <id ordine paper>,
    "position_id": <id posizione>,
    "tp_price": ...,
    "sl_price": ...,
    "exit_strategy": "tp_sl_static"
  }
⬜ Step futuri:

Allineare il modello Order e il flusso BrokerAdapter in modo che order_id
nella risposta venga dalla stessa catena logica
(oggi è ancora “ibrido”: Order/Position esistenti + BrokerAdapterPaperSim).

Collegare RickyBot reale in Shadow/Semi-live
(Bounce EMA10 Strict → LOMS con profilo paper_real_price / semi_live_100eur).

2.4 Abilitazione semi-live 100€ (profilo dedicato)
⬜ Tutto ancora da fare
(profilo RISK_PROFILE=semi_live_100eur, sub-account, BROKER_MODE=live, PRICE_SOURCE=exchange, limiti molto stretti, ecc.).

3. Smart Exit (Fase 2 – Gestione ordine in corso)
3.1 ExitPolicy / PositionLifecycle – design
✅ Definire concettualmente ExitPolicy:

Interfaccia in exit_engine.py:

on_new_price(position, context) -> list[ExitAction]

ExitAction con:

type (ExitActionType: ADJUST_STOP_LOSS, ADJUST_TAKE_PROFIT, CLOSE_POSITION),

parametri opzionali (nuovi TP/SL, close_reason, ecc.),

ExitContext con:

prezzo corrente (float),

quote (PriceQuote completo),

now (timestamp).

✅ Posizionamento motore: app.services.exit_engine.

✅ Associazione policy → posizione tramite campo exit_strategy in Position
(es. "tp_sl_static", in futuro "tp_sl_trailing_v1").

3.2 Estensioni schema Position per Exit Engine
✅ Aggiunte/validate:

exit_strategy (string),

dynamic_tp_price, dynamic_sl_price,

max_favorable_move,

exit_meta (JSON serializzato in stringa, per extra info).

✅ auto_close_positions come orchestratore:

legge prezzo da PriceSource (simulator o exchange),

costruisce ExitContext,

passa a ExitPolicy (ora StaticTpSlPolicy),

applica le ExitAction:

aggiornando TP/SL dinamici (in futuro),

chiudendo la posizione (status, closed_at, close_price, pnl, auto_close_reason).

✅ /positions/{id}/close:

usa lo stesso PriceSource e la stessa ExitPolicy (per ora chiusura diretta),

marchia auto_close_reason = "manual" per distinguere la chiusura manuale dall’auto-close policy.

3.3 ExitPolicy iniziali
✅ ExitPolicyStaticTpSl

Replica la logica attuale TP/SL fissi,

già integrata in auto_close_positions come policy di default
(exit_strategy = "tp_sl_static" in LAB).

⬜ ExitPolicyTrailingV1 (fase 2)

Idee base (da implementare):

dopo +X% di move favorevole → SL a break-even,

dopo +Y% → trailing più stretto,

timeout dopo N candele se il trade non si sblocca.

4. ML Layer (sopra, non al posto di tutto il resto)
(ancora completamente ⬜ – nessun cambio rispetto a v0.2, per ora)

5. Sicurezza & Runbook
5.1 Modalità operative
⬜ Definire in docs (e in config) i profili finali:

LAB:

BROKER_MODE=paper

PRICE_SOURCE=simulator

PRICE_MODE=last (o mid, da decidere come default definitiva)

SHADOW:

BROKER_MODE=paper

PRICE_SOURCE=exchange

PRICE_MODE=last (oppure bid/ask/mid/mark, da definire per ogni strategia)

SEMI-LIVE:

BROKER_MODE=live

PRICE_SOURCE=exchange

PRICE_MODE=last (o altro, ma comunque prezzi reali)

RISK_PROFILE=semi_live_100eur

Oggi (profilo LAB dev, locale):

BROKER_MODE = paper,

PRICE_SOURCE = exchange (ma è possibile usare anche simulator),

PRICE_MODE = last,

testato e funzionante con DummyExchangeHttpClient in dev
(auto-close + manual-close).

5.2 Panic Button
⬜ Da scrivere nel Runbook
(stesso concetto di prima: OMS_ENABLED=false, stop RickyBot, check /positions + pannello exchange, export DB/JSONL, mini post-mortem).