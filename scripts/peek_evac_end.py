#!/usr/bin/env python3
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "CarDriver.csv"
CONFIG_END_S = 11 * 3600 + 20 * 60  # 17:20 - 6:00

last_active = 0
last_step_in_csv = 0
active_at_end = 0

with CSV.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        step = int(float(row["Step"]))
        last_step_in_csv = step
        if row.get("CurrentlyCarDriving", "").lower() != "true":
            continue
        if row.get("GoalReached", "").lower() == "true":
            continue
        last_active = max(last_active, step)
        if step == last_step_in_csv:
            active_at_end += 1

print("config sim length (s)     :", CONFIG_END_S)
print("last Step in CSV (s)      :", last_step_in_csv)
print("auto evac end (s)         :", last_active)
print("same as full run?         :", last_active >= last_step_in_csv - 1)
print("hours evac end            :", f"{last_active // 3600}h {(last_active % 3600) // 60}m")
