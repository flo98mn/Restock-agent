#!/usr/bin/env python3
"""
restock_planner.py — pasul de PLANIFICARE din pipeline-ul Restock-agent.

Determinist, fără LLM/rețea/DB/xlsx. Citește datasetul produs de stock-analyst
(data/cache/restock_dataset_*.json) și produce planul de comandă (cantități AER + TREN
per nickname) în data/cache/restock_plan_<report_date>.json.

NU scrie xlsx, NU modifică datasetul de intrare, NU atinge Stoc_viitor.
Vezi context/business-context.md pentru algoritm și rutare.
"""

import argparse
import glob
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DATE_RE = re.compile(r"(\d{4}_\d{2}_\d{2})")
DATASET_GLOB = os.path.join("data", "cache", "restock_dataset_*.json")


def die(msg):
    sys.stderr.write("EROARE: " + msg + "\n")
    sys.exit(1)


def ceil_to(x, m):
    """0 dacă x<=0; altfel rotunjire în SUS la cel mai apropiat multiplu de m."""
    if x <= 0:
        return 0
    if not m or m <= 0:
        # fără multiplu valid: rotunjire în sus la întreg, fără a inventa un multiplu
        return int(math.ceil(x))
    return int(math.ceil(x / m) * m)


def find_dataset(explicit):
    if explicit:
        if not os.path.isfile(explicit):
            die("fișierul --dataset nu există: " + explicit)
        return explicit
    candidates = glob.glob(DATASET_GLOB)
    if not candidates:
        die("niciun 'restock_dataset_*.json' în data/cache/ (rulează întâi stock-analyst)")
    dated = []
    for c in candidates:
        m = DATE_RE.search(os.path.basename(c))
        if m:
            dated.append((m.group(1), c))
    if not dated:
        die("niciun dataset cu dată (YYYY_MM_DD) în nume în data/cache/")
    dated.sort(key=lambda t: t[0])
    return dated[-1][1]


def plan_product(p):
    nickname = p["nickname"]
    name_l = (nickname or "").lower()
    supplier = p.get("supplier")
    battery = p.get("battery", 0)
    mult = p.get("multiple", 0)

    S = p.get("current_stock", 0) or 0
    In = p.get("incoming", 0) or 0
    sold30 = p.get("pcs_sold_30d", 0) or 0
    v = (sold30 / 30.0) * 1.1

    # Detecție baterie (v1: flag + keyword fallback)
    is_battery = (battery == 1) or ("powerbank" in name_l) or ("power bank" in name_l)
    battery_source = "flag" if battery == 1 else ("keyword" if is_battery else None)

    # Detecție Kaka (pe furnizor)
    is_kaka = "kaka" in (supplier or "").lower()

    # Rutare: Kaka > Baterie > Normal
    if is_kaka:
        route = "kaka"
        raw_aer = v * 60 - S - In
        qty_aer = ceil_to(max(0, raw_aer), mult)
        raw_tren = 0.0
        qty_tren = 0
        kaka_high_risk = not name_l.startswith("starter")
    elif is_battery:
        route = "battery"
        raw_aer = v * 60 - S - In
        qty_aer = ceil_to(max(0, raw_aer), mult)
        raw_tren = 0.0
        qty_tren = 0
        kaka_high_risk = False
    else:
        route = "normal"
        raw_aer = v * 60 - S - In
        qty_aer = ceil_to(max(0, raw_aer), mult)
        raw_tren = v * 180 - S - In - qty_aer
        qty_tren = ceil_to(max(0, raw_tren), mult)
        kaka_high_risk = False

    return {
        "nickname_id": p.get("nickname_id"),
        "nickname": nickname,
        "supplier": supplier,
        "route": route,
        "battery_source": battery_source,
        "kaka_high_risk": kaka_high_risk,
        "current_stock": S,
        "incoming": In,
        "pcs_sold_30d": sold30,
        "v_daily": round(v, 4),
        "multiple": mult,
        "raw_aer": round(raw_aer, 4),
        "qty_aer": qty_aer,
        "raw_tren": round(raw_tren, 4),
        "qty_tren": qty_tren,
    }


def main():
    ap = argparse.ArgumentParser(description="Restock-agent: planner cantități AER + TREN.")
    ap.add_argument("--dataset", help="cale către un dataset JSON anume (override auto-detect)")
    args = ap.parse_args()

    dataset_file = find_dataset(args.dataset)
    with open(dataset_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    src_meta = data.get("meta", {})
    report_date = src_meta.get("report_date")
    if not report_date:
        m = DATE_RE.search(os.path.basename(dataset_file))
        report_date = m.group(1) if m else "unknown"

    products_in = data.get("products", [])
    plan = [plan_product(p) for p in products_in]
    plan.sort(key=lambda r: (r["nickname_id"] is None, r["nickname_id"] or 0, r["nickname"]))

    by_route = {"normal": 0, "battery": 0, "kaka": 0}
    battery_by_source = {"flag": 0, "keyword": 0}
    with_air = 0
    with_train = 0
    for r in plan:
        by_route[r["route"]] = by_route.get(r["route"], 0) + 1
        if r["battery_source"] in battery_by_source:
            battery_by_source[r["battery_source"]] += 1
        if r["qty_aer"] > 0:
            with_air += 1
        if r["qty_tren"] > 0:
            with_train += 1

    meta = {
        "dataset_file": os.path.basename(dataset_file),
        "report_date": report_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "products_total": len(plan),
        "with_air": with_air,
        "with_train": with_train,
        "by_route": by_route,
        "battery_by_source": battery_by_source,
    }

    out_dir = os.path.join("data", "cache")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "restock_plan_" + report_date + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "products": plan}, f, ensure_ascii=False, indent=2)

    # Sumar stdout
    print("=== restock_planner ===")
    print("dataset_file :", meta["dataset_file"])
    print("report_date :", meta["report_date"])
    print("products_total :", meta["products_total"])
    print("by_route :", by_route)
    print("with_air :", with_air, "| with_train :", with_train)
    print("battery_by_source :", battery_by_source)
    print("output :", out_path)
    print("--- exemple produse ---")

    def first(pred):
        for r in plan:
            if pred(r):
                return r
        return None

    ex_normal_tren = first(lambda r: r["route"] == "normal" and r["qty_tren"] > 0)
    ex_kaka = first(lambda r: r["route"] == "kaka")
    ex_zero = first(lambda r: r["qty_aer"] == 0 and r["qty_tren"] == 0)
    for label, r in [("normal+tren", ex_normal_tren), ("kaka", ex_kaka),
                     ("well-stocked", ex_zero)]:
        if r:
            print("  [" + label + "]", json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
