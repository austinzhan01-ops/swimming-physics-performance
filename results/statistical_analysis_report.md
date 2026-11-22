# Statistical Analysis Report: Hydrodynamic & Anthropometric Constraints in Olympic Sprint vs. Distance Freestyle (2000–2024)

## 1. Executive Summary

Using the cleaned, `athlete_key`-deduplicated Olympic freestyle dataset ([swimming_athlete_event_clean.csv](../data/processed/swimming_athlete_event_clean.csv); **N = 252** athlete-event rows across **200** unique athletes: 131 Men [106 unique], 121 Women [94 unique]) and the full multi-round dataset ([swimming_results_clean.csv](../data/processed/swimming_results_clean.csv); **N = 313** rows) for cluster-robust sensitivity checks, we tested the hydrodynamic and anthropometric hypotheses from [Sprint vs. Distance Freestyle Physics_ Research & Data Roadmap - PROJECT SUMMARY.md](../Sprint%20vs.%20Distance%20Freestyle%20Physics_%20Research%20%26%20Data%20Roadmap%20-%20PROJECT%20SUMMARY.md).

**Key Findings:**
1. **Universal Hull-Speed Regime Separation ($Fr \approx 0.42$):** Every single Olympic sprinter (100.0% of 50m and 100m swimmers in both Men and Women) operated above the theoretical wave-drag hull-speed transition ($Fr = 0.42$), whereas **0.0%** of distance swimmers (800m and 1500m in both sexes) exceeded $Fr = 0.42$ ($g = 4.54$ in Men, $g = 4.20$ in Women, $p_{\text{FDR}} < 10^{-52}$). Crucially, this 100% vs. 0% separation persists when excluding the 50m (comparing 100m vs. 800m/1500m) to remove dive-start and 15m-underwater inflation.
2. **Direct Replication of Gagnon et al. (2018) in Women—Height Separates Where BMI Converges:** Among Women, Sprint swimmers were significantly taller than Distance swimmers ($1.777 \pm 0.049\text{ m}$ vs. $1.751 \pm 0.065\text{ m}$; Hedges' $g = 0.48$, 95% CI $[0.10, 0.87]$, $p_{\text{FDR}} = 0.0488$), whereas **BMI was virtually identical** ($20.75 \pm 1.45$ vs. $20.77 \pm 1.18\text{ kg/m}^2$; $g = -0.02$, $p_{\text{FDR}} = 0.9252$). In zero-leakage 5-fold CV logistic regression, `BMI alone` performed at chance ($\text{AUC} = 0.459$), while `Height alone` achieved $\text{AUC} = 0.598$ ($\text{OR} = 1.62$ per SD).
3. **Divergent Sex Scaling in Men—Both Height and Muscle Mass Drive Sprint Specialization:** Among Men, Sprint swimmers were significantly taller ($1.922 \pm 0.054\text{ m}$ vs. $1.873 \pm 0.056\text{ m}$; $g = 0.89$, $p_{\text{FDR}} = 1.14 \times 10^{-5}$), heavier ($86.09 \pm 7.75\text{ kg}$ vs. $77.14 \pm 8.85\text{ kg}$; $g = 1.09$, $p_{\text{FDR}} = 3.86 \times 10^{-7}$), and had higher BMI ($23.29 \pm 1.78$ vs. $21.93 \pm 1.85\text{ kg/m}^2$; $g = 0.75$, $p_{\text{FDR}} = 0.0002$) and Ponderal Index ($g = 0.41$, $p_{\text{FDR}} = 0.0250$). `Height + Mass` achieved 5-fold CV $\text{AUC} = 0.773$ (77.1% accuracy), outperforming `BMI alone` ($\text{AUC} = 0.693$).
4. **Within-Category Physics:** Within Distance swimming (800m/1500m), taller athletes swam faster and scored higher World Aquatics Points in both Men ($r = 0.364$, $p = 0.015$ for velocity; $r = 0.397$, $p = 0.008$ for WA Points) and Women ($r = 0.396$, $p = 0.013$ for velocity; $r = 0.413$, $p = 0.009$ for WA Points), while maintaining significantly lower Froude numbers ($r = -0.478$ in Men, $r = -0.627$ in Women).

---

## 2. Sample Structure, Overlap & Structural Asymmetries

* **Deduplicated Athlete-Event Dataset (`swimming_athlete_event_clean.csv`):** 252 rows, **0% missingness** on all anthropometric (`height_m`, `mass_kg`, `bmi`, `ponderal_index`, `age_approx`) and hydrodynamic (`velocity_ms`, `froude_number`, `froude_hull_ratio`, `reynolds_number`, `wa_points`) variables.
  * **Men (N = 131 rows, 106 unique athletes):** Sprint = 87 (50m: 41, 100m: 46); Distance = 44 (800m: 13, 1500m: 31). **16** male athletes appear in both 50m and 100m; **1** appears in both Sprint and Distance.
  * **Women (N = 121 rows, 94 unique athletes):** Sprint = 82 (50m: 39, 100m: 43); Distance = 39 (800m: 34, 1500m: 5). **23** female athletes appear in both 50m and 100m; **0** appear in both Sprint and Distance.
* **Tokyo 2020 Event-Introduction Asymmetry:** Men's 800m Freestyle ($n = 13$) and Women's 1500m Freestyle ($n = 5$) debuted at Tokyo 2020 (held 2021), creating smaller sample sizes for those two cells compared with Men's 1500m ($n = 31$) and Women's 800m ($n = 34$).
* **Paris 2024 Stage Asymmetry:** 2000–2020 data (`kaggle_1912_2020`) represent finalists ($n = 200$ Final rows across 2000–2024), whereas Paris 2024 includes heat/semifinal swimmers ($n = 52$ non-Final rows). Addressed explicitly in the `finalists_only` (`stage == "Final"`) sensitivity split.

---

## 3. Primary Sprint vs. Distance Comparisons (Sex-Stratified)

All comparisons use Welch's two-sample t-test, Mann-Whitney U test, Hedges' $g$ (95% CI), rank-biserial $r$, and Benjamini-Hochberg FDR adjustment across the 9 metrics within each sex (full table in [sprint_vs_distance_comparisons.csv](sprint_vs_distance_comparisons.csv)).

### Men (Sprint $n = 87$ vs. Distance $n = 44$)
| Metric | Sprint (Mean ± SD) | Distance (Mean ± SD) | Hedges' $g$ [95% CI] | Rank-Biserial $r$ | Welch $p_{\text{FDR}}$ | MWU $p_{\text{FDR}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Height (m)** | $1.922 \pm 0.054$ | $1.873 \pm 0.056$ | $0.89$ $[0.51, 1.27]$ | $0.46$ | $1.14 \times 10^{-5}$ | $2.20 \times 10^{-5}$ |
| **Body Mass (kg)** | $86.09 \pm 7.75$ | $77.14 \pm 8.85$ | $1.09$ $[0.71, 1.48]$ | $0.56$ | $3.86 \times 10^{-7}$ | $2.78 \times 10^{-7}$ |
| **BMI (kg/m²)** | $23.29 \pm 1.78$ | $21.93 \pm 1.85$ | $0.75$ $[0.37, 1.12]$ | $0.41$ | $0.0002$ | $0.0002$ |
| **Ponderal Index (kg/m³)** | $12.12 \pm 1.02$ | $11.71 \pm 0.97$ | $0.41$ $[0.05, 0.78]$ | $0.22$ | $0.0250$ | $0.0441$ |
| **Mean Race Speed (m/s)** | $2.172 \pm 0.122$ | $1.688 \pm 0.029$ | $4.76$ $[4.08, 5.44]$ | $1.00$ | $2.11 \times 10^{-58}$ | $2.50 \times 10^{-20}$ |
| **Froude Number ($Fr$)** | $0.500 \pm 0.028$ | $0.394 \pm 0.007$ | $4.54$ $[3.88, 5.20]$ | $1.00$ | $1.61 \times 10^{-57}$ | $2.50 \times 10^{-20}$ |
| **Froude/Hull Ratio** | $1.191 \pm 0.067$ | $0.938 \pm 0.017$ | $4.54$ $[3.88, 5.20]$ | $1.00$ | $1.61 \times 10^{-57}$ | $2.50 \times 10^{-20}$ |
| **Reynolds Number ($Re$)** | $4.17 \times 10^6 \pm 2.76 \times 10^5$ | $3.16 \times 10^6 \pm 1.25 \times 10^5$ | $4.26$ $[3.63, 4.89]$ | $1.00$ | $1.61 \times 10^{-57}$ | $2.50 \times 10^{-20}$ |
| **WA Points** | $880.7 \pm 48.4$ | $918.6 \pm 45.5$ | $-0.79$ $[-1.17, -0.42]$ | $-0.45$ | $3.60 \times 10^{-5}$ | $4.01 \times 10^{-5}$ |

### Women (Sprint $n = 82$ vs. Distance $n = 39$)
| Metric | Sprint (Mean ± SD) | Distance (Mean ± SD) | Hedges' $g$ [95% CI] | Rank-Biserial $r$ | Welch $p_{\text{FDR}}$ | MWU $p_{\text{FDR}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Height (m)** | $1.777 \pm 0.049$ | $1.751 \pm 0.065$ | $0.48$ $[0.10, 0.87]$ | $0.23$ | $0.0488$ | $0.0800$ |
| **Body Mass (kg)** | $65.55 \pm 5.54$ | $63.79 \pm 6.52$ | $0.30$ $[-0.09, 0.68]$ | $0.16$ | $0.2283$ | $0.2243$ |
| **BMI (kg/m²)** | $20.75 \pm 1.45$ | $20.77 \pm 1.18$ | $-0.02$ $[-0.40, 0.36]$ | $-0.01$ | $0.9252$ | $0.9403$ |
| **Ponderal Index (kg/m³)** | $11.69 \pm 0.92$ | $11.88 \pm 0.72$ | $-0.22$ $[-0.60, 0.16]$ | $-0.13$ | $0.2837$ | $0.3153$ |
| **Mean Race Speed (m/s)** | $1.946 \pm 0.093$ | $1.583 \pm 0.026$ | $4.60$ $[3.91, 5.30]$ | $1.00$ | $2.09 \times 10^{-55}$ | $1.72 \times 10^{-18}$ |
| **Froude Number ($Fr$)** | $0.466 \pm 0.024$ | $0.382 \pm 0.007$ | $4.20$ $[3.55, 4.85]$ | $1.00$ | $6.12 \times 10^{-53}$ | $1.72 \times 10^{-18}$ |
| **Froude/Hull Ratio** | $1.110 \pm 0.056$ | $0.910 \pm 0.018$ | $4.20$ $[3.55, 4.85]$ | $1.00$ | $6.12 \times 10^{-53}$ | $1.72 \times 10^{-18}$ |
| **Reynolds Number ($Re$)** | $3.45 \times 10^6 \pm 1.87 \times 10^5$ | $2.77 \times 10^6 \pm 1.28 \times 10^5$ | $3.99$ $[3.36, 4.63]$ | $1.00$ | $3.10 \times 10^{-43}$ | $1.72 \times 10^{-18}$ |
| **WA Points** | $892.5 \pm 48.0$ | $886.8 \pm 44.0$ | $0.12$ $[-0.26, 0.50]$ | $0.08$ | $0.5833$ | $0.5107$ |

---

## 4. Sensitivity Analyses

Across all five pre-specified sensitivity splits, the core findings remain directionally consistent:

| Sensitivity Split | Men: Height $g$ ($p_{\text{FDR}}$) | Men: Mass $g$ ($p_{\text{FDR}}$) | Men: BMI $g$ ($p_{\text{FDR}}$) | Women: Height $g$ ($p_{\text{FDR}}$) | Women: Mass $g$ ($p_{\text{FDR}}$) | Women: BMI $g$ ($p_{\text{FDR}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary (2000–2024, $N=252$)** | $0.89$ ($1.14 \times 10^{-5}$) | $1.09$ ($3.86 \times 10^{-7}$) | $0.75$ ($0.0002$) | $0.48$ ($0.0488$) | $0.30$ ($0.228$) | $-0.02$ ($0.925$) |
| **Textile Era (2012–2024, $N=150$)** | $0.85$ ($0.0002$) | $1.22$ ($7.27 \times 10^{-7}$) | $0.89$ ($0.0002$) | $0.55$ ($0.141$) | $0.27$ ($0.420$) | $-0.09$ ($0.699$) |
| **Excl. 2008 Supersuit ($N=217$)** | $0.89$ ($1.71 \times 10^{-5}$) | $1.13$ ($2.07 \times 10^{-7}$) | $0.80$ ($9.87 \times 10^{-5}$) | $0.58$ ($0.0255$) | $0.34$ ($0.181$) | $-0.03$ ($0.885$) |
| **Excl. 50m (100m vs. Dist, $N=172$)** | $0.83$ ($0.0002$) | $0.91$ ($6.94 \times 10^{-5}$) | $0.63$ ($0.0037$) | $0.59$ ($0.0170$) | $0.40$ ($0.115$) | $0.01$ ($0.970$) |
| **Finalists Only (`stage=="Final"`, $N=200$)** | $0.97$ ($7.60 \times 10^{-5}$) | $1.00$ ($2.10 \times 10^{-5}$) | $0.58$ ($0.0071$) | $0.33$ ($0.267$) | $0.16$ ($0.603$) | $-0.06$ ($0.769$) |
| **1-Row-Per-Athlete Best WA ($N=200$)** | $0.78$ ($0.0005$) | $0.93$ ($5.42 \times 10^{-5}$) | $0.61$ ($0.0038$) | $0.50$ ($0.055$) | $0.37$ ($0.150$) | $0.05$ ($0.788$) |

* **Start/Turn Confounding (Excl. 50m):** Removing the 50m (where 1 dive start + up to 15m underwater inflates $v$) actually *strengthens* the Height difference in Women ($g = 0.59$, $p_{\text{FDR}} = 0.0170$) and preserves all Men's effects ($g = 0.83$–$0.91$). Moreover, **100.0%** of 100m finalists/swimmers still exceed $Fr = 0.42$ (Men mean $Fr = 0.476$; Women mean $Fr = 0.446$).
* **Range Restriction in Finalists Only:** Restricting to `stage == "Final"` attenuates Women's Height effect ($g = 0.33$, $p_{\text{FDR}} = 0.267$), consistent with range restriction among top-8 Olympic finalists.

---

## 5. Event-Level Distance Gradient (50m → 100m → 800m → 1500m)

Full event-level summaries and trend tests are saved in [event_gradient_summary.csv](event_gradient_summary.csv) and [event_gradient_trends.csv](event_gradient_trends.csv).

* **Men:** Strong monotonic decreases with race distance in Height (ANOVA $F = 8.02, p = 6.17 \times 10^{-5}$; Kruskal-Wallis $H = 19.62, p = 0.0002$; Spearman $\rho = -0.355, p = 3.21 \times 10^{-5}$), Mass ($F = 13.36, p = 1.24 \times 10^{-7}$; $\rho = -0.434$), and BMI ($F = 7.02, p = 0.0002$; $\rho = -0.309$), alongside sharp drops in $v$ ($\rho = -0.943$) and $Fr$ ($\rho = -0.942$).
* **Women:** $v$ ($\rho = -0.936$), $Fr$ ($\rho = -0.939$), and $Re$ ($\rho = -0.905$) drop steeply across events ($p < 10^{-20}$), whereas BMI ($F = 0.76, p = 0.516$; $\rho = 0.037$) and Mass ($F = 1.80, p = 0.151$; $\rho = -0.052$) remain flat across all four distances. Height shows a borderline ANOVA difference ($F = 2.67, p = 0.0507$) driven by the Sprint vs. Distance step.

---

## 6. Within-Category Correlations, Parsimonious OLS & Zero-Leakage Classification

### Within-Category Correlations ([within_category_correlations.csv](within_category_correlations.csv))
* **Within Distance (800m/1500m):** Taller swimmers achieved higher mean race speeds and higher WA Points in both Men ($r = 0.364, p = 0.015$ for $v$; $r = 0.397, p = 0.008$ for WA Points) and Women ($r = 0.396, p = 0.013$ for $v$; $r = 0.413, p = 0.009$ for WA Points), while operating at lower Froude numbers (Men $r = -0.478, p = 0.001$; Women $r = -0.627, p = 1.9 \times 10^{-5}$).
* **Within Sprint (50m/100m):** In Women, Height correlated positively with WA Points ($r = 0.246, p = 0.026$) and negatively with $Fr$ ($r = -0.324, p = 0.003$).

### Parsimonious OLS & Cluster-Robust SEs ([ols_regression_results.csv](ols_regression_results.csv))
* **Collinearity Verified:** Across all 60 OLS models (both `AE_dedup` and `RC_cluster_athlete` with `athlete_key`-clustered SEs), the maximum VIF was **4.200** (strictly $< 5$).
* **Distance Velocity Models:** Adding `Height + Mass` to `Year + Age` explained substantially more variance than `BMI + Year + Age` in both Men ($R^2 = 0.365$ vs. $0.241$) and Women ($R^2 = 0.402$ vs. $0.258$; where Height $\beta = 0.522, p = 0.040$ in AE_dedup and $\beta = 0.500, p = 0.038$ with cluster-robust SEs, while BMI $\beta = -0.028, p = 0.849$).

### Zero-Leakage Anthropometric Classification ([logistic_cv_results.csv](logistic_cv_results.csv))
Strictly excluding all race/kinematic variables ($v, Fr, Re, T, \text{Points}$), 5-fold stratified CV logistic regression yielded:

| Sex | Anthropometric Model | 5-Fold CV ROC-AUC | CV Accuracy | Standardized Odds Ratios (per 1-SD) |
| :--- | :--- | :---: | :---: | :--- |
| **Men** | `Height + Mass` | **0.773** | **0.771** | Height $\text{OR} = 1.49$, Mass $\text{OR} = 2.63$ |
| **Men** | `Height alone` | 0.720 | 0.733 | Height $\text{OR} = 2.65$ |
| **Men** | `BMI alone` | 0.693 | 0.733 | BMI $\text{OR} = 2.23$ |
| **Men** | `PI alone` | 0.595 | 0.641 | PI $\text{OR} = 1.55$ |
| **Women** | `Height + Mass` | 0.590 | **0.686** | Height $\text{OR} = 1.69$, Mass $\text{OR} = 0.94$ |
| **Women** | `Height alone` | **0.598** | 0.669 | Height $\text{OR} = 1.62$ |
| **Women** | `BMI alone` | 0.459 | 0.678 | BMI $\text{OR} = 0.98$ |
| **Women** | `PI alone` | 0.565 | 0.661 | PI $\text{OR} = 0.80$ |

---

## 7. Hydrodynamic Interpretation & Limitations

1. **Wave-Drag Regime Transition:** Above $Fr \approx 0.42$, constructive bow-stern wave interference causes wave-making drag to rise super-quadratically. Because $Fr = v / \sqrt{gL}$, taller swimmers ($L$) achieve a higher theoretical hull speed ($v_{\text{hull}} \approx 0.42\sqrt{gL}$) and lower $Fr$ at any given race velocity. Our finding that 100% of 50m and 100m swimmers exceed $Fr = 0.42$ while 0% of 800m and 1500m swimmers do confirms that sprint and distance freestyle occupy fundamentally distinct hydrodynamic regimes.
2. **Why Height Matters More Than BMI (Gagnon et al., 2018):** In terrestrial running, body mass is directly penalized by gravity, driving steep BMI drops with distance. In water, buoyancy supports body weight; thus, Women sprinters and distance swimmers converge on identical BMI ($20.75$ vs. $20.77\text{ kg/m}^2$), yet sprinters remain taller ($g = 0.48$) to reduce wave drag and extend stroke length. In Men, high anaerobic power demands ($P \propto v^3$) also select for greater muscle mass ($g = 1.09$) alongside height ($g = 0.89$).
3. **Key Limitations:** (a) Standing height is an anthropometric proxy for submerged waterline length ($L_w$); (b) Paris 2024 anthropometrics are restricted to returning Olympians matched to Olympedia/Kaggle bios; (c) Men's 800m ($n=13$) and Women's 1500m ($n=5$) have small post-2020 samples; (d) public datasets lack arm span, frontal cross-sectional area ($A$), and stroke kinematics ($SR, SL$).