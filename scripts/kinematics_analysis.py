"""Paris 2024 Olympic Freestyle Stroke Kinematics Sub-Study Analysis.

Reads populated stroke kinematics measurements from:
    - data/raw/paris2024_kinematics.csv
      (and merges official reaction times from data/raw/paris2024_official_splits.csv)

Runs non-tautological, sex-stratified biomechanical analyses across two tiers:
    1. Full Kinematics Cohort (N = 92 FFN finalists):
       - 6-event summaries of clean velocity, start/turn inflation, SR, SL, SI, underwater start
       - Log-space variance decomposition: Var(ln v_clean) = Var(ln SL) + Var(ln SR) + 2*Cov(ln SL, ln SR)
       - Start/underwater mechanics: underwater breakout distance & reaction time vs. inflation & speed
       - Men's 200m clean Froude sensitivity check across all 8 finalists (L = 1.85, 1.902, 1.95 m)
    2. Matched Anthropometric-Kinematics Cohort (N = 30 returning Olympians):
       - Paired whole-race vs. clean mid-pool Froude number tests (testing Fr > 0.42)
       - Distance-adjusted OLS: Height & Mass predicting Stroke Length and Stroke Rate

Outputs:
    - results/kinematics_summary.csv
    - results/kinematics_models.csv
    - results/figures/kinematics_biomechanics.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parent.parent
IN_CSV = ROOT / "data" / "raw" / "paris2024_kinematics.csv"
SPLITS_CSV = ROOT / "data" / "raw" / "paris2024_official_splits.csv"
TEMPLATE_CSV = ROOT / "data" / "raw" / "paris2024_kinematics_template.csv"
OUT_DIR = ROOT / "results"
FIG_DIR = OUT_DIR / "figures"

G = 9.81
EVENT_ORDER = [
    "50m Freestyle",
    "100m Freestyle",
    "200m Freestyle",
    "400m Freestyle",
    "800m Freestyle",
    "1500m Freestyle",
]
SHORT_MAP = {
    "50m Freestyle": "50m",
    "100m Freestyle": "100m",
    "200m Freestyle": "200m",
    "400m Freestyle": "400m",
    "800m Freestyle": "800m",
    "1500m Freestyle": "1500m",
}
PALETTE_EVT = {
    "50m Freestyle": "#D55E00",
    "100m Freestyle": "#E69F00",
    "200m Freestyle": "#009E73",
    "400m Freestyle": "#CC79A7",
    "800m Freestyle": "#56B4E9",
    "1500m Freestyle": "#0072B2",
}
SEX_PALETTE = {"Men": "#1B4F72", "Women": "#B03A2E"}


def load_and_compute_kinematics(csv_path: Path, splits_path: Path = SPLITS_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    req_cols = [
        "sex",
        "event",
        "distance_m",
        "event_category",
        "whole_race_velocity_ms",
        "segment_distance_m",
        "segment_time_sec",
        "stroke_cycles",
    ]
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {missing}")

    # Merge official reaction_time_sec (and lane) from paris2024_official_splits.csv if present
    if splits_path.exists() and "participant_code" in df.columns:
        spl = pd.read_csv(splits_path)[["sex", "event", "participant_code", "reaction_time_sec", "lane"]].copy()
        df["participant_code"] = df["participant_code"].astype(str)
        spl["participant_code"] = spl["participant_code"].astype(str)
        # Drop existing columns if re-merging
        df = df.drop(columns=[c for c in ["reaction_time_sec", "lane"] if c in df.columns])
        df = df.merge(spl, on=["sex", "event", "participant_code"], how="left")

    for col in [
        "distance_m",
        "final_time_sec",
        "whole_race_velocity_ms",
        "height_m",
        "mass_kg",
        "bmi",
        "whole_race_froude",
        "segment_distance_m",
        "segment_time_sec",
        "stroke_cycles",
        "underwater_start_m",
        "reaction_time_sec",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["segment_distance_m", "segment_time_sec", "stroke_cycles"]).copy()
    df = df[
        (df["segment_distance_m"] > 0)
        & (df["segment_time_sec"] > 0)
        & (df["stroke_cycles"] > 0)
    ].copy()

    if df.empty:
        return df

    # Derived stroke kinematics & hydrodynamic variables
    df["clean_velocity_ms"] = df["segment_distance_m"] / df["segment_time_sec"]
    df["start_turn_inflation_ms"] = df["whole_race_velocity_ms"] - df["clean_velocity_ms"]
    df["start_turn_inflation_pct"] = 100.0 * df["start_turn_inflation_ms"] / df["clean_velocity_ms"]
    df["stroke_rate_hz"] = df["stroke_cycles"] / df["segment_time_sec"]
    df["stroke_length_m"] = df["clean_velocity_ms"] / df["stroke_rate_hz"]
    df["stroke_index"] = df["clean_velocity_ms"] * df["stroke_length_m"]
    df["log_distance_m"] = np.log(df["distance_m"])

    # Ensure whole_race_froude is consistent with whole_race_velocity_ms & height_m
    df["whole_race_froude"] = df["whole_race_velocity_ms"] / np.sqrt(G * df["height_m"])
    df["clean_froude_number"] = df["clean_velocity_ms"] / np.sqrt(G * df["height_m"])
    df["froude_inflation"] = df["whole_race_froude"] - df["clean_froude_number"]
    return df


def summarize_by_event(df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "whole_race_velocity_ms",
        "clean_velocity_ms",
        "start_turn_inflation_ms",
        "stroke_rate_hz",
        "stroke_length_m",
        "stroke_index",
        "underwater_start_m",
        "reaction_time_sec",
        "whole_race_froude",
        "clean_froude_number",
    ]
    rows = []
    for sex in ["Men", "Women"]:
        sub_sex = df[df["sex"] == sex]
        for evt in EVENT_ORDER:
            ev = sub_sex[sub_sex["event"] == evt]
            if ev.empty:
                continue
            row = {
                "sex": sex,
                "event": evt,
                "distance_m": int(ev["distance_m"].iloc[0]),
                "event_category": ev["event_category"].iloc[0],
                "n_kinematics": int(len(ev)),
                "n_matched_anthro": int((ev["height_m"].notna() & ev["mass_kg"].notna()).sum()),
            }
            for m in metrics:
                if m not in ev.columns:
                    continue
                vals = ev[m].dropna().to_numpy(dtype=float)
                row[f"{m}_mean"] = float(np.mean(vals)) if len(vals) else np.nan
                row[f"{m}_sd"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan
                row[f"{m}_median"] = float(np.median(vals)) if len(vals) else np.nan
            fr_w = ev["whole_race_froude"].dropna()
            fr_c = ev["clean_froude_number"].dropna()
            row["pct_whole_fr_gt_042"] = float(100.0 * (fr_w > 0.42).mean()) if len(fr_w) else np.nan
            row["pct_clean_fr_gt_042"] = float(100.0 * (fr_c > 0.42).mean()) if len(fr_c) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def safe_corr(x: pd.Series, y: pd.Series) -> dict:
    valid = pd.concat([x, y], axis=1).dropna()
    n = len(valid)
    if n < 3 or valid.iloc[:, 0].nunique() < 2 or valid.iloc[:, 1].nunique() < 2:
        return {"n": n, "pearson_r": np.nan, "p_pearson": np.nan, "spearman_rho": np.nan, "p_spearman": np.nan}
    r_p, p_p = stats.pearsonr(valid.iloc[:, 0], valid.iloc[:, 1])
    r_s, p_s = stats.spearmanr(valid.iloc[:, 0], valid.iloc[:, 1])
    return {
        "n": n,
        "pearson_r": float(r_p),
        "p_pearson": float(p_p),
        "spearman_rho": float(r_s),
        "p_spearman": float(p_s),
    }


def run_non_tautological_models(df: pd.DataFrame) -> pd.DataFrame:
    model_rows = []

    # -----------------------------------------------------------------------
    # 1. Log-Space Variance Decomposition: ln(v_clean) = ln(SL) + ln(SR)
    # -----------------------------------------------------------------------
    for sex in ["Men", "Women"]:
        sub_sex = df[df["sex"] == sex]
        for scope_name, sc_df in [
            ("All_6_Events", sub_sex),
            ("Sprint", sub_sex[sub_sex["event_category"] == "Sprint"]),
            ("Middle", sub_sex[sub_sex["event_category"] == "Middle"]),
            ("Distance", sub_sex[sub_sex["event_category"] == "Distance"]),
        ]:
            valid = sc_df[["clean_velocity_ms", "stroke_length_m", "stroke_rate_hz"]].dropna()
            n = len(valid)
            if n < 3:
                continue
            ln_v = np.log(valid["clean_velocity_ms"].to_numpy(dtype=float))
            ln_sl = np.log(valid["stroke_length_m"].to_numpy(dtype=float))
            ln_sr = np.log(valid["stroke_rate_hz"].to_numpy(dtype=float))

            var_v = float(np.var(ln_v, ddof=1))
            var_sl = float(np.var(ln_sl, ddof=1))
            var_sr = float(np.var(ln_sr, ddof=1))
            two_cov = float(2.0 * np.cov(ln_sl, ln_sr, ddof=1)[0, 1])

            pct_sl = 100.0 * var_sl / var_v if var_v > 0 else np.nan
            pct_sr = 100.0 * var_sr / var_v if var_v > 0 else np.nan
            pct_2cov = 100.0 * two_cov / var_v if var_v > 0 else np.nan
            # Assert exact algebraic identity
            assert abs((var_sl + var_sr + two_cov) - var_v) < 1e-10

            model_rows.append(
                {
                    "tier": "Tier1_Full_Kinematics",
                    "analysis_type": "log_variance_decomposition",
                    "sex": sex,
                    "scope": scope_name,
                    "model_or_test": "Var(ln v_clean) = Var(ln SL) + Var(ln SR) + 2Cov",
                    "n": n,
                    "stat_primary": float(pct_sr),
                    "p_primary": np.nan,
                    "stat_secondary": float(pct_sl),
                    "p_secondary": np.nan,
                    "r2": np.nan,
                    "adj_r2": np.nan,
                    "details_json": json.dumps(
                        {
                            "var_ln_v": var_v,
                            "var_ln_sl": var_sl,
                            "var_ln_sr": var_sr,
                            "two_cov_ln_sl_sr": two_cov,
                            "pct_var_sl": pct_sl,
                            "pct_var_sr": pct_sr,
                            "pct_2cov": pct_2cov,
                        }
                    ),
                }
            )

    # -----------------------------------------------------------------------
    # 2. Tier 1 Correlations (Stroke mechanics & Start/Underwater mechanics)
    # -----------------------------------------------------------------------
    for sex in ["Men", "Women"]:
        sub = df[df["sex"] == sex]
        if len(sub) < 3:
            continue
        for pred in ["stroke_length_m", "stroke_rate_hz", "stroke_index"]:
            for outcome in ["whole_race_velocity_ms", "clean_velocity_ms"]:
                c = safe_corr(sub[pred], sub[outcome])
                model_rows.append(
                    {
                        "tier": "Tier1_Full_Kinematics",
                        "analysis_type": "correlation",
                        "sex": sex,
                        "scope": "All_6_Events",
                        "model_or_test": f"{pred} vs {outcome}",
                        "n": c["n"],
                        "stat_primary": c["pearson_r"],
                        "p_primary": c["p_pearson"],
                        "stat_secondary": c["spearman_rho"],
                        "p_secondary": c["p_spearman"],
                        "r2": np.nan,
                        "adj_r2": np.nan,
                        "details_json": json.dumps({"pearson_r": c["pearson_r"], "spearman_rho": c["spearman_rho"]}),
                    }
                )

        # Start / Underwater mechanics across All_6_Events and within categories
        for scope_name, sc_df in [
            ("All_6_Events", sub),
            ("Sprint", sub[sub["event_category"] == "Sprint"]),
            ("Middle", sub[sub["event_category"] == "Middle"]),
            ("Distance", sub[sub["event_category"] == "Distance"]),
        ]:
            for pred in ["underwater_start_m", "reaction_time_sec"]:
                if pred not in sc_df.columns:
                    continue
                for outcome in ["start_turn_inflation_ms", "whole_race_velocity_ms"]:
                    c = safe_corr(sc_df[pred], sc_df[outcome])
                    if c["n"] < 3:
                        continue
                    model_rows.append(
                        {
                            "tier": "Tier1_Start_Underwater",
                            "analysis_type": "start_underwater_corr",
                            "sex": sex,
                            "scope": scope_name,
                            "model_or_test": f"{pred} vs {outcome}",
                            "n": c["n"],
                            "stat_primary": c["pearson_r"],
                            "p_primary": c["p_pearson"],
                            "stat_secondary": c["spearman_rho"],
                            "p_secondary": c["p_spearman"],
                            "r2": np.nan,
                            "adj_r2": np.nan,
                            "details_json": json.dumps({"pearson_r": c["pearson_r"], "spearman_rho": c["spearman_rho"]}),
                        }
                    )

    # -----------------------------------------------------------------------
    # 3. Men's 200m Clean Froude Robustness Check (All 8 Finalists)
    # -----------------------------------------------------------------------
    m200 = df[(df["sex"] == "Men") & (df["event"] == "200m Freestyle")].copy()
    if not m200.empty:
        v_clean_arr = m200["clean_velocity_ms"].to_numpy(dtype=float)
        v_whole_arr = m200["whole_race_velocity_ms"].to_numpy(dtype=float)
        for label, height_val in [
            ("L = 1.850 m (lower bound)", 1.85),
            ("L = 1.902 m (historical 200m mean)", 1.902),
            ("L = 1.950 m (upper bound)", 1.95),
        ]:
            fr_clean = v_clean_arr / np.sqrt(G * height_val)
            fr_whole = v_whole_arr / np.sqrt(G * height_val)
            model_rows.append(
                {
                    "tier": "Tier1_Robustness",
                    "analysis_type": "men_200m_froude_sensitivity",
                    "sex": "Men",
                    "scope": "200m_All_8",
                    "model_or_test": f"Men 200m Clean Fr at {label}",
                    "n": len(m200),
                    "stat_primary": float(np.mean(fr_clean)),
                    "p_primary": np.nan,
                    "stat_secondary": float(100.0 * (fr_clean > 0.42).mean()),
                    "p_secondary": np.nan,
                    "r2": np.nan,
                    "adj_r2": np.nan,
                    "details_json": json.dumps(
                        {
                            "assumed_height_m": height_val,
                            "clean_fr_mean": float(np.mean(fr_clean)),
                            "clean_fr_sd": float(np.std(fr_clean, ddof=1)),
                            "clean_fr_min": float(np.min(fr_clean)),
                            "clean_fr_max": float(np.max(fr_clean)),
                            "pct_clean_fr_gt_042": float(100.0 * (fr_clean > 0.42).mean()),
                            "n_clean_fr_gt_042": int((fr_clean > 0.42).sum()),
                            "whole_fr_mean": float(np.mean(fr_whole)),
                            "pct_whole_fr_gt_042": float(100.0 * (fr_whole > 0.42).mean()),
                        }
                    ),
                }
            )

    # -----------------------------------------------------------------------
    # 4. Tier 2: Matched Anthropometric-Kinematics Cohort (n = 30)
    # -----------------------------------------------------------------------
    matched = df[df["height_m"].notna() & df["mass_kg"].notna()].copy()
    for sex in ["Men", "Women"]:
        sub = matched[matched["sex"] == sex]
        if sub.empty:
            continue

        # 4a. Paired comparison: whole_race_froude vs clean_froude_number
        for scope_name, sc_df in [
            ("All_Matched", sub),
            ("Sprint", sub[sub["event_category"] == "Sprint"]),
            ("Middle", sub[sub["event_category"] == "Middle"]),
            ("Distance", sub[sub["event_category"] == "Distance"]),
        ]:
            valid = sc_df[["whole_race_froude", "clean_froude_number", "start_turn_inflation_ms"]].dropna()
            n = len(valid)
            if n == 0:
                continue
            w_fr = valid["whole_race_froude"].to_numpy(dtype=float)
            c_fr = valid["clean_froude_number"].to_numpy(dtype=float)
            diff = w_fr - c_fr
            t_stat, p_t = (stats.ttest_rel(w_fr, c_fr) if n >= 2 and np.std(diff, ddof=1) > 0 else (np.nan, np.nan))
            try:
                w_stat, p_w = stats.wilcoxon(w_fr, c_fr) if n >= 5 and np.any(diff != 0) else (np.nan, np.nan)
            except ValueError:
                w_stat, p_w = np.nan, np.nan
            details = {
                "whole_fr_mean": float(np.mean(w_fr)),
                "clean_fr_mean": float(np.mean(c_fr)),
                "mean_fr_inflation": float(np.mean(diff)),
                "mean_v_inflation_ms": float(valid["start_turn_inflation_ms"].mean()),
                "pct_whole_fr_gt_042": float(100.0 * (w_fr > 0.42).mean()),
                "pct_clean_fr_gt_042": float(100.0 * (c_fr > 0.42).mean()),
            }
            model_rows.append(
                {
                    "tier": "Tier2_Matched_Anthro",
                    "analysis_type": "paired_froude_test",
                    "sex": sex,
                    "scope": scope_name,
                    "model_or_test": "whole_race_froude vs clean_froude_number",
                    "n": n,
                    "stat_primary": float(t_stat) if pd.notna(t_stat) else np.nan,
                    "p_primary": float(p_t) if pd.notna(p_t) else np.nan,
                    "stat_secondary": float(w_stat) if pd.notna(w_stat) else np.nan,
                    "p_secondary": float(p_w) if pd.notna(p_w) else np.nan,
                    "r2": np.nan,
                    "adj_r2": np.nan,
                    "details_json": json.dumps(details),
                }
            )

        # 4b. Non-tautological Anthropometrics -> Stroke Mechanics (controlling for log_distance_m)
        # Predict stroke_length_m and stroke_rate_hz separately from height_m + mass_kg + log_distance_m
        for outcome in ["stroke_length_m", "stroke_rate_hz"]:
            preds = ["height_m", "mass_kg", "log_distance_m"]
            ols_sub = sub[[outcome] + preds].dropna().copy()
            if len(ols_sub) >= 7:
                y_raw = ols_sub[outcome].astype(float)
                X_raw = ols_sub[preds].astype(float)
                y_z = (y_raw - y_raw.mean()) / y_raw.std(ddof=0)
                X_z = sm.add_constant((X_raw - X_raw.mean()) / X_raw.std(ddof=0))
                fit = sm.OLS(y_z, X_z).fit()
                Xv = sm.add_constant(X_raw)
                vifs = {
                    col: float(variance_inflation_factor(Xv.values, i))
                    for i, col in enumerate(Xv.columns)
                    if col != "const"
                }
                model_rows.append(
                    {
                        "tier": "Tier2_Matched_Anthro",
                        "analysis_type": "anthro_to_stroke_ols",
                        "sex": sex,
                        "scope": "All_Matched_DistAdj",
                        "model_or_test": f"Height + Mass + ln(Dist) -> {outcome}",
                        "n": len(ols_sub),
                        "stat_primary": float(fit.params["height_m"]),
                        "p_primary": float(fit.pvalues["height_m"]),
                        "stat_secondary": float(fit.params["mass_kg"]),
                        "p_secondary": float(fit.pvalues["mass_kg"]),
                        "r2": float(fit.rsquared),
                        "adj_r2": float(fit.rsquared_adj),
                        "details_json": json.dumps(
                            {
                                "betas": {k: float(fit.params[k]) for k in preds},
                                "pvals": {k: float(fit.pvalues[k]) for k in preds},
                                "vifs": vifs,
                                "f_stat": float(fit.fvalue),
                                "f_pval": float(fit.f_pvalue),
                            }
                        ),
                    }
                )

            # Within-Sprint correlation (largest matched cell: n=7 Men, n=7 Women)
            spr = sub[sub["event_category"] == "Sprint"]
            for anthro in ["height_m", "mass_kg"]:
                c = safe_corr(spr[anthro], spr[outcome])
                if c["n"] >= 4:
                    model_rows.append(
                        {
                            "tier": "Tier2_Matched_Anthro",
                            "analysis_type": "anthro_to_stroke_corr",
                            "sex": sex,
                            "scope": "Sprint",
                            "model_or_test": f"{anthro} vs {outcome}",
                            "n": c["n"],
                            "stat_primary": c["pearson_r"],
                            "p_primary": c["p_pearson"],
                            "stat_secondary": c["spearman_rho"],
                            "p_secondary": c["p_spearman"],
                            "r2": np.nan,
                            "adj_r2": np.nan,
                            "details_json": json.dumps({"pearson_r": c["pearson_r"], "spearman_rho": c["spearman_rho"]}),
                        }
                    )

    return pd.DataFrame(model_rows)


def make_kinematics_figure(df: pd.DataFrame, out_path: Path) -> None:
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.05)
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.4))
    df_p = df.copy()
    df_p["event_short"] = df_p["event"].map(SHORT_MAP)
    present_short = [SHORT_MAP[e] for e in EVENT_ORDER if e in set(df_p["event"])]

    # Panel A: Whole-Race vs Clean Mid-Pool Velocity (Start/Turn Inflation)
    ax_a = axes[0, 0]
    vel_long = df_p.melt(
        id_vars=["sex", "event_short"],
        value_vars=["whole_race_velocity_ms", "clean_velocity_ms"],
        var_name="metric",
        value_name="velocity_ms",
    )
    vel_long["metric"] = vel_long["metric"].map(
        {"whole_race_velocity_ms": "Whole-Race Speed", "clean_velocity_ms": "Clean Mid-Pool Speed"}
    )
    vel_long["group"] = vel_long["sex"] + " — " + vel_long["metric"]
    vel_hue_order = [
        "Men — Whole-Race Speed",
        "Men — Clean Mid-Pool Speed",
        "Women — Whole-Race Speed",
        "Women — Clean Mid-Pool Speed",
    ]
    sns.pointplot(
        data=vel_long,
        x="event_short",
        y="velocity_ms",
        hue="group",
        hue_order=vel_hue_order,
        order=present_short,
        palette={
            "Men — Whole-Race Speed": "#1B4F72",
            "Men — Clean Mid-Pool Speed": "#5DADE2",
            "Women — Whole-Race Speed": "#B03A2E",
            "Women — Clean Mid-Pool Speed": "#F1948A",
        },
        markers=["o", "o", "s", "s"],
        linestyles=["-", "--", "-", "--"],
        errorbar=("ci", 95),
        dodge=0.18,
        ax=ax_a,
    )
    ax_a.set_title("A. Whole-Race vs. Clean Mid-Pool Speed (N = 92)", fontweight="bold")
    ax_a.set_xlabel("Freestyle Event", fontweight="bold")
    ax_a.set_ylabel("Velocity (m/s)", fontweight="bold")
    ax_a.legend(fontsize=7.5, frameon=True, loc="upper right")

    # Panel B: Stroke Rate vs. Stroke Length Trade-off across 6 Events
    ax_b = axes[0, 1]
    for evt in EVENT_ORDER:
        ev = df_p[df_p["event"] == evt]
        if ev.empty:
            continue
        for sex, marker in [("Men", "o"), ("Women", "^")]:
            es = ev[ev["sex"] == sex]
            if es.empty:
                continue
            lbl = f"{SHORT_MAP[evt]} ({sex[0]})"
            ax_b.scatter(
                es["stroke_rate_hz"],
                es["stroke_length_m"],
                color=PALETTE_EVT[evt],
                marker=marker,
                s=48,
                alpha=0.84,
                edgecolors="white",
                linewidth=0.5,
                label=lbl,
            )
    ax_b.set_title("B. 6-Event Stroke Length vs. Stroke Rate (Circles=Men, Triangles=Women)", fontweight="bold")
    ax_b.set_xlabel("Stroke Rate (cycles/s, Hz)", fontweight="bold")
    ax_b.set_ylabel("Stroke Length (m/cycle)", fontweight="bold")
    ax_b.legend(ncol=3, fontsize=7.2, frameon=True, loc="upper right")

    # Panel C: Paired Whole-Race vs Clean Mid-Pool Froude Number (Matched Cohort)
    ax_c = axes[1, 0]
    matched = df_p[df_p["height_m"].notna() & df_p["clean_froude_number"].notna()].copy()
    if not matched.empty:
        fr_long = matched.melt(
            id_vars=["sex", "event_short"],
            value_vars=["whole_race_froude", "clean_froude_number"],
            var_name="metric",
            value_name="froude",
        )
        fr_long["metric"] = fr_long["metric"].map(
            {"whole_race_froude": "Whole-Race Fr", "clean_froude_number": "Clean Mid-Pool Fr"}
        )
        fr_long["group"] = fr_long["sex"] + " — " + fr_long["metric"]
        matched_short = [SHORT_MAP[e] for e in EVENT_ORDER if e in set(matched["event"])]
        fr_hue_order = [
            "Men — Whole-Race Fr",
            "Men — Clean Mid-Pool Fr",
            "Women — Whole-Race Fr",
            "Women — Clean Mid-Pool Fr",
        ]
        sns.pointplot(
            data=fr_long,
            x="event_short",
            y="froude",
            hue="group",
            hue_order=fr_hue_order,
            order=matched_short,
            palette={
                "Men — Whole-Race Fr": "#1B4F72",
                "Men — Clean Mid-Pool Fr": "#5DADE2",
                "Women — Whole-Race Fr": "#B03A2E",
                "Women — Clean Mid-Pool Fr": "#F1948A",
            },
            markers=["o", "o", "s", "s"],
            linestyles=["-", "--", "-", "--"],
            errorbar=("ci", 95),
            dodge=0.18,
            ax=ax_c,
        )
        ax_c.axhline(0.42, color="#222222", linestyle="--", linewidth=1.3, label="Hull speed (Fr = 0.42)")
        ax_c.legend(fontsize=7.5, frameon=True, loc="upper right")
    else:
        ax_c.text(0.5, 0.5, "No matched anthropometric rows", ha="center", va="center", transform=ax_c.transAxes)
    ax_c.set_title("C. Whole-Race vs. Clean Mid-Pool Froude Number (Matched n = 30)", fontweight="bold")
    ax_c.set_xlabel("Freestyle Event", fontweight="bold")
    ax_c.set_ylabel("Froude Number (Fr)", fontweight="bold")

    # Panel D: Underwater Breakout Distance vs. Start/Turn Speed Inflation (All 92 Finalists)
    ax_d = axes[1, 1]
    uw_df = df_p.dropna(subset=["underwater_start_m", "start_turn_inflation_ms"]).copy()
    if not uw_df.empty:
        for evt in EVENT_ORDER:
            ev = uw_df[uw_df["event"] == evt]
            for sex, marker in [("Men", "o"), ("Women", "^")]:
                es = ev[ev["sex"] == sex]
                if es.empty:
                    continue
                ax_d.scatter(
                    es["underwater_start_m"],
                    es["start_turn_inflation_ms"],
                    color=PALETTE_EVT[evt],
                    marker=marker,
                    s=48,
                    alpha=0.84,
                    edgecolors="white",
                    linewidth=0.5,
                )
        for sex, ls in [("Men", "-"), ("Women", "--")]:
            s_sub = uw_df[uw_df["sex"] == sex]
            if len(s_sub) >= 3:
                r_val, p_val = stats.pearsonr(s_sub["underwater_start_m"], s_sub["start_turn_inflation_ms"])
                slope, intercept = np.polyfit(s_sub["underwater_start_m"], s_sub["start_turn_inflation_ms"], 1)
                xs = np.linspace(s_sub["underwater_start_m"].min(), s_sub["underwater_start_m"].max(), 50)
                ax_d.plot(
                    xs,
                    slope * xs + intercept,
                    color=SEX_PALETTE[sex],
                    linestyle=ls,
                    linewidth=1.8,
                    label=f"{sex} trend (r = {r_val:.2f}, p < 0.001)" if p_val < 0.001 else f"{sex} trend (r = {r_val:.2f}, p = {p_val:.3f})",
                )
        ax_d.legend(fontsize=8.0, frameon=True, loc="upper left")
    ax_d.set_title("D. Start Underwater Breakout vs. Start/Turn Speed Inflation (N = 92)", fontweight="bold")
    ax_d.set_xlabel("Start Underwater Breakout Distance (m)", fontweight="bold")
    ax_d.set_ylabel("Start/Turn Inflation Δv (m/s)", fontweight="bold")

    fig.suptitle(
        "Paris 2024 Olympic Freestyle Finals: Clean Hydrodynamics, Stroke Mechanics & Underwater Starts",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def run_analysis(
    csv_path: Path = IN_CSV,
    out_dir: Path = OUT_DIR,
    fig_dir: Path = FIG_DIR,
) -> int:
    if not csv_path.exists():
        print(
            f"[INFO] Input file not found: {csv_path}\n"
            f"Please populate the stroke measurement columns in:\n"
            f"  {TEMPLATE_CSV}\n"
            f"and save as {csv_path}, then re-run `python scripts/kinematics_analysis.py`."
        )
        return 0

    df = load_and_compute_kinematics(csv_path)
    if df.empty:
        print(f"[INFO] {csv_path} exists, but 0 rows have complete measurements.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    summary_df = summarize_by_event(df)
    models_df = run_non_tautological_models(df)

    summary_path = out_dir / "kinematics_summary.csv"
    models_path = out_dir / "kinematics_models.csv"
    fig_path = fig_dir / "kinematics_biomechanics.png"

    summary_df.to_csv(summary_path, index=False)
    models_df.to_csv(models_path, index=False)
    make_kinematics_figure(df, fig_path)

    n_matched = int((df["height_m"].notna() & df["mass_kg"].notna()).sum())
    print("=== PARIS 2024 KINEMATICS ANALYSIS COMPLETE (NON-TAUTOLOGICAL) ===")
    print(f"Populated finalist rows: {len(df)} (Matched anthropometrics: {n_matched})")
    print(f"Saved: {summary_path}\nSaved: {models_path}\nSaved: {fig_path}")

    print("\n=== 1. LOG-SPACE VARIANCE DECOMPOSITION (ln v_clean = ln SL + ln SR) ===")
    vd = models_df[models_df["analysis_type"] == "log_variance_decomposition"]
    for _, r in vd.iterrows():
        d = json.loads(r["details_json"])
        print(
            f"  {r['sex']:5s} | {r['scope']:12s} (n={int(r['n']):2d}) | "
            f"Var(ln SR)={d['pct_var_sr']:6.1f}% | Var(ln SL)={d['pct_var_sl']:6.1f}% | 2Cov={d['pct_2cov']:+7.1f}%"
        )

    print("\n=== 2. ANTHROPOMETRICS -> STROKE MECHANICS (DIST-ADJUSTED OLS, TIER 2) ===")
    ao = models_df[models_df["analysis_type"] == "anthro_to_stroke_ols"]
    for _, r in ao.iterrows():
        d = json.loads(r["details_json"])
        print(
            f"  {r['sex']:5s} | {r['model_or_test']:42s} (n={int(r['n']):2d}) | "
            f"R2={r['r2']:.3f} | Height b={d['betas']['height_m']:+.3f} (p={d['pvals']['height_m']:.3f}) | "
            f"Mass b={d['betas']['mass_kg']:+.3f} (p={d['pvals']['mass_kg']:.3f})"
        )

    print("\n=== 3. START / UNDERWATER MECHANICS (ALL 6 EVENTS) ===")
    uw = models_df[(models_df["analysis_type"] == "start_underwater_corr") & (models_df["scope"] == "All_6_Events")]
    for _, r in uw.iterrows():
        print(
            f"  {r['sex']:5s} | {r['model_or_test']:44s} (n={int(r['n']):2d}) | "
            f"r={r['stat_primary']:+.3f} (p={r['p_primary']:.3g}) | rho={r['stat_secondary']:+.3f}"
        )

    print("\n=== 4. MEN'S 200M CLEAN FROUDE ROBUSTNESS CHECK (ALL 8 FINALISTS) ===")
    m2 = models_df[models_df["analysis_type"] == "men_200m_froude_sensitivity"]
    for _, r in m2.iterrows():
        d = json.loads(r["details_json"])
        print(
            f"  {r['model_or_test']:48s} | mean Fr={d['clean_fr_mean']:.4f} ± {d['clean_fr_sd']:.4f} "
            f"[{d['clean_fr_min']:.4f}, {d['clean_fr_max']:.4f}] | >0.42: {d['n_clean_fr_gt_042']}/8 ({d['pct_clean_fr_gt_042']:.1f}%)"
        )
    return 0


def main() -> None:
    sys.exit(run_analysis())


if __name__ == "__main__":
    main()