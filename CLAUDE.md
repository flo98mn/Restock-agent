# Restock-agent — orchestrator

## Ce este
Pipeline Claude Code care precompletează raportul Stoc_viitor cu cantitățile de comandat pe
AER și TREN, pentru produsele din Raport stoc 3.0 (Emag_integrator). Detaliile de business și
algoritmul complet sunt în context/business-context.md — citește-l înainte de orice run.

## REGULI CRITICE (NEGOCIABIL ZERO)
- Agentul DOAR precompletează un xlsx. NU trimite comenzi, NU scrie în DB, NU apelează
  furnizori, NU face apeluri de rețea în v1.
- Output exclusiv în output/stock_reports/. NU modifica fișierul sursă din data/reports/.
- DOAR Comanda aer + Comanda tren. Comanda mare rămâne goală (v2).
- Exclude produsele inactive (nu re-introduce nimic ce lipsește din sursă).
- Decizie la nivel de NicknameID.
- Localizează coloanele din Stoc_viitor DUPĂ HEADER (rândul 1), niciodată după index fix.
- Userul verifică manual înainte de import; agentul nu continuă fluxul de comandă.

## Pipeline (subagenți — se adaugă în prompturi ulterioare)
1. stock-analyst   — citește Stoc_viitor + Restock_tehnic, construiește datasetul per nickname.
2. restock-planner — aplică algoritmul + rutarea baterii/Kaka + multipli.
3. report-writer   — scrie xlsx-ul de output (Stoc_viitor completat + sheet de justificare).

## Surse de date (v1, offline)
- data/reports/Raport stoc 3.0_YYYY_MM_DD.xlsx → sheet-urile Stoc_viitor și Restock_tehnic.
- Fără MCP, fără DB, fără endpoint live.

## Rulare end-to-end
Pipeline-ul v1 se rulează cu o singură comandă (orchestrare deterministă, fără pași LLM):

    python scripts/run_pipeline.py

Lanțuiește stock-analyst → restock-planner → report-writer, oprește la prima eroare și afișează
calea fișierului final din output/stock_reports/. Pentru un raport anume:

    python scripts/run_pipeline.py --report "data/reports/Raport stoc 3.0_YYYY_MM_DD.xlsx"

Subagenții (.claude/agents/) rămân disponibili pentru rulare/validare individuală a unui pas.
