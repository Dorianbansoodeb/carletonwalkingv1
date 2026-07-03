#!/usr/bin/env python3
"""Verify all cars route from lot entrance to exit using CarDriver.csv + schedule."""
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "CarDriver.csv"
TRIPS = ROOT / "CarDriver_trips.geojson"
SCHEDULE = ROOT / "resources" / "car_driver_schedule.csv"

COLONEL_BY = (45.3792575, -75.7004525)
BRONSON = (45.3896198, -75.694494)
EXIT_TOL_M = 80  # metres-ish via deg (~0.0007 lat)

LOTS = {
    "P1": {"spawn": (45.3814076, -75.7006193), "exit": COLONEL_BY},
    "P2": {"spawn": (45.3836355, -75.6962699), "exit": COLONEL_BY},
    "P3": {"spawn": (45.384003, -75.694052), "exit": COLONEL_BY},
    "P4": {"spawn": (45.3857089, -75.6950736), "exit": COLONEL_BY},
    "P5": {"spawn": (45.3879759, -75.6932794), "exit": BRONSON},
    "P6": {"spawn": (45.3885825, -75.6970087), "exit": BRONSON},
    "P7": {"spawn": (45.3888841, -75.6962336), "exit": BRONSON},
}
LOT_ORDER = list(LOTS.keys())


def dist_m(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    return math.hypot((lat2 - lat1) * 111_000, (lon2 - lon1) * 85_000)


def nearest_lot(lat, lon):
    return min(LOTS, key=lambda k: dist_m((lat, lon), LOTS[k]["spawn"]))


def near_exit(lat, lon, exit_pt):
    return dist_m((lat, lon), exit_pt) <= EXIT_TOL_M


def parse_clock(value: str) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(value)


def expected_spawns():
    rows = list(csv.DictReader(SCHEDULE.open(encoding="utf-8-sig")))
    per_lot = {}
    total = 0
    for i, lot in enumerate(LOT_ORDER[: len(rows)]):
        row = rows[i]
        start = parse_clock(row["startTime"])
        end = parse_clock(row["endTime"])
        interval = float(row["spawningIntervalInMinutes"])
        amount = int(row["spawningAmount"])
        n = 0
        t = start
        step = timedelta(minutes=interval)
        while t <= end:
            n += amount
            t += step
        per_lot[lot] = n
        total += n
    return total, per_lot


def analyze_csv():
    first = {}
    last = {}
    completed = set()
    spawn_lot = {}
    wrong_exit = []
    never_moved = []
    stuck_at_end = []

    with CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            aid = row["ID"]
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
            if aid not in first:
                first[aid] = (int(row["Step"]), lat, lon)
                lot = nearest_lot(lat, lon)
                spawn_lot[aid] = lot
                if dist_m((lat, lon), LOTS[lot]["spawn"]) > 500:
                    spawn_lot[aid] = f"{lot}? far"
            last[aid] = row
            if row["GoalReached"].lower() == "true":
                completed.add(aid)

    for aid, row in last.items():
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        lot_key = spawn_lot[aid] if isinstance(spawn_lot[aid], str) else spawn_lot[aid]
        if isinstance(lot_key, str):
            continue
        exit_pt = LOTS[lot_key]["exit"]
        if row["GoalReached"].lower() == "true":
            if not near_exit(lat, lon, exit_pt):
                wrong_exit.append((aid, lot_key, lat, lon, exit_pt))
        else:
            rem = float(row["RemainingRouteDistanceToGoal"])
            stuck_at_end.append((aid, lot_key, rem, lat, lon))

        s_step, slat, slon = first[aid]
        if dist_m((slat, slon), (lat, lon)) < 20 and row["GoalReached"].lower() != "true":
            never_moved.append(aid)

    return {
        "agents": len(first),
        "completed_csv": len(completed),
        "spawn_lot": spawn_lot,
        "wrong_exit": wrong_exit,
        "stuck_at_end": stuck_at_end,
        "never_moved": never_moved,
        "lot_counts": Counter(v for v in spawn_lot.values() if isinstance(v, str) is False),
    }


def main():
    if not CSV.is_file():
        print(f"Missing {CSV}")
        return

    expected, per_lot = expected_spawns()
    trips_n = 0
    if TRIPS.is_file():
        trips_n = len(json.loads(TRIPS.read_text(encoding="utf-8")).get("features", []))

    r = analyze_csv()
    lot_counts = Counter()
    for v in r["spawn_lot"].values():
        if v in LOTS:
            lot_counts[v] += 1

    print("=== Entrance → exit verification ===")
    print(f"Schedule expected spawns (uncapped): {expected}")
    print(f"Unique agents in CSV:              {r['agents']}")
    print(f"Completed (GoalReached in CSV):    {r['completed_csv']}")
    print(f"Completed trips (geojson):           {trips_n}")
    print()
    print("Agents per lot (by first GPS position):")
    for lot in LOT_ORDER:
        print(f"  {lot}: {lot_counts.get(lot, 0):4d}  (schedule planned {per_lot.get(lot, 0):4d})")
    print()
    print(f"Finished at wrong exit (>80m from target): {len(r['wrong_exit'])}")
    if r["wrong_exit"][:5]:
        for item in r["wrong_exit"][:5]:
            print(f"  {item[1]} id={item[0][:8]}... at {item[2]:.6f},{item[3]:.6f}")
    print(f"Not finished at sim end: {len(r['stuck_at_end'])}")
    if r["stuck_at_end"][:8]:
        for aid, lot, rem, lat, lon in sorted(r["stuck_at_end"], key=lambda x: -x[2])[:8]:
            print(f"  {lot} rem={rem:.0f}m id={aid[:8]}...")
    print()
    ok = (
        r["completed_csv"] == r["agents"]
        and len(r["wrong_exit"]) == 0
        and trips_n == r["completed_csv"]
    )
    if ok:
        print("PASS: Every agent in CSV reached the correct exit.")
    elif r["completed_csv"] >= r["agents"] * 0.95 and len(r["wrong_exit"]) == 0:
        print("MOSTLY OK: >95% completed at correct exit; some may still be driving or capped.")
    else:
        print("ISSUES: See counts above — not all entrance→exit runs completed correctly.")


if __name__ == "__main__":
    main()
