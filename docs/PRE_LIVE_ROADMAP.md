# CryptoNakCore LOMS – Pre-Live Roadmap (100€ semi-live)

Versione aggiornata – 2025-11-30  
(Stato: risk base da env, `MAX_SIZE_PER_POSITION_USDT` integrato, health tool e `.env.sample` allineati)

Obiettivo: preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

Questa roadmap NON abilita ancora il live: definisce cosa deve essere pronto
prima di anche solo pensarci.

---

## A. Stato di partenza (oggi)

- RickyBot:
  - Bounce EMA10 Strict stabile, taggato  
    `rickybot-pre-oms-stable-2025-11-26` (poi Tuning2).
  - Runner in produzione su Hetzner in modalità “stable farm” (solo segnali).
  - Dev locale separato da prod (env diversi).

- LOMS:
  - Servizio FastAPI `cryptonakcore-loms` con:
    - OMS paper completo (ordini, posizioni, TP/SL, auto_close).
    - Integrazione end-to-end con RickyBot dev via `notify_bounce_alert`.
    - `/stats` + `tools/print_stats.py` funzionanti.
    - `/health` + `tools/check_health.py` funzionanti.
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

### B2. Config dev vs prod (solo paper)

- [ ] Definire chiaramente due profili per LOMS:
  - `DEV` (locale) – DB SQLite locale, `OMS_ENABLED=true`.
  - `PAPER-SERVER` (Hetzner o altro) – DB separato, `OMS_ENABLED=true`.
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

### B3. Logging & retention

- [ ] Verificare dove finiscono:
  - [ ] log applicativi,
  - [ ] log audit JSONL,
  - [ ] DB SQLite.
- [ ] Aggiungere note di retention minima (es. “tenere almeno 30 giorni”).
- [ ] Valutare una rotazione semplice dei log (anche solo manuale).

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
  - [x] `BROKER_MODE=paper|live` (per ora resta sempre `paper`; flag letto da `Settings`
        ed esposto in `/health` → visibile con `tools/check_health.py`).
- [ ] Definire una regola chiara: se `BROKER_MODE=paper` → **nessun** ordine verso exchange
      reale anche in futuro (anche se verrà integrato un broker).
- [ ] Documentare una procedura di emergenza:
  - [ ] edit env → `OMS_ENABLED=false`,
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
  - [x] check health,
  - [x] check stats,
  - [x] tail log / controllare audit.

#### D1.1 Comandi rapidi consigliati (dev locale)

Esempi di comandi “base” da usare in modalità paper:

```bash
# 1) Avviare il servizio LOMS (dev locale)
uvicorn app.main:app --reload

# 2) Controllare che il servizio risponda (health)
python tools/check_health.py

# 3) Controllare le statistiche PnL / TP-SL
python tools/print_stats.py
D2. Checklist giornaliera
Da scrivere (anche solo nel README):

Checklist “pre-apertura”:

server up (ping + SSH),

LOMS /health OK,

RickyBot runner in esecuzione (tmux / log),

ultimi log position_closed sensati.

Checklist “post-giornata”:

salvare snapshot / esportare /stats,

controllare eventuali errori nei log.

E. Fase 4 – Shadow Mode (raccomandata prima del 100€)
Shadow mode = stesso flusso di segnali usato solo per paper, mentre tu
eventualmente fai trading manuale, per confrontare.

E1. Setup shadow
 Avviare LOMS su una macchina “vicina” all’ambiente reale (es. locale o server).

 Configurare RickyBot dev con:

 stessi parametri della futura semi-live,

 LOMS_ENABLED=true,

 BROKER_MODE=paper (flag già presente, da mantenere fisso in questa fase).

 Lasciare girare per almeno N giorni (decidi tu, es. 5–10).

E2. Analisi risultati shadow
 Raccogliere /stats a fine giornata (o con print_stats.py).

 Controllare:

 winrate,

 max drawdown simulato,

 numero medio di operazioni al giorno,

 distribuzione TP vs SL.

 Definire una soglia di “OK per semi-live” (esempio):

 winrate ≥ X%,

 max drawdown accettabile,

 nessun bug critico emerso nei log.

F. Fase 5 – Preparazione account 100€ semi-live
Qui NON attiviamo ancora ordini automatici reali, ma prepariamo il terreno.

F1. Account & fondi
 Creare (o usare) un sub-account dedicato sull’exchange.

 Depositare solo la cifra del test (es. 100€ in USDT).

 Verificare che non ci siano altri asset/posizioni aperte sul sub-account.

F2. API & permessi
 Creare API key dedicate al sub-account:

 permessi SOLO per futures/perp necessari,

 nessun permesso di withdraw.

 Salvare le chiavi in .env del futuro modulo broker (non ancora usato).

 Testare una semplice chiamata “read-only” (es. get balance) quando il broker reale sarà integrato.

G. Fase 6 – Go / No-Go per il live automatico
Questo blocco serve per il futuro, ma conviene fissare da subito i criteri.

G1. Criteri minimi per pensare al semi-live
 Almeno N (es. 200–300) operazioni paper registrate in LOMS.

 Nessun bug critico aperto in:

 chiusura posizioni,

 calcolo PnL,

 /stats.

 Shadow mode con risultati coerenti con gli snapshot / analisi offline.

G2. Piano di rollback
 Una pagina nel README (o runbook) con:

 “come spegnere tutto in 60 secondi”,

 come verificare che nessuna posizione sia rimasta aperta.

 Nota su cosa fare dopo un incidente:

 esportare DB/JSONL,

 scrivere un breve post-mortem tecnico (anche solo per te e Ricky).

H. Prossimi micro-step consigliati
Ordine suggerito, tutti ancora in modalità paper:

 Tag LOMS paper + aggiornamento README / LOMS_CHECKLIST (Fase B1).

 Definire meglio i profili DEV vs PAPER-SERVER (B2 prima riga).

 Completare il parametro MAX_SIZE_PER_POSITION_USDT nel risk engine (C1).

 Quando ti va: avviare una prima Shadow Mode locale di qualche giorno.