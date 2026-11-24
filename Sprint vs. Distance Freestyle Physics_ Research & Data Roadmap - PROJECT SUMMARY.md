# **Sprint vs. Distance Freestyle Physics: Research & Data Roadmap**

**Research Focus:** Comparing anthropometric characteristics and hydrodynamic constraints in elite sprint freestyle (50m / 100m) versus long-distance freestyle (800m / 1500m).

**Core Hypothesis to Test:** Because water buoyancy supports body weight, swimming does not penalize mass the same way running does (see [Gagnon et al., 2018](https://royalsocietypublishing.org/rspb/article/285/1882/20180684/79002/Elite-swimmers-do-not-exhibit-a-body-mass-index)). Instead, sprint vs. distance differences should be driven by hydrodynamic drag (especially wave-making drag at high sprint speeds, which favors greater body length) versus sustained aerobic power-to-drag efficiency over longer distances.

---

# **1. Target Variables**

## **Primary Variables (Public Olympic Datasets)**

* **Standing Height ($L$, in meters):** Relative anthropometric proxy for submerged/streamlined waterline body length ($L_w$), not exact $L_w$. Greater $L$ lowers the Froude number and wave-making drag at sprint speeds.
* **Body Mass ($m$, in kg):** Proxy for overall body size and muscle mass (anaerobic power capacity).
* **Derived Body Ratios:**
  * **BMI** $= m / L^2$ (tests whether sprint and distance swimmers diverge or converge on similar BMI).
  * **Ponderal Index (PI)** $= m / L^3$ (often more physically appropriate than BMI for tall athletes because mass scales with volume).
  * *Collinearity Note:* $L$, $m$, BMI, and PI are algebraically dependent and are never entered together in the same regression model (see Section 3).
* **Event Category & Sex:** 50m/100m Freestyle (Sprint) vs. 800m/1500m Freestyle (Distance), **mandatorily stratified by sex** (Men vs. Women analyzed separately).
  * *Event-Introduction Asymmetry:* Women's 1500m Freestyle and Men's 800m Freestyle debuted at the Tokyo 2020 (held 2021) Olympic Games; consequently, 800m and 1500m samples are structurally unbalanced across 2000–2024.
* **Race Time ($T$, in seconds) & Mean Race Speed ($v = \text{Distance} / T$):**
  * $v$ is explicitly defined as **mean race speed**, not pure surface swimming speed. In the 50m freestyle, 1 dive start plus up to 15m of underwater dolphin kick (30% of the race at ~3 m/s) inflates $v$ and $Fr$ relative to surface swimming; in the 800m/1500m, 15 and 29 turns respectively contribute wall push-off speed. A sensitivity check excluding 50m (100m vs. 800m/1500m) and/or adjusting for turn count is required.
* **Standardized Performance — World Aquatics (FINA) Points:** Allows fair performance comparison across distances and sexes using official LCM base times (Section 4).

## **Secondary / Ideal Variables (Limited Public Data — Club or Literature Collection)**

If supplementing public data with anonymized measurements from a swim club or published sports-science studies (see [Anthropometric Variables Review](https://www.researchgate.net/publication/366484754_Influence_of_Anthropometric_Variables_for_Freestyle_Sprinting_Performance_of_Swimming_A_Review)):

* **Arm Span (Wingspan) & Ape Index (Arm Span / Height):** Strongly tied to stroke length and propulsive reach.
* **Hand Length / Width & Shoulder Breadth:** Proxies for propulsive paddle area and frontal cross-sectional area (FSA).
* **Kinematics (from race video or splits):** Stroke Rate (SR), Stroke Length (SL), and Stroke Index (SI).

---

# **2. Relevant Physics & Biomechanics Equations**

## **Hydrodynamic Drag & Components**

$$F_{\text{drag}} = F_{\text{friction}} + F_{\text{form}} + F_{\text{wave}}$$

* **Form / Active Drag:** $F_d = \frac{1}{2} \cdot \rho \cdot C_d \cdot A \cdot v^2$  
  *($\rho = 996.8\text{ kg/m}^3$ water density at 26 °C competition pool temperature, $C_d =$ drag coefficient, $A =$ frontal cross-sectional area, $v =$ swimming velocity)*
* **Skin Friction Drag:** $F_{\text{friction}} = \frac{1}{2} \cdot \rho \cdot C_f \cdot S_{\text{wet}} \cdot v^2$  
  *($S_{\text{wet}} =$ wetted surface area; accounts for roughly 10–15% of total drag at sprint speeds, while form drag accounts for ~40–60% and wave drag ~30–50%; see [Swimming Hydrodynamics Overview](https://www.mysimulator.uk/content/articles/swimming-hydrodynamics.html))*

## **Froude Number & Hull Speed (Why Height Matters in Sprints)**

$$Fr = \frac{v}{\sqrt{g \cdot L}}$$

$$\text{Theoretical surface hull speed: } v_{\text{hull}} \approx 0.42 \cdot \sqrt{g \cdot L}$$

*($g = 9.81\text{ m/s}^2$, $L =$ standing height used as a relative proxy for waterline length $L_w$)*

Rather than a hard physical threshold, $Fr \approx 0.42$ marks a **smooth constructive-interference wave-drag transition ("hull speed" hump)** where wave-making drag rises steeply as wavelength approaches body length. At elite sprint speeds (mean race speeds of 2.0–2.4 m/s in 50m/100m), taller swimmers have a larger $L$, giving them a higher hull speed and lower Froude number at the same velocity (see [Active Drag Review, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9630912/)). Because 50m mean race speed is inflated by the dive start and underwater phase, $Fr$ should be interpreted alongside a 100m-only sprint sensitivity check.

## **Reynolds Number (Flow Regime)**

$$Re = \frac{\rho \cdot v \cdot L}{\mu}$$

*($\mu = 8.7 \times 10^{-4}\text{ Pa}\cdot\text{s}$ dynamic viscosity of water at 26 °C competition pool temperature)*

At elite speeds, $Re \approx 3\text{–}4 \times 10^6$, confirming turbulent boundary-layer flow.

## **Propulsive Power Required to Overcome Drag**

$$P_{\text{form}} = F_{\text{form}} \cdot v = \frac{1}{2} \cdot \rho \cdot C_d \cdot A \cdot v^3$$

$$P_{\text{mech}} = \eta_p \cdot P_{\text{metabolic}} = P_{\text{drag}} = (F_{\text{friction}} + F_{\text{form}} + F_{\text{wave}}) \cdot v$$

The $\frac{1}{2}\rho C_d A v^3$ term describes **form-drag (and skin-friction) power scaling**; near $Fr \approx 0.42$, **wave-making drag scales super-quadratically** with velocity, causing total drag power to grow even faster than $v^3$ near hull speed. Furthermore, **propelling efficiency ($\eta_p$)** mediates how effectively metabolic power ($P_{\text{metabolic}}$) converts into useful mechanical propulsive power ($P_{\text{mech}}$). Consequently, small speed increases in sprints demand massive anaerobic power output (favoring larger muscle mass and height), whereas distance swimming rewards minimizing frontal area ($A$), drag coefficient ($C_d$), and energetic cost per stroke to stay below aerobic threshold.

## **Stroke Kinematics & Efficiency**

$$v = SL \times SR$$

$$\text{Stroke Index: } SI = v \times SL$$

*(Higher SI indicates greater swimming efficiency; see [50m vs. 100m Kinematics Study](https://www.mdpi.com/2076-3417/12/24/12577))*

## **Performance Standardization (World Aquatics Points)**

$$\text{Points} = \left\lfloor 1000 \cdot \left(\frac{B}{T}\right)^3 \right\rfloor$$

*($B =$ official World Aquatics LCM base time for the event in seconds; $T =$ swimmer's time in seconds; see [World Aquatics Swimming Points](https://www.worldaquatics.com/swimming/points))*

---

# **3. Study Design, Confounder Controls & Statistical Plan**

## **Confounder Controls & Sensitivity Analyses**

1. **Mandatory Sex Stratification:** All primary hypothesis tests, effect sizes, and regression/classification models are stratified by sex (Men vs. Women).
2. **Polyurethane "Supersuit" Era (2008–2009):** Full-body polyurethane suits (Beijing 2008) artificially altered buoyancy and reduced drag, making 2000–2024 non-uniform. Run primary inference on the **post-2010 textile era (2012–2024)** and compare against the **full modern window (2000–2024)** as a sensitivity split.
3. **Event-Introduction Asymmetry & Missingness Audit:** Account for the Tokyo 2020 debut of Women's 1500m and Men's 800m, and sparser post-2016 bio coverage. Report $N$ and `% missing` height/mass per `sex × event × year` cell. **Never impute** height or mass for $Fr$ or anthropometric comparisons.
4. **Selection Bias (Heats vs. Finalists):** Finalists-only samples compress anthropometric variance (range restriction), whereas heats include universality entrants. Run sensitivity comparisons across **all heat entrants** vs. **top-16 / finalists**.
5. **Start/Turn/Underwater Confounding:** Run a sensitivity check **excluding 50m** (comparing 100m vs. 800m/1500m) and/or adjusting for turn count.

## **Independence & Zero-Leakage Rules**

* **Athlete-Event Deduplication & Mixed Effects:** Athletes appear repeatedly across heats/semis/finals, multiple events (e.g., 50m + 100m), and multiple Games, violating i.i.d. assumptions.
  * For group hypothesis tests, deduplicate to **1 primary observation per `athlete_id × event`** (best time at Games, or career best).
  * For multi-observation regressions, use **mixed-effects models** (`statsmodels`, random intercept for `athlete_id`) or cluster-robust standard errors.
* **Strict Anti-Leakage in Classification:** When training Sprint-vs-Distance classifiers (e.g., logistic regression), **strictly exclude `v`, `Fr`, `Re`, `T`, and `Points`**—these directly encode event distance. Restrict predictors strictly to **anthropometrics only** (`Height`, `Mass`, `PI` or `BMI`, plus `Sex` if running a pooled auxiliary model).

## **Statistical Analysis Plan**

* **Group Comparisons (Sprint vs. Distance):** Run both **Welch's two-sample t-test** and the non-parametric **Mann-Whitney U test** (robust to right-skewed race times and $Fr$).
* **Effect Sizes with 95% CIs:** Report **Hedges' $g$** (parametric) and **rank-biserial $r$** (non-parametric) with 95% confidence intervals (bootstrap or analytical).
* **Multiple Comparisons:** Pre-specify primary comparisons and apply **Benjamini-Hochberg (BH) False Discovery Rate (FDR)** correction across `event × sex × metric` test families.
* **Collinearity Control:** Never include `Height`, `Mass`, `BMI`, and `PI` in the same regression. Fit **separate parsimonious models** (`Height + Mass` vs. `BMI` alone vs. `PI` alone, or `Height + PI`) and verify **Variance Inflation Factors (VIF < 5)**.

## **Background Reading Before Coding**

* **Fluid Mechanics Fundamentals:** Study pressure (form) drag, skin friction, and surface wave drag, and how calculus connects force, work, and power ($P = dW/dt = F \cdot v$).
* **Key Literature Benchmark:** Read [Gagnon et al. (2018) on BMI in Olympic Swimmers](https://royalsocietypublishing.org/rspb/article/285/1882/20180684/79002/Elite-swimmers-do-not-exhibit-a-body-mass-index) to understand why swimmers do not show the same mass-vs-distance drop-off as runners—and test whether **height** and **Froude number** separate sprinters from distance swimmers even when BMI does not.

---

# **4. Verified Data Sources, Base Times & Join-Key Strategy**

## **Verified Public Datasets**

| Source | Contents & Coverage | Join Keys & Caveats | Identifier / URL |
| :--- | :--- | :--- | :--- |
| **GitHub: `josephwccheng/olympedia_web_scraping`** | `Olympic_Athlete_Bio.csv` (51.5 MB: `athlete_id, name, sex, born, height, weight, country_noc`), `Olympic_Athlete_Event_Results.csv` (32.1 MB), `Olympic_Results.csv` (10.2 MB). Summer Games through Tokyo 2020. | Primary Olympedia spine via `athlete_id`, `result_id`, `edition_id`. (2024/2028/2032 rows are empty date placeholders.) | [olympedia_web_scraping](https://github.com/josephwccheng/olympedia_web_scraping) |
| **GitHub: `KeithGalli/Olympics-Dataset`** | `bios.csv` (10.8 MB: `athlete_id, name, born_date, NOC, height_cm, weight_kg`) & `results.csv` (33.0 MB). | Clean Olympedia bio/results tables joined on `athlete_id`. | [Olympics-Dataset](https://github.com/KeithGalli/Olympics-Dataset) |
| **GitHub: `chanronnie/Olympics`** | `athletes.csv` (76.5 MB: `id, name, gender, born, height, weight, noc, game, event, medal`) through 2022. | Join key `id` (Olympedia ID) or `(name, noc, game)`. Height/weight strings include units (`172 cm`, `55 kg`). | [Olympics](https://github.com/chanronnie/Olympics) |
| **Kaggle: `heesoo37/120-years-of-olympic-history-athletes-and-results`** | `athlete_events.csv` (41.5 MB: `ID, Name, Sex, Age, Height, Weight, NOC, Year, Event, Medal`), 1896–2016. | Join key `ID` or normalized `(Name, NOC, Year)`. **Stops at 2016** (no 2020/2024) and lacks raw race times. | [Kaggle 120 Years](https://www.kaggle.com/datasets/heesoo37/120-years-of-olympic-history-athletes-and-results) |
| **Paris 2024 Bio & Athletes (`piterfm` / `PietroViolo`)** | Kaggle `piterfm/paris-2024-olympic-summer-games` (3.1 MB) & GitHub mirror `PietroViolo/paris2024` `athletes.csv` (7.1 MB: `code, name, gender, country_code, height, weight, disciplines, events, birth_date`). | Join key `code` or normalized `(name, country_code, birth_date)`. **Note:** Missing height/weight are coded as `0` / `0.0` (must convert to `NaN`). | [PietroViolo/paris2024](https://github.com/PietroViolo/paris2024) |
| **Kaggle: `datasciencedonut/olympic-swimming-1912-to-2020`** | Full Olympic swimming race times (368 KB, 1912–2020): `Location, Year, Distance, Stroke, Relay?, Gender, Team, Athlete, Results, Rank`. | Essential source for 2000–2020 race times (`MM:SS.dd` / `SS.dd`; filter `Relay? == 0`). Requires normalized name/NOC/sex/age matching to Olympedia bios. | [1912–2020 Swimming](https://www.kaggle.com/datasets/datasciencedonut/olympic-swimming-1912-to-2020) |
| **Kaggle: `batuhansalman/olympic-swimming-results-2016-2024`** | Swimming results 2016–2024 (2,522 bytes total). | **Caveat:** ~2.5 KB file size indicates a small summary/subset (e.g., medalists/top finals), not full heats/semis/finals. Inspect before relying on it for 2024 times. | [2016–2024 Swimming](https://www.kaggle.com/datasets/batuhansalman/olympic-swimming-results-2016-2024) |
| **World Aquatics Rankings & Points** | Official LCM base times (1000-pt benchmark) and world rankings. | Used to standardize race times into FINA Points; does not list athlete height/weight. | [World Aquatics Points](https://www.worldaquatics.com/swimming/points) |
| **Optional Supplemental Data** | Anonymized height, wingspan (ape index), mass, and personal bests (50m–1500m). | Solves public-data gap on wingspan; adds original primary data collection. | Local Collection (CSV) |

## **Official World Aquatics (FINA) LCM Base Times (2024 / 2025 Tables)**

Formula: $\text{Points} = \lfloor 1000 \times (B / T)^3 \rfloor$ ($B, T$ in seconds).

| Event (LCM Freestyle) | Men's Base Time $B$ | Women's Base Time $B$ |
| :--- | :--- | :--- |
| **50m Freestyle** | `20.91` s | `23.61` s |
| **100m Freestyle** | `46.40` s | `51.71` s |
| **800m Freestyle** | `452.12` s (`7:32.12`) | `484.79` s (`8:04.79`)* |
| **1500m Freestyle** | `870.67` s (`14:30.67`) | `920.48` s (`15:20.48`) |

*\*Note: Women's 800m LCM base time was updated to `8:04.12` (`484.12` s) only after the May 2025 World Record.*

## **Join-Key Strategy & Match-Rate Audit**

1. **Primary Spine (`athlete_id`):** Use Olympedia `athlete_id` across `Olympic_Athlete_Bio.csv`, `Olympic_Athlete_Event_Results.csv`, `KeithGalli/bios.csv`, and `KeithGalli/results.csv` to eliminate name-collision errors.
2. **Cross-Source Name Matching (Kaggle Race Times & Paris 2024):** When merging `datasciencedonut` race times or Paris 2024 (`code`) onto Olympedia bios:
   * Normalize Unicode (strip diacritics, lowercase, standardize punctuation, and handle `Lastname, Firstname` vs. `Firstname Lastname` ordering).
   * Match on `(normalized_name, NOC, sex)` with a plausible age/birth-year window check.
   * **Match-Rate Audit:** Log and report exact match rates (`% matched` and unmatched counts) per `sex × event × year` before running statistical analyses.

---

# **5. Planned Next Steps (Data Pipeline Automation)**

1. **Extraction & Verification:** Download and verify the Olympedia bio/results CSVs, Paris 2024 athlete bio CSV, and Kaggle swimming race-time datasets into `data/raw/`, plus save the verified World Aquatics base times JSON.
2. **Linkage & Audit:** Build the `athlete_id`-anchored merge pipeline with normalized `(name, NOC, sex, age)` cross-matching for race times; convert `0`/`0.0` Paris 2024 placeholders to `NaN`; audit match rates and missingness per `sex × event × year`.
3. **Filtering & Deduplication:** Filter to modern individual freestyle events (50m, 100m, 800m, 1500m; `Relay? == 0`), tag suit era (`2000–2009` vs. `2012–2024` textile) and round (`Heats` vs. `Finalists`), and produce a deduplicated `athlete_id × event` dataset alongside the full multi-round dataset.
4. **Feature Engineering & Modeling:** Compute BMI, Ponderal Index, mean race speed ($v$), $Fr$, $Re$, and World Aquatics Points (without imputing anthropometrics); run sex-stratified Welch's t-tests / Mann-Whitney U tests with Hedges' $g$ / rank-biserial $r$ (95% CIs) and BH-FDR correction; fit parsimonious VIF-checked regressions and anthropometric-only (zero-leakage) classifiers across all pre-specified sensitivity splits.
