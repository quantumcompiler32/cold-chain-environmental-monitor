from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = PROJECT_ROOT / "exports"
CHART_DIR = EXPORT_DIR / "charts"


def newest_export() -> Path:
    exports = sorted(EXPORT_DIR.glob("telemetry_*.csv"), key=lambda p: p.stat().st_mtime)
    if not exports:
        raise FileNotFoundError("No export found. Run: iot save")
    return exports[-1]


def main() -> None:
    csv_path = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else newest_export()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV does not exist: {csv_path}")

    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    if df.empty:
        raise ValueError("The CSV has no telemetry rows. Run the simulator before exporting.")

    df = df.sort_values("timestamp")
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loaded: {csv_path}")
    print("\nFirst rows:")
    print(df.head().to_string(index=False))
    print("\nMissing values:")
    print(df.isna().sum().to_string())

    numeric_columns = [c for c in ["temperature", "humidity", "pressure"] if c in df.columns]
    summary = df.groupby("device_id")[numeric_columns].agg(["count", "mean", "min", "max"])
    summary_path = CHART_DIR / "device_summary.csv"
    summary.to_csv(summary_path)
    print(f"\nSummary saved: {summary_path}")

    for device_id, group in df.groupby("device_id"):
        if group["temperature"].notna().any():
            plt.figure(figsize=(10, 4))
            plt.plot(group["timestamp"], group["temperature"], marker="o")
            plt.title(f"Temperature — {device_id}")
            plt.xlabel("Time")
            plt.ylabel("Temperature")
            plt.xticks(rotation=45)
            plt.tight_layout()
            path = CHART_DIR / f"temperature_{device_id}.png"
            plt.savefig(path, dpi=150)
            plt.close()
            print(f"Chart saved: {path}")

    pressure_rows = df[df.get("pressure", pd.Series(index=df.index, dtype=float)).notna()]
    if not pressure_rows.empty:
        fig, ax1 = plt.subplots(figsize=(11, 5))
        ax1.plot(df["timestamp"], df["temperature"], marker="o")
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Temperature")
        ax2 = ax1.twinx()
        ax2.plot(pressure_rows["timestamp"], pressure_rows["pressure"], marker="x")
        ax2.set_ylabel("Pressure")
        plt.title("Temperature and Pressure Timeline")
        fig.autofmt_xdate()
        fig.tight_layout()
        path = CHART_DIR / "temperature_pressure_dual_axis.png"
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Chart saved: {path}")

    print("\nAnalysis complete.")


if __name__ == "__main__":
    main()
