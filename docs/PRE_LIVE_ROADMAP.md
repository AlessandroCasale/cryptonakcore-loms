# CryptoNakCore LOMS – Pre-Live Roadmap (100€ semi-live)

Versione aggiornata – 2025-12-02  
(Stato: LOMS **PAPER-SERVER** attivo su Hetzner, `MAX_SIZE_PER_POSITION_USDT`
integrato nel risk engine, health tool e `.env.sample` allineati, logging &
retention mappati, Shadow Mode RickyBot→LOMS agganciata con primi trade paper
BTCUSDT chiusi TP/SL)

Obiettivo: preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

Questa roadmap NON abilita ancora il live: definisce cosa deve essere pronto
prima di anche solo pensarci.

---

## Snapshot stato vs semi-live (2025-12-02)

**✅ Già realtà (solo paper):**

- LOMS in modalità **PAPER-SERVER** su Hetzner (`ENVIRONMENT=paper`, `BROKER_MODE=paper`, `OMS_ENABLED=true`).
- Risk engine lato LOMS con **3 limiti** (`MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`, `MAX_SIZE_PER_POSITION_USDT`).
- Integrazione **RickyBot → LOMS** attiva in **Shadow Mode**:
  - ogni alert reale di Bounce EMA10 Strict viene inviato anche a LOMS (paper).
- `/health` e `/stats` funzionanti, con tool CLI (`tools/check_health.py`, `tools/print_stats.py`).
- Logging & retention **mappati** (DB SQLite + audit JSONL con convenzioni per DEV e PAPER-SERVER).
- Profili `.env` DEV vs PAPER-SERVER definiti e documentati.

**⬜ Mancante / bloccante per il semi-live 100€:**

- Tag **ufficiale** LOMS paper (es. `loms-paper-shadow-2025-12-01`) creato e annotato.
- Parametri **risk lato RickyBot** (`RISK_MAX_ALERTS_PER_DAY`, ecc.) e loro utilizzo nel runner.
- Regole di **kill switch** formalizzate e documentate (BROKER_MODE, OMS_ENABLED, procedura d’emergenza).
- Preparazione **sub-account** dedicato con 100€ e API key limitate.
- Criteri minimi **Go / No-Go** e **piano di rollback** scritti nero su bianco.

---

## A. Stato di partenza (oggi)

- **RickyBot**
  - Bounce EMA10 Strict stabile, taggato  
    `rickybot-pre-oms-tuning2-2025-11-30`.
  - Runner in produzione su Hetzner in modalità “stable farm” + Tuning2
    (Bitget/Bybit PERP 5m).
  - Dev locale separato da prod (env diversi).
  - Integrazione LOMS lato codice già pronta (client + notifier + flag
    `LOMS_ENABLED`, `LOMS_BASE_URL`).
  - Su Hetzner, branch con Tuning2 + LOMS client in **Shadow Mode**:
    ogni alert reale viene inviato anche a LOMS in modalità paper.

- **LOMS**
  - Servizio FastAPI `cryptonakcore-loms` con:
    - OMS paper completo (ordini, posizioni, TP/SL, `auto_close_positions`).
    - Integrazione end-to-end con RickyBot dev via `notify_bounce_alert`.
    - `/stats` + `tools/print_stats.py` funzionanti.
    - `/health` + `tools/check_health.py` funzionanti
      (inclusi `environment`, `broker_mode`, `oms_enabled`,
      `DATABASE_URL`, `AUDIT_LOG_PATH`).
  - Ambiente **DEV** locale funziona.
  - Ambiente **PAPER-SERVER** attivo su Hetzner:
    - `ENVIRONMENT=paper`
    - `BROKER_MODE=paper`
    - `OMS_ENABLED=true`
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`
  - Su Hetzner sono già state aperte e chiuse almeno 2 posizioni di test
    (BTCUSDT long/short) con TP/SL, verificate via `/positions` e
    `tools/print_stats.py`.
  - Tutto gira **solo in modalità paper**.

---

## B. Fase 1 – Hardening ambiente PAPER

> Obiettivo: avere uno “stack paper” talmente solido da poterlo clonare per il
> semi-live, senza sorprese.

### B1. Versioning & tag

- [ ] Taggare una versione paper stabile di LOMS  
      _(nome tag deciso: `loms-paper-shadow-2025-12-01`, da creare quando il repo è pulito)_.
- [ ] Annotare nel README:
  - [ ] tag RickyBot usato,
  - [ ] tag LOMS usato,
  - [ ] schema delle versioni (es. `v0.x-paper`, `v1.x-live`).

---

### B2. Config dev vs prod (solo paper)

- [x] Definire chiaramente due profili per LOMS (concetto + pratica):

  - **`DEV` (locale)**  
    - `ENVIRONMENT=dev`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db`  
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl`  
    - `OMS_ENABLED=true`

  - **`PAPER-SERVER` (Hetzner)** – **profilo attuale**
    - `ENVIRONMENT=paper`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`  
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`  
    - `OMS_ENABLED=true`

- [x] Aggiungere a `services/cryptonakcore/.env.sample` i campi minimi  
      *(✅ fatto 2025-11-30)*:
  - [x] `ENVIRONMENT=dev|paper|live`
  - [x] `DATABASE_URL`
  - [x] `AUDIT_LOG_PATH`
  - [x] `OMS_ENABLED`
  - [x] limiti rischio base (`MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`,
        `MAX_SIZE_PER_POSITION_USDT`)

- [x] Documentare nel README come lanciare in dev (venv + uvicorn, sezione Quickstart)  
      *(profilo server dettagliato in LOMS_CHECKLIST + runbook Hetzner)*.

---

### B3. Logging & retention

> Adesso c’è una prima policy chiara su **dove** finiscono i dati e
> **come** tenerli “in ordine”.

- [x] Verificare dove finiscono:

  - [x] **Log applicativi**
    - In DEV: output console di `uvicorn` (shell / terminale VS Code).
    - In PAPER-SERVER: output della sessione tmux `loms-paper` che lancia  
      `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

  - [x] **Log audit JSONL**
    - Path controllato da `AUDIT_LOG_PATH` in `.env`.
    - Convenzione:
      - DEV → `services/cryptonakcore/data/bounce_signals_dev.jsonl`
      - PAPER-SERVER → `services/cryptonakcore/data/bounce_signals_paper.jsonl`

  - [x] **DB SQLite**
    - Path controllato da `DATABASE_URL` in `.env`.
    - Convenzione:
      - DEV → `sqlite:///./services/cryptonakcore/data/loms_dev.db`
      - PAPER-SERVER → `sqlite:///./services/cryptonakcore/data/loms_paper.db`

- [x] Aggiungere note di retention minima (es. “tenere almeno 30 giorni”).

  - Idea: mantenere **almeno 30 giorni** di storico ragionevole tra:
    - DB corrente,
    - audit JSONL corrente,
    - qualche backup datato in `backups/`.

- [x] Valutare una rotazione semplice dei log (anche solo manuale).

  - In DEV:
    - fermare `uvicorn`,
    - creare (se non esiste) una cartella `backups/`,
    - spostare DB e JSONL con data nel nome, es.  
      `backups/2025-12-01_loms_dev.db`,  
      `backups/2025-12-01_bounce_signals_dev.jsonl`,
    - riavviare `uvicorn` → LOMS ricrea DB/audit “puliti”.
  - In PAPER-SERVER:
    - stessa logica via SSH (stop processo tmux → move file → restart),
    - facoltativo: comprimere i backup più vecchi e tenere sul server
      solo gli ultimi N giorni.

---

## C. Fase 2 – Risk & parametrizzazione per il semi-live

> Obiettivo: avere un **layer di safety** anche se qualcosa va storto lato
> strategia o exchange.  
> ⚠️ Questa fase è **bloccante** prima di muovere 1€ reale.

### C1. Parametri risk lato LOMS

- [x] Leggere da env:
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`
- [x] Aggiornare il risk engine per usare questi parametri  
      *(✅ `check_risk_limits` usa tutti e tre e accetta anche `None` = nessun limite)*.
- [x] Loggare chiaramente i blocchi (`risk_block` con motivi, scope `"total"`, `"symbol"`, `"size"`).

### C2. Parametri risk lato RickyBot  **(TODO – pre-100€)**

- [ ] Definire in `.env` RickyBot (solo dev/live):
  - [ ] `RISK_MAX_ALERTS_PER_DAY`
  - [ ] `RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY`
- [ ] (Opzionale) Aggiungere un contatore nel runner / audit per questi limiti.

### C3. Controlli “kill switch”  **(TODO – pre-100€)**

- [x] Introdurre un flag LOMS:
  - [x] `BROKER_MODE=paper|live`  
        (per ora resta sempre `paper`; flag letto da `Settings`
        ed esposto in `/health` → visibile con `tools/check_health.py`).
- [ ] Definire una regola chiara: se `BROKER_MODE=paper` → **nessun** ordine verso exchange
      reale anche in futuro (anche quando esisterà un adapter reale).
- [ ] Documentare una procedura di emergenza:
  - [ ] edit `.env` → `OMS_ENABLED=false`,
  - [ ] restart servizio LOMS,
  - [ ] stop runner RickyBot se necessario.

---

## D. Fase 3 – Monitoraggio operativo

> Obiettivo: poter vedere rapidamente se “tutto va bene” senza aprire mille file.  
> (Per la routine giornaliera completa vedi anche `LOMS_CHECKLIST_MASTER`, sezione
> **Daily Ops / Shadow Mode**).

### D1. Strumenti minimi

- [x] Comando standard per stats LOMS:
  - [x] `python tools/print_stats.py`
- [x] Script per health:
  - [x] `python tools/check_health.py` → chiama `/health` e stampa stato
        (inclusi `environment` e `broker_mode`).
- [x] Mini guida nel README / checklist con 3 comandi “di controllo”:
  - [x] avvio `uvicorn` in dev,
  - [x] check health,
  - [x] check stats.

#### D1.1 Comandi rapidi consigliati (dev locale)

```bash
# 1) Attivare l'ambiente
.\.venv\Scripts\Activate.ps1   # su Windows (PowerShell)
# oppure
source .venv/bin/activate      # su bash

# 2) Avviare il servizio LOMS (dev locale)
cd services/cryptonakcore
uvicorn app.main:app --reload

# 3) Controllare che il servizio risponda (health)
cd ../../
python tools/check_health.py

# 4) Controllare le statistiche PnL / TP-SL
python tools/print_stats.py
D2. Checklist giornaliera (pre-apertura / post-giornata)
Questa parte è descritta più in dettaglio nella LOMS_CHECKLIST_MASTER
(sezione Daily Ops / Shadow Mode). Qui resta solo la “foto mentale”.

Pre-apertura

server/PC raggiungibile,

processo uvicorn attivo (o avviato),

python tools/check_health.py → status=ok, environment e broker_mode attesi,

python tools/print_stats.py → numeri coerenti (es. open_positions=0),

path DB e audit esistenti/scrivibili.

Post-giornata

python tools/print_stats.py → snapshot finale salvato (file .md/.txt o screenshot),

verifica che non ci siano posizioni aperte,

controllo rapido errori nei log,

eventuale copia DB/audit in backups/ se serve “tagliare” la storia.

E. Fase 4 – Shadow Mode (raccomandata prima del 100€)
Shadow Mode = stesso flusso di segnali, ma solo paper, mentre eventualmente
fai ancora trading manuale per confronto.

E1. Setup shadow
 Avviare LOMS su una macchina “vicina” all’ambiente reale (Hetzner rickybot-01).
(Fatto: PAPER-SERVER attivo dal 2025-12-01)

 Configurare RickyBot con:

 parametri il più possibile vicini a quelli del futuro semi-live
(Bitget/Bybit PERP 5m, Tuning2),

 LOMS_ENABLED=true,

 LOMS_BASE_URL=http://127.0.0.1:8000,

 BROKER_MODE=paper lato LOMS.

[🟡] Lasciare girare per almeno N giorni (es. 5–10).
(Shadow Mode server avviata il 2025-12-01, run in corso con Tuning2+LOMS.)

E2. Analisi risultati shadow
 Raccogliere /stats a fine giornata (via tools/print_stats.py).

 Controllare:

 winrate,

 max drawdown simulato,

 numero medio di operazioni/giorno,

 distribuzione TP vs SL.

 Definire una soglia di “OK per semi-live”, per esempio:

 winrate ≥ X%,

 drawdown massimo accettabile,

 nessun bug critico emerso nei log.

F. Fase 5 – Preparazione account 100€ semi-live
⚠️ NON ANCORA INIZIATA – Piano pronto, da applicare solo quando paper+shadow
saranno stabili per un po’.

Qui NON attiviamo ancora ordini automatici reali, ma prepariamo il terreno.

F1. Account & fondi
 Creare (o usare) un sub-account dedicato sull’exchange target.

 Depositare solo la cifra del test (es. 100€ in USDT).

 Verificare che non ci siano:

 posizioni aperte,

 altri asset “strani” sul sub-account.

F2. API & permessi
 Creare API key dedicate al sub-account:

 permessi SOLO per futures/perp necessari,

 nessun permesso di withdraw.

 Salvare le chiavi in .env del futuro modulo broker (non ancora usato).

 Quando il broker reale sarà integrato:

 prima fare solo test read-only (es. get balance).

G. Fase 6 – Go / No-Go per il live automatico
Blocco più “lontano”, ma conviene fissare i paletti già adesso.

G1. Criteri minimi per pensare al semi-live
 Almeno N (es. 200–300) operazioni paper registrate in LOMS.

 Nessun bug critico aperto in:

 chiusura posizioni,

 calcolo PnL,

 /stats.

 Shadow Mode con risultati coerenti con:

 snapshot PNG/CSV di RickyBot,

 analisi offline.

G2. Piano di rollback
 Una pagina nel README / runbook con:

 “come spegnere tutto in 60 secondi”,

 come verificare che nessuna posizione sia rimasta aperta.

 Dopo un eventuale incidente:

 esportare DB/JSONL,

 scrivere un breve post-mortem tecnico (anche solo per te e Ricky).

H. Prossimi micro-step consigliati (tutti ancora solo paper)
Ordine suggerito, tutti ancora in modalità paper:

Tag LOMS paper + doc allineata

 Creare il tag git loms-paper-shadow-2025-12-01 (o nome equivalente).

✅ LOMS_CHECKLIST_MASTER e questa Pre-Live Roadmap sono già aggiornate
allo stato PAPER-SERVER + Shadow Mode.

Rifinire i profili DEV vs PAPER-SERVER

✅ Profili reali di .env per PC locale e server definiti e testati.

✅ Documentazione aggiornata (README + LOMS_CHECKLIST_MASTER).

Parametri risk lato RickyBot (C2)

 Decidere se introdurre RISK_MAX_ALERTS_PER_DAY / per simbolo.

 (Opzionale) Aggiungere solo logging/telemetria in una prima fase,
senza bloccare nulla.

Shadow Mode continua

✅ Shadow Mode locale già testata (RickyBot dev → LOMS dev).

✅ Shadow Mode su Hetzner attiva (RickyBot prod → LOMS PAPER-SERVER).

[🟡] Lasciare girare Shadow Mode per alcuni giorni e raccogliere /stats
come base numerica prima di anche solo nominare il semi-live 100€.