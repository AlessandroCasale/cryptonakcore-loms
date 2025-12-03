RickyBot + LOMS – Real Price & Smart Exit Roadmap

(versione Jira-style – v0.4 – 2025-12-03)

Scope: percorso definitivo per arrivare a:

prezzi reali nei trade (no MarketSimulator per la parte “seria”),

100€ semi-live sicuri (TP/SL),

gestione avanzata dell’ordine in corso (smart exit, trailing, ecc.),

mantenendo paper/shadow/backtest come laboratorio.

Legenda stato:
✅ completato
🟡 in corso / parzialmente completo
⬜ da fare / idea futura

0. Macro-obiettivo & principi
0.1 Obiettivo finale

⬜ Portare RickyBot + LOMS a:

usare prezzi reali di mercato per PnL e TP/SL,

supportare un profilo semi-live 100€ su exchange reale con risk engine attivo,

integrare un motore di uscita smart (ExitPolicy) sopra il TP/SL fisso,

mantenere tre modalità operative chiare:

LAB: paper + simulator,

SHADOW: paper + prezzi reali,

SEMI-LIVE: ordini reali con capitale limitato.

0.2 Principi architetturali (no rework)

⬜ Nessuna logica di trading “seria” nei tool:
tutto deve passare da RickyBot (pattern/segnali) + LOMS (OMS/esecuzione).

⬜ Un’unica astrazione per i prezzi in LOMS (PriceSource / MarketDataService).

⬜ Un’unica astrazione per l’esecuzione ordini (BrokerAdapter).

⬜ Schema Position pensato da subito per convivere con:

paper puro,

paper con prezzi reali,

live su exchange.

⬜ Ogni step lascia il sistema in uno stato eseguibile (mai “mezzo rotto”).

1. Real Price Engine (PriceSource / MarketDataService)
1.1 Definizione interfaccia prezzi

✅ Definire l’interfaccia concettuale PriceSource (in codice + docs), con:

Struttura PriceQuote con almeno:

symbol,

ts (timestamp),

bid, ask, last, mark (opzionali),

source (es. "simulator", "bybit", "bitget"),

mode (es. "last", "bid", "ask", "mid", "mark").

Metodo base:

get_quote(symbol) -> PriceQuote

Funzione helper:

select_price(quote, mode) per estrarre il prezzo giusto (last/bid/ask/mid/mark).

LOMS ora consuma un PriceQuote e sceglie il campo corretto tramite PRICE_MODE.

✅ Modulo di appartenenza: app.services.pricing
(definiti PriceSourceType, PriceMode, PriceQuote, PriceSource, select_price, SimulatedPriceSource).

⬜ Definire in modo definitivo il contratto d’errore per tutte le sorgenti
(eccezioni specifiche, log strutturati, comportamento in caso di timeout / HTTP error ecc.).

1.2 Implementazioni previste

✅ PriceSourceSimulator

Incapsula l’attuale MarketSimulator (random ±10),

usato per:

dev offline,

test puramente tecnici,

LAB mode attuale.

🟡 PriceSourceExchange

✅ Scheletro definito:

ExchangeClient (Protocol) ed enum ExchangeType in exchange_client.py,

ExchangePriceSource che prende un ExchangeClient e lo trasforma in PriceQuote,

DummyExchangeHttpClient usato per test end-to-end,

tool tools/test_exchange_price_source.py con DummyExchangeClient che verifica:

bid/ask/last/mark,

select_price per tutti i PriceMode.

⬜ Da fare:

implementare davvero i client HTTP (BitgetClient, BybitClient) con le API vere,

adattare le response reali → PriceQuote,

gestione errori/retry/rate-limit.

⬜ PriceSourceReplay (fase successiva)

ReplayPriceSource che usa dati storici (CSV, snapshot, klines) per simulare feed di prezzo,

fondamentale per testare ExitPolicy offline.

1.3 Integrazione PriceSource con LOMS

✅ Introdurre i flag in Settings:

PRICE_SOURCE=simulator|exchange|replay (mappato in PriceSourceType)

PRICE_MODE=last|bid|ask|mid|mark (mappato in PriceMode)

con alias settings.price_source, settings.price_mode usati dal codice.

✅ Integrare in app.services.oms:

_get_price_source():

se PRICE_SOURCE=simulator → SimulatedPriceSource(MarketSimulator),

se PRICE_SOURCE=exchange → ExchangePriceSource(DummyExchangeHttpClient) per ora (dummy),

per valori non supportati: warning + fallback a SimulatedPriceSource.

auto_close_positions(db):

legge le posizioni status='open',

per ciascuna:

rispetta la guardia age_sec < 7 secondi,

ottiene quote = price_source.get_quote(symbol),

current_price = select_price(quote, settings.price_mode),

costruisce ExitContext(price, quote, now) e lo passa a StaticTpSlPolicy,

applica le ExitAction di tipo CLOSE_POSITION aggiornando Position
(status/closed_at/close_price/pnl/auto_close_reason),

fa db.commit() e logga position_closed.

⬜ POST /positions/{id}/close:
per ora usa ancora direttamente MarketSimulator.
TODO: allinearlo a PriceSource quando inizieremo a usare prezzi reali anche per le chiusure manuali.

✅ Garantire:

PRICE_SOURCE=simulator → comportamento LAB attuale (paper puro) invariato,

fallback sicuro: se viene configurato un sorgente non supportato → warning e fallback a SimulatedPriceSource.

2. Semi-live 100€ (Fase 1 – TP/SL semplici)
2.1 Preparazione schema dati “live-ready”

🟡 Verificare/aggiungere in Position:

✅ Campi “profilo”:

exchange (es. "bitget", "bybit"),

market_type / instrument_type (es. "paper_sim" in LAB; in futuro "linear_perp"),

account_label (es. "lab_dev", in futuro "semi_live_100eur").

⬜ Campi legati all’exchange reale:

external_order_id (ID ordine sull’exchange, se live),

external_position_ref (se necessario per l’exchange).

✅ Chiarita semantica di created_at come entry_timestamp della posizione.

✅ Mantenere compatibilità completa con paper/shadow/live
(nuovi campi nullable, vecchie righe tornano con null, come verificato via GET /positions/).

2.2 BrokerAdapter – separare logica da esecuzione

⬜ Definire concettualmente interfaccia BrokerAdapter:

create_order(position_params) -> BrokerOrderResult,

close_position(position) -> BrokerCloseResult,

sync_positions() -> list[ExternalPositionSnapshot] (per futuro).

⬜ Implementazioni target:

BrokerAdapterPaperSim,

BrokerAdapterExchangePaper,

BrokerAdapterExchangeLive.

(tutte da fare, per ora la logica è ancora “inline” in LOMS).

2.3 Flusso RickyBot → LOMS → BrokerAdapter

⬜ Verificare payload BounceSignal lato RickyBot (simile a LOMS):

symbol, side, price, timestamp,

exchange, timeframe_min, strategy,

tp_pct, sl_pct.

⬜ In /signals/bounce:

costruire un NewPositionCommand interno,

passarlo a risk engine + BrokerAdapter.

(Oggi: risk engine + creazione Order/Position sono già presenti, ma non ancora incapsulati in un BrokerAdapter canonico.)

2.4 Abilitazione semi-live 100€ (profilo dedicato)

⬜ Tutto ancora da fare
(profilo RISK_PROFILE=semi_live_100eur, sub-account, BROKER_MODE=live, PRICE_SOURCE=exchange, limiti molto stretti, ecc.).

3. Smart Exit (Fase 2 – Gestione ordine in corso)
3.1 ExitPolicy / PositionLifecycle – design

✅ Definire concettualmente ExitPolicy:

Interfaccia in exit_engine.py:

on_new_price(position, context) -> list[ExitAction]

ExitAction con:

tipo (ExitActionType: ADJUST_STOP_LOSS, ADJUST_TAKE_PROFIT, CLOSE_POSITION),

parametri opzionali (nuovi TP/SL, reason, ecc.),

ExitContext con:

price corrente (float),

quote (PriceQuote completo),

now (timestamp).

✅ Posizionamento motore: app.services.exit_engine.

✅ Associazione policy → posizione tramite campo exit_strategy in Position
(es. "tp_sl_static", in futuro "tp_sl_trailing_v1").

3.2 Estensioni schema Position per Exit Engine

✅ Aggiunte/validate:

exit_strategy (string),

dynamic_tp_price, dynamic_sl_price,

max_favorable_move,

exit_meta (JSON, per extra info).

✅ Aggiornare auto_close_positions (fatto, vedi 1.3):

diventa orchestratore:

legge prezzo da PriceSource,

costruisce ExitContext,

passa a ExitPolicy (ora StaticTpSlPolicy),

applica le ExitAction (update TP/SL, chiusure),

aggiorna Position (status, close_price, pnl, auto_close_reason, ecc.).

3.3 ExitPolicy iniziali

✅ ExitPolicyStaticTpSl

Replica la logica attuale TP/SL fissi,

già integrata in auto_close_positions come policy di default
(exit_strategy="tp_sl_static" in LAB).

⬜ ExitPolicyTrailingV1 (fase 2)

Idee base (da implementare):

dopo +X% di move favorevole → SL a break-even,

dopo +Y% → trailing più stretto,

timeout dopo N candele se il trade non si sblocca.

4. ML Layer (sopra, non al posto di tutto il resto)

(ancora completamente ⬜ – nessun cambio rispetto a v0.2, per ora)

⬜ Collegare dataset snapshot / outcome a ExitPolicy
(per ora solo idea, nessun wiring codice).

5. Sicurezza & Runbook
5.1 Modalità operative

⬜ Definire in docs (e in config) i profili finali:

LAB:

BROKER_MODE=paper

PRICE_SOURCE=simulator

PRICE_MODE=last (o mid, da decidere come default definitiva)

SHADOW:

BROKER_MODE=paper

PRICE_SOURCE=exchange

PRICE_MODE=last (oppure bid/ask/mid/mark, da definire per ogni strategia)

SEMI-LIVE:

BROKER_MODE=live

PRICE_SOURCE=exchange

PRICE_MODE=last (o altro, ma comunque prezzi reali)

RISK_PROFILE=semi_live_100eur

(Oggi: LAB dev = BROKER_MODE=paper, PRICE_SOURCE=simulator, PRICE_MODE=last testato e funzionante.
Abbiamo anche PRICE_SOURCE=exchange funzionante con DummyExchangeHttpClient, verificato via tools/test_price_source_runtime.py.)

5.2 Panic Button

⬜ Da scrivere nel Runbook
(stesso concetto di prima: OMS_ENABLED=false, stop RickyBot, check /positions + pannello exchange, export DB/JSONL, mini post-mortem).