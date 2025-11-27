# CryptoNakCore LOMS – Pre-Live Roadmap (100€ semi-live)

Versione iniziale – 2025-11-27

Obiettivo: preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

Questa roadmap NON abilita ancora il live: definisce cosa deve essere pronto
prima di anche solo pensarci.

---

## A. Stato di partenza (oggi)

- RickyBot:
  - Bounce EMA10 Strict stabile, taggato  
    `rickybot-pre-oms-stable-2025-11-26`.
  - Runner in produzione su Hetzner in modalità “stable farm” (solo segnali).
  - Dev locale separato da prod (env diversi).

- LOMS:
  - Servizio FastAPI `cryptonakcore-loms` con:
    - OMS paper completo (ordini, posizioni, TP/SL, auto_close).
    - Integrazione end-to-end con RickyBot dev via `notify_bounce_alert`.
    - `/stats` + `tools/print_stats.py` funzionanti.
  - Tutto gira **solo in modalità paper**.

---

## B. Fase 1 – Hardening ambiente PAPER

> Obiettivo: avere uno “stack paper” talmente solido da poterlo clonare per il
> semi-live, senza sorprese.

**B1. Versioning & tag**

- [ ] Taggare una versione paper stabile di LOMS (es. `loms-paper-stable-2025-11-27`).
- [ ] Annotare nel README:
  - tag RickyBot usato,
  - tag LOMS usato,
  - schema delle versioni (es. `v0.x-paper`, `v1.x-live`).

**B2. Config dev vs prod (solo paper)**

- [ ] Definire chiaramente due profili per LOMS:
  - `DEV` (locale) – DB SQLite locale, `OMS_ENABLED=true`.
  - `PAPER-SERVER` (Hetzner o altro) – DB separato, `OMS_ENABLED=true`.
- [ ] Aggiungere a `services/cryptonakcore/.env.sample` i campi minimi:
  - `ENVIRONMENT=dev|paper|live`
  - `DATABASE_URL`
  - `AUDIT_LOG_PATH`
  - `OMS_ENABLED`
- [ ] Documentare nel README come lanciare:
  - `uvicorn app.main:app --reload` in dev,
  - `uvicorn ...` o Docker in ambiente server.

**B3. Logging & retention**

- [ ] Verificare dove finiscono:
  - log applicativi,
  - log audit JSONL,
  - DB SQLite.
- [ ] Aggiungere note di retention minima (es. “tenere almeno 30 giorni”).
- [ ] Valutare una rotazione semplice dei log (anche solo manuale).

---

## C. Fase 2 – Risk & parametrizzazione per il semi-live

> Obiettivo: avere un **layer di safety** anche se qualcosa va storto lato
> strategia o exchange.

**C1. Parametri risk lato LOMS**

- [ ] Leggere da env:
  - `MAX_OPEN_POSITIONS_TOTAL`
  - `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - `MAX_SIZE_PER_POSITION_USDT` (limite dimensione posizione)
- [ ] Aggiornare il risk engine per usare questi parametri.
- [ ] Loggare chiaramente i blocchi (`risk_block` con motivi).

**C2. Parametri risk lato RickyBot**

- [ ] Definire in `.env` RickyBot (solo dev/live):
  - `RISK_MAX_ALERTS_PER_DAY`
  - `RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY`
- [ ] (Opzionale) Aggiungere un contatore nel runner / audit per questi limiti.

**C3. Controlli “kill switch”**

- [ ] Introdurre un flag LOMS:
  - `BROKER_MODE=paper|live` (anche se per ora resta sempre `paper`).
- [ ] Definire una regola chiara: se `BROKER_MODE=paper` → **nessun** ordine verso exchange reale anche in futuro.
- [ ] Documentare una procedura di emergenza:
  - edit env → `OMS_ENABLED=false`,
  - restart servizio LOMS,
  - stop runner RickyBot se necessario.

---

## D. Fase 3 – Monitoraggio operativo

> Obiettivo: poter vedere rapidamente se “tutto va bene” senza aprire mille file.

**D1. Strumenti minimi**

- [ ] Comando standard per stats LOMS:
  - `python tools/print_stats.py`
- [ ] Script (anche semplice) per health:
  - `tools/check_health.py` → chiama `/health` e stampa stato.
- [ ] Mini guida nel README con 3 comandi “di controllo”:
  - check health,
  - check stats,
  - tail log posizioni chiuse.

**D2. Checklist giornaliera**

- [ ] Scrivere una mini checklist “pre-apertura” (anche nel README):
  1. Server up (ping + SSH).
  2. LOMS `/health` OK.
  3. RickyBot runner in esecuzione (tmux / log).
  4. Ultimi log `position_closed` sensati.
- [ ] Checklist “post-giornata”:
  - salvare snapshot / esportare `/stats`,
  - controllare eventuali errori.

---

## E. Fase 4 – Shadow Mode (raccomandata prima del 100€)

> Shadow mode = stesso flusso di segnali usato **solo per paper**, mentre tu
> eventualmente fai trading manuale, per confrontare.

**E1. Setup shadow**

- [ ] Avviare LOMS su una macchina “vicina” all’ambiente reale (es. locale o server).
- [ ] Configurare RickyBot dev con:
  - stessi parametri della futura semi-live,
  - `LOMS_ENABLED=true`,
  - `BROKER_MODE=paper`.
- [ ] Lasciare girare per almeno N giorni (decidi tu, es. 5-10).

**E2. Analisi risultati shadow**

- [ ] Raccogliere `/stats` a fine giornata (o con `print_stats.py`).
- [ ] Controllare:
  - winrate,
  - max drawdown simulato,
  - numero medio di operazioni al giorno,
  - distribuzione TP vs SL.
- [ ] Definire una soglia di “OK per semi-live” (esempio):
  - winrate ≥ X%,
  - max drawdown accettabile,
  - nessun bug critico emerso nei log.

---

## F. Fase 5 – Preparazione account 100€ semi-live

> Qui NON attiviamo ancora ordini automatici reali, ma prepariamo il terreno.

**F1. Account & fondi**

- [ ] Creare (o usare) un **sub-account dedicato** sull’exchange.
- [ ] Depositare solo la cifra del test (es. 100€ in USDT).
- [ ] Verificare che non ci siano altri asset/posizioni aperte sul sub-account.

**F2. API & permessi**

- [ ] Creare API key dedicate al sub-account:
  - permessi SOLO per futures/perp necessari,
  - nessun permesso di withdraw.
- [ ] Salvare le chiavi in `.env` del futuro modulo broker (non ancora usato).
- [ ] Testare una semplice chiamata “read-only” (es. get balance) quando il broker reale sarà integrato.

---

## G. Fase 6 – Go / No-Go per il live automatico

> Questo blocco serve per il futuro, ma conviene fissare da subito i criteri.

**G1. Criteri minimi per pensare al semi-live**

- [ ] Almeno N (es. 200–300) operazioni paper registrate in LOMS.
- [ ] Nessun bug critico aperto in:
  - chiusura posizioni,
  - calcolo PnL,
  - stats.
- [ ] Shadow mode con risultati coerenti con gli snapshot / analisi offline.

**G2. Piano di rollback**

- [ ] Una pagina nel README (o runbook) con:
  - “come spegnere tutto in 60 secondi”,
  - come verificare che nessuna posizione sia rimasta aperta.
- [ ] Nota su cosa fare **dopo** un incidente:
  - esportare DB/JSONL,
  - scrivere un breve post-mortem tecnico (anche solo per te e Ricky).

---

## H. Prossimi micro-step consigliati

Ordine suggerito, tutti ancora in modalità paper:

1. **Tag LOMS paper** + aggiornamento README / LOMS_CHECKLIST (Fase B1).  
2. **Env & .env.sample sistemati** (B2 + parte di 5.3/5.4).  
3. **Parametri risk da env** (C1, anche solo MAX_OPEN_POSITIONS_TOTAL + log).  
4. **Mini health script + checklist comandi** (D1).  
5. Quando ti va: avviare una prima **Shadow Mode** locale di qualche giorno.
