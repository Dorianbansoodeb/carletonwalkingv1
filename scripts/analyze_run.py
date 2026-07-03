#!/usr/bin/env python3
"""Summarize a MARS scheduler run — deployed vs completed, charts like DEVS."""
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SCHEDULE = ROOT / "resources" / "car_driver_schedule.csv"
DEVS_TARGET = 3200
LOT_COUNTS = {"P1": 100, "P2": 100, "P3": 200, "P4": 100, "P5": 700, "P6": 900, "P7": 1100}
LOT_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]


def parse_clock(value: str) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Bad time: {value}")


def spawns_for_row(row) -> int:
    start = parse_clock(row["startTime"])
    end = parse_clock(row["endTime"])
    interval = float(row["spawningIntervalInMinutes"])
    amount = int(row["spawningAmount"])
    if interval <= 0:
        return amount
    total = 0
    t = start
    step = timedelta(minutes=interval)
    while t <= end:
        total += amount
        t += step
    return total


def read_schedule(path: Path):
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    per_lot = {lot: spawns_for_row(rows[i]) for i, lot in enumerate(LOT_ORDER[: len(rows)])}
    return sum(per_lot.values()), per_lot


def analyze_csv(path: Path):
    completed_ids = set()
    rows_per_step = Counter()
    agents_per_step = defaultdict(set)
    goal_true_rows = 0

    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            step = int(row["Step"])
            rows_per_step[step] += 1
            agent_id = row.get("ID", "")
            if agent_id:
                agents_per_step[step].add(agent_id)
            if row.get("GoalReached", "").lower() == "true":
                goal_true_rows += 1
                completed_ids.add(agent_id)

    # One CSV row per active CarDriver per tick ≈ cars on campus that second.
    cars_per_step = Counter(
        {step: len(ids) if ids else rows_per_step[step] for step, ids in agents_per_step.items()}
    )
    for step, count in rows_per_step.items():
        if step not in cars_per_step:
            cars_per_step[step] = count

    curve = sorted(cars_per_step.items())
    return len(completed_ids), goal_true_rows, curve, sum(rows_per_step.values())


def count_trips(path: Path) -> int:
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data.get("features", []))


def write_outputs(expected, per_lot, completed_csv, goal_rows, trips, curve, csv_rows, evac_end_s=0):
    RESULTS.mkdir(exist_ok=True)

    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "expected_deployed",
                "devs_target",
                "completed_trips_geojson",
                "completed_unique_ids_csv",
                "goal_reached_rows_csv",
                "completion_rate_pct",
                "csv_tick_rows",
                "evac_end_s",
            ],
        )
        w.writeheader()
        rate = (trips / expected * 100.0) if expected else 0.0
        w.writerow(
            {
                "expected_deployed": expected,
                "devs_target": DEVS_TARGET,
                "completed_trips_geojson": trips,
                "completed_unique_ids_csv": completed_csv,
                "goal_reached_rows_csv": goal_rows,
                "completion_rate_pct": round(rate, 2),
                "csv_tick_rows": csv_rows,
                "evac_end_s": evac_end_s,
            }
        )

    with (RESULTS / "lot_deploy_plan.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lot", "schedule_spawns", "devs_target"])
        w.writeheader()
        for lot in LOT_ORDER:
            w.writerow(
                {
                    "lot": lot,
                    "schedule_spawns": per_lot.get(lot, 0),
                    "devs_target": LOT_COUNTS[lot],
                }
            )

    with (RESULTS / "evac_curve.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "total_cars_driving_on_campus"])
        w.writerows(curve)

    plt.figure(figsize=(6, 4))
    plt.bar(
        ["Expected\n(schedule)", "DEVS\ntarget", "Completed\n(trips)"],
        [expected, DEVS_TARGET, trips],
        color=["#4c72b0", "#8172b2", "#c44e52"],
    )
    plt.ylabel("Vehicles")
    plt.title("Deployment vs completion")
    plt.tight_layout()
    plt.savefig(RESULTS / "summary.png", dpi=200)
    plt.close()

    if curve:
        times, cars = zip(*curve)
        avg_all = sum(cars) / len(cars)
        avg_spawn = sum(c for t, c in curve if t <= 60) / max(1, sum(1 for t, _ in curve if t <= 60))
        plt.figure(figsize=(8, 4))
        plt.plot(times, cars)
        plt.xlabel("Time (s)")
        plt.ylabel("Total Cars Driving on Campus")
        plt.title("Evacuation Curve")
        plt.suptitle(f"Avg(t≤60s)={avg_spawn:.2f}   Avg(all)={avg_all:.2f}", fontsize=9, y=0.98)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(RESULTS / "evac_curve.png", dpi=200)
        plt.close()


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "CarDriver.csv"
    trips_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "CarDriver_trips.geojson"

    expected, per_lot = read_schedule(SCHEDULE)
    trips = count_trips(trips_path)

    if csv_path.is_file():
        completed_csv, goal_rows, curve, csv_rows = analyze_csv(csv_path)
        evac_end_s = max((t for t, c in curve if c > 0), default=0)
    else:
        completed_csv, goal_rows, curve, csv_rows = 0, 0, [], 0
        evac_end_s = 0
        print(f"Note: {csv_path.name} not found — using trips geojson only (saves RAM on long runs).")

    write_outputs(expected, per_lot, completed_csv, goal_rows, trips, curve, csv_rows, evac_end_s)

    print("=== MARS run summary ===")
    print(f"Expected deployed (schedule) : {expected}")
    print(f"DEVS scenario 01 target      : {DEVS_TARGET}")
    print(f"Completed (trips geojson)    : {trips}")
    print(f"Completion rate              : {trips / expected * 100:.2f}%" if expected else "n/a")
    print(f"CSV tick rows                : {csv_rows}")
    if evac_end_s:
        print(f"Evac end (last car on campus): t={evac_end_s}s")
    print(f"Output folder                : {RESULTS}")
    print()
    print("Note: trips geojson = finished drives only.")
    print("      Scheduler spawns often share one agent ID in CSV — use trips for completions.")


if __name__ == "__main__":
    main()
