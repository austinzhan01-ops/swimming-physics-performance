"""
Statistical Analysis & Visualization for Sprint vs. Distance Freestyle Physics
=============================================================================
Tests hydrodynamic and anthropometric hypotheses from PROJECT SUMMARY.md
using deduplicated athlete-event data (primary) and full multi-round results
(cluster-robust sensitivity check), strictly stratified by sex.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor

# ---------------------------------------------------------------------------
# Paths & Setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_AE = ROOT / "data" / "processed" / "swimming_athlete_event_clean.csv"
DATA_RC = ROOT / "data" / "processed" / "swimming_results_clean.csv"
FIG_DIR = ROOT / "results" / "figures"
OUT_DIR = ROOT / "results"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)
PALETTE_CAT = {"Sprint": "#D55E00", "Distance": "#0072B2"}
PALETTE_EVT = {
    "50m Freestyle": "#D55E00",
    "100m Freestyle": "#E69F00",
    "800m Freestyle": "#56B4E9",
    "1500m Freestyle": "#0072B2",
}
EVENT_ORDER = ["50m Freestyle", "100m Freestyle", "800m Freestyle", "1500m Freestyle"]

METRICS = [
    ("height_m", "Height (m)"),
    ("mass_kg", "Body Mass (kg)"),
    ("bmi", "BMI (kg/m²)"),
    ("ponderal_index", "Ponderal Index (kg/m³)"),
    ("velocity_ms", "Mean Race Speed (m/s)"),
    ("froude_number", "Froude Number (Fr)"),
    ("froude_hull_ratio", "Froude / Hull Ratio (Fr/0.42)"),
    ("reynolds_number", "Reynolds Number (Re)"),
    ("wa_points", "World Aquatics Points"),
]


# ---------------------------------------------------------------------------
# Effect Size Helpers
# ---------------------------------------------------------------------------
def hedges_g_ci(x1: np.ndarray, x2: np.ndarray, alpha: float = 0.05) -> tuple[float, float, float]:
    """Compute Hedges' g (x1 - x2) and analytical 95% CI."""
    n1, n2 = len(x1), len(x2)
    m1, m2 = np.mean(x1), np.mean(x2)
    s1, s2 = np.var(x1, ddof=1), np.var(x2, ddof=1)
    sp = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if sp == 0:
        return 0.0, 0.0, 0.0
    d = (m1 - m2) / sp
    df = n1 + n2 - 2
    j = 1.0 - (3.0 / (4.0 * df - 1.0))
    g = d * j
    se_g = np.sqrt((n1 + n2) / (n1 * n2) + (g ** 2) / (2.0 * (n1 + n2)))
    z = stats.norm.ppf(1.0 - alpha / 2.0)
    return float(g), float(g - z * se_g), float(g + z * se_g)


def rank_biserial_ci(
    x1: np.ndarray, x2: np.ndarray, n_boot: int = 1000, seed: int = 42
) -> tuple[float, float, float, float, float]:
    """
    Compute Mann-Whitney U, p-value, and signed rank-biserial r (positive => x1 > x2)
    with percentile bootstrap 95% CI.
    """
    u_stat, p_val = stats.mannwhitneyu(x1, x2, alternative="two-sided")
    n1, n2 = len(x1), len(x2)
    r = (2.0 * u_stat) / (n1 * n2) - 1.0
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        b1 = rng.choice(x1, size=n1, replace=True)
        b2 = rng.choice(x2, size=n2, replace=True)
        u_b, _ = stats.mannwhitneyu(b1, b2, alternative="two-sided")
        boots[i] = (2.0 * u_b) / (n1 * n2) - 1.0
    ci_low, ci_high = np.percentile(boots, [2.5, 97.5])
    return float(u_stat), float(p_val), float(r), float(ci_low), float(ci_high)


def fmt_p(p: float) -> str:
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


# ---------------------------------------------------------------------------
# 1 & 2. Sprint vs. Distance Group Comparisons + Sensitivity Splits
# ---------------------------------------------------------------------------
def run_group_comparisons(df: pd.DataFrame, subset_name: str = "primary") -> pd.DataFrame:
    rows = []
    for sex in ["Men", "Women"]:
        sub = df[df["sex"] == sex]
        spr = sub[sub["event_category"] == "Sprint"]
        dst = sub[sub["event_category"] == "Distance"]
        if len(spr) < 3 or len(dst) < 3:
            continue

        p_welch_list = []
        p_mwu_list = []
        sex_rows = []
        for col, label in METRICS:
            x1 = spr[col].dropna().to_numpy(dtype=float)
            x2 = dst[col].dropna().to_numpy(dtype=float)
            t_stat, p_w = stats.ttest_ind(x1, x2, equal_var=False)
            g, g_lo, g_hi = hedges_g_ci(x1, x2)
            u_stat, p_mwu, r_rb, r_lo, r_hi = rank_biserial_ci(x1, x2, n_boot=800)

            p_welch_list.append(p_w)
            p_mwu_list.append(p_mwu)
            sex_rows.append(
                {
                    "subset": subset_name,
                    "sex": sex,
                    "metric": col,
                    "label": label,
                    "n_sprint": len(x1),
                    "n_distance": len(x2),
                    "sprint_mean": float(np.mean(x1)),
                    "sprint_sd": float(np.std(x1, ddof=1)),
                    "sprint_median": float(np.median(x1)),
                    "sprint_iqr": float(np.percentile(x1, 75) - np.percentile(x1, 25)),
                    "dist_mean": float(np.mean(x2)),
                    "dist_sd": float(np.std(x2, ddof=1)),
                    "dist_median": float(np.median(x2)),
                    "dist_iqr": float(np.percentile(x2, 75) - np.percentile(x2, 25)),
                    "t_welch": float(t_stat),
                    "p_welch": float(p_w),
                    "u_mwu": float(u_stat),
                    "p_mwu": float(p_mwu),
                    "hedges_g": g,
                    "g_ci_low": g_lo,
                    "g_ci_high": g_hi,
                    "rank_biserial_r": r_rb,
                    "r_ci_low": r_lo,
                    "r_ci_high": r_hi,
                }
            )

        _, fdr_welch, _, _ = multipletests(p_welch_list, method="fdr_bh")
        _, fdr_mwu, _, _ = multipletests(p_mwu_list, method="fdr_bh")
        for idx, r in enumerate(sex_rows):
            r["p_welch_fdr"] = float(fdr_welch[idx])
            r["p_mwu_fdr"] = float(fdr_mwu[idx])
        rows.extend(sex_rows)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Event-Level Distance Gradient (50m -> 100m -> 800m -> 1500m)
# ---------------------------------------------------------------------------
def run_event_gradient(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    trend_rows = []
    for sex in ["Men", "Women"]:
        sub = df[df["sex"] == sex]
        for evt in EVENT_ORDER:
            ev = sub[sub["event"] == evt]
            for col, label in METRICS:
                vals = ev[col].dropna().to_numpy(dtype=float)
                summary_rows.append(
                    {
                        "sex": sex,
                        "event": evt,
                        "distance_m": int(ev["distance_m"].iloc[0]) if len(ev) else np.nan,
                        "n": len(vals),
                        "metric": col,
                        "mean": float(np.mean(vals)) if len(vals) else np.nan,
                        "sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan,
                        "median": float(np.median(vals)) if len(vals) else np.nan,
                        "iqr": float(np.percentile(vals, 75) - np.percentile(vals, 25))
                        if len(vals)
                        else np.nan,
                    }
                )

        for col, label in METRICS:
            groups = [sub[sub["event"] == e][col].dropna().to_numpy(dtype=float) for e in EVENT_ORDER]
            f_stat, p_anova = stats.f_oneway(*groups)
            h_stat, p_kw = stats.kruskal(*groups)
            rho, p_sp = stats.spearmanr(sub["distance_m"], sub[col], nan_policy="omit")
            trend_rows.append(
                {
                    "sex": sex,
                    "metric": col,
                    "label": label,
                    "anova_f": float(f_stat),
                    "p_anova": float(p_anova),
                    "kw_h": float(h_stat),
                    "p_kw": float(p_kw),
                    "spearman_rho_dist": float(rho),
                    "p_spearman": float(p_sp),
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(trend_rows)


# ---------------------------------------------------------------------------
# 4a. Within-Category Correlations
# ---------------------------------------------------------------------------
def run_correlations(df: pd.DataFrame) -> pd.DataFrame:
    anthro = ["height_m", "mass_kg", "bmi", "ponderal_index"]
    perf = ["velocity_ms", "froude_number", "wa_points"]
    rows = []
    for sex in ["Men", "Women"]:
        for cat in ["Sprint", "Distance"]:
            sub = df[(df["sex"] == sex) & (df["event_category"] == cat)]
            for a in anthro:
                for p_col in perf:
                    valid = sub[[a, p_col]].dropna()
                    r_p, p_p = stats.pearsonr(valid[a], valid[p_col])
                    r_s, p_s = stats.spearmanr(valid[a], valid[p_col])
                    rows.append(
                        {
                            "sex": sex,
                            "category": cat,
                            "n": len(valid),
                            "predictor": a,
                            "outcome": p_col,
                            "pearson_r": float(r_p),
                            "p_pearson": float(p_p),
                            "spearman_rho": float(r_s),
                            "p_spearman": float(p_s),
                        }
                    )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4b. Parsimonious OLS Regressions + VIF + Cluster-Robust Check
# ---------------------------------------------------------------------------
def fit_ols_model(
    df: pd.DataFrame,
    outcome: str,
    predictors: list[str],
    cluster_col: str | None = None,
) -> dict:
    cols = [outcome] + predictors + ([cluster_col] if cluster_col else [])
    sub = df[cols].dropna().copy()

    # Standardized (z-scored) version for standardized betas & VIFs
    X_raw = sub[predictors].astype(float)
    y_raw = sub[outcome].astype(float)

    X_z = (X_raw - X_raw.mean()) / X_raw.std(ddof=0)
    y_z = (y_raw - y_raw.mean()) / y_raw.std(ddof=0)

    X_z_const = sm.add_constant(X_z)
    if cluster_col:
        model = sm.OLS(y_z, X_z_const).fit(
            cov_type="cluster", cov_kwds={"groups": sub[cluster_col]}
        )
    else:
        model = sm.OLS(y_z, X_z_const).fit()

    # Compute VIF on predictor matrix with constant
    X_vif = sm.add_constant(X_raw)
    vifs = {}
    for i, col in enumerate(X_vif.columns):
        if col == "const":
            continue
        vifs[col] = float(variance_inflation_factor(X_vif.values, i))

    return {
        "n": len(sub),
        "r2": float(model.rsquared),
        "adj_r2": float(model.rsquared_adj),
        "f_stat": float(model.fvalue) if model.fvalue is not None else np.nan,
        "f_pval": float(model.f_pvalue) if model.f_pvalue is not None else np.nan,
        "betas": {k: float(model.params[k]) for k in predictors},
        "pvals": {k: float(model.pvalues[k]) for k in predictors},
        "ses": {k: float(model.bse[k]) for k in predictors},
        "vifs": vifs,
        "max_vif": float(max(vifs.values())) if vifs else 1.0,
    }


def run_ols_suite(df_ae: pd.DataFrame, df_rc: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("M1: Height + Mass + Year + Age", ["height_m", "mass_kg", "year", "age_approx"]),
        ("M2: BMI + Year + Age", ["bmi", "year", "age_approx"]),
        ("M3: PI + Year + Age", ["ponderal_index", "year", "age_approx"]),
    ]
    rows = []
    for dataset_name, df, clust in [
        ("AE_dedup", df_ae, None),
        ("RC_cluster_athlete", df_rc, "athlete_key"),
    ]:
        for sex in ["Men", "Women"]:
            for scope_name, scope_filter in [
                ("Sprint", df["event_category"] == "Sprint"),
                ("Distance", df["event_category"] == "Distance"),
                ("All_Events", pd.Series(True, index=df.index)),
            ]:
                sub = df[(df["sex"] == sex) & scope_filter]
                outcomes = ["wa_points"] if scope_name == "All_Events" else ["velocity_ms", "wa_points"]
                for outcome in outcomes:
                    for model_name, preds in specs:
                        res = fit_ols_model(sub, outcome, preds, cluster_col=clust)
                        rows.append(
                            {
                                "dataset": dataset_name,
                                "sex": sex,
                                "scope": scope_name,
                                "outcome": outcome,
                                "model": model_name,
                                "n": res["n"],
                                "r2": res["r2"],
                                "adj_r2": res["adj_r2"],
                                "max_vif": res["max_vif"],
                                "betas": json.dumps(res["betas"]),
                                "pvals": json.dumps(res["pvals"]),
                                "vifs": json.dumps(res["vifs"]),
                            }
                        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4c. Zero-Leakage Anthropometric Logistic Regression (5-Fold CV + ORs)
# ---------------------------------------------------------------------------
def run_logistic_cv(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    specs = [
        ("Height + Mass", ["height_m", "mass_kg"]),
        ("Height alone", ["height_m"]),
        ("BMI alone", ["bmi"]),
        ("PI alone", ["ponderal_index"]),
    ]
    rows = []
    roc_curves = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for sex in ["Men", "Women"]:
        sub = df[df["sex"] == sex].copy()
        y = (sub["event_category"] == "Sprint").astype(int).to_numpy()
        for model_name, feats in specs:
            X = sub[feats].to_numpy(dtype=float)
            pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42))
            probs = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
            preds = (probs >= 0.5).astype(int)
            auc = roc_auc_score(y, probs)
            acc = accuracy_score(y, preds)
            fpr, tpr, _ = roc_curve(y, probs)
            roc_curves[(sex, model_name)] = (fpr, tpr, auc)

            # Full-sample standardized Odds Ratios via statsmodels Logit
            X_df = sub[feats].astype(float)
            X_z = (X_df - X_df.mean()) / X_df.std(ddof=0)
            logit_res = sm.Logit(y, sm.add_constant(X_z)).fit(disp=False)
            ors = {}
            or_cis = {}
            pvals = {}
            for f in feats:
                coef = float(logit_res.params[f])
                se = float(logit_res.bse[f])
                ors[f] = float(np.exp(coef))
                or_cis[f] = [float(np.exp(coef - 1.96 * se)), float(np.exp(coef + 1.96 * se))]
                pvals[f] = float(logit_res.pvalues[f])

            rows.append(
                {
                    "sex": sex,
                    "model": model_name,
                    "n": len(sub),
                    "n_sprint": int(y.sum()),
                    "n_distance": int((1 - y).sum()),
                    "cv_roc_auc": float(auc),
                    "cv_accuracy": float(acc),
                    "std_odds_ratios": json.dumps(ors),
                    "or_95_cis": json.dumps(or_cis),
                    "pvals": json.dumps(pvals),
                }
            )
    return pd.DataFrame(rows), roc_curves


# ---------------------------------------------------------------------------
# 5. Publication-Quality Figures
# ---------------------------------------------------------------------------
def make_fig1_anthropometrics(df: pd.DataFrame, stats_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), sharex=True)
    panels = [
        ("height_m", "Standing Height (m)"),
        ("mass_kg", "Body Mass (kg)"),
        ("bmi", "Body Mass Index (kg/m²)"),
        ("ponderal_index", "Ponderal Index (kg/m³)"),
    ]
    for ax, (col, ylabel) in zip(axes.flat, panels):
        sns.boxplot(
            data=df,
            x="sex",
            y=col,
            hue="event_category",
            hue_order=["Sprint", "Distance"],
            palette=PALETTE_CAT,
            width=0.55,
            showfliers=False,
            boxprops={"alpha": 0.75},
            ax=ax,
        )
        sns.stripplot(
            data=df,
            x="sex",
            y=col,
            hue="event_category",
            hue_order=["Sprint", "Distance"],
            palette=PALETTE_CAT,
            dodge=True,
            alpha=0.45,
            size=3.5,
            legend=False,
            ax=ax,
        )
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_xlabel("")
        if ax.get_legend() is not None:
            ax.get_legend().remove()

        # Annotate Hedges' g and BH-FDR p-value
        ymin, ymax = ax.get_ylim()
        yrange = ymax - ymin
        ax.set_ylim(ymin, ymax + 0.16 * yrange)
        for i, sex in enumerate(["Men", "Women"]):
            row = stats_df[(stats_df["sex"] == sex) & (stats_df["metric"] == col)].iloc[0]
            txt = f"g = {row['hedges_g']:.2f}\np_FDR = {fmt_p(row['p_welch_fdr'])}"
            ax.text(
                i,
                ymax + 0.02 * yrange,
                txt,
                ha="center",
                va="bottom",
                fontsize=8.5,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CCCCCC", alpha=0.9),
            )

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles[:2], labels[:2], title="Event Category", loc="upper center", bbox_to_anchor=(0.5, 0.945), ncol=2, frameon=True)
    fig.suptitle(
        "Anthropometric Profiles: Olympic Sprint (50m/100m) vs. Distance (800m/1500m) Freestyle",
        fontsize=13,
        fontweight="bold",
        y=0.985,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.89])
    fig.savefig(FIG_DIR / "anthropometrics_sprint_vs_distance.png", dpi=300)
    plt.close(fig)


def make_fig2_froude_vs_height(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, sex in zip(axes, ["Men", "Women"]):
        sub = df[df["sex"] == sex]
        for evt in EVENT_ORDER:
            ev = sub[sub["event"] == evt]
            ax.scatter(
                ev["height_m"],
                ev["froude_number"],
                label=f"{evt.replace(' Freestyle', '')} (n={len(ev)})",
                color=PALETTE_EVT[evt],
                alpha=0.78,
                s=42,
                edgecolors="white",
                linewidth=0.5,
            )
        ax.axhline(0.42, color="#222222", linestyle="--", linewidth=1.4, label="Hull-speed transition (Fr = 0.42)")
        ax.axhspan(0.40, 0.44, color="#888888", alpha=0.12)
        ax.set_title(f"{sex} (N = {len(sub)})", fontweight="bold")
        ax.set_xlabel("Standing Height L (m)", fontweight="bold")
        if ax == axes[0]:
            ax.set_ylabel("Froude Number Fr = v / √(gL)", fontweight="bold")
        ax.legend(loc="lower right", fontsize=8.5, frameon=True)

    fig.suptitle(
        "Froude Number vs. Standing Height Across Olympic Freestyle Events (2000–2024)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG_DIR / "froude_vs_height.png", dpi=300)
    plt.close(fig)


def make_fig3_bmi_vs_height(df: pd.DataFrame, roc_curves: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9.0))
    for row_idx, sex in enumerate(["Men", "Women"]):
        sub = df[df["sex"] == sex]
        # Left: Height vs BMI scatter
        ax_sc = axes[row_idx, 0]
        for cat in ["Sprint", "Distance"]:
            c_sub = sub[sub["event_category"] == cat]
            ax_sc.scatter(
                c_sub["height_m"],
                c_sub["bmi"],
                label=f"{cat} (n={len(c_sub)})",
                color=PALETTE_CAT[cat],
                alpha=0.72,
                s=40,
                edgecolors="white",
                linewidth=0.4,
            )
            ax_sc.axvline(c_sub["height_m"].mean(), color=PALETTE_CAT[cat], linestyle=":", linewidth=1.3)
            ax_sc.axhline(c_sub["bmi"].mean(), color=PALETTE_CAT[cat], linestyle="--", linewidth=1.1, alpha=0.7)
        ax_sc.set_title(f"{sex}: Height vs. BMI (Dashed = Group Means)", fontweight="bold")
        ax_sc.set_xlabel("Standing Height (m)", fontweight="bold")
        ax_sc.set_ylabel("BMI (kg/m²)", fontweight="bold")
        ax_sc.legend(loc="upper left", fontsize=8.5, frameon=True)

        # Right: 5-Fold CV ROC Curves
        ax_roc = axes[row_idx, 1]
        roc_styles = [
            ("Height + Mass", "#D55E00", "-"),
            ("Height alone", "#E69F00", "--"),
            ("BMI alone", "#0072B2", "-."),
            ("PI alone", "#009E73", ":"),
        ]
        for m_name, color, ls in roc_styles:
            fpr, tpr, auc = roc_curves[(sex, m_name)]
            ax_roc.plot(fpr, tpr, label=f"{m_name} (AUC = {auc:.3f})", color=color, linestyle=ls, linewidth=2.0)
        ax_roc.plot([0, 1], [0, 1], color="#888888", linestyle="--", linewidth=1.0)
        ax_roc.set_title(f"{sex}: Zero-Leakage 5-Fold CV ROC (Sprint vs. Distance)", fontweight="bold")
        ax_roc.set_xlabel("False Positive Rate", fontweight="bold")
        ax_roc.set_ylabel("True Positive Rate", fontweight="bold")
        ax_roc.legend(loc="lower right", fontsize=8.5, frameon=True)

    fig.suptitle(
        "Testing Gagnon et al. (2018): Height Separates Sprint vs. Distance Even When BMI Overlaps",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(FIG_DIR / "bmi_vs_height_separation.png", dpi=300)
    plt.close(fig)


def make_fig4_gradient_and_regression(df: pd.DataFrame, logit_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.8))
    short_map = {
        "50m Freestyle": "50m",
        "100m Freestyle": "100m",
        "800m Freestyle": "800m",
        "1500m Freestyle": "1500m",
    }
    df_p = df.copy()
    df_p["event_short"] = df_p["event"].map(short_map)
    short_order = ["50m", "100m", "800m", "1500m"]

    grad_panels = [
        (axes[0, 0], "height_m", "Standing Height (m)", "A. Height Gradient Across Distances"),
        (axes[0, 1], "bmi", "BMI (kg/m²)", "B. BMI Stability Across Distances"),
        (axes[1, 0], "froude_number", "Froude Number (Fr)", "C. Froude Number Across Distances"),
    ]
    for ax, col, ylabel, title in grad_panels:
        sns.pointplot(
            data=df_p,
            x="event_short",
            y=col,
            hue="sex",
            order=short_order,
            palette={"Men": "#1B4F72", "Women": "#B03A2E"},
            errorbar=("ci", 95),
            dodge=0.15,
            markers=["o", "s"],
            ax=ax,
        )
        if col == "froude_number":
            ax.axhline(0.42, color="#222222", linestyle="--", linewidth=1.2, label="Fr = 0.42")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Freestyle Event", fontweight="bold")
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.legend(title="Sex", frameon=True, fontsize=8.5)

    # Panel D: Standardized Logistic Odds Ratios (Height + Mass model & BMI alone)
    ax_or = axes[1, 1]
    or_rows = []
    for sex in ["Men", "Women"]:
        r_hm = logit_df[(logit_df["sex"] == sex) & (logit_df["model"] == "Height + Mass")].iloc[0]
        ors_hm = json.loads(r_hm["std_odds_ratios"])
        cis_hm = json.loads(r_hm["or_95_cis"])
        for feat, lbl in [("height_m", "Height (adj. Mass)"), ("mass_kg", "Mass (adj. Height)")]:
            or_rows.append(
                {
                    "label": f"{sex}: {lbl}",
                    "or": ors_hm[feat],
                    "lo": cis_hm[feat][0],
                    "hi": cis_hm[feat][1],
                    "sex": sex,
                }
            )
        r_bmi = logit_df[(logit_df["sex"] == sex) & (logit_df["model"] == "BMI alone")].iloc[0]
        ors_bmi = json.loads(r_bmi["std_odds_ratios"])
        cis_bmi = json.loads(r_bmi["or_95_cis"])
        or_rows.append(
            {
                "label": f"{sex}: BMI (alone)",
                "or": ors_bmi["bmi"],
                "lo": cis_bmi["bmi"][0],
                "hi": cis_bmi["bmi"][1],
                "sex": sex,
            }
        )
    or_df = pd.DataFrame(or_rows)
    y_pos = np.arange(len(or_df))
    colors = ["#1B4F72" if s == "Men" else "#B03A2E" for s in or_df["sex"]]
    ax_or.errorbar(
        or_df["or"],
        y_pos,
        xerr=[or_df["or"] - or_df["lo"], or_df["hi"] - or_df["or"]],
        fmt="o",
        color="#333333",
        ecolor="#666666",
        capsize=4,
        markersize=0,
    )
    ax_or.scatter(or_df["or"], y_pos, color=colors, s=55, zorder=3)
    ax_or.axvline(1.0, color="#222222", linestyle="--", linewidth=1.2)
    ax_or.set_yticks(y_pos)
    ax_or.set_yticklabels(or_df["label"], fontsize=9)
    ax_or.invert_yaxis()
    ax_or.set_xlabel("Standardized Odds Ratio for Sprint (per 1-SD)", fontweight="bold")
    ax_or.set_title("D. Anthropometric Predictors of Sprint Status", fontweight="bold")

    fig.suptitle(
        "Distance-Gradient Trends & Anthropometric Odds Ratios (Sprint vs. Distance)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(FIG_DIR / "event_gradient_and_regression.png", dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def main() -> None:
    df_ae = pd.read_csv(DATA_AE)
    df_rc = pd.read_csv(DATA_RC)

    # 1. Sample & Overlap Diagnostics
    print("=== SAMPLE & OVERLAP DIAGNOSTICS ===")
    print(f"AE rows: {len(df_ae)}, unique athletes: {df_ae['athlete_key'].nunique()}")
    print(f"RC rows: {len(df_rc)}, unique athletes: {df_rc['athlete_key'].nunique()}")
    for sex in ["Men", "Women"]:
        sub = df_ae[df_ae["sex"] == sex]
        both_sprint = sub[sub["event"].isin(["50m Freestyle", "100m Freestyle"])].groupby("athlete_key")["event"].nunique().gt(1).sum()
        both_cat = sub.groupby("athlete_key")["event_category"].nunique().gt(1).sum()
        print(f"  {sex}: {len(sub)} AE rows, {sub['athlete_key'].nunique()} unique athletes, {both_sprint} in both 50m & 100m, {both_cat} in both Sprint & Distance")

    # 2. Primary + Sensitivity Group Comparisons
    splits = {
        "primary_all_2000_2024": df_ae,
        "textile_2012_2024": df_ae[df_ae["year"] >= 2012],
        "excl_supersuit_2008": df_ae[df_ae["year"] != 2008],
        "excl_50m_100m_vs_dist": df_ae[df_ae["event"] != "50m Freestyle"],
        "finalists_only": df_ae[df_ae["stage"] == "Final"],
        "one_row_per_athlete_best_wa": df_ae.sort_values("wa_points", ascending=False).drop_duplicates("athlete_key"),
    }
    comp_frames = [run_group_comparisons(sub, name) for name, sub in splits.items()]
    comp_df = pd.concat(comp_frames, ignore_index=True)
    comp_df.to_csv(OUT_DIR / "sprint_vs_distance_comparisons.csv", index=False)

    # Froude threshold (> 0.42) rates
    print("\n=== FROUDE > 0.42 RATES (PRIMARY AE) ===")
    for sex in ["Men", "Women"]:
        for evt in EVENT_ORDER:
            ev = df_ae[(df_ae["sex"] == sex) & (df_ae["event"] == evt)]
            pct = 100.0 * (ev["froude_number"] > 0.42).mean() if len(ev) else np.nan
            print(f"  {sex} {evt}: n={len(ev)}, mean Fr={ev['froude_number'].mean():.3f}, % > 0.42 = {pct:.1f}%")

    # 3. Distance-Gradient Analysis
    grad_summary, grad_trends = run_event_gradient(df_ae)
    grad_summary.to_csv(OUT_DIR / "event_gradient_summary.csv", index=False)
    grad_trends.to_csv(OUT_DIR / "event_gradient_trends.csv", index=False)

    # 4. Correlations, OLS (+ Cluster-Robust), Logistic CV
    corr_df = run_correlations(df_ae)
    corr_df.to_csv(OUT_DIR / "within_category_correlations.csv", index=False)

    ols_df = run_ols_suite(df_ae, df_rc)
    ols_df.to_csv(OUT_DIR / "ols_regression_results.csv", index=False)

    logit_df, roc_curves = run_logistic_cv(df_ae)
    logit_df.to_csv(OUT_DIR / "logistic_cv_results.csv", index=False)

    # 5. Figures
    primary_comp = comp_df[comp_df["subset"] == "primary_all_2000_2024"]
    make_fig1_anthropometrics(df_ae, primary_comp)
    make_fig2_froude_vs_height(df_ae)
    make_fig3_bmi_vs_height(df_ae, roc_curves)
    make_fig4_gradient_and_regression(df_ae, logit_df)

    # Print concise key findings to stdout
    print("\n=== PRIMARY SPRINT VS DISTANCE (HEIGHT, MASS, BMI, PI, FR) ===")
    key_cols = ["height_m", "mass_kg", "bmi", "ponderal_index", "froude_number", "wa_points"]
    p_view = primary_comp[primary_comp["metric"].isin(key_cols)]
    for _, r in p_view.iterrows():
        print(
            f"  {r['sex']:5s} | {r['metric']:14s} | Spr={r['sprint_mean']:.3f}±{r['sprint_sd']:.3f} | "
            f"Dst={r['dist_mean']:.3f}±{r['dist_sd']:.3f} | g={r['hedges_g']:.2f} [{r['g_ci_low']:.2f},{r['g_ci_high']:.2f}] | "
            f"p_FDR={fmt_p(r['p_welch_fdr'])} | r_rb={r['rank_biserial_r']:.2f}"
        )

    print("\n=== LOGISTIC CV (ZERO-LEAKAGE ANTHROPOMETRICS) ===")
    for _, r in logit_df.iterrows():
        print(
            f"  {r['sex']:5s} | {r['model']:14s} | AUC={r['cv_roc_auc']:.3f} | Acc={r['cv_accuracy']:.3f} | ORs={r['std_odds_ratios']}"
        )

    print("\n=== MAX VIF CHECK ACROSS ALL OLS MODELS ===")
    print(f"  Max VIF across all {len(ols_df)} OLS models: {ols_df['max_vif'].max():.3f}")
    print("\nSaved all CSVs to results/ and 4 figures to results/figures/.")


if __name__ == "__main__":
    main()