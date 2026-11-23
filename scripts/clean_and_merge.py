"""Clean, standardize, and merge Olympic Freestyle swimming results (2000-2024)
with athlete anthropometric data, compute hydrodynamic and performance metrics,
and validate physical bounds.

Outputs:
    - data/processed/swimming_results_clean.csv
    - data/processed/swimming_athlete_event_clean.csv
    - data/processed/data_validation_report.md
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

TARGET_EVENTS_DIST = {
    "50m": 50,
    "100m": 100,
    "200m": 200,
    "400m": 400,
    "800m": 800,
    "1500m": 1500,
}
G = 9.81
# World Aquatics standard competition pool water temperature (26 °C)
RHO_WATER = 996.8  # kg/m^3
MU_WATER = 8.7e-4  # Pa*s

CORE_COLS = [
    "athlete_key",
    "athlete_name",
    "sex",
    "noc",
    "year",
    "suit_era",
    "event",
    "event_category",
    "distance_m",
    "is_finalist",
    "time_sec",
    "height_m",
    "mass_kg",
    "bmi",
    "ponderal_index",
    "velocity_ms",
    "froude_number",
    "hull_speed_ms",
    "froude_hull_ratio",
    "reynolds_number",
    "wa_points",
]

NOC_ALIASES = {
    "ROC": "RUS",
    "OAR": "RUS",
    "EOR": "ROT",
}


def normalize_name(name: object) -> str:
    """Normalize athlete name: flip 'Lastname, Firstname', strip accents, lowercase."""
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


def token_set(name: object) -> frozenset[str]:
    return frozenset(normalize_name(name).split())


def token_key(name: object) -> str:
    return " ".join(sorted(token_set(name)))


def normalize_noc(noc: object) -> str:
    if pd.isna(noc):
        return ""
    s = str(noc).strip().upper()
    return NOC_ALIASES.get(s, s)


def normalize_sex(sex: object) -> str | None:
    if pd.isna(sex):
        return None
    s = str(sex).strip().lower()
    if s in {"m", "male", "men", "man"}:
        return "Men"
    if s in {"f", "female", "women", "woman"}:
        return "Women"
    return None


def parse_time_to_sec(val: object) -> float:
    """Parse SS.ss, MM:SS.ss, or HH:MM:SS.ss into float seconds; return NaN if invalid."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if not s or any(tok in s.upper() for tok in ("DNS", "DSQ", "DQ", "DNF", "WD", "NT", "NA")):
        return np.nan
    # Strip trailing annotations like 'OR', 'WR', 'r', etc.
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


def parse_olympedia_event(event: object) -> tuple[str | None, str | None]:
    if not isinstance(event, str) or "Relay" in event or "(YOG)" in event:
        return None, None
    sex = "Men" if "Men" in event else ("Women" if "Women" in event else None)
    for prefix, dist in [
        ("50 metres Freestyle", "50m"),
        ("100 metres Freestyle", "100m"),
        ("200 metres Freestyle", "200m"),
        ("400 metres Freestyle", "400m"),
        ("800 metres Freestyle", "800m"),
        ("1,500 metres Freestyle", "1500m"),
    ]:
        if event.startswith(prefix):
            return dist, sex
    return None, None


def parse_paris_event(event: object) -> tuple[str | None, str | None]:
    if not isinstance(event, str) or "Relay" in event:
        return None, None
    m = re.match(r"^(Men|Women)'s\s+(50m|100m|200m|400m|800m|1500m)\s+Freestyle$", event.strip())
    if not m:
        return None, None
    return m.group(2), m.group(1)


def load_bio_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and combine Olympedia and Kaggle 120-years bio tables.

    Returns:
        bios_by_id: indexed by integer athlete_id with height_cm, weight_kg, born_date, name, noc, sex
        bios_flat: deduplicated bio records for fallback name/DOB matching
    """
    ob = pd.read_csv(RAW_DIR / "olympedia_bios.csv", low_memory=False)
    oab = pd.read_csv(RAW_DIR / "Olympic_Athlete_Bio.csv", low_memory=False)
    ae = pd.read_csv(RAW_DIR / "kaggle_120_years" / "athlete_events.csv", low_memory=False)

    ob_clean = pd.DataFrame(
        {
            "athlete_id": pd.to_numeric(ob["athlete_id"], errors="coerce"),
            "name": ob["name"],
            "noc": ob["NOC"].map(normalize_noc),
            "sex": np.nan,
            "born_date": pd.to_datetime(ob["born_date"], errors="coerce").dt.strftime("%Y-%m-%d"),
            "height_cm": pd.to_numeric(ob["height_cm"], errors="coerce"),
            "weight_kg": pd.to_numeric(ob["weight_kg"], errors="coerce"),
            "bio_source": "olympedia_bios",
        }
    )

    oab_clean = pd.DataFrame(
        {
            "athlete_id": pd.to_numeric(oab["athlete_id"], errors="coerce"),
            "name": oab["name"],
            "noc": oab["country_noc"].map(normalize_noc),
            "sex": oab["sex"].map(normalize_sex),
            "born_date": pd.to_datetime(oab["born"], errors="coerce").dt.strftime("%Y-%m-%d"),
            "height_cm": pd.to_numeric(oab["height"], errors="coerce"),
            "weight_kg": pd.to_numeric(oab["weight"], errors="coerce"),
            "bio_source": "Olympic_Athlete_Bio",
        }
    )

    ae_sw = ae[ae["Sport"] == "Swimming"].copy()
    ae_sw = ae_sw.sort_values("Year", ascending=False).drop_duplicates(subset=["Name", "NOC", "Sex"])
    ae_clean = pd.DataFrame(
        {
            "athlete_id": np.nan,
            "name": ae_sw["Name"],
            "noc": ae_sw["NOC"].map(normalize_noc),
            "sex": ae_sw["Sex"].map(normalize_sex),
            "born_date": np.nan,
            "height_cm": pd.to_numeric(ae_sw["Height"], errors="coerce"),
            "weight_kg": pd.to_numeric(ae_sw["Weight"], errors="coerce"),
            "bio_source": "kaggle_120_years",
        }
    )

    # Build athlete_id-indexed lookup preferring olympedia_bios, filling gaps from Olympic_Athlete_Bio
    ob_id = ob_clean.dropna(subset=["athlete_id"]).drop_duplicates("athlete_id").set_index("athlete_id")
    oab_id = oab_clean.dropna(subset=["athlete_id"]).drop_duplicates("athlete_id").set_index("athlete_id")
    bios_by_id = ob_id.combine_first(oab_id)

    bios_flat = pd.concat([ob_clean, oab_clean, ae_clean], ignore_index=True)
    # Zeroes are missing values if any
    bios_flat.loc[bios_flat["height_cm"] <= 0, "height_cm"] = np.nan
    bios_flat.loc[bios_flat["weight_kg"] <= 0, "weight_kg"] = np.nan
    bios_flat["tkey"] = bios_flat["name"].map(token_key)
    bios_flat["tokens"] = bios_flat["name"].map(token_set)
    bios_flat["has_hw"] = bios_flat["height_cm"].notna() & bios_flat["weight_kg"].notna()
    bios_flat["has_h"] = bios_flat["height_cm"].notna()
    # Sort so complete height+weight records come first
    bios_flat = bios_flat.sort_values(
        ["has_hw", "has_h"], ascending=[False, False]
    ).reset_index(drop=True)

    return bios_by_id, bios_flat


def match_bio_fallback(
    name: str,
    noc: str,
    sex: str,
    born_date: str | None,
    bios_flat: pd.DataFrame,
    by_tkey: dict[str, pd.DataFrame],
    by_dob: dict[str, pd.DataFrame],
) -> tuple[float, float, str | None, str | None, str]:
    """Match an athlete to bios_flat using DOB+name, exact token_key, or NOC+token overlap."""
    rtok = token_set(name)
    tkey = token_key(name)
    noc_n = normalize_noc(noc)

    # 1. Exact DOB + name token overlap (strongest for Paris 2024)
    if born_date and not pd.isna(born_date) and born_date in by_dob:
        cand = by_dob[born_date]
        for _, c in cand.iterrows():
            ctok = c["tokens"]
            if rtok and ctok and len(rtok & ctok) / max(len(rtok), len(ctok)) >= 0.4:
                return c["height_cm"], c["weight_kg"], c["born_date"], c["bio_source"], "dob_name"

    # 2. Exact token_key + (NOC or sex)
    if tkey in by_tkey:
        cand = by_tkey[tkey]
        sub = cand[(cand["noc"] == noc_n) | (cand["noc"] == "")]
        if sub.empty:
            sub = cand
        if sex:
            sex_sub = sub[sub["sex"].isna() | (sub["sex"] == sex)]
            if not sex_sub.empty:
                sub = sex_sub
        row = sub.iloc[0]
        return row["height_cm"], row["weight_kg"], row["born_date"], row["bio_source"], "exact_tkey"

    return np.nan, np.nan, born_date, None, "unmatched"


def process_2000_2020(
    bios_by_id: pd.DataFrame,
    bios_flat: pd.DataFrame,
    by_tkey: dict[str, pd.DataFrame],
    by_dob: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict]:
    """Load 2000-2020 Freestyle finalists from Kaggle 1912-2020 and join Olympedia IDs/bios."""
    k12 = pd.read_csv(RAW_DIR / "kaggle_swimming_1912_2020" / "Olympic_Swimming_Results_1912to2020.csv")
    k12_sub = k12[
        (k12["Year"] >= 2000)
        & (k12["Stroke"] == "Freestyle")
        & (k12["Relay?"] == 0)
        & (k12["Distance (in meters)"].isin(TARGET_EVENTS_DIST.keys()))
    ].copy()

    ores = pd.read_csv(RAW_DIR / "olympedia_results.csv", low_memory=False)
    sw = ores[
        (ores["discipline"] == "Swimming (Aquatics)")
        & (ores["type"] == "Summer")
        & (ores["year"] >= 2000)
    ].copy()
    sw[["dist", "sex"]] = sw["event"].apply(lambda e: pd.Series(parse_olympedia_event(e)))
    sw = sw.dropna(subset=["dist", "sex"]).copy()
    sw["year"] = sw["year"].astype(int)
    sw["noc_norm"] = sw["noc"].map(normalize_noc)
    sw["tokens"] = sw["as"].map(token_set)

    records = []
    match_stats = {"total": len(k12_sub), "olympedia_id": 0, "fallback_tkey": 0, "unmatched": 0}

    for _, row in k12_sub.iterrows():
        year = int(row["Year"])
        dist = row["Distance (in meters)"]
        sex = row["Gender"]
        noc = normalize_noc(row["Team"])
        ath_name = str(row["Athlete"]).strip()
        time_sec = parse_time_to_sec(row["Results"])
        rank_val = pd.to_numeric(row["Rank"], errors="coerce")

        # Match to olympedia_results for athlete_id spine
        cand = sw[(sw["year"] == year) & (sw["dist"] == dist) & (sw["sex"] == sex) & (sw["noc_norm"] == noc)]
        if cand.empty:
            cand = sw[(sw["year"] == year) & (sw["dist"] == dist) & (sw["sex"] == sex)]

        rtok = token_set(ath_name)
        best_id, best_score = np.nan, 0.0
        for _, c in cand.iterrows():
            ctok = c["tokens"]
            if not rtok or not ctok:
                continue
            jacc = len(rtok & ctok) / len(rtok | ctok)
            if jacc > best_score:
                best_score = jacc
                best_id = c["athlete_id"]

        ath_id = int(best_id) if best_score >= 0.45 and pd.notna(best_id) else np.nan
        h_cm, w_kg, dob, bio_src, join_method = np.nan, np.nan, np.nan, None, "unmatched"

        if pd.notna(ath_id) and ath_id in bios_by_id.index:
            b = bios_by_id.loc[ath_id]
            h_cm = b["height_cm"]
            w_kg = b["weight_kg"]
            dob = b["born_date"]
            bio_src = b["bio_source"]
            join_method = "olympedia_id"
            match_stats["olympedia_id"] += 1

        # If height or weight still missing, try fallback name match
        if pd.isna(h_cm) or pd.isna(w_kg):
            fh, fw, fdob, fsrc, fmethod = match_bio_fallback(
                ath_name, noc, sex, dob if pd.notna(dob) else None, bios_flat, by_tkey, by_dob
            )
            if pd.isna(h_cm) and pd.notna(fh):
                h_cm = fh
            if pd.isna(w_kg) and pd.notna(fw):
                w_kg = fw
            if pd.isna(dob) and pd.notna(fdob):
                dob = fdob
            if join_method == "unmatched" and fmethod != "unmatched":
                join_method = fmethod
                bio_src = fsrc
                match_stats["fallback_tkey"] += 1

        if join_method == "unmatched":
            match_stats["unmatched"] += 1

        ath_key = f"oly_{int(ath_id)}" if pd.notna(ath_id) else f"norm_{normalize_name(ath_name)}_{noc}_{sex}"
        records.append(
            {
                "athlete_key": ath_key,
                "athlete_id": ath_id,
                "athlete_name": ath_name,
                "sex": sex,
                "noc": noc,
                "born_date": dob,
                "year": year,
                "event": f"{dist} Freestyle",
                "distance_m": TARGET_EVENTS_DIST[dist],
                "stage": "Final",
                "is_finalist": True,
                "rank": rank_val,
                "time_sec": time_sec,
                "height_cm": h_cm,
                "weight_kg": w_kg,
                "result_source": "kaggle_1912_2020",
                "bio_source": bio_src,
                "join_method": join_method,
            }
        )

    return pd.DataFrame(records), match_stats


def process_paris_2024(
    bios_flat: pd.DataFrame,
    by_tkey: dict[str, pd.DataFrame],
    by_dob: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict]:
    """Load Paris 2024 Freestyle results and join Paris bios + historical Olympedia bios."""
    p24_res = pd.read_csv(RAW_DIR / "kaggle_paris2024" / "results" / "Swimming.csv")
    p24_res[["dist", "sex"]] = p24_res["event_name"].apply(lambda e: pd.Series(parse_paris_event(e)))
    p24_sub = p24_res.dropna(subset=["dist", "sex"]).copy()
    total_raw = len(p24_sub)

    # Determine finalists BEFORE filtering/deduplicating to fastest swim per athlete x event
    finalist_mask = p24_sub["stage"].astype(str).str.strip() == "Final"
    finalist_keys = set(
        zip(
            p24_sub.loc[finalist_mask, "participant_code"].astype(str),
            p24_sub.loc[finalist_mask, "dist"],
            p24_sub.loc[finalist_mask, "sex"],
        )
    )

    # Filter out DNS/DSQ/DNF (non-empty result_IRM) and invalid times
    p24_sub = p24_sub[p24_sub["result_IRM"].isna()].copy()
    p24_sub["time_sec"] = p24_sub["result"].map(parse_time_to_sec)
    p24_sub = p24_sub.dropna(subset=["time_sec"]).copy()

    p24_ath = pd.read_csv(RAW_DIR / "kaggle_paris2024" / "athletes.csv", low_memory=False)
    p24_ath["code_str"] = p24_ath["code"].astype(str)
    # Convert 0 / 0.0 to NaN (never impute!)
    p24_ath["height_cm"] = pd.to_numeric(p24_ath["height"], errors="coerce")
    p24_ath.loc[p24_ath["height_cm"] <= 0, "height_cm"] = np.nan
    p24_ath["weight_kg"] = pd.to_numeric(p24_ath["weight"], errors="coerce")
    p24_ath.loc[p24_ath["weight_kg"] <= 0, "weight_kg"] = np.nan
    p24_ath["born_date"] = pd.to_datetime(p24_ath["birth_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    ath_lookup = p24_ath.set_index("code_str")

    records = []
    match_stats = {"total_swims": total_raw, "valid_swims": len(p24_sub), "dob_name": 0, "exact_tkey": 0, "unmatched": 0}

    for _, row in p24_sub.iterrows():
        pcode = str(row["participant_code"])
        dist = row["dist"]
        sex = row["sex"]
        noc = normalize_noc(row["participant_country_code"])
        ath_name = str(row["participant_name"]).strip()
        dob = np.nan
        h_cm, w_kg, bio_src, join_method = np.nan, np.nan, None, "unmatched"

        if pcode in ath_lookup.index:
            a = ath_lookup.loc[pcode]
            if isinstance(a, pd.DataFrame):
                a = a.iloc[0]
            dob = a["born_date"]
            h_cm = a["height_cm"]
            w_kg = a["weight_kg"]

        if pd.isna(h_cm) or pd.isna(w_kg):
            fh, fw, fdob, fsrc, fmethod = match_bio_fallback(
                ath_name, noc, sex, dob if pd.notna(dob) else None, bios_flat, by_tkey, by_dob
            )
            if pd.isna(h_cm) and pd.notna(fh):
                h_cm = fh
            if pd.isna(w_kg) and pd.notna(fw):
                w_kg = fw
            if pd.isna(dob) and pd.notna(fdob):
                dob = fdob
            if fmethod != "unmatched":
                join_method = fmethod
                bio_src = fsrc
                match_stats[fmethod] = match_stats.get(fmethod, 0) + 1
            else:
                match_stats["unmatched"] += 1

        records.append(
            {
                "athlete_key": f"p24_{pcode}",
                "athlete_id": np.nan,
                "athlete_name": ath_name,
                "sex": sex,
                "noc": noc,
                "born_date": dob,
                "year": 2024,
                "event": f"{dist} Freestyle",
                "distance_m": TARGET_EVENTS_DIST[dist],
                "stage": str(row["stage"]).strip() if pd.notna(row["stage"]) else "Unknown",
                "is_finalist": (pcode, dist, sex) in finalist_keys,
                "rank": pd.to_numeric(row["rank"], errors="coerce"),
                "time_sec": float(row["time_sec"]),
                "height_cm": h_cm,
                "weight_kg": w_kg,
                "result_source": "kaggle_paris2024",
                "bio_source": bio_src,
                "join_method": join_method,
            }
        )

    return pd.DataFrame(records), match_stats


def add_derived_variables(df: pd.DataFrame, base_times: dict) -> pd.DataFrame:
    df = df.copy()
    df["event_category"] = np.select(
        [df["distance_m"].isin([50, 100]), df["distance_m"].isin([200, 400])],
        ["Sprint", "Middle"],
        default="Distance",
    )
    df["height_m"] = df["height_cm"] / 100.0
    df["mass_kg"] = df["weight_kg"]
    df["bmi"] = df["mass_kg"] / (df["height_m"] ** 2)
    df["ponderal_index"] = df["mass_kg"] / (df["height_m"] ** 3)
    df["velocity_ms"] = df["distance_m"] / df["time_sec"]
    df["froude_number"] = df["velocity_ms"] / np.sqrt(G * df["height_m"])
    df["hull_speed_ms"] = 0.42 * np.sqrt(G * df["height_m"])
    df["froude_hull_ratio"] = df["velocity_ms"] / df["hull_speed_ms"]
    df["reynolds_number"] = RHO_WATER * df["velocity_ms"] * df["height_m"] / MU_WATER

    def calc_wa_points(row: pd.Series) -> float:
        dist_key = f"{int(row['distance_m'])}m"
        b = base_times["lcm_freestyle"][row["sex"]][dist_key]
        return float(math.floor(1000.0 * ((b / row["time_sec"]) ** 3)))

    df["wa_points"] = df.apply(calc_wa_points, axis=1)
    df["suit_era"] = np.where(
        df["year"] < 2008,
        "pre2008",
        np.where(df["year"] == 2008, "supersuit_2008", "textile_post2010"),
    )

    # Approximate age at Games
    born_yr = pd.to_datetime(df["born_date"], errors="coerce").dt.year
    df["age_approx"] = df["year"] - born_yr
    return df


def validate_table(df: pd.DataFrame, name: str) -> None:
    """Assert physical bounds and zero NaNs in core columns."""
    for col in CORE_COLS:
        n_na = df[col].isna().sum()
        assert n_na == 0, f"[{name}] Column {col} has {n_na} NaNs!"
    assert df["height_m"].between(1.4, 2.3).all(), f"[{name}] height_m out of [1.4, 2.3]"
    assert df["mass_kg"].between(40.0, 130.0).all(), f"[{name}] mass_kg out of [40, 130]"
    assert df["velocity_ms"].between(1.2, 2.6).all(), f"[{name}] velocity_ms out of [1.2, 2.6]"
    assert df["froude_number"].between(0.25, 0.65).all(), f"[{name}] froude_number out of [0.25, 0.65]"


def df_to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in row) + " |"
        for row in df.itertuples(index=False, name=None)
    ]
    return "\n".join([header, sep, *rows])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / "world_aquatics_base_times.json", "r", encoding="utf-8") as f:
        base_times = json.load(f)

    bios_by_id, bios_flat = load_bio_tables()
    by_tkey = {k: g for k, g in bios_flat.groupby("tkey") if k}
    by_dob = {k: g for k, g in bios_flat.dropna(subset=["born_date"]).groupby("born_date")}

    df_2000_2020, stats_k12 = process_2000_2020(bios_by_id, bios_flat, by_tkey, by_dob)
    df_2024, stats_p24 = process_paris_2024(bios_flat, by_tkey, by_dob)

    all_raw = pd.concat([df_2000_2020, df_2024], ignore_index=True)

    # Deduplicate to best valid time per athlete_key x event x year (for Paris 2024 heats/semis/finals)
    # Preserve is_finalist using logical OR (max) so a finalist who swam faster in a heat/semi stays flagged
    all_raw["is_finalist"] = all_raw["is_finalist"].astype(bool)
    all_raw = all_raw.sort_values("time_sec", ascending=True)
    finalist_games = (
        all_raw.groupby(["athlete_key", "event", "year"], as_index=False)["is_finalist"]
        .max()
    )
    results_games = (
        all_raw.groupby(["athlete_key", "event", "year"], as_index=False)
        .first()
        .drop(columns=["is_finalist"])
        .merge(finalist_games, on=["athlete_key", "event", "year"], how="left")
    )
    results_games["is_finalist"] = results_games["is_finalist"].astype(bool)

    # Unify athlete_key across 2000-2020 and 2024 for repeat Olympians (via normalized name + sex)
    # so swimming_athlete_event_clean.csv has 1 row per unique athlete x event!
    results_games["norm_athlete_sex"] = (
        results_games["athlete_name"].map(normalize_name) + "_" + results_games["sex"]
    )
    # Prefer oly_ key if the same athlete competed in both <=2020 and 2024
    oly_map = (
        results_games[results_games["athlete_key"].str.startswith("oly_")]
        .drop_duplicates("norm_athlete_sex")
        .set_index("norm_athlete_sex")["athlete_key"]
        .to_dict()
    )
    results_games["athlete_key"] = results_games.apply(
        lambda r: oly_map.get(r["norm_athlete_sex"], r["athlete_key"]), axis=1
    )

    # Missingness audit before filtering to complete anthropometrics
    miss_audit = (
        results_games.assign(
            has_h=results_games["height_cm"].notna(),
            has_w=results_games["weight_kg"].notna(),
            has_hw=results_games["height_cm"].notna() & results_games["weight_kg"].notna(),
        )
        .groupby(["sex", "event", "year"], as_index=False)
        .agg(
            n_athletes=("athlete_key", "count"),
            n_with_height=("has_h", "sum"),
            n_with_weight=("has_w", "sum"),
            n_complete_hw=("has_hw", "sum"),
        )
    )
    miss_audit["pct_complete_hw"] = (
        100.0 * miss_audit["n_complete_hw"] / miss_audit["n_athletes"]
    ).round(1)

    # Filter to complete anthropometrics & valid race times for physics analysis tables
    clean_results = results_games.dropna(subset=["time_sec", "height_cm", "weight_kg"]).copy()
    clean_results = add_derived_variables(clean_results, base_times)
    clean_results = clean_results.drop(columns=["norm_athlete_sex"]).sort_values(
        ["year", "event", "time_sec"]
    ).reset_index(drop=True)

    # Primary independent table: fastest modern Olympic time per unique athlete_key x event
    # Preserve is_finalist using logical OR (max) across Games/rounds
    finalist_ae = (
        clean_results.groupby(["athlete_key", "event"], as_index=False)["is_finalist"]
        .max()
    )
    clean_ath_event = (
        clean_results.sort_values("time_sec", ascending=True)
        .groupby(["athlete_key", "event"], as_index=False)
        .first()
        .drop(columns=["is_finalist"])
        .merge(finalist_ae, on=["athlete_key", "event"], how="left")
        .sort_values(["sex", "distance_m", "time_sec"])
        .reset_index(drop=True)
    )
    clean_ath_event["is_finalist"] = clean_ath_event["is_finalist"].astype(bool)

    validate_table(clean_results, "swimming_results_clean")
    validate_table(clean_ath_event, "swimming_athlete_event_clean")

    clean_results.to_csv(OUT_DIR / "swimming_results_clean.csv", index=False)
    clean_ath_event.to_csv(OUT_DIR / "swimming_athlete_event_clean.csv", index=False)

    # Build validation report
    cat_order = pd.CategoricalDtype(["Sprint", "Middle", "Distance"], ordered=True)
    cell_counts = (
        clean_ath_event.assign(event_category=clean_ath_event["event_category"].astype(cat_order))
        .groupby(["sex", "event_category"], observed=False)
        .agg(
            n_unique_athlete_event=("athlete_key", "count"),
            n_unique_athletes=("athlete_key", "nunique"),
            n_finalists=("is_finalist", "sum"),
            height_m_mean=("height_m", "mean"),
            height_m_sd=("height_m", "std"),
            mass_kg_mean=("mass_kg", "mean"),
            mass_kg_sd=("mass_kg", "std"),
            velocity_ms_mean=("velocity_ms", "mean"),
            froude_mean=("froude_number", "mean"),
            froude_sd=("froude_number", "std"),
        )
        .round(3)
    )

    event_counts = (
        clean_ath_event.groupby(["sex", "distance_m", "event", "event_category"], as_index=False)
        .agg(
            n_unique_athletes=("athlete_key", "count"),
            n_finalists=("is_finalist", "sum"),
            height_m_mean=("height_m", "mean"),
            mass_kg_mean=("mass_kg", "mean"),
            bmi_mean=("bmi", "mean"),
            velocity_ms_mean=("velocity_ms", "mean"),
            froude_mean=("froude_number", "mean"),
            reynolds_mean=("reynolds_number", "mean"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
        .round({"height_m_mean": 3, "mass_kg_mean": 2, "bmi_mean": 2, "velocity_ms_mean": 3, "froude_mean": 3, "reynolds_mean": 0})
    )

    # Merge-loss summary per event
    merge_loss = (
        results_games.assign(
            has_hw=results_games["height_cm"].notna() & results_games["weight_kg"].notna(),
        )
        .groupby(["sex", "distance_m", "event"], as_index=False)
        .agg(
            n_pre_filter=("athlete_key", "count"),
            n_complete_hw=("has_hw", "sum"),
            n_finalists_pre=("is_finalist", "sum"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
    )
    merge_loss["n_dropped_missing_hw"] = merge_loss["n_pre_filter"] - merge_loss["n_complete_hw"]
    merge_loss["pct_retained"] = (100.0 * merge_loss["n_complete_hw"] / merge_loss["n_pre_filter"]).round(1)

    miss_audit = miss_audit.assign(
        _dist=miss_audit["event"].str.extract(r"(\d+)").astype(int)
    ).sort_values(["sex", "_dist", "year"]).drop(columns=["_dist"])

    n_p24_finalists_total = int(
        results_games[(results_games["year"] == 2024) & (results_games["is_finalist"])].shape[0]
    )
    n_p24_finalists_clean = int(
        clean_results[(clean_results["year"] == 2024) & (clean_results["is_finalist"])].shape[0]
    )
    n_p24_finalists_faster_earlier = int(
        clean_results[
            (clean_results["year"] == 2024)
            & (clean_results["is_finalist"])
            & (clean_results["stage"] != "Final")
        ].shape[0]
    )

    report_lines = [
        "# Data Cleaning & Validation Report",
        "",
        "## 1. Pipeline Summary & Row Counts (6 Events: 50m, 100m, 200m, 400m, 800m, 1500m Freestyle)",
        f"- **2000–2020 Finalists (`kaggle_swimming_1912_2020`)**: {stats_k12['total']} raw rows "
        f"({stats_k12['olympedia_id']} matched via Olympedia `athlete_id` spine, "
        f"{stats_k12['fallback_tkey']} via normalized name fallback, {stats_k12['unmatched']} unmatched). "
        "All 2000–2020 rows are flagged `is_finalist = True`.",
        f"- **Paris 2024 (`kaggle_paris2024/results/Swimming.csv`)**: {stats_p24['total_swims']} raw swim rows "
        f"({stats_p24['valid_swims']} valid after removing DNS/DSQ/DNF; "
        f"{results_games[results_games['year'] == 2024].shape[0]} unique athlete-event entries, of which {n_p24_finalists_total} reached the Final). "
        f"Paris 2024 `athletes.csv` codes all swimmer height/weight as `0`/`0.0` (converted to `NaN`); "
        f"{stats_p24.get('dob_name', 0)} swim rows matched via DOB+name and {stats_p24.get('exact_tkey', 0)} via name token key to Olympedia/Kaggle 120-years.",
        f"- **Paris 2024 `is_finalist` Recovery**: {n_p24_finalists_clean} Paris 2024 clean athlete-event-Games rows are finalists (`is_finalist = True`), "
        f"including **{n_p24_finalists_faster_earlier}** finalists whose fastest Paris 2024 swim occurred in a Heat or Semifinal (preserved via logical OR during deduplication).",
        f"- **Combined athlete-event-Games records (pre-anthropometric filter)**: {len(results_games)}",
        f"- **`swimming_results_clean.csv` (complete anthropometrics, best time per athlete × event × Games)**: **{len(clean_results)}** rows "
        f"({int(clean_results['is_finalist'].sum())} finalists, {int((~clean_results['is_finalist']).sum())} non-finalists)",
        f"- **`swimming_athlete_event_clean.csv` (independent primary table, fastest time per unique athlete × event)**: **{len(clean_ath_event)}** rows "
        f"({int(clean_ath_event['is_finalist'].sum())} finalists, {int((~clean_ath_event['is_finalist']).sum())} non-finalists)",
        "",
        "## 2. Physical Constants (World Aquatics Competition Pool Temperature: 26 °C)",
        f"- Gravitational acceleration: `G = {G}` m/s²",
        f"- Water density at 26 °C: `RHO_WATER = {RHO_WATER}` kg/m³",
        f"- Dynamic viscosity of water at 26 °C: `MU_WATER = {MU_WATER}` Pa·s (`8.7e-4` Pa·s)",
        "- Reynolds number: $Re = \\rho v L / \\mu$ using 26 °C competition pool water properties.",
        "- Event categories: `Sprint` (50m, 100m), `Middle` (200m, 400m), `Distance` (800m, 1500m).",
        "",
        "## 3. Sample Sizes & Summary Stats by `sex × event_category` (`swimming_athlete_event_clean.csv`)",
        "",
        df_to_markdown(cell_counts.reset_index()),
        "",
        "## 4. Event-Level Summary Stats (`swimming_athlete_event_clean.csv`, All 6 Events)",
        "",
        df_to_markdown(event_counts),
        "",
        "## 5. Merge-Loss Diagnostics by `sex × event` (Pre-Filter to Complete Anthropometrics)",
        "",
        df_to_markdown(merge_loss),
        "",
        "## 6. Validation Assertions",
        "- All physical bounds passed: `height_m` ∈ [1.4, 2.3], `mass_kg` ∈ [40, 130], `velocity_ms` ∈ [1.2, 2.6], `froude_number` ∈ [0.25, 0.65].",
        f"- Zero NaNs verified across all {len(CORE_COLS)} core analysis columns (including `is_finalist`) in both output CSVs.",
        "",
        "## 7. Missingness Audit by `sex × event × year` (Pre-Filter, All 6 Events)",
        "",
        df_to_markdown(miss_audit),
        "",
        "## 8. Key Caveats for Modeling",
        "1. **2000–2020 vs. 2024 Sampling Frame**: `kaggle_swimming_1912_2020` contains Olympic **finalists** (top 8 per event-year; all `is_finalist = True`), whereas `kaggle_paris2024` contains all heats/semis/finals (deduplicated to best swim per athlete-event, with `is_finalist = True` preserved via logical OR if the swimmer competed in the Final). Paris 2024 swimmers with complete height/weight are predominantly returning Olympians.",
        "2. **Tokyo 2020 Debut Asymmetry**: Men's 800m Freestyle and Women's 1500m Freestyle debuted at Tokyo 2020 (2021), where Olympedia anthropometric coverage is also sparser than in 2000–2016.",
        "3. **No Anthropometric Imputation**: Missing height/weight values (including Paris 2024 `0`/`0.0`) are strictly preserved as `NaN` and excluded from `Fr`/BMI/PI tables.",
    ]

    (OUT_DIR / "data_validation_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Done! swimming_results_clean={len(clean_results)}, swimming_athlete_event_clean={len(clean_ath_event)}")
    print(cell_counts)


if __name__ == "__main__":
    main()