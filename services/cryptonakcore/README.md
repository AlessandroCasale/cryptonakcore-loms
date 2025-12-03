# CryptoNakCore LOMS
**Logic & Order Management System**

FastAPI microservice che funge da **OMS** (Order Management System) in modalità **paper**  
(per il momento niente ordini reali) a supporto del trading bot **RickyBot**.

Stato attuale (**2025-12-02**):

- LOMS gira in **DEV** sul PC locale.
- LOMS gira in **PAPER-SERVER** su Hetzner (`rickybot-01`) accanto a RickyBot.
- RickyBot → LOMS è collegato in **Shadow Mode**: gli alert reali del bot generano
  **Order + Position paper** in LOMS, con TP/SL simulati e PnL esposto via API.
- Il risk engine LOMS usa **3 limiti** letti da env:
  `MAX_OPEN_POSITIONS`, `MAX_OPEN_POSITIONS_PER_SYMBOL`,
  `MAX_SIZE_PER_POSITION_USDT`.

L’idea:

> RickyBot genera un segnale → LOMS lo riceve → valida rischio → crea **Order + Position paper**  
> → simula TP/SL con un **MarketSimulator** → espone PnL, stats e storico via API.

Per la parte “pre-live 100€” vedi anche:

- `docs/LOMS_CHECKLIST_MASTER.md`
- `docs/PRE_LIVE_ROADMAP.md`
- `docs/PRE_LIVE_CHECKLIST_MASTER.md`

---

## 1. Obiettivi & Use Case

- ✅ Ricevere **segnali di trading** (es. Bounce EMA10 Strict) dal bot.
- ✅ Tradurre un segnale in:
  - `Order` (intento di esecuzione),
  - `Position` (posizione aperta con TP/SL).
- ✅ Simulare l’andamento del prezzo (MarketSimulator) e chiudere le posizioni **in automatico** su:
  - TP raggiunto,
  - SL raggiunto.
- ✅ Esporre API per:
  - vedere ordini e posizioni,
  - interrogare il “mercato” simulato,
  - calcolare **statistiche** (PnL, winrate, TP/SL count…).
- ✅ Implementare un **risk engine base**:
  - numero massimo di posizioni aperte totali,
  - numero massimo di posizioni per simbolo,
  - limite sulla **size notional** per posizione (`entry_price * qty`).
- 🔜 In futuro:
  - engine rischio più avanzato,
  - integrazione con broker reali (Bitget/Bybit),
  - modalità **“semi-live 100€”** per RickyBot.

---

## 2. Architettura in breve

Struttura (semplificata):

```text
cryptonakcore-loms/
│
├── services/
│   └── cryptonakcore/
│       ├── .env / .env.sample
│       ├── data/
│       │   ├── loms_dev.db / loms_paper.db
│       │   └── bounce_signals_*.jsonl
│       └── app/
│           ├── main.py              # FastAPI app, include tutte le route + startup scheduler
│           ├── core/
│           │   ├── config.py        # Settings (ENVIRONMENT, OMS_ENABLED, BROKER_MODE, risk, ecc.)
│           │   ├── logging.py       # setup logging (JSON, ecc.)
│           │   └── scheduler.py     # loop position_watcher / auto_close_positions
│           ├── db/
│           │   ├── session.py       # SessionLocal + Base
│           │   └── models.py        # Order, Position
│           ├── services/
│           │   ├── oms.py           # Risk engine + auto_close_positions
│           │   ├── market_simulator.py
│           │   └── audit.py         # log_bounce_signal() JSONL
│           └── api/
│               ├── health.py        # /health
│               ├── signals.py       # /signals/bounce
│               ├── orders.py        # /orders
│               ├── positions.py     # /positions (+ chiusura manuale)
│               ├── market.py        # /market (MarketSimulator)
│               └── stats.py         # /stats
│
├── tools/
│   ├── check_health.py              # chiama /health e stampa stato (env, broker_mode, ecc.)
│   ├── print_stats.py               # chiama /stats e stampa PnL, winrate, ecc.
│   └── test_bounce_size_limit.py    # mini test per il limite sulla size notional
│
├── docs/
│   ├── LOMS_CHECKLIST_MASTER.md     # Jira-style checklist LOMS
│   ├── PRE_LIVE_ROADMAP.md          # Roadmap pre-live 100€
│   └── PRE_LIVE_CHECKLIST_MASTER.md
│
├── services/cryptonakcore/.env.sample
├── requirements.txt
└── README.md                        # questo file
Tecnologie principali:

FastAPI + Uvicorn

SQLAlchemy + SQLite (DB file locale, creato automaticamente)

Pydantic / pydantic-settings per validazione & config

Scheduler interno (semplice) per auto_close_positions (simulazione TP/SL)

3. Quickstart (dev locale)
3.1 Prerequisiti
Python 3.11+ (consigliato)

pip / venv

3.2 Setup ambiente
bash
Copia codice
cd cryptonakcore-loms

# crea venv
python -m venv .venv

# attiva venv
# PowerShell
.\.venv\Scripts\Activate.ps1
# oppure bash
source .venv/bin/activate

# installa dipendenze
pip install -r requirements.txt
3.3 Avvio server
Dalla root del repo:

bash
Copia codice
cd services/cryptonakcore
uvicorn app.main:app --reload
Per default il server parte su http://127.0.0.1:8000.

Documentazione interattiva:

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc

3.4 Comandi rapidi di controllo (dev locale)
Dopo aver avviato il server in locale, hai tre comandi veloci per verificare che tutto sia ok (dalla root del repo):

Health check del servizio

bash
Copia codice
python tools/check_health.py
Snapshot veloce delle statistiche OMS

bash
Copia codice
python tools/print_stats.py
Tail dei log audit
(se AUDIT_LOG_PATH punta al file JSONL di audit, ad esempio
services/cryptonakcore/data/bounce_signals_dev.jsonl):

PowerShell:

powershell
Copia codice
Get-Content -Path .\services\cryptonakcore\data\bounce_signals_dev.jsonl -Wait
Bash:

bash
Copia codice
tail -f services/cryptonakcore/data/bounce_signals_dev.jsonl
4. API principali (overview)
Più in dettaglio lo vedi da /docs. Qui la mappa mentale:

4.1 GET /health
Ritorna lo stato base del servizio, ad esempio:

json
Copia codice
{
  "ok": true,
  "service": "CryptoNakCore LOMS",
  "status": "ok",
  "environment": "dev",
  "broker_mode": "paper",
  "oms_enabled": true,
  "database_url": "sqlite:///./services/cryptonakcore/data/loms_dev.db",
  "audit_log_path": "services/cryptonakcore/data/bounce_signals_dev.jsonl"
}
Serve per:

vedere se il servizio risponde;

leggere environment (dev, paper, in futuro live);

leggere broker_mode (paper vs live);

sapere quale DB e quale audit JSONL sta usando.

4.2 POST /signals/bounce
Endpoint principale chiamato da RickyBot per ogni segnale Bounce.

4.3 GET /orders
Elenco ordini registrati nel DB (paper).

4.4 GET /positions
Elenco posizioni (aperte + chiuse) con dettagli PnL, TP/SL, auto_close_reason.

4.5 POST /positions/{id}/close
Endpoint per chiusura manuale di una posizione
(vedi docs in /docs → tag positions).

4.6 GET /market (+ eventuali sottoroute)
Lettura/gestione prezzi nel MarketSimulator
(usato da auto_close_positions per TP/SL).

4.7 GET /stats
Statistiche aggregate:

PnL totale,

winrate,

avg_pnl_per_trade,

avg_pnl_win,

avg_pnl_loss,

tp_count, sl_count, ecc.

5. Contratto /signals/bounce
Questo è il contratto chiave usato da RickyBot (via loms_client) per notificare un segnale.

5.1 Request (BounceSignal)
POST /signals/bounce accetta un JSON tipo:

json
Copia codice
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "price": 100.0,
  "timestamp": "2025-11-27T03:17:18.594946+00:00",
  "exchange": "bitget",
  "timeframe_min": 5,
  "strategy": "bounce_ema10_strict",
  "tp_pct": 4.5,
  "sl_pct": 1.5
}
Campi principali:

symbol (str) – es. "BTCUSDT".

side (str) – "BUY" o "SELL" (long/short).

price (float) – prezzo di ingresso usato per calcolare TP/SL.

timestamp (ISO 8601) – timestamp UTC del segnale.

exchange (str) – es. "bitget", "bybit".

timeframe_min (int) – timeframe della strategia (es. 5 = 5m).

strategy (str) – nome strategia, es. "bounce_ema10_strict".

tp_pct (float) – TP in percentuale (es. 4.5 = +4.5%).

sl_pct (float) – SL in percentuale (es. 1.5 = -1.5%).

Nota: se RickyBot non specifica tp_pct / sl_pct, il LOMS può applicare default
interni (es. DEFAULT_TP_PCT / DEFAULT_SL_PCT in api/signals.py).

5.2 Comportamento lato LOMS
Valida il payload (Pydantic BounceSignal).

Logga l’evento in audit JSONL (log_bounce_signal).

Se OMS_ENABLED=True:

esegue i controlli di rischio base (check_risk_limits):

numero massimo di posizioni aperte totali (MAX_OPEN_POSITIONS),

numero massimo di posizioni aperte per simbolo (MAX_OPEN_POSITIONS_PER_SYMBOL),

limite sulla size notional (entry_price * qty <= MAX_SIZE_PER_POSITION_USDT),

se il rischio è ok:

crea un record Order + un record Position in modalità paper,

calcola tp_price e sl_price a partire da price + % (in base al side).

Uno scheduler interno (auto_close_positions) simula il “mercato” via MarketSimulator
e chiude la Position:

con auto_close_reason = "tp" se raggiunto TP,

con auto_close_reason = "sl" se raggiunto SL,

aggiornando close_price, closed_at, pnl.

Attualmente il sistema è solo paper trading:
non vengono inviati ordini reali agli exchange.

5.3 Response
Esempio di risposta (caso OMS abilitato e rischio ok):

json
Copia codice
{
  "received": true,
  "oms_enabled": true,
  "risk_ok": true,
  "order_id": 10,
  "position_id": 10,
  "tp_price": 104.5,
  "sl_price": 98.5
}
Campi tipici:

received (bool) – il segnale è stato accettato.

oms_enabled (bool) – stato della config (OMS_ENABLED).

risk_ok (bool) – il segnale ha passato i controlli base di rischio.

order_id (int | null) – ID ordine creato (se OMS_ENABLED & risk_ok).

position_id (int | null) – ID posizione creata.

tp_price / sl_price (float | null) – livelli prezzo usati per TP/SL.

risk_reason (str, opzionale) – motivo del blocco, se risk_ok = false.

6. Posizioni, ordini e stats
6.1 Modello Order
Concettualmente contiene:

info su symbol, side,

qty, order_type,

TP/SL associati all’ordine (tp_price, sl_price),

created_at, status.

Serve come “traccia” di cosa è stato chiesto al broker (anche se in paper).

6.2 Modello Position
Il modello Position (paper trading) include:

symbol, side, qty,

entry_price,

tp_price, sl_price,

status (open / closed / cancelled),

created_at,

closed_at (null se aperta),

close_price (se chiusa),

pnl (PnL finale della posizione),

auto_close_reason:

"tp" – chiusa dal simulatore per TP raggiunto,

"sl" – chiusa dal simulatore per SL,

altre stringhe per eventuale chiusura manuale ("manual", ecc.).

6.3 GET /positions
Ritorna l’elenco di posizioni (aperte + chiuse) con i campi sopra. Utile per:

debuggare il wiring RickyBot → LOMS,

vedere come “si comporta” la strategia con i TP/SL attuali.

6.4 GET /stats
Ritorna statistiche aggregate, ad esempio:

total_positions

open_positions, closed_positions

winning_trades, losing_trades

tp_count, sl_count

total_pnl

winrate

avg_pnl_per_trade

avg_pnl_win

avg_pnl_loss

Queste metriche servono come primo strato di analisi indipendente rispetto agli
snapshot PNG/CSV di RickyBot.

7. Configurazione LOMS (env)
La configurazione è gestita via settings (Settings in core/config.py) che leggono
dalle variabili d’ambiente / .env.

Campi chiave attuali (vedi anche services/cryptonakcore/.env.sample):

ENVIRONMENT (dev | paper | live in futuro)

DATABASE_URL (es. sqlite:///./services/cryptonakcore/data/loms_dev.db)

AUDIT_LOG_PATH (es. services/cryptonakcore/data/bounce_signals_dev.jsonl)

OMS_ENABLED (bool)

BROKER_MODE (paper | live in futuro)

MAX_OPEN_POSITIONS (int)

MAX_OPEN_POSITIONS_PER_SYMBOL (int)

MAX_SIZE_PER_POSITION_USDT (float)

Esempio .env minimale per sviluppo:

env
Copia codice
ENVIRONMENT=dev
DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db
AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl

OMS_ENABLED=true
BROKER_MODE=paper

MAX_OPEN_POSITIONS=5
MAX_OPEN_POSITIONS_PER_SYMBOL=2
MAX_SIZE_PER_POSITION_USDT=10.0
Comportamento di OMS_ENABLED:

false → il servizio riceve i segnali, li logga, ma non crea ordini/posizioni.
Utile per testare il wiring senza toccare il DB.

true → ad ogni POST /signals/bounce valido viene creato Order + Position in paper
(se i controlli di rischio non bloccano).

8. Profili ambiente: DEV vs PAPER-SERVER
Per ora LOMS gira solo in modalità paper, ma è utile distinguere due profili:

8.1 DEV (locale)
Ambiente sul tuo PC per sviluppare e testare:

env
Copia codice
ENVIRONMENT=dev
BROKER_MODE=paper
DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_dev.db
AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_dev.jsonl
OMS_ENABLED=true
Flow tipico:

bash
Copia codice
# Attiva venv (Windows)
.\.venv\Scripts\activate

# Avvia LOMS in dev
cd services/cryptonakcore
uvicorn app.main:app --reload

# Controlla stato (dalla root)
cd ../..
python tools/check_health.py
python tools/print_stats.py
8.2 PAPER-SERVER (Hetzner / server remoto)
Ambiente su server remoto, sempre in paper:

env
Copia codice
ENVIRONMENT=paper
BROKER_MODE=paper
DATABASE_URL=sqlite:///./services/cryptonakcore/data/loms_paper.db
AUDIT_LOG_PATH=services/cryptonakcore/data/bounce_signals_paper.jsonl
OMS_ENABLED=true
Idea operativa su Hetzner:

repo clonata in /root/cryptonakcore-loms,

.venv dedicata sul server,

.env con profilo PAPER-SERVER,

LOMS avviato in tmux (es. sessione loms-paper) con:

bash
Copia codice
cd ~/cryptonakcore-loms/services/cryptonakcore
source ../../.venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
Attualmente (2025-12-02):

DEV locale usato per sviluppo / test mirati.

PAPER-SERVER su Hetzner usato in Shadow Mode con RickyBot (solo paper).

9. Checklist operativa (solo paper)
Questa checklist è pensata per l’uso in modalità paper (sia in DEV che in profilo
PAPER-SERVER). Per la versione “completa” vedi anche LOMS_CHECKLIST_MASTER.

9.1 Prima di avviare tutto (pre-apertura)
Attiva l’ambiente virtuale (sulla macchina dove gira LOMS):

bash
Copia codice
# Windows (PowerShell)
.\.venv\Scripts\activate
# oppure bash
source .venv/bin/activate
Avvia LOMS (se non è già in esecuzione):

bash
Copia codice
cd services/cryptonakcore
uvicorn app.main:app --reload
(su server: stesso comando ma lanciato in tmux, es. sessione loms-paper).

Controlla che il servizio risponda (health) – dalla root del repo:

bash
Copia codice
python tools/check_health.py
Cosa aspettarsi:

HTTP status code : 200

Service status : ok

Environment : dev (o paper)

Broker mode : paper

OMS enabled : True (se vuoi che apra posizioni)

Controlla le statistiche di base (stats):

bash
Copia codice
python tools/print_stats.py
Prima di iniziare una nuova giornata “pulita” è consigliabile:

open_positions : 0 (nessuna posizione lasciata aperta per sbaglio),

verificare che i numeri di total_positions, tp_count, sl_count abbiano senso
rispetto ai giorni precedenti.

(Se usi anche RickyBot con LOMS)

Verifica che il runner RickyBot sia in esecuzione (tmux / log).

Verifica che la chat Telegram riceva heartbeat come al solito.

9.2 A fine giornata (post-giornata)
Snapshot veloce delle stats:

bash
Copia codice
python tools/print_stats.py
Puoi annotare (anche solo mentalmente):

total_positions,

winning_trades / losing_trades,

total_pnl,

winrate (%).

Controlla eventuali errori nei log:

log applicativi LOMS (stderr / tmux),

eventuali messaggi sospetti su risk_block o errori di auto_close_positions.

(Opzionale) Backup rapido dei dati:

copia il DB SQLite (es. loms_dev.db o loms_paper.db) in una cartella backups/
con data,

copia anche il file JSONL dei segnali (bounce_signals_*.jsonl) se vuoi tenere
uno storico separato.

Verifica che non restino posizioni aperte per sbaglio:

controlla che open_positions : 0 in print_stats.py,

in futuro, quando ci sarà un broker reale, servirà anche verificare il sub-account
sull’exchange.

10. Integrazione con RickyBot
Sul lato RickyBot (repo separata) esiste un client HTTP:

python
Copia codice
# bots/rickybot/clients/loms_client.py

def send_bounce_to_loms(config: RuntimeConfig, payload: Dict[str, Any]) -> Optional[dict]:
    ...
Il client:

legge in RuntimeConfig i campi:

loms_enabled ← (LOMS_ENABLED in .env di RickyBot),

loms_base_url ← (LOMS_BASE_URL in .env di RickyBot),

se loms_enabled = False → non chiama il servizio (logga un evento loms_skip),

se loms_enabled = True e loms_base_url è configurato → invia un POST /signals/bounce.

Esempio .env lato RickyBot (solo per capire il wiring, NON è parte di questo repo):

env
Copia codice
# abilita l'invio dei segnali verso LOMS
LOMS_ENABLED=true
LOMS_BASE_URL=http://127.0.0.1:8000

# default opzionali per TP/SL in percentuale
DEFAULT_TP_PCT=4.5
DEFAULT_SL_PCT=1.5
Flusso end-to-end:

RickyBot individua un Bounce Strict e costruisce il payload.

loms_client.send_bounce_to_loms(...) invia il JSON a POST /signals/bounce.

LOMS:

registra l’evento,

se OMS_ENABLED=True e i limiti di rischio lo permettono:

crea Order + Position paper,

lo scheduler auto_close_positions si occupa di chiudere TP/SL.

Puoi vedere l’effetto su:

GET /positions

GET /stats

log di LOMS + RickyBot.

Attualmente (2025-12-02) questo flusso è attivo in Shadow Mode su Hetzner:
nessun ordine reale verso exchange, solo posizioni paper.

11. Roadmap v1 (sintesi)
Stato attuale (baseline paper pre-live – 2025-12-02):

✅ Modelli Order / Position allineati
(tp_price, sl_price, close_price, closed_at, pnl, auto_close_reason).

✅ Scheduler auto_close_positions funzionante
(chiusura TP/SL su prezzi simulati, con protezione età posizione).

✅ Endpoint funzionanti:

/health, /signals/bounce, /orders, /positions, /market, /stats.

✅ Flag OMS_ENABLED per abilitare/disabilitare la creazione di posizioni dai segnali.

✅ Risk engine base:

limiti su numero di posizioni aperte totali,

limiti per simbolo,

limite sulla size notional (MAX_SIZE_PER_POSITION_USDT).

✅ Strumenti CLI:

tools/check_health.py,

tools/print_stats.py,

tools/test_bounce_size_limit.py.

✅ Integrazione paper con RickyBot:

testata in locale,

collegata in Shadow Mode su Hetzner,

primi trade paper (es. BTCUSDT long/short) chiusi con TP/SL visti su /positions e /stats.

Prossimi passi (idea, non vincolante – vedi anche PRE_LIVE_ROADMAP):

🟡 Migliorare il risk engine:

max esposizione totale,

whitelist simboli.

🟡 Arricchire /stats con breakdown per strategia/symbol/exchange.

🟡 Logging/audit più ricco (es. JSONL eventi OMS → analisi successiva).

⬜ Prima bozza di broker reale (es. Bitget via API) con flag separato tipo BROKER_MODE=paper|live.

⬜ Eventuale autenticazione sull’API (token/JWT) per evitare che “chiunque” chiami /signals/bounce.

12. Note finali
CryptoNakCore LOMS è pensato come “cuore logico” che un domani può gestire:

più strategie,

più bot,

sia paper trading che semi-live.

In questa fase è volutamente semplice e focalizzato su:

ricevere i segnali Bounce EMA10 Strict da RickyBot,

simulare ordini/posizioni in modo trasparente,

fornire un primo livello di numeri (PnL, winrate) per capire se la strategia “sta in piedi”.

Se stai leggendo questo README per riprendere i lavori:

apri /docs,

gioca con /signals/bounce,

guarda /positions e /stats,

e poi decidi se la prossima cosa da fare è:

migliorare i controlli di rischio, oppure

iniziare a preparare il broker reale per la fase “semi-live 100€”. 💡