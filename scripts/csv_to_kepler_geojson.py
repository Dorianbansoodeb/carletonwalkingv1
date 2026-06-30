#!/usr/bin/env python3
"""Convert CarDriver.csv to Kepler-friendly GeoJSON (Dammtor-style trip lines)."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _parse_timestamp(row: dict, tick_interval_s: int = 1) -> int:
    raw = row.get("DateTime", "").strip()
    if raw:
        try:
            return int(datetime.fromisoformat(raw).timestamp())
        except ValueError:
            pass
    return int(row.get("Tick", 0)) * tick_interval_s


def csv_to_trips_geojson(
    csv_path: Path,
    out_path: Path,
    *,
    tick_interval: int = 1,
    group_field: str = "StableId",
) -> int:
    trips: dict[str, list[list[float]]] = defaultdict(list)
    meta: dict[str, dict] = {}

    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = row.get(group_field) or row.get("ID")
            if not key:
                continue
            lon = float(row["Longitude"])
            lat = float(row["Latitude"])
            ts = _parse_timestamp(row, tick_interval)
            trips[key].append([lon, lat, 0.0, ts])
            if key not in meta:
                meta[key] = {
                    "StableId": row.get("StableId", key),
                    "agent_type": "CarDriver",
                    "lot": row.get("StableId", key),
                }

    features = []
    for key, coords in trips.items():
        if len(coords) < 2:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": meta.get(key, {"StableId": key, "agent_type": "CarDriver"}),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2)
    )
    return len(features)


def csv_to_points_geojson(
    csv_path: Path,
    out_path: Path,
    *,
    tick_interval: int = 1,
    sample_every: int = 1,
) -> int:
    features = []
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if index % sample_every:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            float(row["Longitude"]),
                            float(row["Latitude"]),
                        ],
                    },
                    "properties": {
                        k: row[k]
                        for k in row
                        if k not in ("Latitude", "Longitude")
                    },
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2)
    )
    return len(features)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_csv = root / "bin" / "Debug" / "net8.0" / "results" / "CarDriver.csv"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=str(default_csv), help="CarDriver.csv path")
    parser.add_argument(
        "--out",
        default="",
        help="Output trips GeoJSON (default: <csv_dir>/CarDriver_trips.geojson)",
    )
    parser.add_argument(
        "--points",
        action="store_true",
        help="Also write CarDriver_points.geojson (sampled point layer)",
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=60,
        help="Keep every Nth row for points export (default: 60)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise SystemExit(f"Missing CSV: {csv_path}")

    trips_path = Path(args.out) if args.out else csv_path.parent / "CarDriver_trips.geojson"
    trip_count = csv_to_trips_geojson(csv_path, trips_path)
    print(f"Wrote {trips_path} ({trip_count} trips)")

    if args.points:
        points_path = csv_path.parent / "CarDriver_points.geojson"
        point_count = csv_to_points_geojson(
            csv_path, points_path, sample_every=args.sample_every
        )
        print(f"Wrote {points_path} ({point_count} points, every {args.sample_every} ticks)")


if __name__ == "__main__":
    main()
