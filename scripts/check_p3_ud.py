#!/usr/bin/env python3
"""Check P3 agents stuck on University Drive in CarDriver.csv."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
csv_path = ROOT / "CarDriver.csv"

lots = {
    "P1": (45.3814076, -75.7006193),
    "P2": (45.3836355, -75.6962699),
    "P3": (45.384003, -75.694052),
    "P4": (45.3857089, -75.6950736),
    "P5": (45.3879759, -75.6932794),
    "P6": (45.3885825, -75.6970087),
    "P7": (45.3888841, -75.6962336),
}


def near(lat, lon, tlat, tlon, tol=0.003):
    return abs(lat - tlat) < tol and abs(lon - tlon) < tol


def classify_spawn(lat, lon):
    return min(
        lots.keys(),
        key=lambda n: (lat - lots[n][0]) ** 2 + (lon - lots[n][1]) ** 2,
    )


first = {}
last = {}
spawn_lot = {}

with csv_path.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        aid = row["ID"]
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        if aid not in first:
            first[aid] = row
            spawn_lot[aid] = classify_spawn(lat, lon)
        last[aid] = row

p3_ids = [aid for aid, lot in spawn_lot.items() if lot == "P3"]
print(f"Total unique agents in CSV: {len(first)}")
print(f"Agents spawned at P3: {len(p3_ids)}")

completed = sum(1 for aid in p3_ids if last[aid]["GoalReached"].lower() == "true")
print(f"P3 completed (GoalReached at last row): {completed}/{len(p3_ids)}")

stuck_p3 = [aid for aid in p3_ids if last[aid]["GoalReached"].lower() != "true"]
print(f"P3 still not at goal at last CSV row: {len(stuck_p3)}")

for aid in stuck_p3[:5]:
    r = last[aid]
    rem = float(r["RemainingRouteDistanceToGoal"])
    print(
        f"  stuck {aid[:8]}... step={r['Step']} "
        f"lat={float(r['Latitude']):.6f} lon={float(r['Longitude']):.6f} "
        f"rem={rem:.1f}m vel={float(r['Velocity']):.3f}"
    )

# University Drive corridor at screenshot time ~ 6:27:58 = 1678 s
T_SCREEN = 1678
T_WIN = 60
UD_MIN_LAT, UD_MAX_LAT = 45.375, 45.390
UD_MIN_LON, UD_MAX_LON = -75.702, -75.690

on_ud_by_lot = defaultdict(set)
p3_on_ud_samples = []

with csv_path.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        step = int(row["Step"])
        if abs(step - T_SCREEN) > T_WIN:
            continue
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        if UD_MIN_LAT <= lat <= UD_MAX_LAT and UD_MIN_LON <= lon <= UD_MAX_LON:
            aid = row["ID"]
            lot = spawn_lot.get(aid, "?")
            on_ud_by_lot[lot].add(aid)
            if lot == "P3" and len(p3_on_ud_samples) < 5:
                p3_on_ud_samples.append(
                    (step, lat, lon, float(row["RemainingRouteDistanceToGoal"]),
                     row["GoalReached"], float(row["Velocity"]))
                )

print(f"\nAgents in UD corridor near t={T_SCREEN}s (6:27) by spawn lot:")
for lot in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "unknown"]:
    if on_ud_by_lot[lot]:
        print(f"  {lot}: {len(on_ud_by_lot[lot])}")

print(f"\nP3 on University Drive at ~6:27: {len(on_ud_by_lot['P3'])}")
for s in p3_on_ud_samples:
    print(f"  step={s[0]} lat={s[1]:.6f} lon={s[2]:.6f} rem={s[3]:.1f} goal={s[4]} vel={s[5]:.3f}")

# P3 agents still on UD at end of sim with rem > 100m
late = []
for aid in p3_ids:
    r = last[aid]
    if r["GoalReached"].lower() == "true":
        continue
    lat, lon = float(r["Latitude"]), float(r["Longitude"])
    rem = float(r["RemainingRouteDistanceToGoal"])
    if UD_MIN_LAT <= lat <= UD_MAX_LAT and UD_MIN_LON <= lon <= UD_MAX_LON and rem > 100:
        late.append((aid, int(r["Step"]), lat, lon, rem, float(r["Velocity"])))

print(f"\nP3 unfinished, on UD corridor, rem>100m at last tick: {len(late)}")
for item in late[:10]:
    print(f"  {item[0][:8]}... step={item[1]} lat={item[2]:.6f} lon={item[3]:.6f} rem={item[4]:.0f}m")

# Gridlock check at screenshot time (step 1678 = 6:27:58)
rows_at_t = []
with csv_path.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if int(row["Step"]) == T_SCREEN:
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
            if UD_MIN_LAT <= lat <= UD_MAX_LAT and UD_MIN_LON <= lon <= UD_MAX_LON:
                aid = row["ID"]
                rows_at_t.append(
                    (
                        spawn_lot[aid],
                        float(row["Velocity"]),
                        float(row["RemainingRouteDistanceToGoal"]),
                        lat,
                        lon,
                        row["GoalReached"],
                    )
                )

stuck = [r for r in rows_at_t if r[1] < 0.5 and r[5].lower() == "false"]
moving = [r for r in rows_at_t if r[1] >= 0.5]
from collections import Counter

print(f"\nAt step {T_SCREEN} (6:27:58) on University Drive:")
print(f"  total agents: {len(rows_at_t)}")
print(f"  gridlocked (vel<0.5 m/s): {len(stuck)} by lot: {dict(Counter(r[0] for r in stuck))}")
print(f"  moving (vel>=0.5): {len(moving)} by lot: {dict(Counter(r[0] for r in moving))}")
p3_stuck = [r for r in stuck if r[0] == "P3"]
print(f"  P3 gridlocked: {len(p3_stuck)}")
for r in p3_stuck[:5]:
    print(f"    vel={r[1]:.3f} rem={r[2]:.1f}m lat={r[3]:.6f} lon={r[4]:.6f}")
