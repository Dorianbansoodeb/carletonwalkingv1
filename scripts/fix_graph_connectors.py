#!/usr/bin/env python3
"""Remove straight shortcut connectors from campus drive graph."""
import json
from pathlib import Path

GRAPH = Path(__file__).resolve().parents[1] / "resources" / "campus_drive_graph.geojson"
REMOVE_NAMES = {"Stadium Exit connector", "Ravensrd Exit connector"}

data = json.loads(GRAPH.read_text(encoding="utf-8"))
before = len(data["features"])
data["features"] = [
    f for f in data["features"]
    if f.get("properties", {}).get("name") not in REMOVE_NAMES
]
after = len(data["features"])
GRAPH.write_text(json.dumps(data), encoding="utf-8")
print(f"Removed {before - after} connector edges from {GRAPH.name} ({after} edges remain)")
