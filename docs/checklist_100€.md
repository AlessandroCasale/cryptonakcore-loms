Checklist 100€ – versione compatta (pre-deposito)

Obiettivo: non muovere 1€ reale finché non è tutto spuntato da qui in giù.

1. Mettere un “sigillo” alla versione paper

 Repo cryptonakcore-loms pulita (git status clean).

 Creare il tag:

 loms-paper-shadow-2025-12-01

 Annotare da qualche parte (README / notes personali):

 Tag LOMS usato (loms-paper-shadow-2025-12-01)

 Tag RickyBot usato (rickybot-pre-oms-tuning2-2025-11-30)

 Nota: “Profilo: PAPER-SERVER + Shadow Mode ON”.

2. Safety lato LOMS (kill-switch & regole chiare)

 Scrivere 2 righe secche da incollare nel README / runbook:

 Se BROKER_MODE=paper ⇒ vietato avere adapter reali attivi.

 Se qualcosa va storto:

 OMS_ENABLED=false in .env di LOMS

 systemctl/tmux restart LOMS

 stop (o pausa) dei runner RickyBot se serve

 Verificare che /health mostri sempre:

 environment="paper"

 broker_mode="paper"

 oms_enabled=true (normale) / false (se kill-switch attivo)

(Questa parte è solo documentare nero su bianco quello che già c’è.)

3. Safety lato RickyBot (limiti sugli alert)

 Decidere valori MINIMI (anche molto alti, tipo “solo monitoraggio”):

 RISK_MAX_ALERTS_PER_DAY = …

 RISK_MAX_ALERTS_PER_SYMBOL_PER_DAY = …

 Aggiungere queste variabili in .env (dev e/o server).

(Opzionale ma consigliato):

 Loggare almeno in audit quando questi limiti vengono superati
(anche solo come warning, senza bloccare niente per ora).

4. Shadow Mode: farla girare e misurarla

 Lasciare girare Shadow Mode su Hetzner per almeno:

 N giorni consecutivi (es. 5–10)

Ogni sera (o mattina dopo), salvare un mini snapshot:

 python tools/check_health.py → output ok (file / screenshot)

 python tools/print_stats.py → output salvato (file .md/.txt o screen)

Dopo N giorni, fare un mini bilancio:

 Numero totale trade paper

 Winrate approssimativo

 Rapporto TP vs SL

 Nessun errore grave/strano da log LOMS / RickyBot

 Decidere e scrivere 3 numeri “soglia” personali tipo:

 Winrate ≥ X%

 Max drawdown simulato ≤ Y%

 Trade totali ≥ Z

…e confermare che Shadow Mode li rispetta abbastanza.

5. Preparare l’account dell’exchange

(qui siamo ancora “pre-soldi”, solo organizzazione)

 Scegliere l’exchange target definitivo (probabilmente Bitget).

 Creare (o scegliere) un sub-account dedicato al bot:

 Nome chiaro tipo RickyBot-100EUR-test

 Verificare sul sub-account:

 Nessuna posizione aperta

 Nessun asset strano (solo USDT/zero)

 Annotare da qualche parte ID / nome esatto del sub-account che userai.

6. Momento “verso i 100€” (step finale di questa lista)

Quando TUTTO sopra è spuntato:

 Depositare solo 100€ in USDT sul sub-account dedicato.

 Verificare nel pannello dell’exchange che:

 I 100€ risultino solo su quel sub-account

 Ancora nessuna posizione aperta

 Scrivere una mini nota tipo:

 Data, exchange, sub-account, importo

 “Deposito test semi-live, ancora nessun ordine automatico attivo.”