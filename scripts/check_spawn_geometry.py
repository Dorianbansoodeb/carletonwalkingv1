#!/usr/bin/env python3
import csv
import json
import math

LOTS = {
    "P1": (45.3814076, -75.7006193),
    "P2": (45.3836355, -75.6962699),
    "P3": (45.384003, -75.694052),
    "P4": (45.3857089, -75.6950736),
    "P5": (45.3879759, -75.6932794),
    "P6": (45.3885825, -75.6970087),
    "P7": (45.3888841, -75.6962336),
}


def dist(a, b):
    return math.hypot((b[0] - a[0]) * 111_000, (b[1] - a[1]) * 85_000)


first = {}
with open("CarDriver.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        aid = row["ID"]
        if aid not in first:
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
            lot = min(LOTS, key=lambda k: dist((lat, lon), LOTS[k]))
            first[aid] = (lot, dist((lat, lon), LOTS[lot]))

far = [(aid, lot, d) for aid, (lot, d) in first.items() if d > 150]
print("Spawn distance from lot (>150m):", len(far))
if far[:5]:
    print(" examples:", far[:5])

with open("CarDriver_trips.geojson", encoding="utf-8") as f:
    gj = json.load(f)

ratios = []
def flatten_coords(geom):
    t = geom["type"]
    c = geom["coordinates"]
    if t == "LineString":
        return c
    if t == "MultiLineString":
        out = []
        for line in c:
            out.extend(line)
        return out
    return []


for feat in gj["features"][:500]:
    coords = flatten_coords(feat["geometry"])
    if len(coords) < 2:
        continue
    lon1, lat1 = coords[0][0], coords[0][1]
    lon2, lat2 = coords[-1][0], coords[-1][1]
    chord = dist((lat1, lon1), (lat2, lon2))
    path = sum(
        dist((coords[i][1], coords[i][0]), (coords[i + 1][1], coords[i + 1][0]))
        for i in range(len(coords) - 1)
    )
    ratios.append(path / max(chord, 1))

print(
    "Trip path/chord ratio (500 samples): min",
    min(ratios),
    "median",
    sorted(ratios)[250],
    "max",
    max(ratios),
)
print("Nearly straight trips (ratio<1.05):", sum(1 for r in ratios if r < 1.05), "/ 500")
