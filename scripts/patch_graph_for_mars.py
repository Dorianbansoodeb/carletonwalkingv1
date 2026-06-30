#!/usr/bin/env python3
"""Post-process campus drive GeoJSON so MARS CarLayer can route all lots."""

from __future__ import annotations

import json
from pathlib import Path

# Nearest campus gate that MARS can route to from each lot (validated via validate_lots.py).
LOT_EXIT = {
    "P1": "colonel_by",
    "P2": "colonel_by",
    "P3": "colonel_by",
    "P4": "colonel_by",
    "P5": "bronson_university",
    "P6": "bronson_university",
    "P7": "bronson_university",
}

EXITS = {
    "colonel_by": (-75.7004525, 45.3792575),
    "bronson_university": (-75.694494, 45.3896198),
}

SPAWNS = {
    "P1": (-75.7008583198179, 45.38102036933288),
    "P2": (-75.696324145713646, 45.38390667961675),
    "P3": (-75.6919, 45.3847),
    "P4": (-75.69505807743009, 45.385682818310016),
    "P5": (-75.6950176, 45.3876035),
    "P6": (-75.6970087, 45.3885825),
    "P7": (-75.695952778837281, 45.388917569401215),
}

ALL_LOTS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]


def patch_graph_for_mars(path: Path) -> None:
    """Make parking connectors routable and promote non-car highway tags."""
    data = json.loads(path.read_text())
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        if props.get("osmid") is None:
            props["osmid"] = f"carleton-connector-{props['u']}-{props['v']}"
        highway = props.get("highway")
        if highway in ("service", "unclassified") or highway is None:
            props["highway"] = "tertiary"
    path.write_text(json.dumps(data))
