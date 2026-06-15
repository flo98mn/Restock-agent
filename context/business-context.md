# Business context — Restock-agent v1

## Rol
Agentul precompletează Stoc_viitor cu cantitățile de comandat pe AER și TREN. NU trimite
comenzi, NU scrie în DB, NU contactează furnizori. Output = un xlsx pe care userul îl verifică
manual și îl importă în /supplier-orders/stock-report (Emag_integrator).

## Scope v1
- DOAR Comanda aer + Comanda tren. Comanda mare rămâne goală (v2 = regula de volum).
- Decizie la nivel de NicknameID. Exclude inactive (deja excluse din sursă).
- Offline: input xlsx local, output xlsx local. Fără MCP, fără DB, fără API.

## Fișier de intrare
data/reports/Raport stoc 3.0_YYYY_MM_DD.xlsx — se folosește cel mai recent după data din nume.

### Sheet "Stoc_viitor"
Coloanele NU sunt la poziții fixe: coloanele dinamice "Order: <nume> (<eta>, <status>)" se
intercalează după ETA. TOATE coloanele se localizează DUPĂ NUMELE din header (rândul 1).
Coloane folosite:
- "Nickname" (text)
- "Current Stock" = S (valoare)
- "PCS Sold in Last 30 Days" (valoare)
- "Order: ..." = cantitate dintr-o comandă existentă (placed/shipping), ca VALOARE.
  Suma tuturor coloanelor "Order: ..." = In (stoc pe drum).
- "Comanda aer", "Comanda tren" = coloanele pe care le COMPLETĂM.
- "Comanda mare", "Stock in ...", "Zile acoperire ..." = NU se ating (formule/proiecții).

### Sheet "Restock_tehnic"
O linie per nickname activ, aceeași populație ca Stoc_viitor (join pe NicknameID, fallback pe
Nickname). Coloane: NicknameID, Nickname, Furnizor, Baterie (1/0), Multiplu (50 cablu / 10 rest),
Greutate_kg, Volum_cm3 (ultimele două pot fi goale; neutilizate în v1).

## Algoritm cantitate (per nickname activ)
v    = (PCS Sold 30d / 30) * 1.1          # viteză zilnică, safety 1.1
S    = Current Stock
In   = suma coloanelor "Order: ..."        # stoc pe drum (valori)
mult = Multiplu (din Restock_tehnic)
ceil_to(x, m) = 0 dacă x<=0, altfel ceil(x/m)*m

NORMAL (Baterie=0 și furnizor != Kaka):
  qty_aer  = ceil_to(max(0, v*60  - S - In), mult)             # punte 60 zile (transit tren)
  qty_tren = ceil_to(max(0, v*180 - S - In - qty_aer), mult)   # top-up la 180 (=60 transit +120 acoperire)

BATERIE (Baterie=1):  # nu pe tren
  qty_aer  = ceil_to(max(0, v*60 - S - In), mult)              # orizont aer 60 zile
  qty_tren = 0

KAKA (Furnizor conține "kaka", case-insensitive):  # powerbank/ring light high-risk, niciodată tren
  qty_tren = 0
  qty_aer  = ceil_to(max(0, v*60 - S - In), mult)              # orizont aer 60 zile
  - Nickname începe cu "Starter" → comandă aer NORMALĂ (fără flag)
  - altfel → cantitate tot pe Comanda aer, dar CELULA marcată (formatare diferită) ca să
    semnaleze comanda aer SEPARATĂ high-risk.

## Reguli de business (rezumat)
- Inactive: excluse. Multipli: cablu ×50, rest ×10 (rotunjire în SUS), din Restock_tehnic.Multiplu.
- MOQ: există manual, nu în date — v1 nu aplică, userul validează.
- Buget/cash-flow, sezonalitate, multi-furnizor, Comanda mare/volum, curs BNR: toate v2.

## Output
output/stock_reports/Stoc_viitor_completat_YYYY_MM_DD.xlsx:
- Sheet "Stoc_viitor": compatibil cu importul, cu "Comanda aer"/"Comanda tren" completate +
  coloană "NicknameID"; celulele Kaka high-risk formatate distinct.
- Sheet "Restock_calcul": justificare per nickname (S, In, v, raw/qty aer/tren, flag baterie/Kaka).
