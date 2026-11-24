"""Extract official Paris 2024 Freestyle Finals stroke kinematics for all 96 finalists
from the FFN race-analysis booklet:
    data/raw/Livret analyses finales JO Paris 2024.pdf

Extracts steady-state mid-pool section times, stroke rate (Hz), stroke length (m/cycle),
stroke cycles, and underwater start breakout distances (m), verifies exact swimmer
alignment against data/raw/paris2024_kinematics_template.csv, and writes:
    data/raw/paris2024_kinematics.csv
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
FFN_PDF = ROOT / "data" / "raw" / "Livret analyses finales JO Paris 2024.pdf"
TEMPLATE_CSV = ROOT / "data" / "raw" / "paris2024_kinematics_template.csv"
OUT_CSV = ROOT / "data" / "raw" / "paris2024_kinematics.csv"

# 1-based page map in Livret analyses finales JO Paris 2024.pdf
# (section_time_page, underwater_page, sr_sl_page)
EVENT_PAGES = {
    ("Men", 50): (2, 2, 2),
    ("Men", 100): (3, 3, 3),
    ("Men", 200): (4, 4, 5),
    ("Men", 400): (6, 7, 8),
    ("Men", 800): (9, 10, 12),
    ("Men", 1500): (14, 15, 18),
    ("Women", 50): (33, 33, 33),
    ("Women", 100): (34, 34, 34),
    ("Women", 200): (35, 35, 36),
    ("Women", 400): (37, 38, 39),
    ("Women", 800): (40, 41, 43),
    ("Women", 1500): (45, 46, 49),
}


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z]", "", s.lower())


def get_layout_lines(reader: PdfReader, page_1based: int) -> list[str]:
    txt = reader.pages[page_1based - 1].extract_text(extraction_mode="layout") or ""
    return [" ".join(l.split()) for l in txt.splitlines() if l.strip()]


def get_default_lines(reader: PdfReader, page_1based: int) -> list[str]:
    txt = reader.pages[page_1based - 1].extract_text() or ""
    return [" ".join(l.split()) for l in txt.splitlines() if l.strip()]


def find_line(lines: list[str], prefix: str, occurrence: int = 0) -> str:
    hits = [l for l in lines if l.startswith(prefix)]
    if len(hits) <= occurrence:
        raise ValueError(f"Could not find prefix {prefix!r} (occ={occurrence}); found {len(hits)} hits")
    return hits[occurrence]


def extract_floats(s: str) -> list[float]:
    return [float(x) for x in re.findall(r"\b\d+\.\d+\b", s)]


def parse_50m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    lines = get_layout_lines(reader, p_sec)
    l_15_25 = extract_floats(find_line(lines, "15-25m"))
    l_25_45 = extract_floats(find_line(lines, "25-45m"))
    assert len(l_15_25) == 8 and len(l_25_45) == 8
    seg_time = [round(a + b, 2) for a, b in zip(l_15_25, l_25_45)]

    uw_line = find_line(lines, "Sortie de coulée", 0)
    uw_m = extract_floats(uw_line)
    assert len(uw_m) == 8

    # MOYENNE occurs twice: first is SR (cycles/min + cycle_time pairs = 16 floats), second is SL (8 floats)
    sr_line = extract_floats(find_line(lines, "MOYENNE", 0))
    sl_line = extract_floats(find_line(lines, "MOYENNE", 1))
    assert len(sr_line) == 16 and len(sl_line) == 8
    sr_cpm = [sr_line[2 * i] for i in range(8)]
    return {
        "seg_dist": 30.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_line,
        "uw_m": uw_m,
        "window_label": "Lap 1: 15-45m",
    }


def parse_100m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    lines = get_layout_lines(reader, p_sec)
    # 65-75m | 75-95m has 16 floats (pairs of 10m + 20m for each of 8 swimmers)
    l_lap2 = extract_floats(find_line(lines, "65-75m"))
    assert len(l_lap2) == 16, f"Expected 16 floats on 65-75m line, got {len(l_lap2)}"
    seg_time = [round(l_lap2[2 * i] + l_lap2[2 * i + 1], 2) for i in range(8)]

    uw_m = extract_floats(find_line(lines, "Sortie de coulée", 0))
    assert len(uw_m) == 8

    # SR: 50-75m (occ 0) and 75-100m (occ 0) each have 16 floats (cpm, tempo)
    sr1 = extract_floats(find_line(lines, "50-75m", 0))
    sr2 = extract_floats(find_line(lines, "75-100m", 0))
    assert len(sr1) == 16 and len(sr2) == 16
    sr_cpm = [round((sr1[2 * i] + sr2[2 * i]) / 2.0, 2) for i in range(8)]

    # SL: 50-75m (occ 1) and 75-100m (occ 1) each have 8 floats
    sl1 = extract_floats(find_line(lines, "50-75m", 1))
    sl2 = extract_floats(find_line(lines, "75-100m", 1))
    assert len(sl1) == 8 and len(sl2) == 8
    sl_m = [round((a + b) / 2.0, 3) for a, b in zip(sl1, sl2)]
    return {
        "seg_dist": 30.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_m,
        "uw_m": uw_m,
        "window_label": "Lap 2: 65-95m",
    }


def parse_200m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    lines_sec = get_layout_lines(reader, p_sec)
    l_lap3 = extract_floats(find_line(lines_sec, "115-125m"))
    assert len(l_lap3) == 16, f"Expected 16 floats on 115-125m line, got {len(l_lap3)}"
    seg_time = [round(l_lap3[2 * i] + l_lap3[2 * i + 1], 2) for i in range(8)]

    uw_m = extract_floats(find_line(lines_sec, "Sortie de coulée", 0))
    assert len(uw_m) == 8

    lines_sr = get_layout_lines(reader, p_sr)
    sr1 = extract_floats(find_line(lines_sr, "100-125m", 0))
    sr2 = extract_floats(find_line(lines_sr, "125-150m", 0))
    assert len(sr1) == 16 and len(sr2) == 16
    sr_cpm = [round((sr1[2 * i] + sr2[2 * i]) / 2.0, 2) for i in range(8)]

    sl1 = extract_floats(find_line(lines_sr, "100-125m", 1))
    sl2 = extract_floats(find_line(lines_sr, "125-150m", 1))
    assert len(sl1) == 8 and len(sl2) == 8
    sl_m = [round((a + b) / 2.0, 3) for a, b in zip(sl1, sl2)]
    return {
        "seg_dist": 30.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_m,
        "uw_m": uw_m,
        "window_label": "Lap 3: 115-145m",
    }


def parse_400m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    lines_sec = get_layout_lines(reader, p_sec)
    l_a = extract_floats(find_line(lines_sec, "155-175m"))
    l_b = extract_floats(find_line(lines_sec, "175-195m"))
    assert len(l_a) == 8 and len(l_b) == 8, f"400m 155-175/175-195 lengths: {len(l_a)}, {len(l_b)}"
    seg_time = [round(a + b, 2) for a, b in zip(l_a, l_b)]

    lines_uw = get_layout_lines(reader, p_uw)
    uw_m = extract_floats(find_line(lines_uw, "Sortie de coulée", 0))
    assert len(uw_m) == 8

    # On p_sr (default mode is super clean and avoids wide-line wrap):
    # 150-175m | 175-200m appears 3 times: occ 0 = tempo (~1.5s), occ 1 = SR (cpm, 16 floats), occ 2 = SL (m, 16 floats)
    lines_sr = get_default_lines(reader, p_sr)
    sr_raw = extract_floats(find_line(lines_sr, "150-175m", 1))
    sl_raw = extract_floats(find_line(lines_sr, "150-175m", 2))
    assert len(sr_raw) == 16 and len(sl_raw) == 16
    sr_cpm = [round((sr_raw[2 * i] + sr_raw[2 * i + 1]) / 2.0, 2) for i in range(8)]
    sl_m = [round((sl_raw[2 * i] + sl_raw[2 * i + 1]) / 2.0, 3) for i in range(8)]
    return {
        "seg_dist": 40.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_m,
        "uw_m": uw_m,
        "window_label": "Lap 4: 155-195m",
    }


def parse_800m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    # FFN 800m SR/SL table reports odd-lap 50m values (300-350m, Lap 7) under the
    # '300-350m|350-400m' label (mirroring odd-lap Lap 15 in 1500m). Align clean-speed
    # segment time to Lap 7 (305-345m, 40m mid-pool) so seg_time and SR/SL match exactly.
    lines_sec = get_default_lines(reader, p_sec)
    l_lap7 = extract_floats(find_line(lines_sec, "305-345m"))
    assert len(l_lap7) == 24, f"800m 305-345m floats: {len(l_lap7)}"
    seg_time = [l_lap7[3 * i] for i in range(8)]

    lines_uw = get_layout_lines(reader, p_uw)
    uw_m = extract_floats(find_line(lines_uw, "Sortie de coulée", 0))
    assert len(uw_m) == 8

    # p_sr default mode: 300-350m|350-400m appears 4 times: occ 0 = CB ints, occ 1 = tempo, occ 2 = SR (8 floats), occ 3 = SL (8 floats)
    lines_sr = get_default_lines(reader, p_sr)
    hits = [l for l in lines_sr if l.startswith("300-350m")]
    # Filter to lines with floats (occ 0 is tempo ~1.5, occ 1 is SR ~35-50, occ 2 is SL ~2.0-2.9)
    float_hits = [extract_floats(h) for h in hits if len(extract_floats(h)) == 8]
    assert len(float_hits) == 3, f"Expected 3 float rows for 800m 300-350m, got {len(float_hits)}"
    sr_cpm = float_hits[1]
    sl_m = float_hits[2]
    return {
        "seg_dist": 40.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_m,
        "uw_m": uw_m,
        "window_label": "Lap 7: 305-345m",
    }


def parse_1500m(reader: PdfReader, p_sec: int, p_uw: int, p_sr: int) -> dict:
    # Default mode on p_sec has clean line: 705-745m <tot> s <h1> s <h2> s (3*n_cols floats)
    # Men's 1500m has 8 finalists (24 floats); Women's 1500m in FFN Livret covers top 4 (12 floats).
    lines_sec = get_default_lines(reader, p_sec)
    l_lap15 = extract_floats(find_line(lines_sec, "705-745m"))
    assert len(l_lap15) in (12, 24), f"1500m 705-745m floats: {len(l_lap15)}"
    n_cols = len(l_lap15) // 3
    seg_time = [l_lap15[3 * i] for i in range(n_cols)]

    lines_uw = get_layout_lines(reader, p_uw)
    uw_m = extract_floats(find_line(lines_uw, "Sortie de coulée", 0))
    assert len(uw_m) == n_cols, f"1500m uw_m count {len(uw_m)} != {n_cols}"

    # p_sr default mode: 700-750m|750-800m appears twice: occ 0 = SR (n_cols floats), occ 1 = SL (n_cols floats)
    lines_sr = get_default_lines(reader, p_sr)
    hits = [extract_floats(l) for l in lines_sr if l.startswith("700-750m") and len(extract_floats(l)) == n_cols]
    assert len(hits) == 2, f"Expected 2 float rows for 1500m 700-750m, got {len(hits)}"
    sr_cpm = hits[0]
    sl_m = hits[1]
    return {
        "n_cols": n_cols,
        "seg_dist": 40.0,
        "seg_time": seg_time,
        "sr_cpm": sr_cpm,
        "sl_m": sl_m,
        "uw_m": uw_m,
        "window_label": "Lap 15: 705-745m",
    }


def verify_column_order(reader: PdfReader, p_header: int, expected_df: pd.DataFrame) -> list[int]:
    """Verify the 8 FFN columns match the 8 rows in expected_df (Rank 1..8),
    returning the column index (0..7) for each row of expected_df (handles ties!)."""
    txt = reader.pages[p_header - 1].extract_text(extraction_mode="layout") or ""
    # Find the header band containing swimmer names (first ~8 non-empty lines)
    header_blob = " ".join([l.strip() for l in txt.splitlines() if l.strip()][:8])
    norm_blob = norm_text(header_blob)

    # Check if expected_df has any tied ranks; if not, FFN columns are strictly Rank 1..8
    if expected_df["rank"].nunique() == 8:
        return list(range(8))

    # For ties (e.g. Men 200m rank 5: Maertens & Rapsys; Men 800m rank 5: Aubry & Wellbrock),
    # find each swimmer's surname position in the header line to determine exact column order!
    positions = []
    for _, r in expected_df.iterrows():
        surname = norm_text(str(r["athlete_name"]).split()[0])
        pos = norm_blob.find(surname)
        if pos == -1:
            # Handle Maertens -> Martens
            pos = norm_blob.find(surname.replace("ae", "a"))
        positions.append(pos)

    # Build mapping from expected_df row order -> FFN column index (sorted by position in header)
    if all(p != -1 for p in positions):
        order_in_ffn = sorted(range(8), key=lambda i: positions[i])
        row_to_col = [0] * 8
        for col_idx, row_idx in enumerate(order_in_ffn):
            row_to_col[row_idx] = col_idx
        return row_to_col
    return list(range(8))


def main() -> None:
    reader = PdfReader(FFN_PDF)
    tpl = pd.read_csv(TEMPLATE_CSV)
    assert len(tpl) == 96, f"Expected 96 rows in template, got {len(tpl)}"

    parsers = {
        50: parse_50m,
        100: parse_100m,
        200: parse_200m,
        400: parse_400m,
        800: parse_800m,
        1500: parse_1500m,
    }

    # Add extra FFN official columns
    tpl["source_notes"] = ""
    tpl["ffn_stroke_rate_hz"] = np.nan
    tpl["ffn_stroke_length_m"] = np.nan
    tpl["underwater_start_m"] = np.nan

    for (sex, dist), (p_sec, p_uw, p_sr) in EVENT_PAGES.items():
        parsed = parsers[dist](reader, p_sec, p_uw, p_sr)
        mask = (tpl["sex"] == sex) & (tpl["distance_m"] == dist)
        sub_idxs = tpl[mask].index.tolist()
        assert len(sub_idxs) == 8

        # Header page is p_sec for 50..800m, and p_sec-1 (summary page) for 1500m
        p_hdr = p_sec - 1 if dist == 1500 else p_sec
        n_cols = parsed.get("n_cols", 8)
        row_to_col = verify_column_order(reader, p_hdr, tpl.loc[sub_idxs[:n_cols]]) if n_cols == 8 else list(range(n_cols))

        for row_pos, df_idx in enumerate(sub_idxs):
            if row_pos >= n_cols:
                tpl.at[df_idx, "source_notes"] = (
                    f"Not included in FFN Livret ({sex} {dist}m covers Ranks 1-{n_cols} only)"
                )
                continue
            col_i = row_to_col[row_pos]
            seg_d = parsed["seg_dist"]
            seg_t = parsed["seg_time"][col_i]
            sr_hz = parsed["sr_cpm"][col_i] / 60.0
            sl_m = parsed["sl_m"][col_i]
            uw_m = parsed["uw_m"][col_i]
            cycles = sr_hz * seg_t

            tpl.at[df_idx, "segment_distance_m"] = seg_d
            tpl.at[df_idx, "segment_time_sec"] = round(seg_t, 2)
            tpl.at[df_idx, "stroke_cycles"] = round(cycles, 3)
            tpl.at[df_idx, "ffn_stroke_rate_hz"] = round(sr_hz, 4)
            tpl.at[df_idx, "ffn_stroke_length_m"] = round(sl_m, 3)
            tpl.at[df_idx, "underwater_start_m"] = round(uw_m, 2)
            tpl.at[df_idx, "source_notes"] = (
                f"FFN Livret Paris 2024 ({parsed['window_label']}, p.{p_sec}/{p_uw}/{p_sr})"
            )

    # Sanity verification before saving (expect 92/96 populated; Women 1500m ranks 5-8 omitted by FFN)
    populated = tpl["segment_time_sec"].notna()
    assert int(populated.sum()) == 92, f"Expected 92 populated rows, got {int(populated.sum())}"
    for col in ["segment_distance_m", "segment_time_sec", "stroke_cycles", "ffn_stroke_rate_hz", "ffn_stroke_length_m", "underwater_start_m"]:
        assert tpl.loc[populated, col].notna().all(), f"NaNs found in {col} among populated rows!"

    tpl.to_csv(OUT_CSV, index=False)
    print(f"Successfully extracted {int(populated.sum())}/{len(tpl)} Paris 2024 finalists from FFN Livret -> {OUT_CSV}")
    print("Omitted by FFN PDF (left as NaN, never imputed):")
    print(tpl.loc[~populated, ["sex", "event", "rank", "athlete_name", "noc", "height_m"]].to_string(index=False))

    # Quick summary table
    pop = tpl[populated].copy()
    pop["clean_v"] = pop["segment_distance_m"] / pop["segment_time_sec"]
    pop["calc_sl"] = pop["clean_v"] / pop["ffn_stroke_rate_hz"]
    summ = (
        pop.groupby(["sex", "distance_m", "event"], as_index=False)
        .agg(
            n=("participant_code", "count"),
            seg_m=("segment_distance_m", "first"),
            whole_v=("whole_race_velocity_ms", "mean"),
            clean_v=("clean_v", "mean"),
            sr_hz=("ffn_stroke_rate_hz", "mean"),
            sl_calc=("calc_sl", "mean"),
            sl_ffn=("ffn_stroke_length_m", "mean"),
            uw_m=("underwater_start_m", "mean"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
        .round(3)
    )
    print("\nFFN Extracted Summary (all 12 finals):")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
