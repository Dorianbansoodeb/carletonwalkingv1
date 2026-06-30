#!/usr/bin/env python3
"""Run a MARS smoke test for each parking lot (spawn -> campus exit)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_graph_for_mars import ALL_LOTS, EXITS, LOT_EXIT, SPAWNS, patch_graph_for_mars

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "resources" / "campus_drive_graph.geojson"
BIN = ROOT / "bin" / "Debug" / "net8.0"


def _write_config(path: Path, lot: str) -> None:
    start_lon, start_lat = SPAWNS[lot]
    exit_key = LOT_EXIT[lot]
    dest_lon, dest_lat = EXITS[exit_key]
    config = {
        "id": f"validate_{lot}",
        "globals": {
            "deltaT": 1,
            "startPoint": "2021-10-11T06:00:00",
            "endPoint": "2021-10-11T06:30:00",
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
    path.write_text(json.dumps(config))


def main() -> int:
    if not GRAPH.is_file():
        print(f"Missing graph: {GRAPH}\nRun: python scripts/build_drive_graph.py", file=sys.stderr)
        return 1
    if not (BIN / "SOHCarletonDrivingV1Box.dll").is_file():
        print(f"Build first: cd {ROOT} && dotnet build", file=sys.stderr)
        return 1

    patch_graph_for_mars(GRAPH)
    resources = BIN / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    (resources / "campus_drive_graph.geojson").write_text(GRAPH.read_text())
    car_src = ROOT / "resources" / "car.csv"
    if car_src.is_file():
        (resources / "car.csv").write_text(car_src.read_text())

    failed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="validate_lots_") as tmp:
        tmp_path = Path(tmp)
        for lot in ALL_LOTS:
            cfg_path = tmp_path / f"{lot}.json"
            _write_config(cfg_path, lot)
            result = subprocess.run(
                ["dotnet", "SOHCarletonDrivingV1Box.dll", str(cfg_path)],
                cwd=BIN,
                capture_output=True,
                text=True,
            )
            ok = result.returncode == 0
            exit_key = LOT_EXIT[lot]
            status = "OK" if ok else "FAIL"
            print(f"{lot} -> {exit_key}: {status}")
            if not ok:
                failed.append(lot)
                tail = (result.stderr or result.stdout)[-400:]
                print(f"  {tail.strip()}")

    if failed:
        print(f"\nFailed lots: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\nAll {len(ALL_LOTS)} lots route off campus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
