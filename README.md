# SOHCarletonDrivingV1Box

Car-only campus evacuation for Carleton University (`CarDriver` on `CarLayer`).

## Quick start

```bash
cd ~/RiderProjects/model-soh/SOHCarletonDrivingV1Box
bash scripts/install.sh              # once: OSMnx venv
source .venv/bin/activate
python scripts/build_drive_graph.py  # OSM campus drive graph
python scripts/build_resources.py    # patch graph + car_drivers.csv + configs
dotnet build
python scripts/validate_lots.py      # optional: smoke-test all 7 lots
cd bin/Debug/net8.0
dotnet SOHCarletonDrivingV1Box.dll config_smoke.json   # 1 car, 5 min
dotnet SOHCarletonDrivingV1Box.dll config.json         # 7 cars, 6.5 h

# Kepler export (after a run):
cd ~/RiderProjects/model-soh/SOHCarletonDrivingV1Box
python scripts/csv_to_kepler_geojson.py
```

`dotnet build` copies `config*.json` and `resources/` into `bin/Debug/net8.0` automatically.

## Layout

```
SOHCarletonDrivingV1Box/
├── Program.cs
├── config.json / config_smoke.json
├── resources/
│   ├── campus_drive_graph.geojson
│   ├── car_drivers.csv          # one row per lot (P1–P7)
│   └── car.csv
└── scripts/
    ├── install.sh
    ├── build_drive_graph.py     # OSM download
    ├── build_resources.py       # configs + graph patch
    ├── patch_graph_for_mars.py  # spawn/exit definitions + connector fix
    └── validate_lots.py
```

## Run outputs

After the simulation, export GeoJSON for [kepler.gl](https://kepler.gl):

```bash
cd ~/RiderProjects/model-soh/SOHCarletonDrivingV1Box
python scripts/csv_to_kepler_geojson.py
# optional point layer (subsampled):
python scripts/csv_to_kepler_geojson.py --points --sample-every 60
```

Files land next to the CSV:

| File | Use in Kepler |
|------|----------------|
| `bin/Debug/net8.0/results/CarDriver.csv` | Raw traces |
| `bin/Debug/net8.0/results/CarDriver_trips.geojson` | **Trip lines** (one LineString per lot, time in 4th coord) |
| `bin/Debug/net8.0/results/CarDriver_points.geojson` | Point layer (with `--points`) |
| `bin/Debug/net8.0/resources/campus_drive_graph.geojson` | Road network (optional basemap) |

Drag `CarDriver_trips.geojson` into Kepler. Color by `lot` / `StableId`.

## Campus exits

| Lots | Exit |
|------|------|
| P1–P4 | Colonel By Drive (west) |
| P5–P7 | Bronson Ave & University Dr (north) |

Edit `scripts/patch_graph_for_mars.py`, then re-run `build_resources.py`.
