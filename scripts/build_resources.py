#!/usr/bin/env python3
"""Generate MARS CarDriver resources for SOHCarletonDrivingV1Box."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_graph_for_mars import ALL_LOTS, EXITS, LOT_EXIT, SPAWNS, patch_graph_for_mars

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
GRAPH = RESOURCES / "campus_drive_graph.geojson"

CAR_DRIVER_FIELDS = [
    "length",
    "maxAcceleration",
    "maxDeceleration",
    "maxSpeed",
    "driveMode",
    "startLat",
    "startLon",
    "destLat",
    "destLon",
    "stableId",
    "osmRoute",
    "trafficCode",
]


def write_car_drivers_csv(path: Path, lot_ids: list[str]) -> None:
    rows = []
    for lot_id in lot_ids:
        start_lon, start_lat = SPAWNS[lot_id]
        exit_key = LOT_EXIT[lot_id]
        dest_lon, dest_lat = EXITS[exit_key]
        rows.append(
            {
                "length": 4.5,
                "maxAcceleration": 0.73,
                "maxDeceleration": 1.67,
                "maxSpeed": 13.89,
                "driveMode": 3,
                "startLat": start_lat,
                "startLon": start_lon,
                "destLat": dest_lat,
                "destLon": dest_lon,
                "stableId": lot_id,
                "osmRoute": "",
                "trafficCode": "german",
            }
        )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAR_DRIVER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_full_config(path: Path, lot_ids: list[str], end_time: str, sim_id: str) -> None:
    config = {
        "id": sim_id,
        "globals": {
            "deltaT": 1,
            "startPoint": "2021-10-11T06:00:00",
            "endPoint": f"2021-10-11T{end_time}:00",
            "deltaTUnit": "seconds",
            "console": True,
            "csvOptions": {"outputPath": "results"},
        },
        "agents": [
            {
                "name": "CarDriver",
                "output": "csv",
                "count": len(lot_ids),
                "file": "resources/car_drivers.csv",
            }
        ],
        "layers": [
            {
                "name": "CarLayer",
                "file": "resources/campus_drive_graph.geojson",
            }
        ],
        "entities": [{"name": "Car", "output": "none", "file": "resources/car.csv"}],
    }
    path.write_text(json.dumps(config, indent=2))


def write_smoke_config(path: Path) -> None:
    start_lon, start_lat = SPAWNS["P1"]
    dest_lon, dest_lat = EXITS[LOT_EXIT["P1"]]
    config = {
        "id": "carleton_driving_v1_smoke",
        "globals": {
            "deltaT": 1,
            "startPoint": "2021-10-11T06:00:00",
            "endPoint": "2021-10-11T06:05:00",
            "deltaTUnit": "seconds",
            "console": True,
            "csvOptions": {"outputPath": "results"},
        },
        "agents": [
            {
                "name": "CarDriver",
                "output": "csv",
                "count": 1,
                "individual": [
                    {"parameter": "driveMode", "value": 3},
                    {"parameter": "startLat", "value": start_lat},
                    {"parameter": "startLon", "value": start_lon},
                    {"parameter": "destLat", "value": dest_lat},
                    {"parameter": "destLon", "value": dest_lon},
                ],
            }
        ],
        "layers": [{"name": "CarLayer", "file": "resources/campus_drive_graph.geojson"}],
        "entities": [{"name": "Car", "output": "none", "file": "resources/car.csv"}],
    }
    path.write_text(json.dumps(config, indent=2))


def ensure_graph() -> None:
    if not GRAPH.is_file():
        raise SystemExit(
            "Missing drive graph. Run:\n"
            "  bash scripts/install.sh\n"
            "  python scripts/build_drive_graph.py"
        )
    patch_graph_for_mars(GRAPH)


def main() -> None:
    RESOURCES.mkdir(parents=True, exist_ok=True)
    ensure_graph()

    write_car_drivers_csv(RESOURCES / "car_drivers.csv", ALL_LOTS)
    write_full_config(ROOT / "config.json", ALL_LOTS, "12:30", "carleton_driving_v1")
    write_smoke_config(ROOT / "config_smoke.json")

    car_src = ROOT.parent / "SOHTravellingBox" / "resources" / "car.csv"
    if car_src.is_file():
        shutil.copy2(car_src, RESOURCES / "car.csv")

    for legacy in RESOURCES.glob("travellers*.csv"):
        legacy.unlink()

    print(f"Wrote graph + car_drivers.csv ({len(ALL_LOTS)} lots) under {RESOURCES}")
    print("Campus exits:")
    for lot in ALL_LOTS:
        print(f"  {lot} -> {LOT_EXIT[lot]}")


if __name__ == "__main__":
    main()
