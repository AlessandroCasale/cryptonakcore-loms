# CryptoNakCore LOMS – Jira Checklist MASTER

Versione aggiornata al **2025-12-03**  
(Stato: `loms-real-price-paper-dev-2025-12-03` –  
LOMS paper stabile con:

- MarketSimulator v2 incapsulato in **PriceSource** (simulator/exchange),
- risk engine a 3 limiti,
- schema `Position` “live-ready” (exchange/market_type/account_label/exit_strategy),
- `BrokerAdapterPaperSim` operativo,
- integrazione RickyBot → LOMS in **Shadow Mode**,
- tools di health/stats e profili DEV vs PAPER-SERVER operativi.)

Legenda stato:  
✅ completato  
🟡 in corso / parzialmente completo  
⬜ da fare / idea parcheggiata  

---

## 0. Macro-obiettivo LOMS

Portare **CryptoNakCore LOMS** da semplice API di test a:

- vero **OMS paper trading** (ordini/posizioni simulati, TP/SL, PnL, stats),
- integrato con **RickyBot** via `POST /signals/bounce`,
- pronto per fasi successive:
  - risk engine più ricco,
  - strumenti di analisi,
  - in futuro modalità **semi-live / live** (100€ semi-live, ecc.).

---

## 1. Schema DB & Modelli ORM

### 1.1 Base SQLAlchemy unica

✅ Fatto

- `Base` e `SessionLocal` definiti in `app.db.session`.
- `app.db.models` importa `Base` da lì.
- DB ricreato con schema coerente.

### 1.2 Modello `Order`

✅ Modello `Order` semplice con:

- `id`, `symbol`, `side`, `qty`, `order_type`
- `tp_price`, `sl_price`
- `status`, `created_at`

(Per ora usato solo in modo minimale; in futuro verrà allineato al flusso BrokerAdapter.)

### 1.3 Modello `Position`

✅ Modello `Position` allineato a:

- `auto_close_positions` (ExitPolicy + PriceSource)
- chiusura manuale `/positions/{id}/close`
- profili paper / shadow / future live

Campi principali (core PnL + live-ready):

- Identità & contesto:
  - `id` (PK)
  - `exchange` (es. `"bitget"`, `"bybit"`)
  - `market_type` (es. `"paper_sim"`, in futuro `"linear_perp"`)
  - `symbol` (es. `"BTCUSDT"`)
  - `side` (`"long"` / `"short"`)
  - `qty` (float)
  - `account_label` (es. `"lab_dev"`, in futuro `"semi_live_100eur"`)

- Riferimenti esterni (per SHADOW/LIVE):
  - `external_order_id` (ID ordine sull’exchange, indicizzato)
  - `external_position_ref` (eventuale riferimento posizione, se diverso)

- Prezzi & stato:
  - `entry_price` (float, obbligatorio)
  - `tp_price`, `sl_price` (float, opzionali)
  - `status` (`"open"` / `"closed"` / `"cancelled"`)
  - `created_at` (timestamp apertura = entry_timestamp)
  - `closed_at` (timestamp chiusura)
  - `close_price`
  - `pnl` (PnL realizzato)
  - `auto_close_reason` (`"tp"`, `"sl"`, `"manual"`, `"timeout"`, …)

- Exit Engine (smart exit):
  - `exit_strategy` (es. `"tp_sl_static"`, in futuro `"tp_sl_trailing_v1"`)
  - `dynamic_tp_price`, `dynamic_sl_price`
  - `max_favorable_move`
  - `exit_meta` (JSON serializzato in stringa, per diagnostica)

### 1.4 Migrazioni DB (Alembic, ecc.)

⬜ Introdurre un flusso di migrazioni strutturato (Alembic) quando lo schema
diventerà più stabile.

---

## 2. Core OMS Paper

### 2.1 Market simulator

✅ `MarketSimulator.get_price()` (v2):

- prezzo fittizio base `100.0`;
- variazione random ±10.0;
- rende realisticamente raggiungibili TP/SL tipo 4.5% / 1.5% in pochi tick
  (es. `tp=104.5`, `sl=98.5`).

> Nota: ora il simulatore non viene più usato direttamente da `auto_close_positions`,
ma è incapsulato nella sorgente prezzi `SimulatedPriceSource` (vedi sezione PriceSource).

### 2.2 PriceSource & `auto_close_positions`

✅ Introdotto **Real Price Engine v1** tramite `PriceSource`:

- Modulo: `app.services.pricing`
- Tipi chiave:
  - `PriceSourceType` (`SIMULATOR`, `EXCHANGE`, `REPLAY`)
  - `PriceMode` (`LAST`, `BID`, `ASK`, `MID`, `MARK`)
  - `PriceQuote` (symbol, ts, bid/ask/last/mark, source, mode)
  - `PriceSource` (Protocol con `get_quote(symbol) -> PriceQuote`)
  - `SimulatedPriceSource` (wrappa `MarketSimulator`)
  - `select_price(quote, mode)` per estrarre il campo corretto

✅ `_get_price_source()` in `app.services.oms`:

- legge `settings.price_source` (`PriceSourceType`)
- se `SIMULATOR` → `SimulatedPriceSource(MarketSimulator)`
- se `EXCHANGE` → `ExchangePriceSource(get_default_exchange_client())`
  - attualmente `get_default_exchange_client()` restituisce un **DummyExchangeHttpClient**
    che genera quote finte coerenti (`bid/ask/last/mark`)
- default/fallback → warning e ritorno a `SimulatedPriceSource(MarketSimulator)`

✅ `auto_close_positions(db)` (versione attuale):

- legge tutte le posizioni `open`;
- ignora quelle con età `< 7s` (gate in secondi);
- usa **PriceSource**:
  - `price_source = _get_price_source()`
  - `quote = price_source.get_quote(pos.symbol)`
  - `current_price = select_price(quote, settings.price_mode)`

- costruisce `ExitContext(price=current_price, quote=quote, now=now)`;
- passa il tutto a `StaticTpSlPolicy` (`app.services.exit_engine`);
- riceve una lista di `ExitAction`;
- filtra quelle con `type == CLOSE_POSITION`;
- se c’è almeno una `CLOSE_POSITION`:
  - aggiorna la `Position`:
    - `status = "closed"`
    - `closed_at = now`
    - `close_price = current_price`
    - `auto_close_reason = action.close_reason` (es. `"tp"` / `"sl"` / `"tp_sl"`)
  - calcola `pnl` long/short:
    - **long**: `(current_price - entry_price) * qty`
    - **short**: `(entry_price - current_price) * qty`
  - `db.commit()`
  - log strutturato `position_closed`

> Risultato: la logica di TP/SL è ora orchestrata dal **motore di ExitPolicy**,
non è più hardcodata dentro `auto_close_positions`.

### 2.3 Chiusura manuale posizione

✅ Endpoint `POST /positions/{id}/close`:

- cerca la `Position` per `id`:
  - se non esiste → 404;
  - se già `closed` → ritorna la posizione così com’è;
- altrimenti:
  - usa **lo stesso `PriceSource` di `auto_close_positions`**
    (`_get_price_source()` + `select_price` con `settings.price_mode`);
  - imposta `status = "closed"`;
  - valorizza `closed_at`, `close_price`;
  - calcola `pnl` long/short;
  - `auto_close_reason = "manual"`;
  - commit + refresh.

✅ Testata sia con `PRICE_SOURCE=SIMULATOR` sia con `PRICE_SOURCE=EXCHANGE`
(`DummyExchangeHttpClient`).

### 2.4 Risk engine base

✅ Completato (prima versione + limite di size notional).

Funzione `check_risk_limits(db, symbol, entry_price=None, qty=None)` in `app.services.oms`:

- legge i limiti da `settings` (env):
  - `MAX_OPEN_POSITIONS` (limite totale posizioni aperte),
  - `MAX_OPEN_POSITIONS_PER_SYMBOL` (limite per singolo `symbol`),
  - `MAX_SIZE_PER_POSITION_USDT` (limite di **notional** per singola posizione:
    `entry_price * qty`).

- controlli:

  - se il limite totale è superato → ritorna `risk_ok=False` con reason  
    `max_total_open_reached (total=..., limit=...)`
    + log `risk_block` con `scope="total"`;

  - se il limite per simbolo è superato → ritorna `risk_ok=False` con reason  
    `max_symbol_open_reached (symbol=..., count=..., limit=...)`
    + log `risk_block` con `scope="symbol"`;

  - se **entry_price** e **qty** sono forniti e la notional
    supera `MAX_SIZE_PER_POSITION_USDT`
    → `risk_ok=False` con reason  
    `max_size_per_position_exceeded (notional=..., limit=...)`
    + log `risk_block` con `scope="size"`.

- L’endpoint `/signals/bounce`:
  - usa **sempre** `check_risk_limits` prima di creare Order/Position;
  - risponde sempre con `risk_ok` e `risk_reason` (quando bloccato);
  - in caso di blocco NON crea nessun ordine/posizione.

✅ Tool di test dedicato:

- `tools/test_bounce_size_limit.py`:
  - primo segnale simbolo `SIZEOKUSDT` → passa (`risk_ok=True`);
  - secondo segnale simbolo `SIZEBLOCKUSDT` → blocco per:
    - prima variante: limite totale open,
    - variante attuale: `max_size_per_position_exceeded`.

---

## 3. API REST – Endpoints

### 3.1 `/health`

✅ Endpoint base per health check del servizio.

Risposta estesa (versione attuale in DEV/PAPER):

```json
{
  "ok": true,
  "service": "CryptoNakCore LOMS",
  "status": "ok",
  "environment": "paper",
  "broker_mode": "paper",
  "oms_enabled": true,
  "database_url": "sqlite:///./services/cryptonakcore/data/loms_paper.db",
  "audit_log_path": "services/cryptonakcore/data/bounce_signals_paper.jsonl",
  "price_source": "simulator",
  "price_mode": "last"
}
(Valori di environment, database_url, audit_log_path, price_source, price_mode
variano fra DEV e PAPER-SERVER.)

Usato da tools/check_health.py per:

vedere rapidamente se il servizio risponde;

leggere environment (dev / paper / in futuro live);

leggere broker_mode (ora paper);

leggere oms_enabled (kill-switch logico dell’OMS);

verificare rapidamente DB e path dell’audit log;

verificare price_source (simulator/exchange) e price_mode (last/bid/…).

3.2 /market
✅ Endpoint per esporre il prezzo simulato (o informazioni minime di mercato).
Per ora principalmente usato come test di wiring.

3.3 /orders
✅ POST /orders
Crea un Order e una Position paper con i parametri inviati
(entry_price, TP/SL).

✅ GET /orders
Lista tutti gli ordini, ordinati dal più recente.

3.4 /positions
✅ GET /positions
Lista tutte le posizioni con, tra gli altri:

id, symbol, side, qty;

exchange, market_type, account_label;

created_at, closed_at;

entry_price, tp_price, sl_price;

close_price, pnl;

auto_close_reason;

exit_strategy.

✅ POST /positions/{id}/close
Chiusura manuale completa:

prezzo letto da PriceSource (select_price(quote, settings.price_mode));

PnL calcolato;

auto_close_reason = "manual".

⬜ Filtri avanzati futuri:

per symbol;

per status;

per strategy;

per intervallo date, ecc.

3.5 /stats
✅ Endpoint GET /stats con:

Count base

total_positions, open_positions, closed_positions;

winning_trades, losing_trades;

tp_count, sl_count.

PnL

total_pnl;

avg_pnl_per_trade;

avg_pnl_win;

avg_pnl_loss.

Qualità

winrate (in % sui trade chiusi).

⬜ Estensioni future:

stats per symbol, exchange, strategy;

stats per intervallo temporale.

3.6 /signals/bounce
✅ Modello BounceSignal base:

symbol, side, price, timestamp.

✅ Esteso con meta:

exchange (es. bitget, bybit);

timeframe_min;

strategy (es. "bounce_ema10_strict");

tp_pct, sl_pct (percentuali di TP/SL).

✅ Logging audit:

log_bounce_signal(payload) in formato JSONL;

datetime serializzati con model_dump(mode="json").

✅ Creazione automatica Order + Position paper
(quando l’OMS è abilitato):

entry_price = signal.price;

qty = DEFAULT_QTY (o equivalente lato LOMS);

tp_price / sl_price calcolati da tp_pct / sl_pct per long/short;

status = "created" (order);

status = "open" (position).

✅ Normalizzazione side lato LOMS tramite _normalize_side:

gestisce "buy" / "sell", "long" / "short" (maiuscole/miste);

garantisce un valore canonico long / short per il calcolo TP/SL.

✅ Integrazione risk engine base:

usa check_risk_limits per:

totale aperte;

aperte per simbolo;

limite di notional per posizione;

risponde sempre con risk_ok e risk_reason;

se i limiti sono superati → nessun ordine/posizione, risposta 200 con
risk_ok: false.

⬜ Validazioni aggiuntive:

idempotenza (evitare doppioni);

controlli sui valori (tp/sl troppo vicini o irrealistici, ecc.);

supporto futuro per altri tipi di segnali (stop, partial close, ecc.).

4. Scheduler & Background Tasks
4.1 Loop watcher
✅ position_watcher() in app.core.scheduler:

loop infinito con asyncio.sleep(1);

apre una SessionLocal;

chiama auto_close_positions(db) ogni secondo;

chiude la sessione.

4.2 Integrazione FastAPI
✅ start_scheduler(app) registrato con @app.on_event("startup"):

agganciato in app.main dopo la creazione delle tabelle.

4.3 Parametrizzazione frequenza
⬜ Intervallo del watcher configurabile via env
(es. AUTO_CLOSE_INTERVAL_SEC).

4.4 Monitoring scheduler
⬜ Contatori / log dedicati per vedere:

ogni quanto gira;

quante posizioni chiude;

eventuali errori/salti.

5. Configurazione & Environment
5.1 Settings base
✅ Settings (app.core.config.Settings) con, tra gli altri:

ENVIRONMENT

DATABASE_URL

AUDIT_LOG_PATH

OMS_ENABLED

BROKER_MODE

MAX_OPEN_POSITIONS

MAX_OPEN_POSITIONS_PER_SYMBOL

MAX_SIZE_PER_POSITION_USDT

Real Price:

PRICE_SOURCE (simulator / exchange / in futuro replay)

PRICE_MODE (last / bid / ask / mid / mark)

JWT_SECRET (placeholder per futuri auth/JWT)

5.2 Flag OMS_ENABLED
✅ OMS_ENABLED: bool in Settings:

se True: /signals/bounce apre ordini/posizioni (se risk_ok);

se False: logga solo il segnale e non tocca il DB
(risposta con oms_enabled=false).

5.3 Profili DEV / PAPER-SERVER
✅ Concetto, documentazione e setup reale su Hetzner completati.

DEV (locale)

ENVIRONMENT=dev

BROKER_MODE=paper

DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db

AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl

PRICE_SOURCE=exchange (in dev stiamo testando PriceSource con DummyExchange)

PRICE_MODE=last

PAPER-SERVER (Hetzner accanto a RickyBot, sempre paper)

ENVIRONMENT=paper

BROKER_MODE=paper

OMS_ENABLED=true

DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db

AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl

PRICE_SOURCE:

oggi può rimanere simulator (profilo “paper puro”),

in futuro → exchange quando agganciamo davvero le API Bitget/Bybit.

PRICE_MODE=last (default attuale)

Stato attuale (server rickybot-01):

è attivo il profilo PAPER-SERVER con Shadow Mode (RickyBot → LOMS paper).

server avviato in tmux (loms-paper) con:

bash
Copia codice
cd /root/cryptonakcore-loms/services/cryptonakcore
uvicorn app.main:app --host 0.0.0.0 --port 8000
5.4 .env.sample / .env.example
✅ services/cryptonakcore/.env.sample aggiornato (2025-11-30) con:

ENVIRONMENT

DATABASE_URL

AUDIT_LOG_PATH

OMS_ENABLED

BROKER_MODE

MAX_OPEN_POSITIONS

MAX_OPEN_POSITIONS_PER_SYMBOL

MAX_SIZE_PER_POSITION_USDT

PRICE_SOURCE

PRICE_MODE

⬜ Valutare in futuro un .env.example in root o solo una sezione dedicata
nel README che punti a .env.sample come modello.

6. Integrazione RickyBot → LOMS
6.1 Payload ufficiale RickyBot → LOMS (POST /signals/bounce)
Il servizio LOMS espone:

POST /signals/bounce

Content-Type: application/json

Body: oggetto JSON conforme al modello BounceSignal.

Schema BounceSignal (JSON):

symbol (string, ✅) – coppia di trading (es. "BTCUSDT").

side (string, ✅) – "long" / "short" o "buy" / "sell".

price (number, ✅) – prezzo di ingresso (entry price paper).

timestamp (string, ✅) – ISO8601 (es. "2025-11-27T01:40:00Z").

exchange (string, ❌, default "bitget") – nome exchange.

timeframe_min (integer, ❌, default 5) – timeframe in minuti.

strategy (string, ❌, default "bounce_ema10_strict") – strategia.

tp_pct (number, ❌, default TP_PCT lato LOMS es. 4.5) – Take Profit %.

sl_pct (number, ❌, default SL_PCT lato LOMS es. 1.5) – Stop Loss %.

Calcolo TP/SL lato LOMS (dato entry_price = price):

Long

tp_price = entry_price * (1 + tp_pct/100)

sl_price = entry_price * (1 - sl_pct/100) (se sl_pct non è null)

Short

tp_price = entry_price * (1 - tp_pct/100)

sl_price = entry_price * (1 + sl_pct/100) (se sl_pct non è null)

Se tp_pct o sl_pct non sono inviati, vengono usati i default lato LOMS.

Comportamento /signals/bounce:

logga sempre il segnale su file JSONL (AUDIT_LOG_PATH);

se OMS_ENABLED=false:

non crea ordini/posizioni;

risponde con oms_enabled=false;

se OMS_ENABLED=true:

chiama il risk engine;

se risk_ok=false → blocca e risponde con risk_reason;

se risk_ok=true → crea Order + Position via BrokerAdapterPaperSim
e risponde con:

order_id, position_id

tp_price, sl_price.

6.2 Client HTTP in RickyBot
✅ Già implementato.

File: bots/rickybot/clients/loms_client.py

usa RuntimeConfig (config.loms_enabled, config.loms_base_url);

gestione:

se LOMS_ENABLED=false → log loms_skip e non chiama il servizio;

se LOMS_BASE_URL manca → log loms_skip;

chiamata HTTP POST /signals/bounce con timeout 5s;

parsing della risposta JSON.

Logging strutturato:

loms_http_error

loms_conn_error

loms_error (invalid JSON)

loms_oms_disabled

loms_risk_reject (con risk_reason)

loms_order_created (con order_id, position_id, tp_price, sl_price)

Tool di test collegati:

tools/test_notify_loms.py → usa il client per inviare un segnale finto
e mostra la risposta LOMS.

tools/test_notify_notifier_loms.py → testa la catena completa
notify_bounce_alert → LOMS.

Server Hetzner 2025-12-01:

i due tool di test eseguiti con successo:

hanno creato e chiuso posizioni paper (TP/SL)

/stats aggiornato correttamente.

6.3 Modalità paper-only
✅ Pipeline RickyBot → LOMS solo paper:

LOMS lavora su SQLite;

nessun ordine reale sull’exchange;

RickyBot invia i segnali (quando LOMS_ENABLED=true);

LOMS gestisce ordini/posizioni simulate, auto-close e stats.

6.4 Toggle lato RickyBot
✅ Implementato e attivo su Hetzner in Shadow Mode.

In RuntimeConfig:

loms_enabled

loms_base_url

In .env / .env.local di RickyBot:

LOMS_ENABLED=true/false

LOMS_BASE_URL=http://127.0.0.1:8000 (su Hetzner e in locale quando si usa LOMS paper).

Stato attuale 2025-12-01 (server):

env
Copia codice
LOMS_ENABLED=true
LOMS_BASE_URL=http://127.0.0.1:8000
I runner rickybot-bitget e rickybot-bybit in tmux sono stati riavviati
dopo questa modifica → Shadow Mode ON
(ogni alert reale va anche a LOMS paper).

Da rifinire (opzionale):

⬜ LOMS_TIMEOUT_SEC configurabile (ora timeout hardcoded a 5s).

6.5 Logging lato RickyBot
✅ Audit minimo degli esiti LOMS:

in loms_client:

log per skip,

errori HTTP/rete,

oms_enabled,

risk_ok / risk_reason,

order_id / position_id (quando creati).

in notify_bounce_alert:

log loms_alert_sent con symbol, side normalizzato, price e response.

7. Monitoring & Strumenti di Analisi
7.1 /stats come mini-dashboard
✅ /stats viene usato per verificare:

numero di trade;

qualità (winrate);

distribuzione TP/SL;

PnL totale e medio.

7.2 Script CLI per stats
✅ tools/print_stats.py creato e funzionante.

Caratteristiche:

chiama GET /stats su BASE_URL (default http://127.0.0.1:8000);

gestisce errori HTTP ([HTTP ERROR]) e di connessione ([CONNECTION ERROR])
con messaggio chiaro e hint per avviare il server
(uvicorn app.main:app --host 0.0.0.0 --port 8000);

stampa in console uno snapshot ordinato:

total_positions, open_positions, closed_positions;

winning_trades, losing_trades, tp_count, sl_count;

total_pnl;

winrate;

avg_pnl_per_trade, avg_pnl_win, avg_pnl_loss;

i float sono formattati con 4 decimali, None viene mostrato come -.

Uso tipico:

bash
Copia codice
python tools/print_stats.py
7.3 Log strutturato per chiusure
✅ Logging in auto_close_positions con dict Python
(evento position_closed).

7.4 Report PnL storico
⬜ Notebook / script per generare report più completi:

equity curve;

PnL day-by-day;

breakdown per symbol / strategy.

7.5 Script CLI per health
✅ tools/check_health.py creato e funzionante.

chiama GET /health su BASE_URL
(default http://127.0.0.1:8000);

gestisce errori HTTP / connessione con messaggi leggibili;

stampa:

HTTP status code;

Service status;

Environment (es. dev, paper);

Broker mode (es. paper);

OMS enabled;

Price source (simulator/exchange);

Price mode (last/bid/…);

JSON completo della risposta.

Uso tipico:

bash
Copia codice
python tools/check_health.py
8. Fase 2+ (Risk Engine & Live)
8.1 Risk engine completo
⬜ Regole come:

max posizioni aperte totali (parametrizzata),

max esposizione per simbolo/strategia,

max perdita giornaliera,

soft/hard kill switch.

8.2 Multi-strategy / multi-account
⬜ Estendere schema e API per gestire:

più strategie;

più “account logici” (es. paper_1, live_small, ecc.).

8.3 DB “serio” (Postgres)
⬜ Portare il backend da SQLite a Postgres
per uso prolungato / produzione.

8.4 Autenticazione / API key
⬜ Proteggere le chiamate a LOMS con API key o JWT:

almeno su /signals/bounce;

idealmente su tutte le route sensibili.

8.5 Modalità semi-live / live
⬜ Dopo lungo periodo di paper:

connettere LOMS a un adapter exchange reale;

usare gli stessi segnali, ma con ordini reali protetti dal risk engine;

separare chiaramente paper vs live
(flag tipo BROKER_MODE=paper|live).

9. Prossimi 3 step concreti (roadmap breve)
Nota: molti punti qui sono ormai completati; li teniamo come storia
ma con stato aggiornato, e lasciamo ⬜ solo sui pezzi opzionali.

9.1 Step 1 – Stabilizzare il client RickyBot → LOMS
✅ Core completato (opzionali ancora aperti)

Obiettivo: avere un client HTTP unico e pulito lato RickyBot
che chiama POST /signals/bounce in modo sicuro.

Stato:

✅ bots/rickybot/clients/loms_client.py operativo (timeout fisso 5s).

✅ Payload allineato allo schema BounceSignal
(campi: symbol, side, price, timestamp, exchange,
timeframe_min, strategy, tp_pct, sl_pct).

✅ tools/test_notify_loms.py usa il client e stampa la risposta LOMS.

✅ Su Hetzner i tool di test hanno creato posizioni paper TP/SL
confermate da /positions e /stats.

Da rifinire (opzionale):

⬜ aggiungere parametri CLI a tools/test_notify_loms.py
(--symbol, --side, --price, --tp, --sl);

⬜ rendere configurabile LOMS_TIMEOUT_SEC.

9.2 Step 2 – Integrare il client nel runner RickyBot (dev / paper)
✅ Completato in Shadow Mode su Hetzner.

notify_bounce_alert:

invia Telegram,

normalizza side,

costruisce payload, chiama send_bounce_to_loms,

logga loms_alert_sent.

RuntimeState ha config: Optional[RuntimeConfig].

setup_runtime passa settings dentro RuntimeState(config=settings).

scan_service.scan_symbol chiama notify_bounce_alert
quando c’è un alert Bounce Strict.

tools/test_notify_notifier_loms.py verifica la catena end-to-end
senza bisogno di alert reali.

Su Hetzner, con LOMS_ENABLED=true e LOMS_BASE_URL configurato,
Shadow Mode è attivo.

9.3 Step 3 – Test end-to-end (RickyBot → LOMS → /stats) con alert reali
✅ Completato per ambiente locale; su Hetzner l’infrastruttura è attiva
in Shadow Mode e sta popolando /positions e /stats
man mano che arrivano gli alert reali Tuning2.

Scenario già eseguito:

avviato LOMS (uvicorn app.main:app ...) con OMS_ENABLED=true;

lanciato RickyBot con:

LOMS_ENABLED=true;

preset di test (GAINERS_PERP 5m su Bitget, top_n piccolo).

su un alert reale Bounce Strict:

notify_bounce_alert invia il segnale al LOMS;

LOMS crea Order + Position;

il watcher auto_close_positions chiude la posizione dopo ~7s
con auto_close_reason="tp" o "sl".

Verifiche:

GET /positions → position closed con auto_close_reason corretto;

GET /stats e python tools/print_stats.py:

total_positions, open_positions, closed_positions;

winning_trades, losing_trades, tp_count, sl_count;

total_pnl, winrate, avg_pnl_per_trade, avg_pnl_win, avg_pnl_loss.

Su Hetzner (2025-12-01+):

LOMS è in paper con Shadow Mode attiva;

i tool di test hanno confermato e2e RickyBot (client) → LOMS → /stats;

la normale “farming” di RickyBot Tuning2 popola via via /positions
e /stats con alert reali di mercato.

10. Daily Ops / Shadow Mode (PAPER-SERVER)
Obiettivo: avere una routine veloce (2–5 minuti) per controllare che la coppia
RickyBot → LOMS (Shadow Mode PAPER-SERVER) stia funzionando in modo sano.

Stato: ✅ definita – da seguire manualmente quando il server è acceso.

DO-1 – Controllo rapido sessioni tmux (RickyBot)
✅ DO-1.1 – Verificare che le sessioni tmux dei bot siano attive:

bash
Copia codice
ssh root@<IP_RICKYBOT_01>
tmux ls
Devono esistere almeno:

rickybot-bitget (Bitget PERP 5m, GAINERS_PERP)

rickybot-bybit (Bybit PERP 5m, GAINERS_PERP – opzionale ma consigliata)

Nessun messaggio di errore tipo “no server running”.

DO-2 – Health check LOMS (PAPER-SERVER)
✅ DO-2.1 – Lanciare il tool di health:

bash
Copia codice
cd /root/cryptonakcore-loms
source .venv/bin/activate
python tools/check_health.py
Verificare che i campi chiave siano:

Service status : ok

Environment : paper

Broker mode : paper

OMS enabled : True

Price source e Price mode coerenti con il profilo desiderato
(es. simulator/exchange, last).

Se uno di questi non è come previsto → segnare il problema e NON
fare modifiche di fretta a .env; si interviene a mente fresca.

DO-3 – Statistiche paper trading (/stats)
✅ DO-3.1 – Controllare le statistiche aggregate:

bash
Copia codice
cd /root/cryptonakcore-loms
source .venv/bin/activate
python tools/print_stats.py
# oppure
curl -s http://127.0.0.1:8000/stats/ | python -m json.tool
Controllare che:

total_positions non rimanga fermo a 0 per giorni;

winrate sia in un range realistico (non 0% fisso, non 100% fisso per settimane);

tp_count / sl_count aumentino nel tempo;

nessun valore “rotto” (NaN, inf, ecc.).

DO-4 – Posizioni aperte/chiuse (/positions)
✅ DO-4.1 – Dare un occhio alle posizioni:

bash
Copia codice
cd /root/cryptonakcore-loms
source .venv/bin/activate
curl -s http://127.0.0.1:8000/positions/ | python -m json.tool
Cosa considerare “sano”:

pochissime posizioni status: "open" (con auto-close a ~7s spesso 0);

molte posizioni status: "closed" con closed_at recente;

nessuna posizione “zombie” aperta da ore/giorni senza motivo.

Se compaiono zombie → annotare il caso per debugging mirato,
non intervenire a caldo nella routine.

DO-5 – Stato runner RickyBot + heartbeat Telegram
✅ DO-5.1 – Verifica rapida del runner:

bash
Copia codice
cd /root/RickyBot
source .venv/bin/activate
python tools/runner_status.py --max-loops 50 --show-alerts 10
Controllare che:

l’ultimo loop sia recente (coerente con INTERVAL_MIN / heartbeat);

watchlist size > 0;

ci siano near-miss e qualche alert nelle ultime ore (non completamente piatto).

✅ DO-5.2 – Dare un’occhiata alla chat Telegram del bot:

heartbeat [BITGET] / [BYBIT] presenti e recenti;

nessun flood di errori (stack trace ripetuti, errori HTTP verso il LOMS);

ogni tanto qualche alert vero (non solo heartbeat).

DO-6 – Regola d’oro operativa
⬜ DO-6.1 – Non modificare .env / .env.local (RickyBot o LOMS)
sul server quando sei stanco o di fretta.

Ogni modifica di tuning:

si testa prima in locale;

si verifica con runtime_config_inspector.py / tools/check_health.py;

solo dopo si porta in .env.local su Hetzner e si riavviano le sessioni tmux.

Questa sezione definisce il profilo “Daily Ops / Shadow Mode” che deve essere
completato prima di qualsiasi ragionamento su tuning, cambi logica
o passaggi verso il semi-live da 100€.