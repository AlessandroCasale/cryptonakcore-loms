# RickyBot + LOMS – Cheatsheet 2col (v9 – 2025-12-02)

LOCALE / DEV (Windows)                          SERVER / PROD (Hetzner – RickyBot + LOMS)
==========================================================================================

Preambolo – Stato attuale (Shadow Mode agganciata)
==========================================================================================

- **Dove gira cosa**
  - LOCALE:
    - `C:\Projects\crypto-bot` → RickyBot DEV (segnali + snapshot).
    - `C:\Projects\cryptonakcore-loms` → LOMS DEV (FastAPI + paper broker).
  - SERVER Hetzner `rickybot-01`:
    - `~/RickyBot` → RickyBot (Bounce EMA10 Strict Tuning2).
    - `~/cryptonakcore-loms` → LOMS PAPER-SERVER (OMS paper).

- **LOMS PAPER-SERVER (server)**
  - `ENVIRONMENT = paper`
  - `BROKER_MODE = paper`
  - `OMS_ENABLED = true`
  - DB: `services/cryptonakcore/data/loms_paper.db`
  - Audit: `services/cryptonakcore/data/bounce_signals_paper.jsonl`

- **RickyBot + Shadow Mode (server)**
  - RickyBot gira con Tuning2 su Bitget/Bybit 5m (GAINERS_PERP).
  - `.env` RickyBot server:
    - `LOMS_ENABLED = true`
    - `LOMS_BASE_URL = http://127.0.0.1:8000`
  - 2 sessioni tmux principali:
    - `rickybot-bitget`
    - `rickybot-bybit`
  - Ogni alert reale va sia su **Telegram** sia su **LOMS** (via `/signals/bounce`).

- **Flusso Shadow Mode (mental model)**
  1. RickyBot trova un pattern Bounce EMA10 Strict (Tuning2) su 5m.
  2. Manda l’alert su Telegram (come sempre).
  3. Se `LOMS_ENABLED=true`, chiama il `loms_client` → `POST /signals/bounce` su LOMS.
  4. LOMS controlla i limiti di rischio, crea ordine + posizione paper e il MarketSimulator chiude TP/SL dopo ~7s.
  5. Vedi il risultato su:
     - `/positions` (lista posizioni),
     - `/stats` (winrate, tp/sl count, ecc.).

- **Cosa consideriamo stabile adesso (v9)**
  - RickyBot Bounce EMA10 Strict Tuning2 lato server (solo segnali, no ordini reali).
  - LOMS PAPER-SERVER con auto-close TP/SL e `/stats` funzionante.
  - Integrazione RickyBot → LOMS testata:
    - con tool di test,
    - con almeno un alert reale.
  - Modalità **Shadow Mode** attiva: ordini solo nel DB paper di LOMS, non sull’exchange.

- 📌 **Nota Real Price (DEV vs PAPER-SERVER)**  
  - **DEV locale (Windows)**  
    - `PRICE_SOURCE=exchange` con **DummyExchangeHttpClient`**  
    - Le posizioni paper usano già il nuovo percorso **Real Price / ExitEngine** (PriceSource + ExitPolicy),  
      ma le quote sono ancora **finte** (client HTTP dummy, nessun contatto reale con Bitget/Bybit).  
  - **PAPER-SERVER (Hetzner)**  
    - `PRICE_SOURCE=simulator`  
    - LOMS lavora ancora con **MarketSimulator v2** per TP/SL (paper puro),  
      mentre ascolta comunque tutti i segnali reali da RickyBot in Shadow Mode.

0) REPO, VENV, GIT                              0) SSH, REPO, VENV, GIT
----------------------------------------        ------------------------------------------

Apri terminale PowerShell / VS Code            Connessione al server
----------------------------------------        ------------------------------------------
# RickyBot DEV                                  ssh root@<IP_SERVER>
cd C:\Projects\crypto-bot                      # es: ssh root@37.27.xx.xx
& .\.venv\Scripts\Activate.ps1

# LOMS DEV                                     Entra nella repo RickyBot
cd C:\Projects\cryptonakcore-loms              ------------------------------------------
& .\.venv\Scripts\Activate.ps1                 cd ~/RickyBot
                                               source .venv/bin/activate

GIT locale RickyBot                            GIT server RickyBot
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd ~/RickyBot
git status                                     git status
git log -1 --oneline                           git log -1 --oneline
git pull                                       git pull

GIT locale LOMS                                GIT server LOMS
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms              cd ~/cryptonakcore-loms
git status                                     git status
git log -1 --oneline                           git log -1 --oneline
git pull                                       git pull


A) RICKYBOT – LOCALE / DEV                     A) RICKYBOT – SERVER / PROD
----------------------------------------        ------------------------------------------

A1) ENV & CONFIG                               A1) ENV & CONFIG
----------------------------------------        ------------------------------------------
Mostra runtime config DEV                      Mostra runtime config server
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd ~/RickyBot
& .\.venv\Scripts\Activate.ps1                 source .venv/bin/activate
python tools\runtime_config_inspector.py       python tools/runtime_config_inspector.py --pretty
  --pretty

Apri .env / .env.local (VS Code)               Controlla/greppa env RickyBot
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd ~/RickyBot
code .env                                      grep -E '^(EXCHANGE|MODE|INTERVAL_MIN|GAINERS_TOP_N)' .env
code .env.local                                grep -E '^(LOMS_ENABLED|LOMS_BASE_URL)' .env

A2) AVVIO RUNNER DEV                           A2) AVVIO RUNNER IN TMUX (SERVER)
----------------------------------------        ------------------------------------------
Run veloce una volta (DEV)                     Lista sessioni tmux
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      tmux ls
& .\.venv\Scripts\Activate.ps1
python -m bots.rickybot --top 5                Crea nuova sessione runner Bitget
                                               ------------------------------------------
Uso tipico DEV (loop continuo)                 cd ~/RickyBot
----------------------------------------        source .venv/bin/activate
python -m bots.rickybot                        tmux new -s rickybot-bitget
  --top 30                                     # dentro tmux:
  --once false                                 python -m bots.rickybot
                                               # poi stacca: CTRL+b, quindi d

A3) TMUX – COMANDI BASE (SERVER)               A3) TMUX – ATTACCO / DETACH / KILL
----------------------------------------        ------------------------------------------
(elenco per memoria)                           Attaccare a una sessione
                                               ------------------------------------------
# lista sessioni                               tmux attach -t rickybot-bitget
tmux ls                                        tmux attach -t rickybot-bybit
                                               tmux attach -t loms-paper
# nuova sessione
tmux new -s nome                               Staccarsi (senza fermare il processo)
                                               ------------------------------------------
# attacca                                      CTRL+b, poi d
tmux attach -t nome

# chiudi sessione                              Chiudere una sessione
tmux kill-session -t nome                      ------------------------------------------
                                               tmux kill-session -t rickybot-bitget


A4) STATO RUNNER & LOG                         A4) STATO RUNNER & LOG (SERVER)
----------------------------------------        ------------------------------------------
Stato sintetico runner (DEV)                   Stato sintetico runner (SERVER)
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd ~/RickyBot
& .\.venv\Scripts\Activate.ps1                 source .venv/bin/activate
python tools\runner_status.py                  python tools/runner_status.py \
  --max-loops 50                                 --max-loops 50 --show-alerts 10
  --show-alerts 10

Tail log locale (se log su file)               Tail log server (se hai log su file)
----------------------------------------        ------------------------------------------
Get-Content .\logs\ross123.log -Tail 50        tail -n 50 logs/ross123.log
Get-Content .\logs\ross123.log -Wait           tail -f logs/ross123.log


A5) SNAPSHOT – LOCALE DEV                      A5) SNAPSHOT – SERVER
----------------------------------------        ------------------------------------------
Root standard (storico server in locale)       Conta snapshot sul server
----------------------------------------        ------------------------------------------
C:\Projects\crypto-bot\local_data\            cd ~/RickyBot
  rickybot_snapshots                           find logs/snapshots -type f -name "*.json" | wc -l

Root standard run locale                       Pulisci snapshot prima di un nuovo giro
----------------------------------------        ------------------------------------------
C:\Projects\crypto-bot\logs\snapshots          cd ~/RickyBot
                                               rm -rf logs/snapshots/*

Copia snapshot dal server al PC                Copia snapshot dal server (da fare da PC)
----------------------------------------        ------------------------------------------
# da PowerShell sul PC                         # PowerShell sul PC:
scp -r `                                       scp -r `
  root@<IP_SERVER>:/root/RickyBot/logs/snapshots `  root@<IP_SERVER>:/root/RickyBot/logs/snapshots `
  C:\Projects\crypto-bot\local_data\               C:\Projects\crypto-bot\local_data\rickybot_snapshots
    rickybot_snapshots\

A6) DATASET SNAPSHOT & REPORT (DEV)            A6) VERIFICA SNAPSHOT (DEV/SERVER)
----------------------------------------        ------------------------------------------
Genera dataset dallo storico server copiato    Verifica snapshot vs exchange
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd C:\Projects\crypto-bot
& .\.venv\Scripts\Activate.ps1                 & .\.venv\Scripts\Activate.ps1
python tools\make_snapshot_dataset.py          python tools\snapshot_verify_exchange.py `
  --root local_data\rickybot_snapshots `         --root local_data\rickybot_snapshots
  --out datasets

Genera dataset solo da run locale              Ispeziona una singola snapshot
----------------------------------------        ------------------------------------------
python tools\make_snapshot_dataset.py          python tools\snapshot_inspect.py `
  --root logs\snapshots `                        --file local_data\rickybot_snapshots\...\*.json
  --out datasets

Report generale snapshot                       Report per gruppo
----------------------------------------        ------------------------------------------
python tools\snapshot_features_report.py       python tools\snapshot_features_report.py `
  --csv datasets\snapshot_index.csv              --csv datasets\snapshot_index.csv `
                                                 --group exchange
Esempi grouping:                               python tools\snapshot_features_report.py `
----------------------------------------          --csv datasets\snapshot_index.csv `
python tools\snapshot_features_report.py          --group side
  --csv datasets\snapshot_index.csv `           python tools\snapshot_features_report.py `
  --group pm_clean_ok                              --csv datasets\snapshot_index.csv `
python tools\snapshot_features_report.py          --group exchange --min-count 10
  --csv datasets\snapshot_index.csv `
  --group exchange --min-count 10               Report per simbolo
                                               ------------------------------------------
Preview outcome sequenziale (1 snapshot)       python tools\snapshot_report_by_symbol.py `
----------------------------------------          --csv datasets\snapshot_index.csv `
python tools\snapshot_outcome_seq_preview.py      --symbol BTCUSDT
  --file path\alla\snapshot.json


A7) NEAR-MISS & TELEMETRY                      A7) NEAR-MISS & TELEMETRY (SERVER)
----------------------------------------        ------------------------------------------
Near-miss report (DEV / log locale)            Near-miss report su log copiati dal server
----------------------------------------        ------------------------------------------
cd C:\Projects\crypto-bot                      cd C:\Projects\crypto-bot
& .\.venv\Scripts\Activate.ps1                 & .\.venv\Scripts\Activate.ps1
python tools\near_miss_report.py               python tools\near_miss_report.py `
  --limit 5                                      --limit 20


B) LOMS – LOCALE / DEV (Windows)               B) LOMS – SERVER / PAPER-SERVER
----------------------------------------        ------------------------------------------

B1) AVVIO SERVIZIO LOMS (DEV)                  B1) AVVIO SERVIZIO LOMS (SERVER)
----------------------------------------        ------------------------------------------
Attiva venv + avvia uvicorn (DEV)              tmux + uvicorn (PAPER-SERVER)
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             ssh root@<IP_SERVER>
& .\.venv\Scripts\Activate.ps1                cd ~/cryptonakcore-loms
cd services\cryptonakcore                     source .venv/bin/activate
uvicorn app.main:app --reload                 tmux ls
                                              # se non esiste:
Stop ordinato LOMS DEV                        tmux new -s loms-paper
----------------------------------------        # dentro loms-paper:
CTRL+C nel terminale dove gira uvicorn        cd ~/cryptonakcore-loms/services/cryptonakcore
                                              uvicorn app.main:app --host 0.0.0.0 --port 8000

                                              Staccarsi da loms-paper
                                              ------------------------------------------
                                              CTRL+b, poi d


B2) HEALTH & STATS (DEV)                       B2) HEALTH & STATS (SERVER)
----------------------------------------        ------------------------------------------
Health check DEV                               Health check PAPER-SERVER
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             cd ~/cryptonakcore-loms
& .\.venv\Scripts\Activate.ps1                source .venv/bin/activate
python tools\check_health.py                  python tools/check_health.py
# controlla:                                  # controlla:
#  Environment : dev                          #  Environment : paper
#  Broker mode: paper                         #  Broker mode: paper
#  OMS enabled: True                          #  OMS enabled: True

Stats DEV                                      Stats PAPER-SERVER
----------------------------------------        ------------------------------------------
python tools\print_stats.py                   cd ~/cryptonakcore-loms
                                              python tools/print_stats.py

Posizioni PAPER-SERVER (debug rapido)
----------------------------------------
cd ~/cryptonakcore-loms
curl -s http://127.0.0.1:8000/positions/ | python -m json.tool


B3) ENV LOMS & FILE (DEV)                      B3) ENV LOMS & FILE (SERVER)
----------------------------------------        ------------------------------------------
Aprire .env / .env.sample                      Controllo rapido .env server
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             cd ~/cryptonakcore-loms/services/cryptonakcore
code services\cryptonakcore\.env              sed -n '1,120p' .env
code services\cryptonakcore\.env.sample

Cartella dati LOMS DEV                         Cartella dati LOMS PAPER
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             cd ~/cryptonakcore-loms
dir services\cryptonakcore\data               ls services/cryptonakcore/data
# loms_dev.db                                  # loms_paper.db
# bounce_signals_dev.jsonl                     # bounce_signals_paper.jsonl


B4) TEST INTEGRAZIONE RICKYBOT → LOMS         B4) SHADOW MODE (SERVER)
----------------------------------------        ------------------------------------------
Test diretto /signals/bounce (DEV)            Verifica flag LOMS lato RickyBot
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             cd ~/RickyBot
& .\.venv\Scripts\Activate.ps1                source .venv/bin/activate
python tools\test_notify_loms.py              grep -E '^(LOMS_ENABLED|LOMS_BASE_URL)' .env
  --symbol TESTUSDT                           python tools/runtime_config_inspector.py --pretty
  --side long
  --price 100                                 Verifica Shadow Mode operativa
                                              ------------------------------------------
Test catena notifier RickyBot → LOMS DEV      - tmux attach -t rickybot-bitget (vedi alert)
(se presente)                                 - tmux attach -t rickybot-bybit
----------------------------------------        - tmux attach -t loms-paper (vedi log uvicorn)
cd C:\Projects\crypto-bot
& .\.venv\Scripts\Activate.ps1                Controlla che in LOMS:
python tools\test_notify_notifier_loms.py     ------------------------------------------
                                              - arrivino nuove posizioni su /positions
                                              - /stats mostri trade chiusi


B5) BACKUP & ROTAZIONE LOMS (DEV)             B5) BACKUP & ROTAZIONE LOMS (SERVER)
----------------------------------------        ------------------------------------------
Backup DEV                                    Backup PAPER-SERVER (manuale)
----------------------------------------        ------------------------------------------
cd C:\Projects\cryptonakcore-loms             cd ~/cryptonakcore-loms
& .\.venv\Scripts\Activate.ps1                mkdir -p backups
mkdir backups                                 # ferma uvicorn (in tmux: CTRL+C)
Copy-Item services\cryptonakcore\data\* `     mv services/cryptonakcore/data/loms_paper.db \
  backups\2025-12-01_loms_dev_*                 backups/$(date +%F)_loms_paper.db
                                              mv services/cryptonakcore/data/bounce_signals_paper.jsonl \
                                                backups/$(date +%F)_bounce_signals_paper.jsonl
                                              # riavvia uvicorn in tmux: loms-paper


C) MINI CHECKLIST SHADOW MODE                  C) MINI CHECKLIST SHADOW MODE (SERVER)
(LOCALE / DEV)                                ------------------------------------------
----------------------------------------
1. LOMS DEV attivo                            1. tmux ls → vedi:
   - `uvicorn app.main:app --reload`             - loms-paper
   - `python tools\check_health.py`              - rickybot-bitget
   - Environment=dev, Broker=paper               - rickybot-bybit

2. RickyBot DEV attivo                        2. python tools/check_health.py
   - `python -m bots.rickybot --top 5`           - Environment=paper, Broker=paper, OMS_ENABLED=True
   - `python tools\runner_status.py ...`

3. Test segnale fake → LOMS DEV               3. python tools/print_stats.py
   - `python tools\test_notify_loms.py`          - controlla total_positions, open_positions, tp/sl

4. Controlla /stats DEV                       4. Verifica log in tmux:
   - `python tools\print_stats.py`               - rickybot-* → alert LOMS OK
                                                  - loms-paper → ordini/posizioni creati/chiusi


D) EMERGENCY – Spegnere tutto in 60 secondi
===========================================

LOCALE / DEV (Windows)                         SERVER (Hetzner – RickyBot + LOMS)
-------------------------------------------    -------------------------------------------
1. Spegnere RickyBot DEV                      1. Fermare RickyBot (tmux)
-------------------------------------------    -------------------------------------------
- Vai nella finestra dove gira il runner      - Verifica le sessioni:

  (es. terminale con `python -m bots.rickybot`)  tmux ls

- Premi: CTRL+C                               - Per ogni sessione attiva del bot:

- Controlla che il prompt torni libero          tmux attach -t rickybot-bitget
                                                 CTRL+C          # ferma il bot
                                                 tmux kill-session -t rickybot-bitget

                                               (stesso per rickybot-bybit)

2. Spegnere LOMS DEV                          2. Fermare LOMS (tmux)
-------------------------------------------    -------------------------------------------
- Vai nel terminale dove gira `uvicorn`       - Attacca alla sessione LOMS:

  (es. `uvicorn app.main:app --reload`)         tmux attach -t loms-paper

- Premi: CTRL+C                               - Premi CTRL+C per fermare uvicorn

                                               - Chiudi la sessione (opzionale):

                                                 tmux kill-session -t loms-paper

3. Controllo finale DEV                       3. Controllo finale SERVER
-------------------------------------------    -------------------------------------------
- Nessun terminale con python che gira        - Controlla che non restino sessioni tmux:

- Facoltativo: controlla Task Manager           tmux ls

                                               - (Opzionale) controlla processi python:

                                                 ps aux | grep python


E) CHECK RAPIDO “PRE-NANNA”
===========================

LOCALE / DEV (facoltativo)                    SERVER (Hetzner – consigliato)
-------------------------------------------    -------------------------------------------
1. Se stai facendo girare DEV                 1. Controlla tmux
-------------------------------------------    -------------------------------------------
- Stato runner:                               - Verifica che le sessioni siano vive:

  cd C:\Projects\crypto-bot                     tmux ls
  & .\.venv\Scripts\Activate.ps1
  python tools\runner_status.py \
    --max-loops 20 --show-alerts 5

- Stato LOMS DEV:

  cd C:\Projects\cryptonakcore-loms
  & .\.venv\Scripts\Activate.ps1
  python tools\check_health.py
  python tools\print_stats.py

2. Snapshot / dataset (se stai testando)      2. Health & stats LOMS (SERVER)
-------------------------------------------    -------------------------------------------
- Se hai fatto un giro di test:               - Da ~/cryptonakcore-loms:

  python tools\make_snapshot_dataset.py          source .venv/bin/activate
    --root logs\snapshots --out datasets         python tools/check_health.py
                                                 python tools/print_stats.py

                                               Controlla che:

                                               - Environment : paper
                                               - Broker mode : paper
                                               - OMS enabled : True
                                               - open_positions sia 0
                                                 (o valore atteso)


3. Log veloci (DEV)                           3. Runner status (RickyBot SERVER)
-------------------------------------------    -------------------------------------------
- Se hai log su file:                         - Da ~/RickyBot:

  Get-Content .\logs\ross123.log -Tail 40       source .venv/bin/activate
                                                python tools/runner_status.py \
                                                  --max-loops 50 --show-alerts 10

                                              Controlla:

                                              - ultimo loop recente
                                              - watchlist sensata
                                              - ultimi alert ok


4. Nota mentale / TODO                        4. Nota mentale / TODO
-------------------------------------------    -------------------------------------------
- Se vedi qualcosa di strano,                 - Se vedi errori gravi nei log:
  scrivilo al volo in un file                  

  tipo `DEV_NOTES_TODAY.md`                    - valuta di:

                                                 1) fermare il bot (tmux → CTRL+C)
                                                 2) fermare LOMS (loms-paper → CTRL+C)
                                                 3) segnare l’orario / log di riferimento