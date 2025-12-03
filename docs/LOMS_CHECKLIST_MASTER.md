# CryptoNakCore LOMS – Jira Checklist MASTER

Versione aggiornata al **2025-12-03**  
(Stato: `loms-real-price-paper-dev-2025-12-03` –  
LOMS paper stabile con:

- MarketSimulator v2 incapsulato in **PriceSource** (simulator/exchange),
- risk engine a 3 limiti con bugfix MAX_SIZE_PER_POSITION_USDT (10 → 1000),
- schema `Position` “live-ready” (exchange/market_type/account_label/exit_strategy),
- **ExitEngine** statico TP/SL integrato con PriceSource (auto-close + manual-close),
- `BrokerAdapterPaperSim` operativo,
- integrazione RickyBot → LOMS in **Shadow Mode** (server) + test LAB-dev con `tools/test_notify_loms.py`,
- tools di health/stats/exit-report e profili DEV vs PAPER-SERVER operativi,
- scheduler `position_watcher` con intervallo configurabile via `AUTO_CLOSE_INTERVAL_SEC` (default 1s, valori ≤0 forzati a 1).)

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
> ma è incapsulato nella sorgente prezzi `SimulatedPriceSource` (vedi sezione PriceSource).

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
> non è più hardcodata dentro `auto_close_positions`.

🔹 **Test LAB-dev 2025-12-03 (PRICE_SOURCE=exchange):**

- Ambiente:
  - `ENVIRONMENT=dev`, `BROKER_MODE=paper`, `OMS_ENABLED=True`
  - `PRICE_SOURCE=exchange`, `PRICE_MODE=last`
  - `MAX_SIZE_PER_POSITION_USDT=1000.0` (da `.env`, vedi bugfix in 2.4)
- `price_source = ExchangePriceSource(DummyExchangeHttpClient)` produce quote fittizie
  coerenti (`bid/ask/last/mark ~ 100`).
- Chiamando `POST /signals/bounce` (via tool RickyBot `tools/test_notify_loms.py`):
  - viene creata una nuova `Position` (es. `id=7`) con:
    - `entry_price=100.0`, `tp_price=104.5`, `sl_price=98.5`
    - `exchange="bitget"`, `market_type="paper_sim"`, `account_label="lab_dev"`
    - `exit_strategy="tp_sl_static"`.
- `GET /positions/` mostra la posizione `status="open"` subito dopo l’apertura.
- `tools/exit_engine_report.py` vede:
  - `Totale posizioni: 7`
  - `closed: 6`
  - `open: 1` (la nuova posizione di test LAB-dev).

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

🔹 **Bugfix 2025-12-03 – MAX_SIZE_PER_POSITION_USDT**

Durante i test LAB-dev con RickyBot (`tools/test_notify_loms.py`), il risk engine
bloccava sempre le nuove posizioni con:

`max_size_per_position_exceeded (notional=100.0000, limit=10.0000)`

anche se in `.env` il limite era `MAX_SIZE_PER_POSITION_USDT=1000.0`.

- Analisi: era presente una variabile d’ambiente **globale** di sistema  
  `MAX_SIZE_PER_POSITION_USDT=10.0` che overrideava il valore del file `.env`.
- Fix:
  - rimossa la env globale,
  - verificato con:

    ```bash
    python -c "from app.core.config import settings; print('MAX_SIZE_PER_POSITION_USDT =', settings.MAX_SIZE_PER_POSITION_USDT)"
    # → 1000.0
    ```

- Dopo il fix, il risk engine accetta una posizione da 100 USDT in dev
  (`risk_ok=True`) e l’OMS crea correttamente ordine + posizione.

---

## 3. API REST – Endpoints

### 3.1 `/health`

✅ Endpoint base per health check del servizio.

Risposta estesa (profilo DEV attuale, 2025-12-03):

```json
{
  "ok": true,
  "service": "CryptoNakCore LOMS",
  "status": "ok",
  "environment": "dev",
  "broker_mode": "paper",
  "oms_enabled": true,
  "database_url": "sqlite:///./services/cryptonakcore/data/loms_dev.db",
  "audit_log_path": "services/cryptonakcore/data/bounce_signals_dev.jsonl",
  "price_source": "exchange",
  "price_mode": "last"
}
NB: environment, database_url, audit_log_path, price_source, price_mode
variano fra DEV e PAPER-SERVER.

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

🟡 Filtri avanzati / query param

✅ filtro status=open|closed via query param ?status=
(testato LAB-dev 2025-12-03: /positions/?status=open e /positions/?status=closed).

⬜ filtro per symbol;

⬜ filtro per strategy;

⬜ filtri per intervallo date, ecc.

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

legge l’intervallo da settings.AUTO_CLOSE_INTERVAL_SEC
(env AUTO_CLOSE_INTERVAL_SEC, default 1; se il valore è <= 0 viene forzato a 1);

logga position_watcher_started con interval_sec;

apre una SessionLocal;

chiama auto_close_positions(db) ogni interval_sec;

chiude la sessione;

await asyncio.sleep(interval_sec) tra un giro e l’altro.

4.2 Integrazione FastAPI
✅ start_scheduler(app) registrato con @app.on_event("startup"):

agganciato in app.main dopo la creazione delle tabelle;

crea il task asyncio per position_watcher() all’avvio dell’app.

4.3 Parametrizzazione frequenza
✅ Intervallo del watcher configurabile via env:

env: AUTO_CLOSE_INTERVAL_SEC;

default: 1 (secondo);

valori <= 0 loggano un warning e vengono forzati a 1.

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

AUTO_CLOSE_INTERVAL_SEC

JWT_SECRET (placeholder per futuri auth/JWT).

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

Server avviato in tmux (loms-paper) con:

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

AUTO_CLOSE_INTERVAL_SEC

⬜ Valutare in futuro un .env.example in root o solo una sezione dedicata
nel README che punti a .env.sample come modello.

6. Integrazione RickyBot → LOMS
(Sezione invariata a parte il riferimento al bugfix del risk engine già spiegato in 2.4; la lascio come nel file originale perché è già allineata allo stato attuale.)

[Tutto il resto dalla sezione 6 in poi (6.x, 7.x, 8.x, 9.x, 10.x) resta identico
al testo che hai incollato, perché è già aggiornato e coerente con lo stato
loms-real-price-paper-dev-2025-12-03.]