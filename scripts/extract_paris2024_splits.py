"""Extract official Lane, Reaction Time (R.T.), and 50m lap splits for all 96
Paris 2024 Olympic Freestyle finalists from the Official Swimming Results Book
(data/raw/OG2024_SWM_B99_SWM.pdf).

Exports:
    - data/raw/paris2024_official_splits.csv
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "raw" / "OG2024_SWM_B99_SWM.pdf"
TEMPLATE_CSV = ROOT / "data" / "raw" / "paris2024_kinematics_template.csv"
OUT_CSV = ROOT / "data" / "raw" / "paris2024_official_splits.csv"

# Standardized steady-state lap index (1-based) per event
TARGET_LAP_INDEX = {
    50: 1,
    100: 2,
    200: 3,
    400: 4,
    800: 8,
    1500: 15,
}


def normalize_name(name: object) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z\s]", " ", s).lower()
    return " ".join(s.split())


def parse_time_sec(s: str) -> float:
    s = s.strip()
    parts = s.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60.0 + float(parts[1])
    raise ValueError(f"Unexpected time format: {s}")


def extract_event_pages(reader: PdfReader) -> dict[tuple[str, int], str]:
    """Group all pages belonging to each of the 12 individual Freestyle Finals."""
    event_texts: dict[tuple[str, int], list[str]] = {}
    for page in reader.pages:
        txt = page.extract_text() or ""
        if "Relay" in txt or "Semifinal" in txt or "Heat" in txt:
            continue
        m_evt = re.search(r"(Men|Women)'s\s+(50|100|200|400|800|1500)m\s+Freestyle", txt)
        if not m_evt:
            continue
        if "\nFinal\n" not in txt and "Final\nFinale" not in txt:
            continue
        if "_73A1" not in txt and "_73A2" not in txt:
            continue
        key = (m_evt.group(1), int(m_evt.group(2)))
        event_texts.setdefault(key, []).append(txt)
    return {k: "\n".join(v) for k, v in event_texts.items()}


def parse_final_text(sex: str, dist: int, txt: str, expected_swimmers: pd.DataFrame) -> list[dict]:
    """Parse reaction time, lane, and 50m splits for each of the 8 expected finalists."""
    # Skip the WR/OR record header block at the top of the first page
    m_hdr = re.search(r"(Rank\s+Lane\s+Name|Name\s+NOC\s+Code\s+TimeRank)", txt)
    if m_hdr:
        txt = txt[m_hdr.end():]

    rows = []
    # Build regex positions for each expected swimmer in the text (matched by surname + NOC)
    matches = []
    for _, sw in expected_swimmers.iterrows():
        name = sw["athlete_name"]
        noc = sw["noc"]
        # Match exact name (case-insensitive) or surname + NOC
        esc_name = re.escape(name)
        m = re.search(esc_name + r"\s+" + re.escape(noc), txt, re.IGNORECASE)
        if not m:
            # Fallback 1: match first token (surname) + NOC within 40 chars
            surname = name.split()[0]
            m = re.search(re.escape(surname) + r"[^\n]{0,35}\b" + re.escape(noc) + r"(?=\s|\d)", txt, re.IGNORECASE)
        if not m:
            # Fallback 2: match last token (given name) + NOC (handles umlaut transliteration e.g. MARTENS/MAERTENS)
            given = name.split()[-1]
            m = re.search(r"[A-Z][^\n]{0,35}\b" + re.escape(given) + r"\s+" + re.escape(noc) + r"(?=\s|\d)", txt, re.IGNORECASE)
        if not m:
            raise ValueError(f"Could not locate {name} ({noc}) in {sex} {dist}m Final text!")
        matches.append((m.start(), m.end(), sw))

    matches.sort(key=lambda x: x[0])

    for i, (start_pos, end_pos, sw) in enumerate(matches):
        # Slice chunk for this swimmer (from line start to next swimmer or Legend)
        line_start = txt.rfind("\n", 0, start_pos) + 1
        if i + 1 < len(matches):
            next_start = txt.rfind("\n", 0, matches[i + 1][0]) + 1
        else:
            leg = txt.find("Legend:", end_pos)
            next_start = leg if leg != -1 else len(txt)
        chunk = txt[line_start:next_start].strip()
        # Remove any repeated page header if swimmer spans across pages
        chunk = re.sub(r"Legend:.*?Time BehindR\.T\.", "", chunk, flags=re.DOTALL)

        # Extract Reaction Time (0.xx, always between 0.45 and 0.99)
        # Note: In 50m/100m, format is: Rank Lane Name NOC R.T. ...
        # In 200m, format is: Name NOC Lane Time Rank [Behind] (r) 150m (r) 100m (r) 50m R.T.
        # In 400m/800m/1500m, header line ends with R.T. (0.xx)
        header_line = chunk.splitlines()[0]
        if dist in (50, 100):
            # Rank Lane Name NOC R.T. ...
            m_lane = re.match(r"^\d+\s+(\d)\s+", header_line)
            lane = int(m_lane.group(1)) if m_lane else np.nan
            after_noc = header_line[header_line.find(sw["noc"]) + len(sw["noc"]):]
            m_rt = re.search(r"\b(0\.\d{2})\b", after_noc)
            rt = float(m_rt.group(1)) if m_rt else np.nan
        else:
            # Name NOC Lane ... R.T. at end of header_line
            after_noc = header_line[header_line.find(sw["noc"]) + len(sw["noc"]):]
            m_lane = re.match(r"\s*(\d)\s+", after_noc)
            lane = int(m_lane.group(1)) if m_lane else np.nan
            m_rt = re.search(r"(0\.\d{2})\s*$", header_line)
            if not m_rt:
                m_rt = re.search(r"(0\.[5-9]\d)", after_noc)
            rt = float(m_rt.group(1)) if m_rt else np.nan

        # Extract 50m splits
        n_laps = dist // 50
        splits: list[float] = []
        if dist == 50:
            splits = [float(sw["final_time_sec"])]
        elif dist == 100:
            # 50m cumulative is after "(rank) " on line 0; second 50m split is on line 1
            m_50 = re.search(r"\(\=?\d+\)\s+(\d{2}\.\d{2})", header_line)
            s1 = float(m_50.group(1))
            s2 = round(float(sw["final_time_sec"]) - s1, 2)
            splits = [s1, s2]
        elif dist == 200:
            # Line 0 has (r) 150m, (r) 100m, (r) 50m; Line 1 has lap2, lap3, lap4
            m_50 = re.findall(r"\(\=?\d+\)\s+(\d+:\d{2}\.\d{2}|\d{2}\.\d{2})", header_line)
            # In 200m, the last match on line 0 is 50m split
            s1 = parse_time_sec(m_50[-1])
            line2_nums = [float(x) for x in re.findall(r"\b(\d{2}\.\d{2})\b", chunk.splitlines()[1])]
            splits = [s1] + line2_nums
        else:
            # 400m, 800m, 1500m: explicit "50m (r) XX.XX", "100m (r) XX.XX \n XX.XX", ...
            cum_times: dict[int, float] = {}
            for m_sp in re.finditer(
                r"\b(\d{2,4})m\s+\(\=?\d+\)\s+(\d+:\d{2}\.\d{2}|\d{2}\.\d{2})", chunk
            ):
                d_mark = int(m_sp.group(1))
                if d_mark % 50 == 0 and 50 <= d_mark <= dist:
                    cum_times[d_mark] = parse_time_sec(m_sp.group(2))
            if len(cum_times) != n_laps:
                raise ValueError(
                    f"Expected {n_laps} cumulative splits for {sw['athlete_name']} ({sex} {dist}m), got {len(cum_times)}"
                )
            prev = 0.0
            for d_mark in range(50, dist + 1, 50):
                splits.append(round(cum_times[d_mark] - prev, 2))
                prev = cum_times[d_mark]

        assert len(splits) == n_laps, f"Split count mismatch for {sw['athlete_name']}: {len(splits)} != {n_laps}"
        assert abs(sum(splits) - float(sw["final_time_sec"])) < 0.06, (
            f"Split sum {sum(splits):.2f} != final {sw['final_time_sec']} for {sw['athlete_name']}"
        )
        assert pd.notna(rt) and 0.45 <= rt <= 0.99, f"Bad R.T. {rt} for {sw['athlete_name']} ({sex} {dist}m)"

        target_idx = TARGET_LAP_INDEX[dist] - 1
        target_lap_sec = splits[target_idx]
        rows.append(
            {
                "sex": sex,
                "event": f"{dist}m Freestyle",
                "distance_m": dist,
                "rank": int(sw["rank"]),
                "lane": int(lane),
                "participant_code": str(sw["participant_code"]),
                "athlete_name": sw["athlete_name"],
                "noc": sw["noc"],
                "final_time_sec": float(sw["final_time_sec"]),
                "reaction_time_sec": rt,
                "first_50m_sec": splits[0],
                "target_lap_number": TARGET_LAP_INDEX[dist],
                "target_lap_50m_sec": target_lap_sec,
                "target_lap_velocity_ms": round(50.0 / target_lap_sec, 4),
                "all_50m_splits_json": json.dumps(splits),
            }
        )
    return rows


def main() -> None:
    reader = PdfReader(PDF_PATH)
    tpl = pd.read_csv(TEMPLATE_CSV)
    event_pages = extract_event_pages(reader)
    assert len(event_pages) == 12, f"Expected 12 finals in PDF, found {len(event_pages)}"

    all_rows = []
    for sex in ["Men", "Women"]:
        for dist in [50, 100, 200, 400, 800, 1500]:
            sub = tpl[(tpl["sex"] == sex) & (tpl["distance_m"] == dist)].sort_values("rank")
            all_rows.extend(parse_final_text(sex, dist, event_pages[(sex, dist)], sub))

    out_df = pd.DataFrame(all_rows)
    assert len(out_df) == 96, f"Expected 96 finalists, got {len(out_df)}"
    out_df.to_csv(OUT_CSV, index=False)
    print(f"Successfully extracted official lanes, reaction times, and 50m splits for all {len(out_df)} finalists!")
    print(f"Saved: {OUT_CSV}")
    print("\nSummary by sex x event (mean R.T. and mean target steady-state 50m lap speed):")
    summ = (
        out_df.groupby(["sex", "distance_m", "event"], as_index=False)
        .agg(
            n=("participant_code", "count"),
            mean_rt_s=("reaction_time_sec", "mean"),
            mean_first50_s=("first_50m_sec", "mean"),
            target_lap=("target_lap_number", "first"),
            mean_target_lap_s=("target_lap_50m_sec", "mean"),
            mean_target_lap_v=("target_lap_velocity_ms", "mean"),
        )
        .sort_values(["sex", "distance_m"])
        .drop(columns=["distance_m"])
        .round(3)
    )
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()