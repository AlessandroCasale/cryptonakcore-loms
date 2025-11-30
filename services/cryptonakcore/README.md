# CryptoNakCore LOMS
**Logic & Order Management System**

FastAPI microservice che funge da **OMS** (Order Management System) in modalità **paper**  
(per il momento niente ordini reali) a supporto del trading bot **RickyBot**.

L’idea:  
> RickyBot genera un segnale → LOMS lo riceve → valida rischio → crea **Order + Position paper**  
> → simula TP/SL con un **MarketSimulator** → espone PnL, stats e storico via API.

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
- 🔜 In futuro:
  - engine rischio più avanzato,
  - integrazione con broker reali (Bitget/Bybit),
  - modalità “semi-live 100€” per RickyBot.

---

## 2. Architettura in breve

Repo (semplificata):

```text
cryptonakcore-loms/
│
├── services/
│   └── cryptonakcore/
│       └── app/
│           ├── main.py         # FastAPI app, include tutte le route
│           ├── config.py       # Settings (es. OMS_ENABLED)
│           ├── db.py           # SQLAlchemy + SQLite
│           ├── models.py       # Order, Position, ecc.
│           ├── schemas.py      # Pydantic (BounceSignal, OrderOut, PositionOut, StatsOut, ...)
│           └── api/
│               ├── health.py   # /health
│               ├── signals.py  # /signals/bounce
│               ├── orders.py   # /orders
│               ├── positions.py# /positions (+ chiusura manuale)
│               ├── market.py   # /market (MarketSimulator)
│               └── stats.py    # /stats
│
├── .env                        # (opzionale) config OMS (es. OMS_ENABLED)
├── requirements.txt
└── README.md                   # questo file
Tecnologie:

FastAPI + Uvicorn

SQLAlchemy + SQLite (DB file locale, creato automaticamente)

Pydantic per validazione richieste/risposte

Scheduler interno per auto_close_positions (simulazione TP/SL)

Quickstart (dev locale)
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

bash
Copia codice
uvicorn services.cryptonakcore.app.main:app --reload
Per default il server parte su http://127.0.0.1:8000.

Documentazione interattiva:

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc

3.4 Comandi rapidi di controllo (dev locale)
Dopo aver avviato il server in locale, hai tre comandi veloci per verificare che tutto sia ok:

Health check del servizio

bash
Copia codice
python tools/check_health.py
Snapshot veloce delle statistiche OMS

bash
Copia codice
python tools/print_stats.py
Tail dei log audit (se AUDIT_LOG_PATH=logs/oms_audit.jsonl)

PowerShell:

powershell
Copia codice
Get-Content -Path .\logs\oms_audit.jsonl -Wait
Bash:

bash
Copia codice
tail -f logs/oms_audit.jsonl
API principali (overview)
Più in dettaglio lo vedi da /docs, qui la mappa mentale:

GET /health
Ritorna stato base del servizio (es. {"status": "ok"}).

POST /signals/bounce
Endpoint principale chiamato da RickyBot per ogni segnale Bounce.

GET /orders
Elenco ordini registrati nel DB (paper).

GET /positions
Elenco posizioni (aperte + chiuse) con dettagli PnL, TP/SL, auto_close_reason.

POST ... (positions)
Endpoint per chiusura manuale di una posizione (vedi docs in /docs → tag positions).

GET /market (+ eventuali sottoroute)
Lettura/gestione prezzi nel MarketSimulator (usato da auto_close per TP/SL).

GET /stats
Statistiche aggregate:

PnL totale,

winrate,

avg_pnl_per_trade,

avg_pnl_win,

avg_pnl_loss,

tp_count, sl_count, ecc.

Contratto /signals/bounce
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

Nota: se RickyBot non specifica tp_pct / sl_pct, il LOMS può applicare default interni (dipende dalla configurazione corrente).

5.2 Comportamento lato LOMS
Valida il payload (BounceSignal Pydantic).

Logga l’evento in audit (se previsto).

Se OMS_ENABLED=True (config LOMS):

crea un record Order + un record Position in modalità paper,

calcola tp_price e sl_price a partire da price + %.

Uno scheduler interno (auto_close_positions) simula il “mercato” via MarketSimulator e chiude la Position:

con auto_close_reason = "tp" se raggiunto TP,

con auto_close_reason = "sl" se raggiunto SL,

aggiornando close_price, closed_at, pnl.

Attualmente il sistema è solo paper trading: non vengono inviati ordini reali a exchange.

5.3 Response
Esempio di risposta (caso OMS abilitato):

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

risk_ok (bool) – il segnale ha passato i controlli base di rischio (per ora semplici).

order_id (int | null) – ID ordine creato (se OMS abilitato).

position_id (int | null) – ID posizione creata.

tp_price / sl_price (float | null) – livelli prezzo usati per TP/SL.

Posizioni, ordini e stats

6.1 Modello Order
Concettualmente contiene:

info su simbolo, side, exchange,

prezzo di esecuzione,

timestamp,

eventuali meta extra.

Serve come “traccia” di cosa è stato chiesto al broker (anche se in paper).

6.2 Modello Position
Il modello Position (paper trading) include:

symbol, exchange, side

entry_price

tp_pct, sl_pct (salvati anche sulla posizione)

tp_price, sl_price (calcolati)

created_at

closed_at (null se aperta)

close_price (se chiusa)

pnl (PnL finale della posizione)

auto_close_reason:

"tp" – chiusa dal simulatore per TP raggiunto,

"sl" – chiusa dal simulatore per SL,

oppure valore che indica chiusura manuale.

6.3 GET /positions
Ritorna l’elenco di posizioni (aperte + chiuse) con i campi sopra.
Utile per:

debuggare il wiring RickyBot → LOMS,

vedere come “si comporta” la strategia con i TP/SL attuali.

6.4 GET /stats
Ritorna statistiche aggregate, ad esempio:

total_trades

winrate

tp_count, sl_count

avg_pnl_per_trade

avg_pnl_win

avg_pnl_loss

Queste metriche servono come primo strato di analisi indipendente rispetto agli snapshot PNG/CSV di RickyBot.

Configurazione LOMS (env)

La configurazione è gestita via settings (Pydantic) che leggono dalle variabili d’ambiente / .env.

Campo chiave attuale:

OMS_ENABLED (bool)

False → il servizio riceve i segnali, li logga, ma non crea ordini/posizioni.
Utile per testare il wiring senza toccare il DB.

True → ad ogni POST /signals/bounce valido viene creato Order + Position in paper.

Esempio .env minimale per sviluppo:

env
Copia codice
# abilita/disable la creazione automatica di ordini/posizioni da /signals/bounce
OMS_ENABLED=true
Altri parametri (DB, auto-close, ecc.) possono essere gestiti direttamente nel codice/config del servizio (vedi services/cryptonakcore/app/config.py).

Integrazione con RickyBot

Sul lato RickyBot (repo separata) esiste un piccolo client HTTP:

python
Copia codice
# bots/rickybot/clients/loms_client.py

def send_bounce_to_loms(config: RuntimeConfig, payload: Dict[str, Any]) -> Optional[dict]:
    ...
Il client:

legge in RuntimeConfig i campi:

loms_enabled ← (LOMS_ENABLED in .env di RickyBot)

loms_base_url ← (LOMS_BASE_URL in .env di RickyBot)

default_tp_pct, default_sl_pct (se non specificati dal segnale)

se loms_enabled=False → non chiama il servizio (logga un evento loms_skip).

se loms_enabled=True e loms_base_url è configurato → invia un POST /signals/bounce.

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

se OMS_ENABLED=True crea Order+Position paper,

avvia/continua lo scheduler auto_close_positions (TP/SL).

Puoi vedere l’effetto su:

GET /positions

GET /stats

(e sui log di LOMS + RickyBot).

Roadmap v1 (sintesi)

Stato attuale (2025-11-27):

✅ Modelli Order / Position allineati (tp/sl, close_price, closed_at, pnl, auto_close_reason).

✅ Scheduler auto_close_positions funzionante (chiusura TP/SL su prezzi simulati).

✅ Endpoint funzionanti:

/health, /signals/bounce, /orders, /positions, /market, /stats.

✅ Flag OMS_ENABLED per abilitare/disabilitare la creazione di posizioni dai segnali.

✅ Integrazione di test con RickyBot tramite tools/test_notify_loms.py (repo RickyBot).

Prossimi passi (idea, non vincolante):

🟡 Migliorare il risk engine:

max posizioni aperte,

max esposizione per simbolo,

whitelist simboli.

🟡 Arricchire /stats con breakdown per strategia/symbol/exchange.

🟡 Logging/audit più ricco (es. JSONL eventi OMS → analisi successiva).

⬜ Prima bozza di broker reale (es. Bitget real via API) con flag separato tipo BROKER_MODE=paper|live.

⬜ Eventuale autenticazione sull’API (token per evitare che “chiunque” chiami /signals/bounce).

Note finali

CryptoNakCore LOMS è pensato come “cuore logico” che un domani può gestire:

più strategie,

più bot,

sia paper trading che semi-live.

In questa fase è volutamente semplice e focalizzato su:

Ricevere i segnali Bounce EMA10 Strict da RickyBot,

Simulare gli ordini/posizioni in modo trasparente,

Fornire un primo livello di numeri (PnL, winrate) per capire se la strategia “sta in piedi”.

Se stai leggendo questo README per riprendere i lavori:
apri /docs, gioca con /signals/bounce, guarda /positions e /stats,
e poi decidi se la prossima cosa da fare è:

migliorare i controlli di rischio,

o iniziare a preparare il broker reale per la fase “semi-live 100€”. 💡

---

## 10. Comandi rapidi di controllo (dev locale)

Con ambiente attivo (venv) e server LOMS su `http://127.0.0.1:8000`, puoi fare tre check veloci.

### 1) Health check API

Verifica che il servizio risponda e che `/health` sia `status: "ok"`:

```bash
python tools/check_health.py
