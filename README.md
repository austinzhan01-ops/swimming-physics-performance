# The Physics of Swimming Performance: Sprint vs. Distance Freestyle (2000–2024)

Empirical hydrodynamic and anthropometric analysis of elite Olympic sprint freestyle (50m, 100m) versus long-distance freestyle (800m, 1500m) across the 2000–2024 Olympic Games.

## Key Findings
- **Universal Hull-Speed Regime Separation (`Fr = 0.42`):** **100.0%** of Olympic sprint swimmers (50m and 100m, both Men and Women) operated above the theoretical wave-drag hull-speed transition (`Fr = 0.42`), whereas **0.0%** of distance swimmers (800m and 1500m) exceeded it (`g = 4.54` Men, `g = 4.20` Women, `p_FDR < 1e-52`). This holds when excluding 50m (`100m` vs. `800m/1500m`).
- **Women (Gagnon et al., 2018 Replication):** Sprint women are significantly taller than Distance women (`1.777 ± 0.049 m` vs. `1.751 ± 0.065 m`, `g = 0.48`, `p_FDR = 0.0488`), while BMI is virtually identical (`20.75` vs. `20.77 kg/m²`, `g = -0.02`, `p_FDR = 0.925`). Zero-leakage 5-fold CV logistic regression: `BMI alone` AUC = `0.459` (chance) vs. `Height alone` AUC = `0.598` (`OR = 1.62`/SD).
- **Men:** Sprint men are taller (`1.922` vs. `1.873 m`, `g = 0.89`), heavier (`86.09` vs. `77.14 kg`, `g = 1.09`), and higher in BMI (`g = 0.75`). `Height + Mass` achieves 5-fold CV AUC = `0.773` (77.1% accuracy) vs. `BMI alone` (`0.693`).

## Repository Structure
- `Sprint vs. Distance Freestyle Physics_ Research & Data Roadmap - PROJECT SUMMARY.md` — Upgraded research plan, hydrodynamic equations, confounder controls, and verified data sources.
- `scripts/clean_and_merge.py` — Merges Olympedia/Kaggle anthropometric bios with 2000–2024 Olympic freestyle results, computes derived physics metrics (`Fr`, `Re`, `v_hull`, World Aquatics Points), and validates bounds.
- `scripts/statistical_analysis.py` — Runs sex-stratified group comparisons (Welch's t-test, Mann-Whitney U, Hedges' g, BH-FDR), sensitivity analyses, event-gradient tests, parsimonious OLS regressions (`VIF < 5`), zero-leakage 5-fold CV logistic regression, and generates figures.
- `data/processed/` — Cleaned analysis datasets (`swimming_athlete_event_clean.csv`, `swimming_results_clean.csv`) and `data_validation_report.md`.
- `data/raw/world_aquatics_base_times.json` — Official 2024/2025 World Aquatics LCM Freestyle base times. *(Large raw Olympic CSVs are excluded via `.gitignore`; see `PROJECT SUMMARY.md` for direct download sources.)*
- `results/` — Full quantitative report (`statistical_analysis_report.md`) and summary CSV tables.

## Quickstart
```bash
python -m venv .venv
.venv\Scripts\activate   # or: source .venv/bin/activate
pip install -r requirements.txt
python scripts/statistical_analysis.py
```
Running `scripts/statistical_analysis.py` reproduces all statistical tables in `results/` and all 4 figures in `results/figures/`.
