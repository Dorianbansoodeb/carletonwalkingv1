# Carleton campus car evacuation (MARS / SOH)

Scenario 01: scheduler-based car evacuation on the **blueprint Jupyter drive graph** (`edges_drive.geojson` → `resources/campus_drive_graph.geojson`).

## Prerequisites

- .NET 8
- Python 3 with `matplotlib` (for analysis plots)
- `SOHModel` project reference (sibling folder `../SOHModel`)

## Workflow

```
1. Run simulation
2. Analyze run (CSV + trips geojson)
3. Build heatmap matrix (CSV → DEVS-format matrix)
4. Plot heatmap
```

Optional checks after step 2: `verify_entrance_exit.py`, `explain_spawn_gap.py`.

---

### 1. Run simulation

From this folder:

```powershell
cd C:\Users\doria\Documents\model-soh\carletonwalkingv1
dotnet run --project SOHCarletonWalkingBox.csproj
```

Uses `config.json` by default (~3200 cars, full day). Outputs in the project root:

| File | Purpose |
|------|---------|
| `CarDriver.csv` | Per-tick agent state (large on full runs) |
| `CarDriver_trips.geojson` | Completed trips only — **use for completion counts** |

Short smoke test with CSV:

```powershell
dotnet run --project SOHCarletonWalkingBox.csproj -- config_with_csv.json
```

---

### 2. Analyze run

Evacuation curve, deployment summary, completion rate (matches DEVS-style charts):

```bash
# WSL / Linux
cd carletonwalkingv1
python3 scripts/analyze_run.py
```

Or with explicit paths:

```bash
python3 scripts/analyze_run.py CarDriver.csv CarDriver_trips.geojson
```

Writes to **`results/`**:

| File | Content |
|------|---------|
| `summary.csv` | Expected vs completed, completion rate |
| `evac_curve.csv` | Time (s) vs cars on campus |
| `evac_curve.png` | Evacuation curve plot |
| `summary.png` | Deployed vs completed bar chart |
| `lot_deploy_plan.csv` | Per-lot schedule counts |

**Note:** For scheduler runs, trust **`CarDriver_trips.geojson`** for completions, not unique IDs in the CSV.

Optional verification:

```bash
python3 scripts/verify_entrance_exit.py   # lot → exit checks
python3 scripts/explain_spawn_gap.py      # why each lot is −12 vs schedule
```

---

### 3. Build heatmap matrix

Same format as DEVS `heatmap_matrix.csv` (20 sim-road columns, vehicles per 100 m, 1 s steps).

**End time is automatic by default:** scans `CarDriver.csv` for the last second any car is still driving (`CurrentlyCarDriving=true`, `GoalReached=false`) — i.e. when the last car leaves campus. Use `--max-time 6000` only if you want to match the DEVS plot window for side-by-side comparison.

```bash
python3 scripts/build_heatmap_matrix.py
```

Optional fixed cap (DEVS comparison window):

```bash
python3 scripts/build_heatmap_matrix.py --max-time 6000
```

Reads:

- `CarDriver.csv` — active drivers per second
- `resources/campus_drive_graph.geojson` — blueprint graph for edge → sim-road mapping
- `resources/sim_road_lengths.csv` — DEVS segment lengths (normalization)

Writes:

- **`output_data/processed/heatmap_matrix.csv`**

---

### 4. Visualize heatmap

```bash
python3 scripts/plot_heatmap.py
```

Writes **`output_data/processed/heatmap_matrix.png`** (same style as DEVS: plasma, vmax=20).

---

## Key files

| Path | Role |
|------|------|
| `config.json` | Production run config |
| `resources/car_driver_schedule.csv` | Spawn schedule (7 lots) |
| `resources/campus_drive_graph.geojson` | Drive network (from blueprint `Download Graph.ipynb`) |
| `resources/sim_road_lengths.csv` | DEVS sim-road lengths for heatmap |
| `scripts/analyze_run.py` | Post-run analysis |
| `scripts/build_heatmap_matrix.py` | Heatmap CSV |
| `scripts/plot_heatmap.py` | Heatmap PNG |

## Graph updates

After re-running **`blueprint-geovector/Download Graph.ipynb`**, refresh the MARS graph:

```powershell
Copy-Item `
  "...\blueprint-geovector\GeoVectorBlueprint\Resources\edges_drive.geojson" `
  "resources\campus_drive_graph.geojson" -Force
```

Do **not** use the DEVS `carleton_campus_car_roads.geojson` here — that is a simplified graph for the DEVS model only.

## DEVS comparison

| DEVS | MARS equivalent |
|------|-----------------|
| Scenario log CSV | `CarDriver.csv` |
| `output_data/processed/evac_curve.csv` | `results/evac_curve.csv` |
| `output_data/processed/heatmap_matrix.csv` | `output_data/processed/heatmap_matrix.csv` |
| `analysis/visualize_processed.py` | `analyze_run.py` + `plot_heatmap.py` |
| Completion count | `CarDriver_trips.geojson` feature count |

Heatmap **values** differ (different engine and graph detail); **columns, units, and plot layout** match DEVS.
