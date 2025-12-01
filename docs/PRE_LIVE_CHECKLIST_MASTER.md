# CryptoNakCore LOMS – Pre-Live Checklist MASTER (100€ semi-live)

Versione aggiornata – 2025-11-30  
Basata su: `docs/PRE_LIVE_ROADMAP.md` + tag `loms-paper-baseline-2025-11-30`

---

## 0. Obiettivo

Preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

---

## 1. Stato di partenza

- [x] RickyBot Bounce EMA10 Strict stabile  
      (tag: `rickybot-pre-oms-tuning2-2025-11-30`, Tuning2 EMA10-60 + micro-candle guard).
- [x] RickyBot runner in produzione su Hetzner in modalità “stable farm” (solo segnali).
- [x] LOMS FastAPI attivo in modalità **paper** (ordini, posizioni, TP/SL, auto-close).
- [x] LOMS baseline paper taggato: `loms-paper-baseline-2025-11-30`.
- [x] Integrazione RickyBot → LOMS testata end-to-end (segnale reale → ordine/posizione paper).
- [x] Endpoint `/stats` funzionante + `tools/print_stats.py`.
- [x] Endpoint `/health` funzionante + `tools/check_health.py`
      (mostra anche `environment` e `broker_mode`).

---

## 2. Fase 1 – Hardening ambiente PAPER

### 2.1 Versioning & tag

- [x] Tag LOMS paper baseline: `loms-paper-baseline-2025-11-30`.
- [ ] Annotare nel README:
  - [ ] tag RickyBot usato (es. `rickybot-pre-oms-tuning2-2025-11-30`),
  - [ ] tag LOMS usato (`loms-paper-baseline-2025-11-30`),
  - [ ] schema versioni (`v0.x-paper`, `v1.x-live`).

### 2.2 Config dev vs paper-server

- [x] Definire due profili LOMS (solo paper, per ora a livello di documentazione):
  - [x] `DEV` locale (SQLite + `OMS_ENABLED=true`, `ENVIRONMENT=dev`, `BROKER_MODE=paper`).
  - [x] `PAPER-SERVER` (DB separato + `OMS_ENABLED=true`, `ENVIRONMENT=paper`, `BROKER_MODE=paper`).
- [x] Allineare `.env.sample` con `Settings` (✅ 2025-11-30):
  - [x] `ENVIRONMENT`
  - [x] `DATABASE_URL`
  - [x] `AUDIT_LOG_PATH`
  - [x] `OMS_ENABLED`
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`
- [x] Documentare Quickstart dev nel README (uvicorn + venv).
- [x] Documentare i profili `DEV` vs `PAPER-SERVER` nel README
      (sezione “Profili ambiente: DEV vs PAPER-SERVER”).

### 2.3 Logging & retention

- [ ] Mappare dove finiscono:
  - [ ] log applicativi (stdout / file, a seconda del run),
  - [ ] audit JSONL (es. `services/cryptonakcore/data/bounce_signals*.jsonl`),
  - [ ] DB SQLite (es. `loms_dev.db`, `loms_paper.db`).
- [ ] Definire retention minima (es. ≥ 30 giorni).
- [ ] Pensare a una rotazione semplice dei log (anche manuale).

---

## 3. Fase 2 – Risk lato LOMS & RickyBot

### 3.1 Risk LOMS

- [x] Parametri da env letti in `Settings`:
  - [x] `MAX_OPEN_POSITIONS`
  - [x] `MAX_OPEN_POSITIONS_PER_SYMBOL`
  - [x] `MAX_SIZE_PER_POSITION_USDT`
- [x] `check_risk_limits`:
  - [x] usa `MAX_OPEN_POSITIONS` (limite totale posizioni aperte),
  - [x] usa `MAX_OPEN_POSITIONS_PER_SYMBOL` (limite per simbolo),
  - [x] integra `MAX_SIZE_PER_POSITION_USDT` come limite sulla size notional
        (`entry_price * qty`), con log `risk_block` scope `"size"`,
  - [x] logga `risk_block` con motivo,
  - [x] accetta `None` come “nessun limite” (se in futuro lo vorrai usare così).
- [x] Test manuale del limite size notional con `tools/test_bounce_size_limit.py`
      (caso OK + caso blocco `max_size_per_position_exceeded`).

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
- [ ] Nota esplicita in README: con `BROKER_MODE=paper` **mai** ordini reali verso l’exchange
      (anche dopo l’introduzione del broker reale).

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

- [ ] Scrivere mini checklist “pre-apertura” (server + LOMS + RickyBot + log), ad es.:

  - server up (ping + SSH),
  - LOMS `/health` ok (env + broker_mode attesi),
  - `print_stats.py` con `Open positions : 0`,
  - runner RickyBot in esecuzione su Hetzner con heartbeat regolare.

- [ ] Scrivere mini checklist “post-giornata” (export `/stats`, log errori, eventuale backup DB/JSONL).

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

- [ ] Annotare esplicitamente in README i tag di riferimento:
  - [ ] `rickybot-pre-oms-tuning2-2025-11-30`,
  - [ ] `loms-paper-baseline-2025-11-30`,
  - [ ] schema versioni (`v0.x-paper`, `v1.x-live`).
- [x] Definire meglio profili `DEV` vs `PAPER-SERVER` e documentarli  
      (✅ fatto 2025-11-30, vedi README sezione “Profili ambiente”).
- [x] Integrare `MAX_SIZE_PER_POSITION_USDT` nel risk engine
      (✅ fatto 2025-11-30, vedi sezione 3.1).
- [ ] Avviare una prima Shadow Mode locale di qualche giorno.