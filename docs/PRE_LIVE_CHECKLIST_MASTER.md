# CryptoNakCore LOMS – Pre-Live Checklist MASTER (100€ semi-live)

Versione aggiornata – **2025-12-04**  
Basata su: `docs/PRE_LIVE_ROADMAP.md` + `RickyBot + LOMS – Real Price & Smart Exit Roadmap`  
(Stato: **stack paper+shadow v1.0 congelato** – LOMS in **PAPER-SERVER** su Hetzner  
(branch `feature/real-price-exit-2025-12`, tag `loms-paper-shadow-v1.0-2025-12-04`, profilo `ENVIRONMENT=paper`),  
RickyBot in **Shadow Mode** con `LOMS_ENABLED=true` su Bitget/Bybit  
(tag `rickybot-loms-v1.0-2025-12-02`, basato su `rickybot-pre-oms-tuning2-2025-11-30`),  
**nessun ordine reale verso l’exchange**; Real Price Engine (PriceSource + ExitEngine + BrokerAdapterPaperSim)
integrato lato codice e testato in **DEV** (Dummy/Bybit/Bitget), ma sul PAPER-SERVER è ancora attivo
solo il profilo **PRICE_SOURCE=simulator**.)

---

## 0. Obiettivo

Preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

---

## 1. Stato di partenza

- [x] RickyBot Bounce EMA10 Strict stabile (tag pre-OMS / Tuning2).
- [x] RickyBot runner in produzione su Hetzner in modalità “stable farm” (Tuning2 su Bitget/Bybit 5m).
- [x] LOMS FastAPI attivo in modalità **paper** (ordini, posizioni, TP/SL, auto-close).
- [x] LOMS PAPER-SERVER in esecuzione su Hetzner, profilo `ENVIRONMENT=paper`, `BROKER_MODE=paper`.
- [x] Integrazione RickyBot → LOMS testata end-to-end  
      (segnale reale → ordine/posizione paper in locale; ora Shadow Mode attiva anche su Hetzner).
- [x] Su Hetzner, LOMS PAPER-SERVER ha già gestito posizioni di test
      (BTCUSDT long/short) chiuse con TP/SL in pochi secondi, confermate via
      `GET /positions` e `tools/print_stats.py`.
- [x] Endpoint `/stats` funzionante + `tools/print_stats.py`.
- [x] Endpoint `/health` funzionante + `tools/check_health.py`.
- [x] Schema `Position` già “live-ready”:
      `exchange`, `market_type`, `account_label`, `external_order_id`,
      `external_position_ref`, `exit_strategy`, `dynamic_tp_price`,
      `dynamic_sl_price`, `max_favorable_move`, `exit_meta`.
- [x] Real Price Engine v1 integrato:
      `PriceSource` (simulator/exchange/replay), `PriceMode`, `PriceQuote`,
      orchestrato da `auto_close_positions` tramite `ExitPolicy` (`StaticTpSlPolicy`).
      In DEV sono disponibili:
      - `SimulatedPriceSource(MarketSimulator)`
      - `ExchangePriceSource` con:
        - `DummyExchangeHttpClient` (quote finte ~100),
        - `BybitHttpClient` (REST `/v5/market/tickers`),
        - `BitgetHttpClient` (REST `/api/v2/spot/market/tickers`),
      e tool:
      - `tools/test_exchange_price_source.py`
      - `tools/test_exit_engine_real_price.py`.
      Sul PAPER-SERVER attuale usiamo ancora **`PRICE_SOURCE=simulator`** (no prezzi reali).
- [x] `BrokerAdapterPaperSim` operativo: apertura posizioni paper via
      `NewPositionParams` (symbol, side, qty, entry_price, exchange, market_type,
      account_label, tp_price, sl_price, exit_strategy="tp_sl_static").

---

## 2. Fase 1 – Hardening ambiente PAPER

### 2.1 Versioning & tag

- [x] Tag LOMS paper stabile creato (stack paper+shadow v1.0):  
      `loms-paper-shadow-v1.0-2025-12-04` sul branch `feature/real-price-exit-2025-12`.
- [x] Annotare nei documenti LOMS i tag dello stack paper+shadow:
  - [x] tag RickyBot principale: `rickybot-loms-v1.0-2025-12-02`
        (basato su `rickybot-pre-oms-tuning2-2025-11-30`),
  - [x] tag LOMS paper: `loms-paper-shadow-v1.0-2025-12-04`,
  - [x] schema versioni: `v0.x` = profili paper/shadow, `v1.x` = futuri profili live/semi-live.

### 2.2 Config dev vs paper-server

- [x] Definire due profili LOMS (concetto + pratica):

  - [x] **`DEV` locale** – tipicamente:
        - `ENVIRONMENT=dev`
        - `BROKER_MODE=paper`
        - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db`
        - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl`
        - `OMS_ENABLED=true`
        - `PRICE_SOURCE=exchange`
        - `PRICE_MODE=last`
        - `PRICE_EXCHANGE=dummy|bybit|bitget`
        - `PRICE_HTTP_TIMEOUT` (timeout HTTP per Bybit/Bitget reali)

  - [x] **`PAPER-SERVER` (Hetzner)** – attualmente in uso:
        - `ENVIRONMENT=paper`
        - `BROKER_MODE=paper`
        - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`
          (profilo attivo su `rickybot-01`)
        - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`
        - `OMS_ENABLED=true`
        - `PRICE_SOURCE=simulator` (paper puro, nessun prezzo reale in auto_close)
        - `PRICE_MODE=last`
        - `PRICE_EXCHANGE` ignorato (non entra in gioco finché PRICE_SOURCE=simulator)

- [x] Allineare `.env.sample` con `Settings` (✅ 2025-11-30 + Real Price 2025-12-03):
  - [x] `ENVIRONMENT`
  - [x] `DATABASE_URL`
  - [x] `AUDIT_LOG_PATH`
  - [x] `OMS_ENABLED`
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`
  - [x] `PRICE_SOURCE`
  - [x] `PRICE_MODE`
  - [x] `PRICE_EXCHANGE`
  - [x] `PRICE_HTTP_TIMEOUT`
  - [x] `AUTO_CLOSE_INTERVAL_SEC`

- [x] Documentare Quickstart dev nel README (venv + uvicorn + uso tools health/stats).

### 2.3 Logging & retention

- [x] Mappare dove finiscono:
  - [x] **log applicativi**
        - In DEV: output console di `uvicorn` (shell / terminale VS Code).
        - In PAPER-SERVER (Hetzner): output della sessione tmux `loms-paper`
          che lancia `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  - [x] **audit JSONL**
        - Path controllato da `AUDIT_LOG_PATH` in `.env`.
        - Convenzione:
          - DEV → `services/cryptonakcore/data/bounce_signals_dev.jsonl`
          - PAPER-SERVER → `services/cryptonakcore/data/bounce_signals_paper.jsonl`
  - [x] **DB SQLite**
        - Path controllato da `DATABASE_URL` in `.env`.
        - Convenzione:
          - DEV → `sqlite:///./services/cryptonakcore/data/loms_dev.db`
          - PAPER-SERVER → `sqlite:///./services/cryptonakcore/data/loms_paper.db`

- [x] Definire retention minima (es. ≥ 30 giorni).
  - Idea operativa:
    - tenere sempre almeno ~30 giorni di storico “attivo” tra:
      - DB corrente,
      - audit JSONL corrente,
      - qualche backup datato in `backups/`.

- [x] Pensare a una rotazione semplice dei log (anche manuale).
  - In DEV:
    - fermare `uvicorn`,
    - creare (se non esiste) `backups/`,
    - spostare DB + JSONL con data nel nome  
      (es. `backups/2025-12-01_loms_dev.db`,
      `backups/2025-12-01_bounce_signals_dev.jsonl`),
    - riavviare `uvicorn` → LOMS ricrea DB/audit “puliti”.
  - In PAPER-SERVER:
    - stessa logica via SSH (stop processo tmux → move file → restart),
    - opzionale: comprimere i backup vecchi e tenere sul server solo gli ultimi N giorni.

---

## 3. Fase 2 – Risk lato LOMS & RickyBot

### 3.1 Risk LOMS

- [x] Parametri da env letti in `Settings`:
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`

- [x] `check_risk_limits`:
  - [x] usa `MAX_OPEN_POSITIONS`,
  - [x] usa `MAX_OPEN_POSITIONS_PER_SYMBOL`,
  - [x] integra `MAX_SIZE_PER_POSITION_USDT` come limite sulla size notional
        (`entry_price * qty`), con log `risk_block` scope `"size"`,
  - [x] logga `risk_block` con motivo,
  - [x] accetta `None` come “nessun limite” (se in futuro lo vorrai usare così).

- 🔧 **Bug/override risolto – MAX_SIZE_PER_POSITION_USDT (DEV vs PAPER)**  
  - In DEV c’era una variabile d’ambiente globale di sistema
    `MAX_SIZE_PER_POSITION_USDT=10.0` che overrideava il valore di `.env`.
  - Questo causava blocchi del tipo  
    `max_size_per_position_exceeded (notional=100.0000, limit=10.0000)`
    anche con `.env` a 1000.0.
  - Fix fatto 2025-12-04:
    - rimossa la env globale,
    - Verifiche:

      ```bash
      # DEV locale (dentro venv, services/cryptonakcore)
      python -c "from app.core.config import settings; \
                 print('ENV=', settings.ENVIRONMENT, \
                       'MAX_SIZE_PER_POSITION_USDT =', \
                       settings.MAX_SIZE_PER_POSITION_USDT)"
      # → ENV= dev MAX_SIZE_PER_POSITION_USDT = 100000.0 (profilo LAB)

      # PAPER-SERVER (ssh, dentro venv, services/cryptonakcore)
      ../../.venv/bin/python -c "from app.core.config import settings; \
                 print('ENV=', settings.ENVIRONMENT, \
                       'MAX_SIZE_PER_POSITION_USDT =', \
                       settings.MAX_SIZE_PER_POSITION_USDT)"
      # → ENV= paper MAX_SIZE_PER_POSITION_USDT = 1000.0
      ```

    - Dopo il fix:
      - in DEV i test LAB con `tools/test_notify_loms.py` passano (`risk_ok=True`),
      - sul server PAPER-SERVER il limite è effettivamente 1000.0 USDT.

### 3.2 Risk RickyBot (futuro)

- [ ] Aggiungere in `.env` RickyBot (dev/live):
  - [ ] `RISK_MAX_ALERTS_PER_DAY`,
  - [ ] `RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY`.
- [ ] Eventuale contatore nel runner / audit per questi limiti.

### 3.3 Kill switch & modalità broker

- [x] Flag LOMS:
  - [x] `BROKER_MODE=paper|live` (per ora sempre `paper`, esposto in `/health`
        e visualizzabile con `python tools/check_health.py`).
  - [x] `OMS_ENABLED` come kill-switch logico (se `false` → `/signals/bounce`
        non crea più ordini/posizioni).

- [x] Procedura emergenza (panic button documentata in Pre-Live Roadmap / LOMS_CHECKLIST):
  - [x] set `OMS_ENABLED=false` in `.env` LOMS,
  - [x] restart LOMS (`uvicorn` / tmux `loms-paper`),
  - [x] stop runner RickyBot se necessario (sessioni tmux bot) per evitare nuovi segnali.

- [x] Regola esplicita in doc: con `BROKER_MODE=paper` **mai** ordini reali verso l’exchange,  
      anche quando esisterà un `BrokerAdapterExchange*`.  
      Il PAPER-SERVER usa solo `BrokerAdapterPaperSim` + `PRICE_SOURCE=simulator`.

---

## 4. Fase 3 – Monitoraggio operativo

### 4.1 Strumenti minimi (già pronti)

- [x] Health:
  - [x] `python tools/check_health.py`
- [x] Stats:
  - [x] `python tools/print_stats.py`
- [x] README / roadmap con i 3 comandi base:
  - [x] avvio `uvicorn`,
  - [x] check health,
  - [x] check stats.

### 4.2 Checklist operativa

#### 4.2.1 Pre-apertura (giorno di trading)

- [ ] **Server raggiungibile**
  - [ ] PC / server (es. Hetzner) raggiungibile via SSH / RDP.
- [ ] **Servizio LOMS attivo**
  - [ ] Verificare che il processo `uvicorn` sia in esecuzione:
        - in DEV: `uvicorn app.main:app --reload` da `services/cryptonakcore`;
        - su Hetzner: sessione tmux `loms-paper` con  
          `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] **Health OK**
  - [ ] Eseguire `python tools/check_health.py`.
  - [ ] Controllare che:
    - [ ] `HTTP status code` sia `200`,
    - [ ] `Service status` sia `ok`,
    - [ ] `Environment` e `Broker mode` siano quelli attesi (`dev` / `paper`),
    - [ ] `price_source` / `price_mode` abbiano i valori previsti
          (es. `simulator/last` sul server paper, `exchange/last` in DEV).
- [ ] **Stats di partenza sensate**
  - [ ] Eseguire `python tools/print_stats.py`.
  - [ ] Verificare almeno:
    - [ ] `open_positions = 0` (o comunque valore atteso),
    - [ ] nessun numero “strano” (es. PnL enormi inspiegabili).
- [ ] **Percorsi file OK**
  - [ ] Esiste il file DB (`loms_*.db` a seconda del profilo).
  - [ ] La cartella `services/cryptonakcore/data/` esiste.
  - [ ] Il path configurato in `AUDIT_LOG_PATH` è raggiungibile/scrivibile
        (in caso di primo avvio può non esistere ancora il file, va bene così).
- [ ] **(Solo quando LOMS è collegato a RickyBot)**
  - [ ] Verificare che il runner RickyBot sia in esecuzione (sessioni tmux attive).
  - [ ] Controllare dagli ultimi log che non ci siano errori gravi al bootstrap.

#### 4.2.2 Post-giornata

- [ ] **Snapshot finale stats**
  - [ ] Eseguire `python tools/print_stats.py`.
  - [ ] Salvare l’output (copia/incolla in un file `.md` / `.txt` datato
        o screenshot) per storico giornaliero.
- [ ] **Controllo posizioni aperte**
  - [ ] Verificare da `print_stats.py` che `open_positions = 0`.
  - [ ] In caso di dubbi, controllare anche via `GET /positions`.
- [ ] **Verifica errori**
  - [ ] Dare un’occhiata agli ultimi log applicativi LOMS
        (traceback / errori evidenti).
  - [ ] Se usato, fare un `tail` dell’audit JSONL per controllare che gli ultimi
        eventi siano sensati.
- [ ] **Backup leggero (quando serve)**
  - [ ] Copiare il file DB (`loms_*.db`) in una cartella di backup con data
        (es. `backups/2025-12-01_loms_paper.db`).
  - [ ] Facoltativo: copiare/comprimere anche il file di audit JSONL.
- [ ] **Spegnimento ordinato (se richiesto)**
  - [ ] Se non serve tenerlo acceso H24, fermare in modo pulito:
    - [ ] processo `uvicorn` / servizio LOMS,
    - [ ] eventuale runner RickyBot collegato (quando saremo in Shadow / semi-live).

---

## 5. Fase 4 – Shadow Mode

### 5.1 Setup shadow

- [x] Avviare LOMS vicino all’ambiente reale (locale o server).
- [x] Configurare RickyBot con:
  - [x] parametri vicini ai futuri semi-live (GAINERS_PERP 5m, Tuning2),
  - [x] `LOMS_ENABLED=true`,
  - [x] `BROKER_MODE=paper`.
- [x] Lasciare girare per N giorni (es. 5–10)  
      _(in corso: Shadow Mode su Hetzner avviata il 2025-12-01, ora in farm continua)._  

### 5.2 Analisi Shadow

- [ ] Raccogliere `/stats` (es. con `print_stats.py`) a fine giornata.
- [ ] Valutare:
  - [ ] winrate,
  - [ ] max drawdown,
  - [ ] operazioni/giorno,
  - [ ] distribuzione TP vs SL.
- [ ] Definire soglia “ok per semi-live” (es. winrate minimo, drawdown massimo
      accettabile).

---

## 6. Fase 5 – Preparazione account 100€ semi-live

### 6.1 Account & fondi

- [ ] Sub-account dedicato su Bitget (o exchange target).
- [ ] Depositare solo la cifra test (es. 100€ in USDT).
- [ ] Verificare che non ci siano posizioni aperte/asset strani sul sub-account.

### 6.2 API & permessi

- [ ] Creare API key dedicate al sub-account:
  - [ ] permessi solo futures/perp necessari,
  - [ ] nessun permesso withdraw.
- [ ] Salvare le chiavi in env del modulo broker (quando esisterà).
- [ ] Test “read-only” (es. get balance) quando il broker reale sarà integrato.

---

## 7. Fase 6 – Go / No-Go + rollback

### 7.1 Criteri Go/No-Go

- [ ] Almeno N (es. 200–300) operazioni paper in LOMS.
- [ ] Nessun bug critico aperto in:
  - [ ] chiusura posizioni,
  - [ ] calcolo PnL,
  - [ ] `/stats`.
- [ ] Shadow mode con risultati coerenti con snapshot / analisi offline.

### 7.2 Piano di rollback

- [ ] Sezione nel README / runbook con:
  - [ ] “come spegnere tutto in 60 secondi”,
  - [ ] come verificare che non restino posizioni aperte.
- [ ] Procedura post-incident:
  - [ ] esportare DB/JSONL,
  - [ ] scrivere mini post-mortem tecnico (anche solo per te e Ricky).

---

## 8. Prossimi micro-step consigliati

- [x] Tag LOMS paper + aggiornamento doc stack paper+shadow (Fase 2.1).  
      (✅ `loms-paper-shadow-v1.0-2025-12-04` creato e referenziato in  
      LOMS_CHECKLIST_MASTER + PRE_LIVE_ROADMAP + questa checklist.)
- [x] Definire meglio profili `DEV` vs `PAPER-SERVER`  
      (✅ fatto: profili documentati, con Real Price solo in DEV e simulator su PAPER-SERVER).
- [x] Integrare `MAX_SIZE_PER_POSITION_USDT` nel risk engine  
      (✅ fatto, con bugfix override env e verifica su DEV e PAPER-SERVER).
- [x] Avviare una prima Shadow Mode (locale + server)  
      (✅ locale già testata; ✅ Shadow Mode su Hetzner attiva dal 2025-12-01).
- [ ] Lasciare girare Shadow Mode per N giorni e fare una prima review di `/stats`
      prima di pensare al semi-live 100€.