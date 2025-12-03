RickyBot + LOMS – Real Price & Smart Exit Roadmap  
(versione Jira-style – v0.6 – 2025-12-03)

**Stato attuale (2025-12-03 – rickybot-loms-v1.0 + loms-real-price-paper-dev-2025-12-03):**

- ✅ **Real Price Engine v1** (`PriceSource` + `PriceMode`) integrato in LOMS (DEV e PAPER-SERVER).
- ✅ **ExitEngine statico** (`StaticTpSlPolicy`) usato da `auto_close_positions` e dalla chiusura manuale.
- ✅ **BrokerAdapterPaperSim** usato da `/signals/bounce` per creare Order + Position paper.
- ✅ **Risk engine a 3 limiti** operativo, con bug `MAX_SIZE_PER_POSITION_USDT` risolto
  (usa il valore da `.env` e non da variabili globali sporche).
- ✅ **Shadow Mode LIVE**: RickyBot Tuning2 → LOMS PAPER-SERVER (Hetzner) con TP/SL paper e stats reali.
- 🟡 PriceSource `exchange` in DEV usa ancora `DummyExchangeHttpClient` (stub, niente API reali).
- ⬜ Nessun ordine reale ancora: niente broker live, niente modalità semi-live 100€ attiva.

Legenda stato:  
✅ completato  
🟡 in corso / parzialmente completo  
⬜ da fare / idea futura  

---

## 0. Macro-obiettivo & principi

### 0.1 Obiettivo finale

🟡 Portare RickyBot + LOMS a:

- usare **prezzi reali di mercato** per PnL e TP/SL,
- supportare un profilo **semi-live 100€** su exchange reale con risk engine attivo,
- integrare un motore di uscita **smart (ExitPolicy)** sopra il TP/SL fisso,
- mantenere tre modalità operative chiare:

  - **LAB**: paper + simulator  
  - **SHADOW**: paper + prezzi reali  
  - **SEMI-LIVE**: ordini reali con capitale limitato  

### 0.2 Principi architetturali (no rework)

⬜ Nessuna logica di trading “seria” nei tool:
tutto deve passare da RickyBot (pattern/segnali) + LOMS (OMS/esecuzione).

✅ Un’unica astrazione per i prezzi in LOMS (**PriceSource / PriceMode / PriceQuote**).

🟡 Un’unica astrazione per l’esecuzione ordini (**BrokerAdapter**) – paper già fatto.

✅ Schema `Position` pensato per convivere con:

- paper puro,
- paper con prezzi reali,
- live su exchange (campi exchange/market_type/account_label/exit_strategy/externals).

✅ Ogni step lascia il sistema in uno stato eseguibile (mai “mezzo rotto”).

---

## 1. Real Price Engine (PriceSource / MarketDataService)

### 1.1 Definizione interfaccia prezzi

✅ Definire l’interfaccia concettuale **PriceSource** (in codice + docs), con:

Struttura **PriceQuote** con almeno:

- `symbol`
- `ts` (timestamp)
- `bid`, `ask`, `last`, `mark` (opzionali)
- `source` (es. `"simulator"`, `"bybit"`, `"bitget"`)
- `mode` (es. `"last"`, `"bid"`, `"ask"`, `"mid"`, `"mark"`)

Metodo base:

- `get_quote(symbol) -> PriceQuote`

Funzione helper:

- `select_price(quote, mode)` per estrarre il prezzo giusto (last/bid/ask/mid/mark).

LOMS ora consuma un `PriceQuote` e sceglie il campo corretto tramite `PRICE_MODE`.

✅ Modulo di appartenenza: `app.services.pricing`  
(definiti `PriceSourceType`, `PriceMode`, `PriceQuote`, `PriceSource`, `select_price`, `SimulatedPriceSource`).

⬜ Definire in modo definitivo il **contratto d’errore** per tutte le sorgenti
(eccezioni specifiche, log strutturati, comportamento in caso di timeout / HTTP error ecc.).

---

### 1.2 Implementazioni previste

#### ✅ PriceSourceSimulator

Incapsula l’attuale `MarketSimulator` (random ±10), usato per:

- dev offline,
- test puramente tecnici,
- LAB mode attuale (paper puro).

#### 🟡 PriceSourceExchange

✅ Scheletro definito:

- `ExchangeClient` (Protocol) ed enum `ExchangeType` in `exchange_client.py`
- `ExchangePriceSource` che prende un `ExchangeClient` e lo trasforma in `PriceQuote`
- `DummyExchangeHttpClient` usato per test end-to-end
- tool `tools/test_exchange_price_source.py` con `DummyExchangeClient` che verifica:
  - `bid/ask/last/mark`
  - `select_price` per tutti i `PriceMode`

⬜ Da fare:

- implementare davvero i client HTTP (`BitgetClient`, `BybitClient`) con le API vere,
- adattare le response reali → `PriceQuote`,
- gestione errori/retry/rate-limit.

#### ⬜ PriceSourceReplay (fase successiva)

- `ReplayPriceSource` che usa dati storici (CSV, snapshot, klines) per simulare feed di prezzo,
- fondamentale per testare ExitPolicy offline.

---

### 1.3 Integrazione PriceSource con LOMS

✅ Introdurre i flag in `Settings`:

- `PRICE_SOURCE = simulator|exchange|replay` (mappato in `PriceSourceType`)
- `PRICE_MODE   = last|bid|ask|mid|mark` (mappato in `PriceMode`)

con alias `settings.price_source`, `settings.price_mode` usati dal codice.

✅ Integrare in `app.services.oms`:

`_get_price_source()`:

- se `PRICE_SOURCE=simulator` → `SimulatedPriceSource(MarketSimulator)`
- se `PRICE_SOURCE=exchange` → `ExchangePriceSource(get_default_exchange_client())`
  (per ora `get_default_exchange_client()` → `DummyExchangeHttpClient`)
- per valori non supportati: warning + fallback a `SimulatedPriceSource`.

`auto_close_positions(db)`:

- legge le posizioni `status='open'`,
- per ciascuna:
  - rispetta la guardia `age_sec < 7` secondi,
  - ottiene `quote = price_source.get_quote(symbol)`,
  - `current_price = select_price(quote, settings.price_mode)`,
  - costruisce `ExitContext(price, quote, now)` e lo passa a `StaticTpSlPolicy`,
  - applica le `ExitAction` di tipo `CLOSE_POSITION` aggiornando `Position`
    (`status/closed_at/close_price/pnl/auto_close_reason`),
  - fa `db.commit()` e logga `position_closed`.

✅ `POST /positions/{id}/close`:

- ora usa **lo stesso PriceSource** di `auto_close_positions`  
  (niente più `MarketSimulator` diretto),
- legge `quote` via `_get_price_source()` + `select_price`,
- calcola PnL long/short,
- imposta `auto_close_reason="manual"`.

✅ Garantire:

- `PRICE_SOURCE=simulator` → comportamento LAB attuale (paper puro) invariato,
- `PRICE_SOURCE=exchange` → comportamento LAB-dev con `DummyExchangeHttpClient`,
- fallback sicuro: sorgente non supportata → warning + `SimulatedPriceSource`.

> **Nota stato (2025-12-03):**  
> - DEV: `PRICE_SOURCE=exchange`, `PRICE_MODE=last` con DummyExchange → test LAB-dev ok.  
> - PAPER-SERVER: `PRICE_SOURCE=simulator`, `PRICE_MODE=last` → Shadow Mode su Hetzner usa ancora simulator per i prezzi ma tutta la pipeline Real Price / ExitEngine è operativa.

---

## 2. Semi-live 100€ (Fase 1 – TP/SL semplici)

### 2.1 Preparazione schema dati “live-ready”

✅ In `Position`:

**Campi “profilo”:**

- `exchange` (es. `"bitget"`, `"bybit"`)
- `market_type` / `instrument_type` (es. `"paper_sim"` in LAB; in futuro `"linear_perp"`)
- `account_label` (es. `"lab_dev"`, in futuro `"semi_live_100eur"`)

**Campi legati all’exchange reale:**

- `external_order_id` (ID ordine sull’exchange, se live)
- `external_position_ref` (se necessario per l’exchange)

✅ Chiarita semantica di `created_at` come **entry_timestamp** della posizione.

✅ Compatibilità completa con paper/shadow/live  
(nuovi campi nullable, vecchie righe tornano con `null`, verificato via `GET /positions/`).

---

### 2.2 BrokerAdapter – separare logica da esecuzione

🟡 Stato: paper adapter pronto, exchange adapter ancora da fare.

✅ Definizione concreta **paper**:

- introdotto `NewPositionParams` (o equivalente comando interno) con:
  - `symbol`, `side`, `qty`, `entry_price`,
  - `exchange`, `market_type`, `account_label`,
  - `tp_price`, `sl_price`,
  - `exit_strategy` (es. `"tp_sl_static"`).

- creato **`BrokerAdapterPaperSim`** con metodo:
  - `open_position(db, params) -> BrokerOpenResult`  
    che crea una `Position` in DB con:
    - `exchange`, `market_type`, `account_label`,
    - `entry_price`, `tp_price`, `sl_price`,
    - `exit_strategy="tp_sl_static"`.

- tool di test: `tools/test_broker_adapter_papersim.py`  
  che:
  - crea il DB se manca (`Base.metadata.create_all(bind=engine)`),
  - apre una posizione di prova,
  - stampa/controlla i campi principali.

> **Stato 2025-12-03:**  
> `BrokerAdapterPaperSim` è usato in produzione paper da `/signals/bounce`
> (lato DEV e PAPER-SERVER, via Shadow Mode) per creare Order + Position paper.

⬜ Estendere l’interfaccia BrokerAdapter (design completo):

- `create_order(params) -> BrokerOrderResult` (per modalità SHADOW/LIVE),
- `close_position(position) -> BrokerCloseResult`,
- `sync_positions() -> list[ExternalPositionSnapshot]` (per futuri allineamenti con l’exchange).

⬜ Implementazioni target:

- `BrokerAdapterExchangePaper` (ordini finti su prezzi reali),
- `BrokerAdapterExchangeLive` (ordini reali con size ultra-ridotte).

---

### 2.3 Flusso RickyBot → LOMS → BrokerAdapter

🟡 Stato: flusso LAB/shadow con `BrokerAdapterPaperSim` operativo; live da progettare.

✅ Payload `BounceSignal` lato RickyBot / LOMS:

- `symbol`, `side`, `price`, `timestamp`,
- `exchange`, `timeframe_min`, `strategy`,
- `tp_pct`, `sl_pct`.

✅ In `/signals/bounce`:

- converte il JSON in `BounceSignal`,
- logga sempre su audit (`AUDIT_LOG_PATH`),
- se `OMS_ENABLED=False`:  
  - non crea ordini/posizioni,  
  - risponde con `oms_enabled=false`.

- se `OMS_ENABLED=True`:
  - chiama il **risk engine** (`check_risk_limits`),
  - se `risk_ok=False` → blocca e risponde con `risk_reason`,
  - se `risk_ok=True`:
    - costruisce un `NewPositionParams` con:
      - `symbol`, `side_normalizzato` (`long`/`short`),
      - `qty` (profilo LAB: 1.0),
      - `entry_price = signal.price`,
      - `exchange = signal.exchange` (default `"bitget"`),
      - `market_type = "paper_sim"`,
      - `account_label = "lab_dev"` (DEV) o profilo paper server,
      - `tp_price` / `sl_price` da `tp_pct` / `sl_pct`,
      - `exit_strategy = "tp_sl_static"`;
    - passa il comando a `BrokerAdapterPaperSim`,
    - crea Order/Position e restituisce:
      - `order_id`, `position_id`,
      - `tp_price`, `sl_price`,
      - `exit_strategy`.

> **Nota stato (2025-12-03):**  
> - DEV: test con `tools/test_notify_loms.py` → `risk_ok=True`, `order_id/position_id` creati,
>   posizioni chiuse da ExitEngine su prezzi `exchange (dummy)`.  
> - PAPER-SERVER: Shadow Mode attivo; alert reali RickyBot creano posizioni paper
>   che vengono chiuse dal motore TP/SL (prezzi simulator).

⬜ Step futuri:

- estrarre l’intera logica in un **BrokerAdapter** canonico (anche per exchange),
- aggiungere supporto a profili diversi (paper_real_price / semi_live_100eur).

---

### 2.4 Abilitazione semi-live 100€ (profilo dedicato)

⬜ Tutto ancora da progettare / implementare:

- profilo `RISK_PROFILE=semi_live_100eur`,
- sub-account dedicato su exchange,
- `BROKER_MODE=live`, `PRICE_SOURCE=exchange`,
- limiti molto stretti nel risk engine (size, max drawdown, max loss/day),
- primo wiring verso `BrokerAdapterExchangeLive`.

---

## 3. Smart Exit (Fase 2 – Gestione ordine in corso)

### 3.1 ExitPolicy / PositionLifecycle – design

✅ Definire concettualmente `ExitPolicy`:

Interfaccia in `exit_engine.py`:

- `on_new_price(position, context) -> list[ExitAction]`

`ExitAction` con:

- `type` (`ExitActionType`: `ADJUST_STOP_LOSS`, `ADJUST_TAKE_PROFIT`, `CLOSE_POSITION`),
- parametri opzionali (nuovi TP/SL, `close_reason`, ecc.).

`ExitContext` con:

- `price` corrente (float),
- `quote` (`PriceQuote` completo),
- `now` (timestamp).

✅ Posizionamento motore: `app.services.exit_engine`.

✅ Associazione policy → posizione tramite campo `exit_strategy` in `Position`
(es. `"tp_sl_static"`, in futuro `"tp_sl_trailing_v1"`).

---

### 3.2 Estensioni schema Position per Exit Engine

✅ Aggiunte/validate:

- `exit_strategy` (string),
- `dynamic_tp_price`, `dynamic_sl_price`,
- `max_favorable_move`,
- `exit_meta` (JSON serializzato in stringa, per extra info).

✅ Aggiornare `auto_close_positions` (fatto, vedi 1.3):

diventa orchestratore:

- legge prezzo da `PriceSource`,
- costruisce `ExitContext`,
- passa a `ExitPolicy` (ora `StaticTpSlPolicy`),
- applica le `ExitAction`:
  - aggiornando TP/SL dinamici (in futuro),
  - chiudendo la posizione (status, `close_price`, `pnl`, `auto_close_reason`, ecc.).

✅ `POST /positions/{id}/close`:

- usa **lo stesso PriceSource** e la logica PnL/ExitEngine,
- marca `auto_close_reason = "manual"` per distinguere manual vs auto-close.

---

### 3.3 ExitPolicy iniziali

✅ `ExitPolicyStaticTpSl`

- Replica la logica attuale TP/SL fissi,
- già integrata in `auto_close_positions` come policy di default
  (`exit_strategy="tp_sl_static"` in LAB/SHADOW).

⬜ `ExitPolicyTrailingV1` (fase 2)

Idee base (da implementare):

- dopo `+X%` di move favorevole → SL a **break-even**,
- dopo `+Y%` → trailing più stretto,
- timeout dopo `N` candele se il trade non si sblocca.

---

## 4. ML Layer (sopra, non al posto di tutto il resto)

(ancora completamente ⬜ – nessun cambio rispetto a v0.2, per ora)

⬜ Collegare dataset snapshot / outcome a ExitPolicy
(per ora solo idea, nessun wiring codice).

---

## 5. Sicurezza & Runbook

### 5.1 Modalità operative

⬜ Definire in docs (e in config) i profili finali:

**LAB:**

- `BROKER_MODE=paper`
- `PRICE_SOURCE=simulator`
- `PRICE_MODE=last` (o `mid`, da decidere come default definitiva)

**SHADOW:**

- `BROKER_MODE=paper`
- `PRICE_SOURCE=exchange`
- `PRICE_MODE=last` (oppure bid/ask/mid/mark, da definire per ogni strategia)

**SEMI-LIVE:**

- `BROKER_MODE=live`
- `PRICE_SOURCE=exchange`
- `PRICE_MODE=last` (o altro, ma comunque prezzi reali)
- `RISK_PROFILE=semi_live_100eur`

Stato attuale:

- **LAB dev locale:**
  - tipico: `BROKER_MODE=paper`, `PRICE_SOURCE=simulator` o `exchange (dummy)`,
  - `PRICE_MODE=last`, testato e funzionante in entrambi gli scenari.
- **PAPER-SERVER (Hetzner, Shadow Mode):**
  - `BROKER_MODE=paper`
  - `PRICE_SOURCE` oggi = `simulator` (può evolvere a `exchange` quando agganciamo Bitget/Bybit),
  - RickyBot Tuning2 invia segnali reali a LOMS paper.

### 5.2 Panic Button

⬜ Da scrivere nel Runbook:

- `OMS_ENABLED=false`,
- stop dei runner RickyBot,
- check `/positions` + pannello exchange,
- export DB/JSONL,
- mini post-mortem prima di riavviare.