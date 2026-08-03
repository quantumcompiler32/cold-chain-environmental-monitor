#!/usr/bin/env python3
"""Analyze one exported Cold-Chain Environmental Monitor run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_run(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    readings = pd.read_csv(run_dir / "readings.csv", parse_dates=["timestamp"])
    events = pd.read_csv(run_dir / "events.csv", parse_dates=["timestamp"])
    metadata = json.loads((run_dir / "metadata.json").read_text())
    readings = readings.sort_values("timestamp").reset_index(drop=True)
    return readings, events, metadata


def add_derived_columns(df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    result = df.copy()
    dt_minutes = result["timestamp"].diff().dt.total_seconds().div(60)
    result["aht_rate_c_per_min"] = result["aht20_temp_c"].diff().div(dt_minutes.replace(0, np.nan))
    result["rolling_mean_c"] = result["aht20_temp_c"].rolling(6, min_periods=1).mean()
    result["rolling_std_c"] = result["aht20_temp_c"].rolling(6, min_periods=2).std()
    result["temp_disagreement_c"] = (result["aht20_temp_c"] - result["dht22_temp_c"]).abs()
    result["humidity_disagreement_pct"] = (result["aht20_humidity_pct"] - result["dht22_humidity_pct"]).abs()
    if metadata.get("thresholdEnabled"):
        lower = float(metadata["lowerThresholdC"])
        upper = float(metadata["upperThresholdC"])
        result["outside_configured_range"] = (result["aht20_temp_c"] < lower) | (result["aht20_temp_c"] > upper)
    else:
        result["outside_configured_range"] = False
    return result


def summarize(df: pd.DataFrame, metadata: dict) -> dict:
    valid = df[df["aht_valid"].astype(str).str.lower().isin(["true", "1"])]
    interval = valid["timestamp"].diff().dt.total_seconds().median()
    return {
        "trial_id": metadata.get("trialId"),
        "samples": int(len(df)),
        "valid_primary_samples": int(len(valid)),
        "missing_primary_samples": int(len(df) - len(valid)),
        "collection_minutes": round((df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60, 2) if len(df) > 1 else 0,
        "median_sampling_interval_seconds": None if pd.isna(interval) else round(float(interval), 2),
        "mean_temperature_c": round(float(valid["aht20_temp_c"].mean()), 3) if len(valid) else None,
        "minimum_temperature_c": round(float(valid["aht20_temp_c"].min()), 3) if len(valid) else None,
        "maximum_temperature_c": round(float(valid["aht20_temp_c"].max()), 3) if len(valid) else None,
        "maximum_temperature_disagreement_c": round(float(df["temp_disagreement_c"].max()), 3),
        "outside_range_samples": int(df["outside_configured_range"].sum()),
        "educational_use_only": True,
    }


def create_charts(df: pd.DataFrame, events: pd.DataFrame, metadata: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["timestamp"], df["aht20_temp_c"], label="AHT20")
    ax.plot(df["timestamp"], df["dht22_temp_c"], label="DHT22", alpha=0.8)
    if metadata.get("thresholdEnabled"):
        ax.axhline(float(metadata["lowerThresholdC"]), linestyle="--", label="Lower study threshold")
        ax.axhline(float(metadata["upperThresholdC"]), linestyle="--", label="Upper study threshold")
    for _, event in events.iterrows():
        ax.axvline(event["timestamp"], alpha=0.15)
    ax.set_title("Temperature and recorded events")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "temperature_timeline.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["timestamp"], df["aht20_humidity_pct"], label="AHT20 RH")
    ax.plot(df["timestamp"], df["dht22_humidity_pct"], label="DHT22 RH", alpha=0.8)
    ax.set_title("Relative humidity")
    ax.set_ylabel("Relative humidity (%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "humidity_timeline.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["timestamp"], df["temp_disagreement_c"], label="Temperature disagreement")
    ax.axhline(1.0, linestyle="--", label="Advisory threshold")
    ax.axhline(2.0, linestyle="--", label="Fault-candidate threshold")
    ax.set_title("AHT20–DHT22 disagreement")
    ax.set_ylabel("Absolute difference (°C)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "sensor_disagreement.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("exports"))
    args = parser.parse_args()
    readings, events, metadata = load_run(args.run_dir)
    derived = add_derived_columns(readings, metadata)
    args.output.mkdir(parents=True, exist_ok=True)
    derived.to_csv(args.output / "processed_readings.csv", index=False)
    summary = summarize(derived, metadata)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    create_charts(derived, events, metadata, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
