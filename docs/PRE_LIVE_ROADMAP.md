# CryptoNakCore LOMS – Pre-Live Roadmap (100€ semi-live)

Versione aggiornata – **2025-12-04**  
(Stato: LOMS **PAPER-SERVER** attivo su Hetzner (branch `feature/real-price-exit-2025-12`, profilo `ENVIRONMENT=paper`),
`MAX_SIZE_PER_POSITION_USDT` integrato nel risk engine **con bug override env risolto**
(verificato DEV vs PAPER-SERVER), Real Price Engine (PriceSource + PriceMode + ExitPolicy
+ BrokerAdapterPaperSim) agganciato in codice e testato in **DEV** con Dummy/Bybit/Bitget,
health tool e `.env.sample` allineati, logging & retention mappati, Shadow Mode RickyBot→LOMS
agganciata con primi trade paper BTCUSDT/altro chiusi TP/SL – ~36 posizioni chiuse, winrate ~58%)

Obiettivo: preparare la coppia **RickyBot + CryptoNakCore LOMS** a un test
**semi-live con 100€** su Bitget, con rischio ultra-limitato e possibilità di
rollback immediato.

Questa roadmap NON abilita ancora il live: definisce cosa deve essere pronto
prima di anche solo pensarci.

---

## Snapshot stato vs semi-live (2025-12-03)

**✅ Già realtà (solo paper):**

- LOMS in modalità **PAPER-SERVER** su Hetzner  
  (`ENVIRONMENT=paper`, `BROKER_MODE=paper`, `OMS_ENABLED=true`).
- Risk engine lato LOMS con **3 limiti**  
  (`MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`, `MAX_SIZE_PER_POSITION_USDT`),
  con override di env globale **corretto** (DEV e PAPER-SERVER leggono i valori attesi da `.env`).
- Integrazione **RickyBot → LOMS** attiva in **Shadow Mode**:
  - ogni alert reale di Bounce EMA10 Strict viene inviato anche a LOMS (paper).
- `/health` e `/stats` funzionanti, con tool CLI  
  (`tools/check_health.py`, `tools/print_stats.py`).
- Logging & retention **mappati** (DB SQLite + audit JSONL con convenzioni per DEV e PAPER-SERVER).
- Profili `.env` DEV vs PAPER-SERVER definiti e documentati.
- Schema `Position` già “live-ready”  
  (`exchange`, `market_type`, `account_label`, `external_order_id`,
  `external_position_ref`, `exit_strategy`, `dynamic_tp_price`,
  `dynamic_sl_price`, `max_favorable_move`, `exit_meta`).
- Real Price Engine v1 integrato:
  - `PriceSourceType` (simulator/exchange/replay),
  - `PriceQuote` + `select_price(quote, mode)`,
  - `PRICE_SOURCE` / `PRICE_MODE` / `PRICE_EXCHANGE` / `PRICE_HTTP_TIMEOUT` in Settings,
  - orchestrazione in `auto_close_positions` tramite `StaticTpSlPolicy` (ExitPolicy),
  - in **DEV**:
    - `SimulatedPriceSource(MarketSimulator)`,
    - `ExchangePriceSource` con:
      - `DummyExchangeHttpClient` (quote finte ~100),
      - `BybitHttpClient` (REST `/v5/market/tickers`),
      - `BitgetHttpClient` (REST `/api/v2/spot/market/tickers`),
    - tool:
      - `tools/test_exchange_price_source.py`
      - `tools/test_exit_engine_real_price.py`.
  - su PAPER-SERVER attuale usiamo ancora **`PRICE_SOURCE=simulator`** (niente prezzi reali in produzione).
- `BrokerAdapterPaperSim` operativo:
  - apertura posizioni paper tramite `NewPositionParams`
    (symbol, side, qty, entry_price, exchange, market_type, account_label,
    tp_price, sl_price, exit_strategy="tp_sl_static"),
  - già usato da `handle_bounce_signal` per creare `Position` da segnali Bounce.
- Tag ufficiale stack **paper+shadow v1.0**:
  - RickyBot: `rickybot-loms-v1.0-2025-12-02`
  - LOMS: `loms-paper-shadow-v1.0-2025-12-04`  
    (tag annotati in `LOMS_CHECKLIST_MASTER`, sezione Versioning).

**⬜ Mancante / bloccante per il semi-live 100€:**

- Parametri **risk lato RickyBot** (`RISK_MAX_ALERTS_PER_DAY`, ecc.) e loro utilizzo nel runner.
- Regole di **kill switch** formalizzate e documentate (BROKER_MODE, OMS_ENABLED, procedura d’emergenza).
- Preparazione **sub-account** dedicato con 100€ e API key limitate.
- Criteri minimi **Go / No-Go** e **piano di rollback** scritti nero su bianco.
- Adapter exchange reali (`BrokerAdapterExchange*` + `ExchangeClient` veri) per la fase semi-live/live.

---

## A. Stato di partenza (oggi)

### A1. RickyBot

- Bounce EMA10 Strict stabile, taggato  
  `rickybot-pre-oms-tuning2-2025-11-30`.
- Runner in produzione su Hetzner in modalità “stable farm” + Tuning2  
  (Bitget/Bybit PERP 5m).
- Dev locale separato da prod (env diversi).
- Integrazione LOMS lato codice pronta:
  - client HTTP `loms_client.py`,
  - `notify_bounce_alert` che manda sia Telegram che LOMS,
  - flag `LOMS_ENABLED`, `LOMS_BASE_URL`.
- Su Hetzner, main + LOMS client in **Shadow Mode**:
  ogni alert reale viene inviato anche a LOMS in modalità paper.

### A2. LOMS

- Servizio FastAPI `cryptonakcore-loms` con:
  - OMS paper completo (ordini, posizioni, TP/SL, `auto_close_positions`).
  - Real Price Engine v1 integrato (PriceSource + PriceMode + ExitPolicy),
    usato in dev con Dummy/Bybit/Bitget, ma su server PAPER-SERVER ancora in
    modalità `PRICE_SOURCE=simulator`.
  - `/stats` + `tools/print_stats.py` funzionanti.
  - `/health` + `tools/check_health.py` funzionanti
    (inclusi `environment`, `broker_mode`, `oms_enabled`,
    `DATABASE_URL`, `AUDIT_LOG_PATH` e, in dev, i campi prezzo/PriceSource).
- Ambiente **DEV** locale funziona.
- Ambiente **PAPER-SERVER** attivo su Hetzner:
  - `ENVIRONMENT=paper`
  - `BROKER_MODE=paper`
  - `OMS_ENABLED=true`
  - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`
  - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`
  - `PRICE_SOURCE=simulator`
  - `PRICE_MODE=last`
- Su Hetzner sono già state aperte e chiuse almeno 36 posizioni di test
  (es. BTCUSDT + altri simboli) con TP/SL, verificate via `/positions` e
  `tools/print_stats.py` (winrate ~58%).
- Tutto gira **solo in modalità paper** (nessun ordine reale).

---

## B. Fase 1 – Hardening ambiente PAPER

> Obiettivo: avere uno “stack paper” talmente solido da poterlo clonare per il
> semi-live, senza sorprese.

### B1. Versioning & tag

- [x] Taggare una versione paper stabile di LOMS  
      _(tag creato: `loms-paper-shadow-v1.0-2025-12-04`, associato al commit `bc90e71` sul branch `feature/real-price-exit-2025-12`)._
- [x] Annotare nella documentazione (LOMS_CHECKLIST_MASTER + roadmap):
  - [x] tag RickyBot usato (`rickybot-loms-v1.0-2025-12-02`),
  - [x] tag LOMS usato (`loms-paper-shadow-v1.0-2025-12-04`),
  - [x] schema delle versioni (es. `v0.x-paper`, `v1.x-live`, `v2.x+`).

---

### B2. Config dev vs prod (solo paper)

- [x] Definire chiaramente due profili per LOMS (concetto + pratica):

  - **`DEV` (locale)**  
    - `ENVIRONMENT=dev`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db`  
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl`  
    - `OMS_ENABLED=true`  
    - `PRICE_SOURCE=exchange` (per test con Dummy/Bybit/Bitget in locale)  
    - `PRICE_MODE=last`  
    - `PRICE_EXCHANGE=dummy|bybit|bitget`  
    - `PRICE_HTTP_TIMEOUT` per client reali

  - **`PAPER-SERVER` (Hetzner)** – **profilo attuale**
    - `ENVIRONMENT=paper`  
    - `BROKER_MODE=paper`  
    - `DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db`  
    - `AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl`  
    - `OMS_ENABLED=true`  
    - `PRICE_SOURCE=simulator`  
    - `PRICE_MODE=last`  

- [x] Aggiungere a `services/cryptonakcore/.env.sample` i campi minimi  
      *(✅ fatto 2025-11-30 + Real Price 2025-12-03)*:
  - [x] `ENVIRONMENT=dev|paper|live`
  - [x] `DATABASE_URL`
  - [x] `AUDIT_LOG_PATH`
  - [x] `OMS_ENABLED`
  - [x] limiti rischio base
        (`MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`,
        `MAX_SIZE_PER_POSITION_USDT`)
  - [x] `PRICE_SOURCE`
  - [x] `PRICE_MODE`
  - [x] `PRICE_EXCHANGE`
  - [x] `PRICE_HTTP_TIMEOUT`
  - [x] `AUTO_CLOSE_INTERVAL_SEC`

- [x] Documentare nel README come lanciare in dev (venv + uvicorn, sezione Quickstart)  
  *(profilo server dettagliato in LOMS_CHECKLIST + runbook Hetzner).*

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
      *(✅ `check_risk_limits` usa tutti e tre e accetta anche `None` = nessun limite).*  
- [x] Loggare chiaramente i blocchi (`risk_block` con motivi, scope `"total"`, `"symbol"`, `"size"`).
- [x] **Bug override env risolto (2025-12-04)**:
  - in DEV esisteva una env di sistema `MAX_SIZE_PER_POSITION_USDT=10.0` che overrideava `.env`;
  - è stata rimossa, e verificato che:
    - DEV: `ENV=dev MAX_SIZE_PER_POSITION_USDT = 100000.0` (profilo LAB),
    - PAPER-SERVER: `ENV=paper MAX_SIZE_PER_POSITION_USDT = 1000.0`;
  - i test con `tools/test_notify_loms.py` confermano `risk_ok=True` quando notional ≤ limite.

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
- [x] Usare `OMS_ENABLED` come kill-switch logico  
      (se `false` → `/signals/bounce` non crea ordini/posizioni).
- [x] Definire una regola chiara:

  - `BROKER_MODE=paper`  
    - LOMS deve usare **solo** `BrokerAdapterPaperSim` / simulazione.
    - Anche se esiste un `BrokerAdapterExchange*` reale, **non deve mai** essere chiamato in questo profilo.
    - Profilo usato per DEV e PAPER-SERVER (Shadow Mode, nessun ordine reale).

  - `BROKER_MODE=live`  
    - LOMS deve usare **solo** `BrokerAdapterExchange*` verso sub-account reale.
    - Richiede sempre:
      - sub-account dedicato (es. Bitget 100€),
      - fondi limitati e separati,
      - API key con permessi SOLO trading (no withdraw).

- [x] Documentare una procedura di emergenza (“panic button”):

  1. Su PAPER-SERVER, editare `.env` e impostare `OMS_ENABLED=false`.
  2. Riavviare il servizio LOMS:
     - entrare nella sessione tmux `loms-paper`,
     - interrompere `uvicorn` (CTRL+C),
     - rilanciare `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
  3. Fermare il runner RickyBot:
     - sessioni tmux `rickybot-bitget` e `rickybot-bybit`,
     - CTRL+C in ciascuna sessione per fermare il bot.
  4. Verificare che non ci siano posizioni aperte:
     - `python tools/print_stats.py` → `open_positions = 0`,
     - `/positions` (o `curl .../positions/ | python -m json.tool`) → nessuna `status="open"`,
     - controllare il sub-account Bitget da app/sito → nessuna posizione aperta.
  5. Solo dopo aver verificato che tutto è chiuso, valutare eventuale riavvio in modalità paper o debug.

---

## D. Fase 3 – Monitoraggio operativo

> Obiettivo: poter vedere rapidamente se “tutto va bene” senza aprire mille file.  
> (Per la routine giornaliera completa vedi anche `LOMS_CHECKLIST_MASTER`,
> sezione **Daily Ops / Shadow Mode**.)

### D1. Strumenti minimi

- [x] Comando standard per stats LOMS:
  - [x] `python tools/print_stats.py`
- [x] Script per health:
  - [x] `python tools/check_health.py` → chiama `/health` e stampa stato
        (inclusi `environment`, `broker_mode`, `oms_enabled`,
        e – in dev – info su DB/audit e PriceSource).
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

python tools/check_health.py → status=ok, environment/broker_mode attesi,

python tools/print_stats.py → numeri coerenti (es. open_positions=0),

path DB e audit esistenti/scrivibili,

se collegato a RickyBot: sessioni tmux bot attive e log puliti al bootstrap.

Post-giornata

python tools/print_stats.py → snapshot finale salvato (file .md/.txt o screenshot),

verifica che non ci siano posizioni aperte,

controllo rapido errori nei log,

eventuale copia DB/audit in backups/ se serve “tagliare” la storia.

E. Fase 4 – Shadow Mode (raccomandata prima del 100€)
Shadow Mode = stesso flusso di segnali di domani, ma ordini solo paper,
mentre eventualmente fai ancora trading manuale per confronto.

E1. Setup shadow
Avviare LOMS su una macchina “vicina” all’ambiente reale (Hetzner rickybot-01).
(Fatto: PAPER-SERVER attivo dal 2025-12-01)

Configurare RickyBot con:

parametri vicini ai futuri semi-live
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

Tag LOMS paper + doc allineata ✅

Creato il tag git loms-paper-shadow-v1.0-2025-12-04.

LOMS_CHECKLIST_MASTER e questa Pre-Live Roadmap sono allineate
allo stato PAPER-SERVER + Shadow Mode + Real Price Engine integrato.

Rifinire i profili DEV vs PAPER-SERVER ✅

Profili reali di .env per PC locale e server definiti e testati.

Documentazione aggiornata (README + LOMS_CHECKLIST_MASTER).

Parametri risk lato RickyBot (C2) ⬜

Decidere se introdurre RISK_MAX_ALERTS_PER_DAY / per simbolo.

(Opzionale) Aggiungere solo logging/telemetria in una prima fase,
senza bloccare nulla.

Shadow Mode continua 🟡

Shadow Mode locale già testata (RickyBot dev → LOMS dev).

Shadow Mode su Hetzner attiva (RickyBot prod → LOMS PAPER-SERVER).

[🟡] Lasciare girare Shadow Mode per alcuni giorni e raccogliere /stats
come base numerica prima di anche solo nominare il semi-live 100€.

I. Shadow Mode – Snapshot iniziale (2025-12-02)
Fotografia del primo giro “serio” di Shadow Mode su Hetzner
(RickyBot Tuning2 → LOMS PAPER-SERVER).

I1. Health & config
Comandi eseguiti:

bash
Copia codice
python tools/check_health.py
python tools/print_stats.py
curl -s http://127.0.0.1:8000/positions/ | python -m json.tool
python tools/runner_status.py --max-loops 50 --show-alerts 10
Riassunto /health:

environment = "paper"

broker_mode = "paper"

oms_enabled = true

database_url = "sqlite:///./services/cryptonakcore/data/loms_paper.db"

audit_log_path = "services/cryptonakcore/data/bounce_signals_paper.jsonl"

→ conferma che il profilo PAPER-SERVER è attivo e coerente.

I2. Snapshot /stats (fine notte 2025-12-02)
Output python tools/print_stats.py:

Total positions: 36

Open positions: 0

Closed positions: 36

Winning trades: 21

Losing trades: 15

TP count: 21

SL count: 15

Total PnL: 659.8853

Winrate: 58.3333 %

Avg PnL per trade: 18.3301

Avg PnL win: 96.0799

Avg PnL loss: -90.5195

Osservazioni:

tutte le posizioni risultano chiuse (open_positions = 0);

rapporto TP/SL equilibrato (21 vs 15) con PnL totale positivo;

nessuna posizione “zombie” rimasta aperta.

I3. Posizioni vs alert RickyBot (consistenza Shadow Mode)
Confronto tra:

/positions (id 1–36)

runner_status (python tools/runner_status.py --max-loops 50 --show-alerts 10)

Gli ultimi alert nel file audit RickyBot:

MOCAUSDT (short)

BANKUSDT (short)

PARTIUSDT (long x2)

COAIUSDT (long)

LAUSDT (long)

GOATUSDT (long x3)

CKBUSDT (long)

hanno match quasi 1:1 con le ultime posizioni LOMS:

BANKUSDT short → posizione created_at = 2025-12-02T02:25:09

PARTIUSDT long → posizioni 2025-12-02T02:02:28 e 2025-12-02T02:05:43

COAIUSDT long → posizione 2025-12-02T02:05:40

LAUSDT long → posizione 2025-12-02T01:50:40

GOATUSDT long → posizioni 2025-12-02T01:26:28, 01:45:16, 01:45:31

CKBUSDT long → posizione 2025-12-02T00:47:23

→ conferma che, per ogni alert Bounce EMA10 Strict loggato da RickyBot, viene creato
un ordine+posizione paper in LOMS e chiuso dal MarketSimulator entro pochi secondi
(auto_close_reason = "tp" / "sl").

MOCAUSDT è l’unico alert recente non ancora visto in /positions al momento dello
snapshot: è plausibilmente in fase di apertura/chiusura nel momento del curl,
ma verrà catturato dai comandi successivi.

I4. Stato della pipeline Shadow Mode (2025-12-02)
Pipeline confermata operativa end-to-end:

RickyBot Tuning2 genera alert Bounce EMA10 Strict

watchlist ~30 simboli (GAINERS_PERP linear 5m)

filtraggio CleanChart molto attivo (pochi segnali, ma puliti).

notify_bounce_alert:

invia il messaggio a Telegram,

costruisce il payload BounceSignal,

chiama POST /signals/bounce su LOMS (Shadow Mode ON).

LOMS (PAPER-SERVER):

accetta il segnale,

passa dal check_risk_limits,

crea Order + Position paper quando risk_ok = true via BrokerAdapterPaperSim,

position_watcher (auto_close_positions) chiude la posizione dopo ~7s
con TP/SL deciso dalla policy statica.

Monitoring:

/positions mostra solo posizioni closed con auto_close_reason = "tp" / "sl",

/stats consolida PnL, winrate e conteggi TP/SL,

tools/check_health.py e tools/print_stats.py danno la “foto” giornaliera,

tools/runner_status.py collega watchlist, near-miss CLEAN e ultimi alert.

Questa sezione va usata come baseline di riferimento per le prossime giornate
di Shadow Mode: se in futuro cambiano Tuning, risk o configurazioni, si può
ripetere la stessa routine e confrontare i numeri con questo snapshot del
2025-12-02.

yaml
Copia codice
