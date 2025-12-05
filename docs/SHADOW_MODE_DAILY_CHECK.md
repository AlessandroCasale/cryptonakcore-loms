# Shadow Mode – Daily Check

File operativo per tenere traccia, giorno per giorno, del comportamento
di **RickyBot + LOMS** in Shadow Mode sul server Hetzner.

Obiettivo: prima di parlare di semi-live / 100€, avere:
- N giorni di Shadow Mode **continua**,
- numeri minimi su winrate, TP/SL, eventuali problemi,
- evidenza che non ci sono bug critici ricorrenti.

---

## 0. Come usare questo file

- Una volta al giorno (es. mattina, dopo qualche ora di run):
  1. Vai sul server Hetzner.
  2. Lancia i comandi di check (vedi sezione **“Comandi da usare sul server”**).
  3. Copia i numeri / info qui dentro in una nuova sezione per la giornata.
  4. Aggiungi qualche riga di commento libero (“giornata ok / meh / brutta”, bug, note).

---

## 1. Comandi da usare sul server (Hetzner – PAPER-SERVER)

> Da eseguire su `rickybot-01`, dentro le repo giuste.

**1) Check LOMS – health + stats**

```bash
ssh root@<IP_SERVER>

cd ~/cryptonakcore-loms
source .venv/bin/activate

python tools/check_health.py
python tools/print_stats.py
Dati da annotare qui:

Environment (atteso: paper)

Broker mode (atteso: paper)

OMS enabled

total_positions, open_positions

winrate %, tp_count, sl_count, avg_pnl_per_trade, ecc.

2) (Opzionale) Check posizioni raw

bash
Copia codice
cd ~/cryptonakcore-loms
curl -s http://127.0.0.1:8000/positions/ | python -m json.tool
Utile per verificare che:

non ci siano posizioni “strane” aperte da tempo,

gli auto-close TP/SL stiano funzionando.

3) Check rapido runner RickyBot

bash
Copia codice
cd ~/RickyBot
source .venv/bin/activate

python tools/runner_status.py --max-loops 50 --show-alerts 10
Dati da annotare qui (in modo sintetico):

ultimo loop timestamp,

watchlist size,

ultimi alert (quanti, simboli, tutto ok?),

eventuali errori evidenti nei log.

2. Soglie minime desiderate (idea iniziale)
Queste soglie sono solo un promemoria, si possono rifinire più avanti.

Per dire “Shadow Mode validata per parlare di 100€” voglio:

almeno N giorni di run continuativo (es. 5–10+),

almeno N trade totali (es. 50–100+),

nessun bug critico aperto (crash LOMS, bot fermo, errori gravi ripetuti),

winrate e TP/SL “sensati” rispetto alle mie aspettative (da definire con i dati).

Quando avremo un po’ di storico, qui possiamo scrivere qualcosa tipo:

[TODO] Min winrate accettabile: >= X%

[TODO] Max drawdown accettabile: <= Y%

[TODO] Min numero di giorni consecutivi “stabili”: >= Z

3. Log giornaliero Shadow Mode
Ogni giorno aggiungi un blocco come questo.
Non serve essere super precisi scientificamente, basta costanza e chiarezza.

YYYY-MM-DD – Template esempio (da copiare e riempire)
Fascia oraria osservata: (es. 08:00–12:00)

RickyBot runner:

sessioni tmux attive: (es. rickybot-bitget, rickybot-bybit)

runner_status ok? (sì/no, eventuali note)

LOMS – check_health.py:

Environment: paper

Broker mode: paper

OMS enabled: true/false

LOMS – print_stats.py:

total_positions: …

open_positions: …

winrate: … %

tp_count: …

sl_count: …

avg_pnl_per_trade: …

Posizioni raw (se controllate):

anomalie? (es. posizioni aperte troppo a lungo, simboli strani) → sì/no + note

Eventuali errori visti nei log:

(es. eccezioni ripetute, problemi di rete, errori Telegram, ecc.)

Giudizio sintetico del giorno:

(es. “OK”, “meh ma accettabile”, “NO – c’è un bug serio da guardare”)

Note libere:

…

2025-12-04 – Prima giornata log (esempio reale)
(Puoi usare questo blocco per la giornata di oggi/stanotte quando fai il primo giro di check,
oppure duplicarlo per domani e compilarlo con i dati veri.)

Fascia oraria osservata: …

RickyBot runner:

sessioni tmux attive: …

runner_status ok? …

LOMS – check_health.py:

Environment: …

Broker mode: …

OMS enabled: …

LOMS – print_stats.py:

total_positions: …

open_positions: …

winrate: …

tp_count: …

sl_count: …

avg_pnl_per_trade: …

Posizioni raw (se controllate):

anomalie?: …

Eventuali errori visti nei log:

…

Giudizio sintetico del giorno:

…

Note libere:

…