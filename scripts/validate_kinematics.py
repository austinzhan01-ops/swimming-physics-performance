"""Phase 3: Batch Data-Quality Audit for Paris 2024 Stroke Kinematics
(data/raw/paris2024_kinematics.csv).

Verifies:
    1. Row counts per sex x event cell, duplicate swimmers, and missing values.
    2. Physical bounds & outlier flags:
         - stroke_length_m in [1.5, 2.9] m/cycle
         - stroke_rate_hz in [0.50, 1.15] Hz
         - clean_velocity_ms in [1.3, 2.4] m/s
         - start_turn_inflation_ms >= -0.05 m/s in 50m/100m
    3. Internal consistency check (derived SL = clean_v / SR vs FFN reported SL:
       MAE, Pearson r, and ICC(2,1)) + repeatability helper for manual re-measurements.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
KIN_CSV = ROOT / "data" / "raw" / "paris2024_kinematics.csv"
EVENT_ORDER = [
    "50m Freestyle",
    "100m Freestyle",
    "200m Freestyle",
    "400m Freestyle",
    "800m Freestyle",
    "1500m Freestyle",
]


def compute_icc_agreement(x: np.ndarray, y: np.ndarray) -> float:
    """Compute two-way random, single-measures absolute-agreement ICC(2,1)."""
    mat = np.column_stack([x, y]).astype(float)
    n, k = mat.shape
    if n < 3:
        return float("nan")
    mean_rows = mat.mean(axis=1, keepdims=True)
    mean_cols = mat.mean(axis=0, keepdims=True)
    grand = mat.mean()
    ss_rows = k * np.sum((mean_rows - grand) ** 2)
    ss_cols = n * np.sum((mean_cols - grand) ** 2)
    ss_err = np.sum((mat - mean_rows - mean_cols + grand) ** 2)
    ms_r = ss_rows / (n - 1)
    ms_c = ss_cols / (k - 1)
    ms_e = ss_err / ((n - 1) * (k - 1))
    denom = ms_r + (k - 1) * ms_e + (k / n) * (ms_c - ms_e)
    return float((ms_r - ms_e) / denom) if denom != 0 else float("nan")


def main() -> None:
    df = pd.read_csv(KIN_CSV)
    print("=== PHASE 3: PARIS 2024 KINEMATICS DATA-QUALITY AUDIT ===")
    print(f"Total template rows: {len(df)}")

    dupes = int(df.duplicated(subset=["sex", "event", "participant_code"]).sum())
    assert dupes == 0, f"Found {dupes} duplicate swimmers within a final!"
    print(f"Duplicate swimmers within any final: {dupes} (PASS)")

    # Cell completeness audit
    pop_mask = df["segment_distance_m"].notna() & df["segment_time_sec"].notna() & df["stroke_cycles"].notna()
    print(f"Populated kinematics rows: {int(pop_mask.sum())} / {len(df)}")
    matched_pop = pop_mask & df["height_m"].notna() & df["mass_kg"].notna()
    print(f"Populated Tier 2 matched anthropometric rows: {int(matched_pop.sum())} / {int((df['height_m'].notna() & df['mass_kg'].notna()).sum())}")

    cell_audit = (
        df.assign(populated=pop_mask, matched_pop=matched_pop)
        .groupby(["sex", "distance_m", "event"], as_index=False)
        .agg(
            n_total=("participant_code", "count"),
            n_populated=("populated", "sum"),
            n_missing=("populated", lambda s: int((~s).sum())),
            n_matched_pop=("matched_pop", "sum"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
    )
    print("\n--- 1. Row Counts by sex x event ---")
    print(cell_audit.to_string(index=False))

    # Compute derived kinematics on populated rows
    pop = df[pop_mask].copy()
    pop["clean_velocity_ms"] = pop["segment_distance_m"] / pop["segment_time_sec"]
    pop["start_turn_inflation_ms"] = pop["whole_race_velocity_ms"] - pop["clean_velocity_ms"]
    pop["stroke_rate_hz"] = pop["stroke_cycles"] / pop["segment_time_sec"]
    pop["stroke_length_m"] = pop["clean_velocity_ms"] / pop["stroke_rate_hz"]

    # Outlier checks
    flags = {
        "stroke_length_out_of_[1.5,2.9]": ~pop["stroke_length_m"].between(1.5, 2.9),
        "stroke_rate_out_of_[0.50,1.15]": ~pop["stroke_rate_hz"].between(0.50, 1.15),
        "clean_velocity_out_of_[1.3,2.4]": ~pop["clean_velocity_ms"].between(1.3, 2.4),
        "sprint_inflation_lt_-0.05": (pop["distance_m"].isin([50, 100])) & (pop["start_turn_inflation_ms"] < -0.05),
    }

    print("\n--- 2. Physical Bounds & Outlier Checks ---")
    total_flags = 0
    for name, mask in flags.items():
        n_f = int(mask.sum())
        total_flags += n_f
        status = "PASS (0 flags)" if n_f == 0 else f"FLAGGED ({n_f} rows)"
        print(f"  {name:34s}: {status}")
        if n_f > 0:
            cols = ["sex", "event", "rank", "athlete_name", "clean_velocity_ms", "stroke_rate_hz", "stroke_length_m", "start_turn_inflation_ms"]
            print(pop.loc[mask, cols].round(3).to_string(index=False))

    print("\nObserved ranges across populated rows:")
    for col in ["clean_velocity_ms", "stroke_rate_hz", "stroke_length_m", "start_turn_inflation_ms", "underwater_start_m"]:
        if col in pop.columns and pop[col].notna().any():
            print(f"  {col:25s}: min={pop[col].min():.3f}, median={pop[col].median():.3f}, max={pop[col].max():.3f}")

    # 3. Internal consistency check: derived SL (v_clean / SR) vs FFN reported SL
    if "ffn_stroke_length_m" in pop.columns and pop["ffn_stroke_length_m"].notna().all():
        x = pop["stroke_length_m"].to_numpy(dtype=float)
        y = pop["ffn_stroke_length_m"].to_numpy(dtype=float)
        mae = float(np.mean(np.abs(x - y)))
        r_val, p_val = stats.pearsonr(x, y)
        icc = compute_icc_agreement(x, y)
        print("\n--- 3. Internal Consistency Check (Derived Clean SL vs. FFN Reported SL) ---")
        print(f"  N = {len(pop)} | MAE = {mae:.4f} m/cycle | Pearson r = {r_val:.5f} (p = {p_val:.2e}) | ICC(2,1) = {icc:.5f}")

    if total_flags == 0:
        print("\n[AUDIT PASSED] Zero physical-bound violations across all populated rows.")
    else:
        print(f"\n[AUDIT NOTICE] {total_flags} flag(s) detected — review rows above before proceeding.")


if __name__ == "__main__":
    main()