# Scenario: Carleton driving v1

## Scope

- **Campus:** Carleton University, Ottawa
- **Agents:** 7 `CarDriver` agents (P1–P7), spawned at t=0 via `car_drivers.csv`
- **Graph:** `resources/campus_drive_graph.geojson` (OSM + parking connectors)
- **Window:** 2021-10-11 06:00–12:30, Δt = 1 s

## Lot → campus exit

| Lots | Exit |
|------|------|
| P1–P4 | Colonel By Drive (west) |
| P5–P7 | Bronson Ave & University Dr (north) |

## Run

```bash
dotnet build
cd bin/Debug/net8.0
dotnet SOHCarletonDrivingV1Box.dll config.json          # 7 cars, t=0
dotnet SOHCarletonDrivingV1Box.dll config_scenario_01.json  # DEVS scenario_01 (3200 cars)
```

### DEVS scenario_01 match

Regenerate schedule from `model-campus-evacuation` then run:

```bash
python scripts/build_scenario_01.py
dotnet build
cd bin/Debug/net8.0
dotnet SOHCarletonDrivingV1Box.dll config_scenario_01.json
```

| Lot | Cars | Release |
|-----|------|---------|
| P1 | 100 | every 5 s from t=0 |
| P2 | 100 | every 5 s from t=0 |
| P3 | 200 | every 5 s from t=0 |
| P4 | 100 | every 5 s from t=0 |
| P5 | 700 | every 5 s from t=0 |
| P6 | 900 | every 5 s from t=0 |
| P7 | 1100 | every 5 s from t=0 |

Simulation window: **15000 s** (matches DEVS default `-m`). Exits: P1–P4 → Colonel By; P5–P7 → Bronson.

Outputs: `results/CarDriver.csv` → run `python scripts/csv_to_kepler_geojson.py` for `CarDriver_trips.geojson` (Kepler).
