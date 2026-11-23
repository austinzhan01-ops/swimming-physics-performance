# Data Cleaning & Validation Report

## 1. Pipeline Summary & Row Counts (6 Events: 50m, 100m, 200m, 400m, 800m, 1500m Freestyle)
- **2000–2020 Finalists (`kaggle_swimming_1912_2020`)**: 504 raw rows (446 matched via Olympedia `athlete_id` spine, 8 via normalized name fallback, 50 unmatched). All 2000–2020 rows are flagged `is_finalist = True`.
- **Paris 2024 (`kaggle_paris2024/results/Swimming.csv`)**: 661 raw swim rows (652 valid after removing DNS/DSQ/DNF; 460 unique athlete-event entries, of which 96 reached the Final). Paris 2024 `athletes.csv` codes all swimmer height/weight as `0`/`0.0` (converted to `NaN`); 315 swim rows matched via DOB+name and 8 via name token key to Olympedia/Kaggle 120-years.
- **Paris 2024 `is_finalist` Recovery**: 31 Paris 2024 clean athlete-event-Games rows are finalists (`is_finalist = True`), including **7** finalists whose fastest Paris 2024 swim occurred in a Heat or Semifinal (preserved via logical OR during deduplication).
- **Combined athlete-event-Games records (pre-anthropometric filter)**: 956
- **`swimming_results_clean.csv` (complete anthropometrics, best time per athlete × event × Games)**: **491** rows (439 finalists, 52 non-finalists)
- **`swimming_athlete_event_clean.csv` (independent primary table, fastest time per unique athlete × event)**: **392** rows (340 finalists, 52 non-finalists)

## 2. Physical Constants (World Aquatics Competition Pool Temperature: 26 °C)
- Gravitational acceleration: `G = 9.81` m/s²
- Water density at 26 °C: `RHO_WATER = 996.8` kg/m³
- Dynamic viscosity of water at 26 °C: `MU_WATER = 0.00087` Pa·s (`8.7e-4` Pa·s)
- Reynolds number: $Re = \rho v L / \mu$ using 26 °C competition pool water properties.
- Event categories: `Sprint` (50m, 100m), `Middle` (200m, 400m), `Distance` (800m, 1500m).

## 3. Sample Sizes & Summary Stats by `sex × event_category` (`swimming_athlete_event_clean.csv`)

| sex | event_category | n_unique_athlete_event | n_unique_athletes | n_finalists | height_m_mean | height_m_sd | mass_kg_mean | mass_kg_sd | velocity_ms_mean | froude_mean | froude_sd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Men | Sprint | 87 | 71 | 70 | 1.922 | 0.054 | 86.092 | 7.754 | 2.172 | 0.5 | 0.028 |
| Men | Middle | 64 | 54 | 61 | 1.896 | 0.058 | 83.234 | 8.664 | 1.835 | 0.426 | 0.015 |
| Men | Distance | 44 | 36 | 34 | 1.873 | 0.056 | 77.136 | 8.854 | 1.688 | 0.394 | 0.007 |
| Women | Sprint | 82 | 59 | 67 | 1.777 | 0.049 | 65.549 | 5.545 | 1.946 | 0.466 | 0.024 |
| Women | Middle | 76 | 66 | 72 | 1.765 | 0.066 | 64.553 | 6.319 | 1.67 | 0.402 | 0.014 |
| Women | Distance | 39 | 35 | 36 | 1.751 | 0.065 | 63.795 | 6.522 | 1.583 | 0.382 | 0.007 |

## 4. Event-Level Summary Stats (`swimming_athlete_event_clean.csv`, All 6 Events)

| sex | event | event_category | n_unique_athletes | n_finalists | height_m_mean | mass_kg_mean | bmi_mean | velocity_ms_mean | froude_mean | reynolds_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Men | 50m Freestyle | Sprint | 41 | 35 | 1.928 | 87.41 | 23.54 | 2.294 | 0.528 | 5065892.0 |
| Men | 100m Freestyle | Sprint | 46 | 35 | 1.918 | 84.91 | 23.06 | 2.064 | 0.476 | 4535520.0 |
| Men | 200m Freestyle | Middle | 33 | 32 | 1.902 | 83.33 | 23.0 | 1.89 | 0.438 | 4118772.0 |
| Men | 400m Freestyle | Middle | 31 | 29 | 1.891 | 83.13 | 23.2 | 1.777 | 0.413 | 3849576.0 |
| Men | 800m Freestyle | Distance | 13 | 7 | 1.871 | 74.46 | 21.24 | 1.706 | 0.398 | 3656996.0 |
| Men | 1500m Freestyle | Distance | 31 | 27 | 1.875 | 78.26 | 22.22 | 1.68 | 0.392 | 3609566.0 |
| Women | 50m Freestyle | Sprint | 39 | 30 | 1.769 | 64.85 | 20.71 | 2.036 | 0.489 | 4128012.0 |
| Women | 100m Freestyle | Sprint | 43 | 37 | 1.784 | 66.19 | 20.78 | 1.864 | 0.446 | 3810494.0 |
| Women | 200m Freestyle | Middle | 38 | 38 | 1.777 | 65.21 | 20.62 | 1.718 | 0.411 | 3497863.0 |
| Women | 400m Freestyle | Middle | 38 | 34 | 1.752 | 63.89 | 20.77 | 1.622 | 0.392 | 3256809.0 |
| Women | 800m Freestyle | Distance | 34 | 32 | 1.749 | 63.29 | 20.65 | 1.584 | 0.383 | 3173783.0 |
| Women | 1500m Freestyle | Distance | 5 | 4 | 1.762 | 67.2 | 21.63 | 1.576 | 0.379 | 3184439.0 |

## 5. Merge-Loss Diagnostics by `sex × event` (Pre-Filter to Complete Anthropometrics)

| sex | event | n_pre_filter | n_complete_hw | n_finalists_pre | n_dropped_missing_hw | pct_retained |
| --- | --- | --- | --- | --- | --- | --- |
| Men | 50m Freestyle | 121 | 55 | 56 | 66 | 45.5 |
| Men | 100m Freestyle | 127 | 52 | 56 | 75 | 40.9 |
| Men | 200m Freestyle | 73 | 43 | 56 | 30 | 58.9 |
| Men | 400m Freestyle | 85 | 41 | 56 | 44 | 48.2 |
| Men | 800m Freestyle | 39 | 13 | 16 | 26 | 33.3 |
| Men | 1500m Freestyle | 72 | 41 | 56 | 31 | 56.9 |
| Women | 50m Freestyle | 127 | 53 | 56 | 74 | 41.7 |
| Women | 100m Freestyle | 77 | 52 | 56 | 25 | 67.5 |
| Women | 200m Freestyle | 78 | 49 | 56 | 29 | 62.8 |
| Women | 400m Freestyle | 69 | 45 | 56 | 24 | 65.2 |
| Women | 800m Freestyle | 64 | 42 | 56 | 22 | 65.6 |
| Women | 1500m Freestyle | 24 | 5 | 16 | 19 | 20.8 |

## 6. Validation Assertions
- All physical bounds passed: `height_m` ∈ [1.4, 2.3], `mass_kg` ∈ [40, 130], `velocity_ms` ∈ [1.2, 2.6], `froude_number` ∈ [0.25, 0.65].
- Zero NaNs verified across all 21 core analysis columns (including `is_finalist`) in both output CSVs.

## 7. Missingness Audit by `sex × event × year` (Pre-Filter, All 6 Events)

| sex | event | year | n_athletes | n_with_height | n_with_weight | n_complete_hw | pct_complete_hw |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Men | 50m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 50m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 50m Freestyle | 2016 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 50m Freestyle | 2020 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 50m Freestyle | 2024 | 73 | 12 | 12 | 12 | 16.4 |
| Men | 100m Freestyle | 2000 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 100m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 100m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 100m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 100m Freestyle | 2024 | 79 | 12 | 12 | 12 | 15.2 |
| Men | 200m Freestyle | 2000 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 200m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 200m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 200m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 200m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 200m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 200m Freestyle | 2024 | 25 | 3 | 3 | 3 | 12.0 |
| Men | 400m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 400m Freestyle | 2004 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 400m Freestyle | 2008 | 8 | 7 | 7 | 7 | 87.5 |
| Men | 400m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 400m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 400m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 400m Freestyle | 2024 | 37 | 3 | 3 | 3 | 8.1 |
| Men | 800m Freestyle | 2020 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 800m Freestyle | 2024 | 31 | 9 | 8 | 8 | 25.8 |
| Men | 1500m Freestyle | 2000 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 1500m Freestyle | 2004 | 8 | 5 | 5 | 5 | 62.5 |
| Men | 1500m Freestyle | 2008 | 8 | 6 | 6 | 6 | 75.0 |
| Men | 1500m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Men | 1500m Freestyle | 2016 | 8 | 8 | 7 | 7 | 87.5 |
| Men | 1500m Freestyle | 2020 | 8 | 3 | 3 | 3 | 37.5 |
| Men | 1500m Freestyle | 2024 | 24 | 7 | 6 | 6 | 25.0 |
| Women | 50m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2004 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 50m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 50m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2016 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 50m Freestyle | 2020 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 50m Freestyle | 2024 | 79 | 12 | 12 | 12 | 15.2 |
| Women | 100m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 100m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 100m Freestyle | 2008 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 100m Freestyle | 2012 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 100m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 100m Freestyle | 2020 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 100m Freestyle | 2024 | 29 | 10 | 10 | 10 | 34.5 |
| Women | 200m Freestyle | 2000 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 200m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 200m Freestyle | 2008 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 200m Freestyle | 2012 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 200m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 200m Freestyle | 2020 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 200m Freestyle | 2024 | 30 | 4 | 4 | 4 | 13.3 |
| Women | 400m Freestyle | 2000 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 400m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 400m Freestyle | 2008 | 8 | 6 | 6 | 6 | 75.0 |
| Women | 400m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 400m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 400m Freestyle | 2020 | 8 | 2 | 2 | 2 | 25.0 |
| Women | 400m Freestyle | 2024 | 21 | 6 | 6 | 6 | 28.6 |
| Women | 800m Freestyle | 2000 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2004 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2008 | 8 | 5 | 5 | 5 | 62.5 |
| Women | 800m Freestyle | 2012 | 8 | 7 | 7 | 7 | 87.5 |
| Women | 800m Freestyle | 2016 | 8 | 8 | 8 | 8 | 100.0 |
| Women | 800m Freestyle | 2020 | 8 | 2 | 2 | 2 | 25.0 |
| Women | 800m Freestyle | 2024 | 16 | 4 | 4 | 4 | 25.0 |
| Women | 1500m Freestyle | 2020 | 8 | 2 | 2 | 2 | 25.0 |
| Women | 1500m Freestyle | 2024 | 16 | 3 | 3 | 3 | 18.8 |

## 8. Key Caveats for Modeling
1. **2000–2020 vs. 2024 Sampling Frame**: `kaggle_swimming_1912_2020` contains Olympic **finalists** (top 8 per event-year; all `is_finalist = True`), whereas `kaggle_paris2024` contains all heats/semis/finals (deduplicated to best swim per athlete-event, with `is_finalist = True` preserved via logical OR if the swimmer competed in the Final). Paris 2024 swimmers with complete height/weight are predominantly returning Olympians.
2. **Tokyo 2020 Debut Asymmetry**: Men's 800m Freestyle and Women's 1500m Freestyle debuted at Tokyo 2020 (2021), where Olympedia anthropometric coverage is also sparser than in 2000–2016.
3. **No Anthropometric Imputation**: Missing height/weight values (including Paris 2024 `0`/`0.0`) are strictly preserved as `NaN` and excluded from `Fr`/BMI/PI tables.