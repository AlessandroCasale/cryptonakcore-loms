# CryptoNakCore LOMS – Jira Checklist MASTER

Versione aggiornata al 2025-11-27  
(Stato: dopo integrazione `notify_bounce_alert` → LOMS + `MarketSimulator` v2 + **primo alert reale end-to-end**)

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
  - in futuro modalità **semi-live**.

---

## 1. Schema DB & Modelli ORM

### 1.1 Base SQLAlchemy unica

✅ Fatto

- `Base` e `SessionLocal` definiti in `app.db.session`,
- `app.db.models` importa `Base` da lì,
- DB ricreato con schema coerente.

### 1.2 Modello Order

✅ Modello `Order` semplice con:

- `id`, `symbol`, `side`, `qty`, `order_type`
- `tp_price`, `sl_price`
- `status`, `created_at`

### 1.3 Modello Position

✅ Modello `Position` allineato a `auto_close_positions` e chiusura manuale:

- `symbol`, `side`, `qty`, `entry_price`
- `tp_price`, `sl_price`
- `status` (`open` / `closed`)
- `created_at`, `closed_at`
- `close_price`, `pnl`
- `auto_close_reason` (`tp`, `sl`, `manual`, …)

### 1.4 Migrazioni DB (Alembic, ecc.)

⬜ Introdurre un flusso di migrazioni strutturato (Alembic) quando lo schema diventerà più stabile.

---

## 2. Core OMS Paper

### 2.1 Market simulator

✅ `MarketSimulator.get_price()` (v2):

- prezzo fittizio base `100.0`,
- variazione random ±10.0,
- questo rende realisticamente raggiungibili TP/SL del tipo 4.5% / 1.5% in pochi tick (es. `tp=104.5`, `sl=98.5`).

### 2.2 `auto_close_positions`

✅ Implementato in `app.services.oms`:

- legge tutte le posizioni `open`,
- ignora quelle con età `< 7s` (gate in secondi),
- usa `MarketSimulator` per il prezzo corrente,
- converte `tp_price` / `sl_price` a `float`,
- normalizza `side` (`long` / `short`),

logica TP/SL:

- long: TP se `price >= tp`, SL se `price <= sl`
- short: TP se `price <= tp`, SL se `price >= sl`

chiusura posizione:

- `status = "closed"`,
- `closed_at`, `close_price`,
- calcolo `pnl` long/short,
- `auto_close_reason = "tp"` o `"sl"`,
- commit sul DB e log strutturato `position_closed`.

### 2.3 Chiusura manuale posizione

✅ Endpoint `POST /positions/{id}/close`:

- cerca la `Position` per `id`,
- se non esiste → 404,
- se già `closed` → ritorna la posizione così com’è,
- altrimenti:
  - legge il prezzo dal `MarketSimulator`,
  - imposta `status = "closed"`,
  - valorizza `closed_at`, `close_price`,
  - calcola `pnl`,
  - `auto_close_reason = "manual"`,
  - commit + refresh.

### 2.4 Risk engine base

🟡 Parzialmente completo

✅ Esiste un controllo base che può bloccare l’apertura di nuove posizioni con:

- risposta tipo  
  `risk_ok: false`,  
  `risk_reason: "max_total_open_reached (total=1, limit=1)"`.

✅ `/signals/bounce` include sempre `risk_ok` e `risk_reason` nella risposta.

✅ Lato RickyBot, i blocchi risk vengono loggati come `event: "loms_risk_reject"`.

Da completare:

⬜ leggere i limiti (es. `MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`) da settings/env,  
⬜ introdurre davvero il limite per simbolo (`max_symbol_open_reached`) se non ancora presente,  
⬜ log dedicati `risk_block` più dettagliati (scope totale / per simbolo).

---

## 3. API REST – Endpoints

### 3.1 `/health`

✅ Endpoint base per health check del servizio.

---

### 3.2 `/market`

✅ Endpoint per esporre il prezzo simulato (o informazioni minime di mercato).

---

### 3.3 `/orders`

✅ `POST /orders`  
Crea un `Order` **e** una `Position` paper con i parametri inviati (`entry_price`, TP/SL).

✅ `GET /orders`  
Lista tutti gli ordini, ordinati dal più recente.

---

### 3.4 `/positions`

✅ `GET /positions`  
Lista tutte le posizioni con:

- `created_at`, `closed_at`
- `close_price`, `pnl`
- `auto_close_reason`

✅ `POST /positions/{id}/close`  
Chiusura manuale completa:

- prezzo simulato da `MarketSimulator`,
- `pnl` calcolato,
- `auto_close_reason = "manual"`.

⬜ Filtri avanzati futuri:

- per `symbol`,
- per `status`,
- per `strategy`,
- per intervallo date, ecc.

---

### 3.5 `/stats`

✅ Endpoint `GET /stats` con:

**Count base**

- `total_positions`, `open_positions`, `closed_positions`
- `winning_trades`, `losing_trades`
- `tp_count`, `sl_count`

**PnL**

- `total_pnl`
- `avg_pnl_per_trade`
- `avg_pnl_win`
- `avg_pnl_loss`

**Qualità**

- `winrate` (in % sui trade chiusi)

⬜ Estensioni future:

- stats per `symbol`, `exchange`, `strategy`,
- stats per intervallo temporale.

---

### 3.6 `/signals/bounce`

✅ Modello `BounceSignal` base:

- `symbol`, `side`, `price`, `timestamp`.

✅ Esteso con meta:

- `exchange` (es. `bitget`, `bybit`),
- `timeframe_min`,
- `strategy` (es. `"bounce_ema10_strict"`),
- `tp_pct`, `sl_pct` (percentuali di TP/SL).

✅ Logging audit:

- `log_bounce_signal(payload)` in formato JSONL,
- datetime serializzati con `model_dump(mode="json")`.

✅ Creazione automatica `Order + Position` paper (quando l’OMS è abilitato):

- `entry_price = signal.price`,
- `qty = DEFAULT_QTY` (o equivalente lato LOMS),
- `tp_price` / `sl_price` calcolati da `tp_pct` / `sl_pct` per long/short,
- `status = "created"` (order),
- `status = "open"` (position).

✅ Normalizzazione `side` lato LOMS tramite `_normalize_side`:

- gestisce `"buy"` / `"sell"`, `"long"` / `"short"` (maiuscole/miste),
- garantisce un valore canonico `long` / `short` per il calcolo TP/SL.

✅ Integrazione risk engine base:

- risponde sempre con `risk_ok` e `risk_reason`,
- se i limiti sono superati → nessun ordine/posizione, risposta 200 con `risk_ok: false`.

✅ Risposte tipiche:

- se `OMS_ENABLED = true` e passano i controlli →  
  `{ "received": true, "oms_enabled": true, "risk_ok": true, "order_id": ..., "position_id": ..., "tp_price": ..., "sl_price": ... }`
- se `OMS_ENABLED = false` →  
  `{ "received": true, "oms_enabled": false, "risk_ok": false, "reason": "OMS disabled via config" }`

⬜ Validazioni aggiuntive:

- idempotenza (evitare doppioni),
- controlli sui valori (tp/sl troppo vicini o irrealistici, ecc.),
- supporto futuro per altri tipi di segnali (stop, partial close, ecc.).

---

## 4. Scheduler & Background Tasks

### 4.1 Loop watcher

✅ `position_watcher()` in `app.core.scheduler`:

- loop infinito con `asyncio.sleep(1)`,
- apre una `SessionLocal`,
- chiama `auto_close_positions(db)` ogni secondo,
- chiude la sessione.

### 4.2 Integrazione FastAPI

✅ `start_scheduler(app)` registrato con `@app.on_event("startup")`:

- agganciato in `app.main` dopo la creazione delle tabelle.

### 4.3 Parametrizzazione frequenza

⬜ Intervallo del watcher configurabile via env (es. `AUTO_CLOSE_INTERVAL_SEC`).

### 4.4 Monitoring scheduler

⬜ Contatori / log dedicati per vedere:

- ogni quanto gira,
- quante posizioni chiude,
- eventuali errori/salti.

---

## 5. Configurazione & Environment

### 5.1 Settings base

✅ `Settings` (`app.core.config`) con, tra gli altri:

- `DATABASE_URL`
- `JWT_SECRET`
- `AUDIT_LOG_PATH`
- `OMS_ENABLED`

### 5.2 Flag `OMS_ENABLED`

✅ `OMS_ENABLED: bool` in `Settings`:

- se `True`: `/signals/bounce` apre ordini/posizioni (se `risk_ok`),
- se `False`: logga solo il segnale e non tocca il DB (risposta con `oms_enabled=false`).

### 5.3 Profili dev/prod

⬜ Config separata dev/prod:

- DB diversi,
- log path diversi,
- valori diversi di `OMS_ENABLED` e parametri core.

### 5.4 `.env.example`

⬜ File di esempio documentato per configurazione rapida.

---

## 6. Integrazione RickyBot → LOMS

### 6.1 Payload ufficiale RickyBot → LOMS (`POST /signals/bounce`)

Il servizio LOMS espone:

- `POST /signals/bounce`
- `Content-Type: application/json`
- Body: oggetto JSON conforme al modello `BounceSignal`.

**Schema `BounceSignal` (JSON):**

- `symbol` (string, ✅) – coppia di trading (es. `"BTCUSDT"`).
- `side` (string, ✅) – `"long"` / `"short"` o `"buy"` / `"sell"`.
- `price` (number, ✅) – prezzo di ingresso (entry price paper).
- `timestamp` (string, ✅) – ISO8601 (es. `"2025-11-27T01:40:00Z"`).
- `exchange` (string, ❌, default `"bitget"`) – nome exchange (`"bitget"`, `"bybit"`, …).
- `timeframe_min` (integer, ❌, default `5`) – timeframe in minuti (1, 3, 5, 15, …).
- `strategy` (string, ❌, default `"bounce_ema10_strict"`) – strategia che ha generato il segnale.
- `tp_pct` (number, ❌, default 4.5 lato LOMS) – Take Profit % rispetto a `price`.
- `sl_pct` (number, ❌, default 1.5 lato LOMS) – Stop Loss % rispetto a `price`.

**Calcolo TP/SL lato LOMS (dato `entry_price = price`):**

- Long:
  - `tp_price = entry_price * (1 + tp_pct/100)`
  - `sl_price = entry_price * (1 - sl_pct/100)` (se `sl_pct` non è null)
- Short:
  - `tp_price = entry_price * (1 - tp_pct/100)`
  - `sl_price = entry_price * (1 + sl_pct/100)` (se `sl_pct` non è null)

Se `tp_pct` o `sl_pct` non sono inviati, vengono usati i default lato LOMS (es. 4.5 / 1.5).

**Comportamento `/signals/bounce`:**

- logga sempre il segnale su file JSONL (`AUDIT_LOG_PATH`),
- se `OMS_ENABLED=false`:
  - non crea ordini/posizioni,
  - risponde con `oms_enabled=false`,
- se `OMS_ENABLED=true`:
  - chiama il risk engine,
  - se `risk_ok=false` → blocca e risponde con `risk_reason`,
  - se `risk_ok=true` → crea `Order + Position` e risponde con `order_id`, `position_id`, `tp_price`, `sl_price`.

---

### 6.2 Client HTTP in RickyBot

✅ Già implementato

- File: `bots/rickybot/clients/loms_client.py`
- Usa `RuntimeConfig` (`config.loms_enabled`, `config.loms_base_url`).

Gestione:

- se `LOMS_ENABLED=false` → log `loms_skip` e non chiama il servizio,
- se `LOMS_BASE_URL` manca → log `loms_skip`,
- chiamata HTTP `POST /signals/bounce` con timeout 5s,
- parsing della risposta JSON.

Logging strutturato:

- `loms_http_error`
- `loms_conn_error`
- `loms_error` (invalid JSON)
- `loms_oms_disabled`
- `loms_risk_reject` (con `risk_reason`)
- `loms_order_created` (con `order_id`, `position_id`, `tp_price`, `sl_price`)

Tool di test collegato:

- `tools/test_notify_loms.py` → usa il client per inviare un segnale finto e mostra la risposta LOMS.

---

### 6.3 Modalità paper-only

✅ Pipeline RickyBot → LOMS solo paper:

- LOMS lavora su SQLite,
- nessun ordine reale sull’exchange,
- RickyBot invia i segnali (quando `LOMS_ENABLED=true`),
- LOMS gestisce ordini/posizioni simulate, auto-close e stats.

---

### 6.4 Toggle lato RickyBot

🟡 In gran parte fatto

In `RuntimeConfig` esistono:

- `loms_enabled`
- `loms_base_url`

In `.env` / `.env.local` di RickyBot:

- `LOMS_ENABLED=true/false`
- `LOMS_BASE_URL=http://127.0.0.1:8000` (per i test locali)

Da rifinire (opzionale):

⬜ eventuale `LOMS_TIMEOUT_SEC` configurabile (ora timeout è hardcoded a 5s),  
⬜ documentare in modo chiaro la distinzione dev/prod (es. `LOMS_ENABLED=false` su Hetzner, `true` in locale).

---

### 6.5 Logging lato RickyBot

✅ Audit minimo degli esiti LOMS:

- in `loms_client`:
  - log per skip,
  - errori HTTP/rete,
  - `oms_enabled`,
  - `risk_ok` / `risk_reason`,
  - `order_id` / `position_id` (quando creati).
- in `notify_bounce_alert`:
  - log `loms_alert_sent` con `symbol`, `side` normalizzato, `price` e `response`.

---

## 7. Monitoring & Strumenti di Analisi

### 7.1 `/stats` come mini-dashboard

✅ `/stats` viene usato per verificare:

- numero di trade,
- qualità (winrate),
- distribuzione TP/SL,
- PnL totale e medio.

### 7.2 Script CLI per stats

✅ `tools/print_stats.py` creato e funzionante.

Caratteristiche:

- chiama `GET /stats` su `BASE_URL` (default `http://127.0.0.1:8000`);
- gestisce errori HTTP (`[HTTP ERROR]`) e di connessione (`[CONNECTION ERROR]`)
  con messaggio chiaro e hint per avviare il server (`uvicorn app.main:app --reload`);
- stampa in console uno snapshot ordinato:
  - `total_positions`, `open_positions`, `closed_positions`
  - `winning_trades`, `losing_trades`, `tp_count`, `sl_count`
  - `total_pnl`
  - `winrate`
  - `avg_pnl_per_trade`, `avg_pnl_win`, `avg_pnl_loss`
- i float sono formattati con 4 decimali, `None` viene mostrato come `-`.

Uso tipico con LOMS in locale:

```bash
python tools/print_stats.py
7.3 Log strutturato per chiusure
✅ Logging in auto_close_positions con dict Python (evento position_closed).

7.4 Report PnL storico
⬜ Notebook / script per generare report più completi:

equity curve,

PnL day-by-day,

breakdown per symbol/strategy.

8. Fase 2+ (Risk Engine & Live)
8.1 Risk engine completo
⬜ Regole come:

max posizioni aperte totali (parametrizzata),

max esposizione per simbolo/strategia,

max perdita giornaliera,

soft/hard kill switch.

8.2 Multi-strategy / multi-account
⬜ Estendere schema e API per gestire:

più strategie,

più “account logici” (es. paper_1, live_small, ecc.).

8.3 DB “serio” (Postgres)
⬜ Portare il backend da SQLite a Postgres per uso prolungato / produzione.

8.4 Autenticazione / API key
⬜ Proteggere le chiamate a LOMS con API key o JWT:

almeno su /signals/bounce,

idealmente su tutte le route sensibili.

8.5 Modalità semi-live / live
⬜ Dopo lungo periodo di paper:

connettere LOMS a un adapter exchange reale,

usare gli stessi segnali, ma con ordini reali protetti dal risk engine,

separare chiaramente paper vs live (flag tipo BROKER_MODE=paper|live).

9. Prossimi 3 step concreti (roadmap breve)
9.1 Step 1 – Stabilizzare il client RickyBot → LOMS
🟡 Quasi completo

Obiettivo: avere un client HTTP unico e pulito lato RickyBot che chiama POST /signals/bounce in modo sicuro.

Stato:

✅ bots/rickybot/clients/loms_client.py già operativo (con timeout fisso 5s).
✅ Payload allineato allo schema BounceSignal (campi: symbol, side, price, timestamp, exchange, timeframe_min, strategy, tp_pct, sl_pct).
✅ tools/test_notify_loms.py usa il client e stampa la risposta LOMS.

Da rifinire (opzionale):

⬜ aggiungere parametri CLI a tools/test_notify_loms.py (--symbol, --side, --price, --tp, --sl),
⬜ rendere configurabile LOMS_TIMEOUT_SEC.

9.2 Step 2 – Integrare il client nel runner RickyBot (dev / paper)
✅ Integrazione logica completata

Obiettivo: fare in modo che, in ambiente dev, ogni alert Bounce Strict possa essere inviato anche al LOMS in modalità paper.

Stato attuale:

✅ Esiste notify_bounce_alert nel runner:

manda Telegram,

normalizza side,

costruisce il payload e chiama send_bounce_to_loms,

logga loms_alert_sent.

✅ RuntimeState ha il campo config: Optional[RuntimeConfig].
✅ setup_runtime passa settings dentro RuntimeState(config=settings).
✅ scanner.run_scanner_tick legge runtime.config e lo passa a run_scan_loop_once.
✅ scan_service.scan_symbol chiama notify_bounce_alert (Telegram + LOMS) quando runtime_config non è None e c’è un alert Bounce Strict; altrimenti usa il fallback send_telegram.
✅ tools/test_notify_notifier_loms.py verifica questa catena end-to-end senza bisogno di alert reali.

Da fare (organizzazione dev/prod):

⬜ tenere la feature attiva solo in dev all’inizio:

LOMS_ENABLED=true in locale,

LOMS_ENABLED=false su Hetzner (documentato in README / runbook).

9.3 Step 3 – Test end-to-end locale (RickyBot → LOMS → /stats) con alert reali
✅ Completato (primo test con alert reale KGENUSDT)

Obiettivo: validare che tutta la catena funzioni in locale con il runner reale, non solo con gli script di test.

Scenario eseguito:

Avviato LOMS in locale con:

bash
Copia codice
uvicorn app.main:app --reload
# OMS_ENABLED=true
Lanciato RickyBot in locale con:

LOMS_ENABLED=true,

preset di test (GAINERS_PERP 5m su Bitget, top_n piccolo).

Verificato che, su un alert reale Bounce Strict (es. KGENUSDT short):

il runner chiama notify_bounce_alert,

notify_bounce_alert invia il segnale al LOMS,

LOMS crea Order + Position (con order_id e position_id),

il watcher auto_close_positions chiude la posizione dopo ~7s con auto_close_reason="tp" o "sl".

Risultati controllati tramite:

GET /positions (position con status="closed" e auto_close_reason="sl"),

GET /stats e python tools/print_stats.py per:

total_positions, open_positions, closed_positions,

winning_trades, losing_trades, tp_count, sl_count,

total_pnl, winrate, avg_pnl_per_trade, avg_pnl_win, avg_pnl_loss