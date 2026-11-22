# Data Cleaning & Validation Report

## 1. Pipeline Summary & Row Counts
- **2000–2020 Finalists (`kaggle_swimming_1912_2020`)**: 304 raw rows (266 matched via Olympedia `athlete_id` spine, 3 via normalized name fallback, 35 unmatched).
- **Paris 2024 (`kaggle_paris2024/results/Swimming.csv`)**: 480 raw swim rows (475 valid after removing DNS/DSQ/DNF; 347 unique athlete-event entries). Paris 2024 `athletes.csv` codes all swimmer height/weight as `0`/`0.0` (converted to `NaN`); 223 swim rows matched via DOB+name and 8 via name token key to Olympedia/Kaggle 120-years.
- **Combined athlete-event-Games records (pre-anthropometric filter)**: 651
- **`swimming_results_clean.csv` (complete anthropometrics, best time per athlete × event × Games)**: **313** rows
- **`swimming_athlete_event_clean.csv` (independent primary table, fastest time per unique athlete × event)**: **252** rows

## 2. Sample Sizes & Summary Stats by `sex × event_category` (`swimming_athlete_event_clean.csv`)

| sex | event_category | n_unique_athlete_event | n_unique_athletes | height_m_mean | height_m_sd | mass_kg_mean | mass_kg_sd | velocity_ms_mean | froude_mean | froude_sd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Men | Distance | 44 | 36 | 1.873 | 0.056 | 77.136 | 8.854 | 1.688 | 0.394 | 0.007 |
| Men | Sprint | 87 | 71 | 1.922 | 0.054 | 86.092 | 7.754 | 2.172 | 0.5 | 0.028 |
| Women | Distance | 39 | 35 | 1.751 | 0.065 | 63.795 | 6.522 | 1.583 | 0.382 | 0.007 |
| Women | Sprint | 82 | 59 | 1.777 | 0.049 | 65.549 | 5.545 | 1.946 | 0.466 | 0.024 |

## 3. Validation Assertions
- All physical bounds passed: `height_m` ∈ [1.4, 2.3], `mass_kg` ∈ [40, 130], `velocity_ms` ∈ [1.2, 2.6], `froude_number` ∈ [0.25, 0.65].
- Zero NaNs verified across all 20 core analysis columns in both output CSVs.

## 4. Missingness Audit by `sex × event × year` (Pre-Filter)

| sex | event | year | n_athletes | n_with_height | n_with_weight | n_complete_hw | pct_complete_hw |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Men | 100m Freestyle | 2000 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 100m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 100m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 100m Freestyle | 2024 | 79 | 12 | 12 | 12 | 15.2 |
| Men | 1500m Freestyle | 2000 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 1500m Freestyle | 2004 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 1500m Freestyle | 2008 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 1500m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 1500m Freestyle | 2016 | 8 | 8 | 7 | 7 | 87.5 |
| Men | 1500m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 1500m Freestyle | 2024 | 24 | 7 | 6 | 6 | 25.0 |
| Men | 50m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 50m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2016 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 50m Freestyle | 2020 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 50m Freestyle | 2024 | 73 | 12 | 12 | 12 | 16.4 |
| Men | 800m Freestyle | 2020 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 800m Freestyle | 2024 | 31 | 9 | 8 | 8 | 25.8 |
| Women | 100m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 100m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 100m Freestyle | 2008 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 100m Freestyle | 2012 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 100m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 100m Freestyle | 2020 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 100m Freestyle | 2024 | 29 | 10 | 10 | 10 | 34.5 |
| Women | 1500m Freestyle | 2020 | 8 | 2 | 2 | 2 | 25.0 |
| Women | 1500m Freestyle | 2024 | 16 | 3 | 3 | 3 | 18.8 |
| Women | 50m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2004 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 50m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 50m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2016 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2020 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 50m Freestyle | 2024 | 79 | 12 | 12 | 12 | 15.2 |
| Women | 800m Freestyle | 2000 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2008 | 8 | 5 | 5 | 5 | 62.5 |
| Women | 800m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 800m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2020 | 8 | 2 | 2 | 2 | 25.0 |
| Women | 800m Freestyle | 2024 | 16 | 4 | 4 | 4 | 25.0 |

## 5. Key Caveats for Modeling
1. **2000–2020 vs. 2024 Sampling Frame**: `kaggle_swimming_1912_2020` contains Olympic **finalists** (top 8 per event-year), whereas `kaggle_paris2024` contains all heats/semis/finals (deduplicated to best swim per athlete-event). Paris 2024 swimmers with complete height/weight are predominantly returning Olympians (~15% of Paris 2024 swimmers).
2. **Tokyo 2020 Debut Asymmetry**: Men's 800m Freestyle and Women's 1500m Freestyle debuted at Tokyo 2020 (2021), where Olympedia anthropometric coverage is also sparser (~48% complete vs. ~88% in 2000–2016).
3. **No Anthropometric Imputation**: Missing height/weight values (including Paris 2024 `0`/`0.0`) are strictly preserved as `NaN` and excluded from `Fr`/BMI/PI tables.