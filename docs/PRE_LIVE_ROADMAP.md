# CryptoNakCore LOMS – Pre-Live Roadmap (100€ semi-live)

Versione aggiornata – 2025-11-30  
(Stato: risk base da env, `MAX_SIZE_PER_POSITION_USDT` integrato, health tool e `.env.sample` allineati, logging & retention mappati, mini checklist operative abbozzate)

Obiettivo: preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

Questa roadmap NON abilita ancora il live: definisce cosa deve essere pronto
prima di anche solo pensarci.

---

## A. Stato di partenza (oggi)

- **RickyBot**
  - Bounce EMA10 Strict stabile, taggato  
    `rickybot-pre-oms-stable-2025-11-26` (poi Tuning2).
  - Runner in produzione su Hetzner in modalità “stable farm” (solo segnali).
  - Dev locale separato da prod (env diversi).

- **LOMS**
  - Servizio FastAPI `cryptonakcore-loms` con:
    - OMS paper completo (ordini, posizioni, TP/SL, auto_close).
    - Integrazione end-to-end con RickyBot dev via `notify_bounce_alert`.
    - `/stats` + `tools/print_stats.py` funzionanti.
    - `/health` + `tools/check_health.py` funzionanti (inclusi `environment` e `broker_mode`).
  - Tutto gira **solo in modalità paper**.

---

## B. Fase 1 – Hardening ambiente PAPER

> Obiettivo: avere uno “stack paper” talmente solido da poterlo clonare per il
> semi-live, senza sorprese.

### B1. Versioning & tag

- [ ] Taggare una versione paper stabile di LOMS (es. `loms-paper-stable-2025-11-30`).
- [ ] Annotare nel README:
  - [ ] tag RickyBot usato,
  - [ ] tag LOMS usato,
  - [ ] schema delle versioni (es. `v0.x-paper`, `v1.x-live`).

---

### B2. Config dev vs prod (solo paper)

- [ ] Definire chiaramente due profili per LOMS (concetto già descritto nel README):

  - **`DEV` (locale)**  
    - `ENVIRONMENT=dev`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db`  
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl`  
    - `OMS_ENABLED=true`

  - **`PAPER-SERVER` (Hetzner o altro)**  
    - `ENVIRONMENT=paper`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`
      (o path assoluto sul server)  
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

- [x] Documentare nel README come lanciare in dev (uvicorn + venv, sezione Quickstart).  
      *(profilo server potrà essere dettagliato più avanti)*

---

### B3. Logging & retention

> Adesso c’è una prima policy chiara su **dove** finiscono i dati e
> **come** tenerli “in ordine”.

- [x] Verificare dove finiscono:

  - [x] **Log applicativi**
    - In DEV: output console di `uvicorn` (shell / terminale VS Code).
    - In futuro su server: stesso output, da vedere via `tmux`, `journalctl`
      o redirect su file (es. `services/cryptonakcore/logs/loms_paper_app.log`).

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
  - In PAPER-SERVER (futuro):
    - stessa logica via SSH (stop servizio → move file → restart),
    - facoltativo: comprimere i backup più vecchi e tenere sul server
      solo gli ultimi N giorni.

---

## C. Fase 2 – Risk & parametrizzazione per il semi-live

> Obiettivo: avere un **layer di safety** anche se qualcosa va storto lato
> strategia o exchange.

### C1. Parametri risk lato LOMS

- [x] Leggere da env:
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`
- [x] Aggiornare il risk engine per usare questi parametri  
      *(✅ `check_risk_limits` usa tutti e tre e accetta anche `None` = nessun limite)*.
- [x] Loggare chiaramente i blocchi (`risk_block` con motivi, scope `"total"`, `"symbol"`, `"size"`).

### C2. Parametri risk lato RickyBot

- [ ] Definire in `.env` RickyBot (solo dev/live):
  - [ ] `RISK_MAX_ALERTS_PER_DAY`
  - [ ] `RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY`
- [ ] (Opzionale) Aggiungere un contatore nel runner / audit per questi limiti.

### C3. Controlli “kill switch”

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
uvicorn services.cryptonakcore.app.main:app --reload

# 3) Controllare che il servizio risponda (health)
python tools/check_health.py

# 4) Controllare le statistiche PnL / TP-SL
python tools/print_stats.py
D2. Checklist giornaliera (pre-apertura / post-giornata)
Questa parte è descritta più in dettaglio nella Pre-Live Checklist MASTER,
qui resta solo la “foto mentale”.

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
Shadow mode = stesso flusso di segnali, ma solo paper, mentre eventualmente
fai ancora trading manuale, per confrontare.

E1. Setup shadow
Avviare LOMS su una macchina “vicina” all’ambiente reale (es. locale o server).

Configurare RickyBot dev con:

parametri il più possibile vicini a quelli che userai nel semi-live,

LOMS_ENABLED=true,

BROKER_MODE=paper.

Lasciare girare per almeno N giorni (es. 5–10).

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

Shadow mode con risultati coerenti con:

snapshot PNG/CSV di RickyBot,

analisi offline.

G2. Piano di rollback
Una pagina nel README / runbook con:

“come spegnere tutto in 60 secondi”,

come verificare che nessuna posizione sia rimasta aperta.

Dopo un eventuale incidente:

esportare DB/JSONL,

scrivere un breve post-mortem tecnico (anche solo per te e Ricky).

H. Prossimi micro-step consigliati
Ordine suggerito, tutti ancora in modalità paper:

Tag LOMS paper + aggiornamento README / LOMS_CHECKLIST (Fase B1).

Rifinire i profili DEV vs PAPER-SERVER (anche solo a livello di esempi
reali di .env per PC locale vs server).

Pensare ai primi parametri risk lato RickyBot (C2) – anche se poi li
userai più avanti.

Quando ti va: avviare una prima Shadow Mode locale di qualche giorno
(LOMS in locale, RickyBot dev → LOMS, BROKER_MODE=paper fisso).