# SOHCarletonWalkingBox

Carleton campus car evacuation (scenario 01). Based on [SOHTravellingBox](../SOHTravellingBox).

## Run

```bash
dotnet build
dotnet run --project SOHCarletonWalkingBox.csproj                    # scenario 01 (config.json)
dotnet run --project SOHCarletonWalkingBox.csproj -- config_test.json  # smoke: 1 car per lot at t=0
```

## Output

After the run, open in [kepler.gl](https://kepler.gl):

- `bin/Debug/net8.0/results/CarDriver_trips.geojson` — trip lines (primary)

## Resources

| File | Role |
|------|------|
| `resources/campus_drive_graph.geojson` | OSM drive network |
| `resources/car_driver_schedule.csv` | P1–P7 spawn schedule (DEVS scenario_01) |
| `resources/car_drivers_test.csv` | Test: 7 cars at t=0 (`config_test.json`) |
| `resources/car_driver_schedule.csv` | Scenario 01 timed spawns (`config.json`) |
| `resources/car.csv` | Vehicle template |

Graph: export from [blueprint-geovector](https://github.com/MARS-Group-HAW/blueprint-geovector) or replace `campus_drive_graph.geojson` with your own AOI export.
