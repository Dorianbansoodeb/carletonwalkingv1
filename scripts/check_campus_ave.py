#!/usr/bin/env python3
"""Trip density on Campus Avenue (Kepler black-bar diagnosis)."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
trips_path = ROOT / "CarDriver_trips.geojson"
csv_path = ROOT / "CarDriver.csv"

# Campus Ave segment: P2 area → University Dr roundabout (from drive graph)
CA_MIN_LON, CA_MAX_LON = -75.69635, -75.69565
CA_MIN_LAT, CA_MAX_LAT = 45.3824, 45.3840

# Horizontal leg in screenshot (east-west into roundabout)
CA_H_MIN_LON, CA_H_MAX_LON = -75.69633, -75.69574
CA_H_MIN_LAT, CA_H_MAX_LAT = 45.38245, 45.38395


def on_campus_ave(lon, lat, horizontal_only=False):
    if horizontal_only:
        return CA_H_MIN_LON <= lon <= CA_H_MAX_LON and CA_H_MIN_LAT <= lat <= CA_H_MAX_LAT
    return CA_MIN_LON <= lon <= CA_MAX_LON and CA_MIN_LAT <= lat <= CA_MAX_LAT


data = json.loads(trips_path.read_text(encoding="utf-8"))
trips_through = 0
points_on_ca = 0
trips_through_h = 0

for feat in data.get("features", []):
    coords = feat.get("geometry", {}).get("coordinates", [])
    hit = False
    hit_h = False
    for c in coords:
        lon, lat = c[0], c[1]
        if on_campus_ave(lon, lat):
            points_on_ca += 1
            hit = True
        if on_campus_ave(lon, lat, horizontal_only=True):
            hit_h = True
    if hit:
        trips_through += 1
    if hit_h:
        trips_through_h += 1

print("=== Trips geojson (completed routes) ===")
print(f"Total completed trips: {len(data.get('features', []))}")
print(f"Trips with any point on Campus Ave: {trips_through}")
print(f"Trips through horizontal Campus Ave (screenshot bar): {trips_through_h}")
print(f"Coordinate points on Campus Ave (all trips): {points_on_ca}")

# Live traffic on Campus Ave at mid-evac from CSV
lots = {
    "P1": (45.3814076, -75.7006193),
    "P2": (45.3836355, -75.6962699),
    "P3": (45.384003, -75.694052),
    "P4": (45.3857089, -75.6950736),
    "P5": (45.3879759, -75.6932794),
    "P6": (45.3885825, -75.6970087),
    "P7": (45.3888841, -75.6962336),
}
first_lot = {}
on_ca_at = Counter()
stuck_at = 0
moving_at = 0
T = 2000  # ~6:33

with csv_path.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        aid = row["ID"]
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        if aid not in first_lot:
            first_lot[aid] = min(
                lots, key=lambda n: (lat - lots[n][0]) ** 2 + (lon - lots[n][1]) ** 2
            )
        if int(row["Step"]) != T:
            continue
        if on_campus_ave(lon, lat, horizontal_only=True):
            on_ca_at[first_lot[aid]] += 1
            v = float(row["Velocity"])
            if v < 0.5:
                stuck_at += 1
            else:
                moving_at += 1

print(f"\n=== CSV at step {T} (~6:33) on horizontal Campus Ave ===")
print(f"Agents present: {sum(on_ca_at.values())} (stuck {stuck_at}, moving {moving_at})")
print(f"By lot: {dict(on_ca_at)}")
