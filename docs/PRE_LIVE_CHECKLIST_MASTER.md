# CryptoNakCore LOMS – Pre-Live Checklist MASTER (100€ semi-live)

Versione aggiornata – 2025-11-30  
Basata su: `docs/PRE_LIVE_ROADMAP.md`  
(Stato: risk base da env, `MAX_SIZE_PER_POSITION_USDT` integrato, health tool ok, `.env.sample` allineato, logging & retention mappati, checklist operative abbozzate)

---

## 0. Obiettivo

Preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

---

## 1. Stato di partenza

- [x] RickyBot Bounce EMA10 Strict stabile (tag pre-OMS).
- [x] RickyBot runner in produzione su Hetzner in modalità “stable farm”.
- [x] LOMS FastAPI attivo in modalità paper (ordini, posizioni, TP/SL, auto-close).
- [x] Integrazione RickyBot → LOMS testata end-to-end (segnale reale → ordine/posizione paper).
- [x] Endpoint `/stats` funzionante + `tools/print_stats.py`.
- [x] Endpoint `/health` funzionante + `tools/check_health.py`.

---

## 2. Fase 1 – Hardening ambiente PAPER

### 2.1 Versioning & tag

- [ ] Tag LOMS paper stabile (es. `loms-paper-stable-2025-11-30`).
- [ ] Annotare nel README:
  - [ ] tag RickyBot usato,
  - [ ] tag LOMS usato,
  - [ ] schema versioni (`v0.x-paper`, `v1.x-live`).

### 2.2 Config dev vs paper-server

- [ ] Definire due profili LOMS (concetto spiegato nella Pre-Live Roadmap):

  - [ ] **`DEV` locale** – tipicamente:
        - `ENVIRONMENT=dev`
        - `BROKER_MODE=paper`
        - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db`
        - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl`
        - `OMS_ENABLED=true`

  - [ ] **`PAPER-SERVER` (Hetzner o altro)** – tipicamente:
        - `ENVIRONMENT=paper`
        - `BROKER_MODE=paper`
        - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`
          (o path assoluto sul server)
        - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`
        - `OMS_ENABLED=true`

- [x] Allineare `.env.sample` con `Settings` (✅ 2025-11-30):
  - [x] `ENVIRONMENT`
  - [x] `DATABASE_URL`
  - [x] `AUDIT_LOG_PATH`
  - [x] `OMS_ENABLED`
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`

- [x] Documentare Quickstart dev nel README (uvicorn + venv).

### 2.3 Logging & retention

- [x] Mappare dove finiscono:
  - [x] **log applicativi**
        - In DEV: output console di `uvicorn` (shell / terminale VS Code).
        - In futuro su server: stesso output, da leggere via `tmux`, `journalctl`
          o con redirect su file (es. `services/cryptonakcore/logs/loms_paper_app.log`).
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
  - In PAPER-SERVER (futuro):
    - stessa logica via SSH (stop servizio → move file → restart),
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

### 3.2 Risk RickyBot (futuro)

- [ ] Aggiungere in `.env` RickyBot (dev/live):
  - [ ] `RISK_MAX_ALERTS_PER_DAY`,
  - [ ] `RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY`.
- [ ] Eventuale contatore nel runner / audit per questi limiti.

### 3.3 Kill switch & modalità broker

- [x] Flag LOMS:
  - [x] `BROKER_MODE=paper|live` (per ora sempre `paper`, esposto in `/health`
        e visualizzabile con `python tools/check_health.py`).
- [ ] Procedura emergenza:
  - [ ] set `OMS_ENABLED=false` in env,
  - [ ] restart LOMS,
  - [ ] stop runner RickyBot se necessario.
- [ ] Nota esplicita in README: con `BROKER_MODE=paper` **mai** ordini reali verso l’exchange.

---

## 4. Fase 3 – Monitoraggio operativo

### 4.1 Strumenti minimi (già pronti)

- [x] Health:
  - [x] `python tools/check_health.py`
- [x] Stats:
  - [x] `python tools/print_stats.py`
- [x] README / roadmap con i 3 comandi base:
  - [x] avvio uvicorn,
  - [x] check health,
  - [x] check stats.

### 4.2 Checklist operativa

#### 4.2.1 Pre-apertura (giorno di trading)

- [ ] **Server raggiungibile**
  - [ ] PC / server (es. Hetzner) raggiungibile via SSH / RDP.
- [ ] **Servizio LOMS attivo**
  - [ ] Verificare che il processo `uvicorn` sia in esecuzione  
        (oppure avviarlo con `uvicorn services.cryptonakcore.app.main:app --reload` in DEV).
- [ ] **Health OK**
  - [ ] Eseguire `python tools/check_health.py`.
  - [ ] Controllare che:
    - [ ] `HTTP status code` sia `200`,
    - [ ] `Service status` sia `ok`,
    - [ ] `Environment` e `Broker mode` siano quelli attesi (`dev` / `paper`).
- [ ] **Stats di partenza sensate**
  - [ ] Eseguire `python tools/print_stats.py`.
  - [ ] Verificare almeno:
    - [ ] `open_positions = 0` (o comunque valore atteso),
    - [ ] nessun numero “strano” (es. PnL enormi inspiegabili).
- [ ] **Percorsi file OK**
  - [ ] Esiste il file DB (`loms.db`, `loms_dev.db` o `loms_paper.db` a seconda del profilo).
  - [ ] La cartella `services/cryptonakcore/data/` esiste.
  - [ ] Il path configurato in `AUDIT_LOG_PATH` è raggiungibile/scrivibile
        (in caso di primo avvio può non esistere ancora il file, va bene così).
- [ ] **(Solo quando LOMS è collegato a RickyBot)**
  - [ ] Verificare che il runner RickyBot sia in esecuzione (sessione tmux attiva).
  - [ ] Controllare dagli ultimi log che non ci siano errori gravi al bootstrap.

#### 4.2.2 Post-giornata

- [ ] **Snapshot finale stats**
  - [ ] Eseguire `python tools/print_stats.py`.
  - [ ] Salvare l’output (copia/incolla in un file `.md` / `.txt` datato
        o screenshot) per storico giornaliero.
- [ ] **Controllo posizioni aperte**
  - [ ] Verificare da `print_stats.py` che `open_positions = 0`.
  - [ ] In caso di dubbi, controllare anche da `/docs` → `GET /positions`.
- [ ] **Verifica errori**
  - [ ] Dare un’occhiata agli ultimi log applicativi LOMS
        (traceback / errori evidenti).
  - [ ] Se usato, fare un `tail` dell’audit JSONL per controllare che gli ultimi
        eventi siano sensati.
- [ ] **Backup leggero (quando serve)**
  - [ ] Copiare il file DB (`loms_*.db`) in una cartella di backup con data
        (es. `backups/2025-12-01_loms_dev.db`).
  - [ ] Facoltativo: copiare/comprimere anche il file di audit JSONL.
- [ ] **Spegnimento ordinato (se richiesto)**
  - [ ] Se non serve tenerlo acceso H24, fermare in modo pulito:
    - [ ] processo `uvicorn` / servizio LOMS,
    - [ ] eventuale runner RickyBot collegato (quando saremo in Shadow / semi-live).

---

## 5. Fase 4 – Shadow Mode

### 5.1 Setup shadow

- [ ] Avviare LOMS vicino all’ambiente reale (locale o server).
- [ ] Configurare RickyBot dev con:
  - [ ] parametri vicini ai futuri semi-live,
  - [ ] `LOMS_ENABLED=true`,
  - [ ] `BROKER_MODE=paper`.
- [ ] Lasciare girare per N giorni (es. 5–10).

### 5.2 Analisi Shadow

- [ ] Raccogliere `/stats` (es. con `print_stats.py`) a fine giornata.
- [ ] Valutare:
  - [ ] winrate,
  - [ ] max drawdown,
  - [ ] operazioni/giorno,
  - [ ] distribuzione TP vs SL.
- [ ] Definire soglia “ok per semi-live” (es. winrate minimo, drawdown massimo accettabile).

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

- [ ] Tag LOMS paper + aggiornamento README / LOMS_CHECKLIST (Fase 2.1).
- [ ] Definire meglio profili `DEV` vs `PAPER-SERVER`.
- [x] Integrare `MAX_SIZE_PER_POSITION_USDT` nel risk engine  
      (✅ fatto 2025-11-30, vedi sezione 3.1).
- [ ] Avviare una prima Shadow Mode locale di qualche giorno.