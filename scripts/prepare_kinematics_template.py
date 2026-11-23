"""Generate the 96-finalist Paris 2024 Freestyle stroke kinematics measurement template.

Reads all 12 Paris 2024 Olympic Freestyle finals (Men & Women: 50m, 100m, 200m,
400m, 800m, 1500m; 8 finalists each = 96 rows), left-joins verified anthropometric
and performance fields from data/processed/swimming_results_clean.csv (year == 2024)
without imputing missing values, and exports:
    - data/raw/paris2024_kinematics_template.csv
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PARIS_SWIM = ROOT / "data" / "raw" / "kaggle_paris2024" / "results" / "Swimming.csv"
CLEAN_RESULTS = ROOT / "data" / "processed" / "swimming_results_clean.csv"
OUT_TEMPLATE = ROOT / "data" / "raw" / "paris2024_kinematics_template.csv"

G = 9.81
TARGET_EVENTS_DIST = {
    "50m": 50,
    "100m": 100,
    "200m": 200,
    "400m": 400,
    "800m": 800,
    "1500m": 1500,
}
NOC_ALIASES = {"ROC": "RUS", "OAR": "RUS", "EOR": "ROT"}


def normalize_name(name: object) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[1]:
            s = f"{parts[1]} {parts[0]}"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z\s]", " ", s).lower()
    return " ".join(s.split())


def normalize_noc(noc: object) -> str:
    if pd.isna(noc):
        return ""
    s = str(noc).strip().upper()
    return NOC_ALIASES.get(s, s)


def parse_paris_event(event: object) -> tuple[str | None, str | None]:
    if not isinstance(event, str) or "Relay" in event:
        return None, None
    m = re.match(r"^(Men|Women)'s\s+(50m|100m|200m|400m|800m|1500m)\s+Freestyle$", event.strip())
    if not m:
        return None, None
    return m.group(2), m.group(1)


def parse_time_to_sec(val: object) -> float:
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if not s or any(tok in s.upper() for tok in ("DNS", "DSQ", "DQ", "DNF", "WD", "NT", "NA")):
        return np.nan
    s = re.sub(r"[^\d:.]", "", s)
    if not s:
        return np.nan
    parts = s.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60.0 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])
    except ValueError:
        return np.nan
    return np.nan


def main() -> None:
    p24 = pd.read_csv(RAW_PARIS_SWIM)
    parsed = p24["event_name"].apply(lambda e: pd.Series(parse_paris_event(e)))
    p24[["dist", "sex"]] = parsed

    finals = p24[
        p24["dist"].notna()
        & p24["sex"].notna()
        & (p24["stage"].astype(str).str.strip() == "Final")
    ].copy()

    finals["event"] = finals["dist"] + " Freestyle"
    finals["distance_m"] = finals["dist"].map(TARGET_EVENTS_DIST).astype(int)
    finals["event_category"] = np.select(
        [finals["distance_m"].isin([50, 100]), finals["distance_m"].isin([200, 400])],
        ["Sprint", "Middle"],
        default="Distance",
    )
    finals["rank"] = pd.to_numeric(finals["rank"], errors="coerce").astype("Int64")
    finals["participant_code"] = finals["participant_code"].astype(str).str.strip()
    finals["athlete_name"] = finals["participant_name"].astype(str).str.strip()
    finals["noc"] = finals["participant_country_code"].map(normalize_noc)
    finals["final_time_sec"] = finals["result"].map(parse_time_to_sec)
    finals["whole_race_velocity_ms"] = finals["distance_m"] / finals["final_time_sec"]
    finals["_norm_name"] = finals["athlete_name"].map(normalize_name)

    # Left-join verified 2024 anthropometrics from swimming_results_clean.csv (never impute)
    rc = pd.read_csv(CLEAN_RESULTS)
    rc24 = rc[rc["year"] == 2024].copy()
    rc24["_norm_name"] = rc24["athlete_name"].map(normalize_name)
    rc24_join = (
        rc24[
            [
                "_norm_name",
                "sex",
                "event",
                "athlete_key",
                "height_m",
                "mass_kg",
                "bmi",
                "wa_points",
            ]
        ]
        .drop_duplicates(subset=["_norm_name", "sex", "event"])
    )

    merged = finals.merge(
        rc24_join,
        on=["_norm_name", "sex", "event"],
        how="left",
        validate="one_to_one",
    )

    # Compute whole_race_froude directly from Final velocity and verified height_m (NaN if height_m is NaN)
    merged["whole_race_froude"] = merged["whole_race_velocity_ms"] / np.sqrt(G * merged["height_m"])

    # Sort by sex, distance_m, rank (tie-break by final_time_sec)
    merged = merged.sort_values(
        ["sex", "distance_m", "rank", "final_time_sec"], ascending=[True, True, True, True]
    ).reset_index(drop=True)

    # Blank columns for manual video/PDF stroke kinematics entry
    merged["segment_distance_m"] = np.nan
    merged["segment_time_sec"] = np.nan
    merged["stroke_cycles"] = np.nan
    merged["source_notes"] = ""

    out_cols = [
        "sex",
        "event",
        "distance_m",
        "event_category",
        "rank",
        "participant_code",
        "athlete_key",
        "athlete_name",
        "noc",
        "final_time_sec",
        "whole_race_velocity_ms",
        "height_m",
        "mass_kg",
        "bmi",
        "whole_race_froude",
        "wa_points",
        "segment_distance_m",
        "segment_time_sec",
        "stroke_cycles",
        "source_notes",
    ]
    out_df = merged[out_cols].copy()

    # Round numeric pre-filled columns for clean spreadsheet editing
    out_df["final_time_sec"] = out_df["final_time_sec"].round(2)
    out_df["whole_race_velocity_ms"] = out_df["whole_race_velocity_ms"].round(4)
    out_df["bmi"] = out_df["bmi"].round(2)
    out_df["whole_race_froude"] = out_df["whole_race_froude"].round(4)

    # Verification assertions
    assert len(out_df) == 96, f"Expected 96 finalists, got {len(out_df)}"
    cell_sizes = out_df.groupby(["sex", "event"]).size()
    assert len(cell_sizes) == 12, f"Expected 12 finals, got {len(cell_sizes)}"
    assert (cell_sizes == 8).all(), f"Each final must have 8 swimmers:\n{cell_sizes}"
    dupes = out_df.duplicated(subset=["sex", "event", "participant_code"]).sum()
    assert dupes == 0, f"Found {dupes} duplicate swimmers within a final!"
    assert out_df["final_time_sec"].notna().all(), "Missing final_time_sec!"
    assert out_df["whole_race_velocity_ms"].between(1.4, 2.5).all(), "whole_race_velocity_ms out of [1.4, 2.5]!"

    out_df.to_csv(OUT_TEMPLATE, index=False)

    # Print verification summary
    print("=== PARIS 2024 KINEMATICS TEMPLATE VERIFICATION ===")
    print(f"Saved: {OUT_TEMPLATE}")
    print(f"Total finalist rows: {len(out_df)} (12 finals x 8 lanes; 0 duplicate swimmers per final)")
    n_matched = int((out_df["height_m"].notna() & out_df["mass_kg"].notna()).sum())
    n_unmatched = len(out_df) - n_matched
    print(f"Matched verified anthropometrics (height_m & mass_kg): {n_matched} / {len(out_df)}")
    print(f"Unmatched (retained as NaN, never imputed):            {n_unmatched} / {len(out_df)}")
    print("\nBreakdown by sex x event:")
    summary = (
        out_df.assign(has_hw=out_df["height_m"].notna() & out_df["mass_kg"].notna())
        .groupby(["sex", "distance_m", "event"], as_index=False)
        .agg(
            n_finalists=("participant_code", "count"),
            n_with_hw=("has_hw", "sum"),
            n_without_hw=("has_hw", lambda s: int((~s).sum())),
            min_time_s=("final_time_sec", "min"),
            max_time_s=("final_time_sec", "max"),
            mean_v_ms=("whole_race_velocity_ms", "mean"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
    )
    summary["mean_v_ms"] = summary["mean_v_ms"].round(3)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()