import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "CarDriver_trips.geojson"
with p.open(encoding="utf-8") as f:
    # read only start of file
    head = f.read(5000)
start = head.find('"features"')
print(head[:start + 2000] if start > 0 else head[:3000])
