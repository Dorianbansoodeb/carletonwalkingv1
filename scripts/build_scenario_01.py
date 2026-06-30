#!/usr/bin/env python3
"""Build MARS resources matching DEVS scenario_01 (parking lot schedule)."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_graph_for_mars import ALL_LOTS, EXITS, LOT_EXIT, SPAWNS, patch_graph_for_mars

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
GRAPH = RESOURCES / "campus_drive_graph.geojson"
CAMPUS_REPO = (
    Path(__file__).resolve().parents[2] / ".." / ".." / "devs" / "model-campus-evacuation"
).resolve()
SCENARIO_SCHEDULE = CAMPUS_REPO / "input_data/parking_lot_schedules/scenario_01.csv"

# Match DEVS default max simulation time (seconds).
MAX_SIM_SECONDS = 15000
SIM_START = datetime(2021, 10, 11, 6, 0, 0)

SPAWN_FIELDS = [
    "releaseTime",
    "stableId",
    "startLat",
    "startLon",
    "destLat",
    "destLon",
]


def load_devs_schedule(path: Path) -> dict[str, dict[str, int]]:
    schedules: dict[str, dict[str, int]] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            schedules[row["id"]] = {
                "initEventInSec": int(row["initEventInSec"]),
                "periodInSec": int(row["periodInSec"]),
                "totalEvents": int(row["totalEvents"]),
            }
    return schedules


def write_spawn_csv(path: Path, schedules: dict[str, dict[str, int]]) -> int:
    rows = []
    total_cars = 0
    for lot_id in ALL_LOTS:
        lot = schedules[lot_id]
        init_sec = lot["initEventInSec"]
        period_sec = lot["periodInSec"]
        total_events = lot["totalEvents"]
        start_lon, start_lat = SPAWNS[lot_id]
        dest_lon, dest_lat = EXITS[LOT_EXIT[lot_id]]

        for index in range(total_events):
            release = SIM_START + timedelta(seconds=init_sec + index * period_sec)
            rows.append(
                {
                    "releaseTime": release.strftime("%Y-%m-%dT%H:%M:%S"),
                    "stableId": f"{lot_id}-{index + 1:04d}",
                    "startLat": start_lat,
                    "startLon": start_lon,
                    "destLat": dest_lat,
                    "destLon": dest_lon,
                }
            )
        total_cars += total_events

    rows.sort(key=lambda row: row["releaseTime"])

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SPAWN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return total_cars


def write_config(path: Path, spawn_file: str) -> None:
    sim_end = SIM_START + timedelta(seconds=MAX_SIM_SECONDS)
    config = {
        "id": "carleton_scenario_01",
        "globals": {
            "deltaT": 1,
            "startPoint": SIM_START.strftime("%Y-%m-%dT%H:%M:%S"),
            "endPoint": sim_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "deltaTUnit": "seconds",
            "console": True,
            "csvOptions": {"outputPath": "results"},
        },
        "agents": [{"name": "CarDriver", "output": "csv"}],
        "layers": [
            {"name": "CarLayer", "file": "resources/campus_drive_graph.geojson"},
            {
                "name": "CarletonParkingSchedulerLayer",
                "file": spawn_file,
            },
        ],
        "entities": [{"name": "Car", "output": "none", "file": "resources/car.csv"}],
    }
    path.write_text(json.dumps(config, indent=2))


def main() -> None:
    if not SCENARIO_SCHEDULE.is_file():
        raise SystemExit(f"Missing DEVS schedule: {SCENARIO_SCHEDULE}")
    if not GRAPH.is_file():
        raise SystemExit("Missing drive graph. Run: python scripts/build_drive_graph.py")

    patch_graph_for_mars(GRAPH)
    schedules = load_devs_schedule(SCENARIO_SCHEDULE)
    missing = [lot for lot in ALL_LOTS if lot not in schedules]
    if missing:
        raise SystemExit(f"scenario_01.csv missing lots: {', '.join(missing)}")

    spawn_path = RESOURCES / "scenario_01_spawns.csv"
    total_cars = write_spawn_csv(spawn_path, schedules)
    write_config(ROOT / "config_scenario_01.json", f"resources/{spawn_path.name}")

    print(f"Wrote {spawn_path} ({total_cars} timed vehicle releases)")
    print(f"Wrote {ROOT / 'config_scenario_01.json'} (sim window {MAX_SIM_SECONDS}s)")
    print("Per lot (init s, period s, count):")
    for lot in ALL_LOTS:
        s = schedules[lot]
        print(
            f"  {lot}: init={s['initEventInSec']}, period={s['periodInSec']}, "
            f"total={s['totalEvents']}"
        )


if __name__ == "__main__":
    main()
