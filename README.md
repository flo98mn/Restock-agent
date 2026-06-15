# Restock-agent

Agent Claude Code care **precompletează** raportul `Stoc_viitor` cu cantitățile de comandat pe
**Comanda aer** și **Comanda tren**, pe baza vânzărilor, stocului curent și a stocului aflat pe
drum. Rezultatul este un xlsx pe care îl verifici manual înainte de import — agentul **nu**
trimite comenzi.

## Scope v1
- **Offline**, file-in / file-out. Fără MCP, fără DB, fără API.
- Doar **Comanda aer** + **Comanda tren**. `Comanda mare` rămâne goală (v2).
- Decizie la nivel de **NicknameID**. Produsele inactive sunt deja excluse din sursă.

## Input / Output
- **Input:** `data/reports/Raport stoc 3.0_YYYY_MM_DD.xlsx` (se folosește cel mai recent după
  data din nume). Sheet-uri folosite: `Stoc_viitor` și `Restock_tehnic`.
- **Output:** `output/stock_reports/` — copia `Stoc_viitor` completată + un sheet de justificare.
  Fișierul sursă din `data/reports/` **nu** se modifică.

## Business
Toată logica de business și algoritmul de cantitate sunt în
[`context/business-context.md`](context/business-context.md). Citește-l înainte de orice run.

## Subagenți
Pipeline-ul (`stock-analyst` → `restock-planner` → `report-writer`) se adaugă în prompturi
ulterioare. Vezi [`CLAUDE.md`](CLAUDE.md).
