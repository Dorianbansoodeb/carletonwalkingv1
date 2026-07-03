#!/usr/bin/env python3
"""Show spawn count: MARS uses exclusive endTime (t < end), not inclusive (t <= end)."""
import csv
from datetime import datetime, timedelta
from pathlib import Path

SCHEDULE = Path(__file__).resolve().parents[1] / "resources" / "car_driver_schedule.csv"
LOT_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]


def parse_clock(value: str) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(value)


def count_spawns(start, end, interval_min, amount, inclusive_end):
    n = 0
    t = start
    step = timedelta(minutes=interval_min)
    while (t <= end) if inclusive_end else (t < end):
        n += amount
        t += step
    events = n // amount
    return n, events


def main():
    rows = list(csv.DictReader(SCHEDULE.open(encoding="utf-8-sig")))
    print("Lot | endTime | inclusive (<=end) | MARS exclusive (<end) | missing")
    print("----|---------|-------------------|----------------------|--------")
    total_inc = total_exc = 0
    for i, lot in enumerate(LOT_ORDER):
        row = rows[i]
        start = parse_clock(row["startTime"])
        end = parse_clock(row["endTime"])
        interval = float(row["spawningIntervalInMinutes"])
        amount = int(row["spawningAmount"])
        inc, inc_ev = count_spawns(start, end, interval, amount, True)
        exc, exc_ev = count_spawns(start, end, interval, amount, False)
        total_inc += inc
        total_exc += exc
        print(
            f"{lot:3} | {row['endTime']:7} | {inc:5d} ({inc_ev:2d} events) | "
            f"{exc:5d} ({exc_ev:2d} events) | {inc - exc:2d}"
        )
    print()
    print(f"Total inclusive: {total_inc}  |  Total exclusive (MARS): {total_exc}  |  gap: {total_inc - total_exc}")
    print()
    print("Example P1 (6:00-6:09, every 1 min, 12 cars):")
    print("  inclusive: spawns at 6:00,6:01,...,6:09  -> 10 batches -> 120 cars")
    print("  exclusive: spawns at 6:00,6:01,...,6:08  ->  9 batches -> 108 cars  (matches run)")


if __name__ == "__main__":
    main()
