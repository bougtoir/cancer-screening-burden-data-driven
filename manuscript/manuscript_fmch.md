# False-positive cascade from direct-to-consumer multi-cancer early detection blood tests: implications for primary and specialty care

### Key points

- **Question:** What primary care, diagnostic, and specialist workload is generated when direct-to-consumer blood-based multi-cancer early detection (MCED) tests return positive results in an asymptomatic population?
- **Finding:** A 100,000-person MCED wave at 50% follow-up produced 383 true positives and 7995 false positives (PPV 4.58%), generating 4189 primary care visits and exceeding the illustrative specialist capacity ceiling once follow-up exceeded 40%.
- **Meaning:** Without regulatory guardrails on performance claims and follow-up obligations, widespread direct-to-consumer MCED screening could overload primary care, specialty care, and community health systems with unnecessary investigations.

## Abstract

**Background:** Direct-to-consumer blood-based multi-cancer early detection (MCED) tests are advertised as a convenient single-blood-draw screen. In asymptomatic populations most positive results are false positives, each triggering primary care, imaging, endoscopy, and specialist follow-up visits.

**Methods:** A deterministic expected-value model was parameterised with 2023 adult cancer incidence and population data, 2023 national diagnostic volumes, and primary care and specialist capacity derived from NDB Open Data outpatient counts and Japanese specialist-board counts. True positives, false positives, downstream visits, capacity utilisation, and per-specialist case load were estimated across follow-up rates of 0-100% and specificities of 95.0-99.9%.

**Results:** In a 100,000-person cohort at 50% follow-up and 0.990 specificity, the model generated 383.5 true positives and 7994.5 false positives (positive predictive value 4.58%; false-positive/true-positive ratio 20.8). Total downstream visits reached 19873.4, including 4189.0 primary care visits (35.0% of the illustrative primary-care capacity). Maximum capacity utilisation was 163.2% (specialist visits). The illustrative capacity ceiling was exceeded at a follow-up rate of 40% (specialist total visits). False-positive specialist visits added 168.8 visits per relevant specialist, raising the effective cases per specialist from 35.1 to 204.0 (481% increase).

**Conclusions:** Even with optimistic 99% specificity, a direct-to-consumer MCED wave can trigger a false-positive cascade that exceeds outpatient and endoscopic capacity and overloads primary care. Transparent positive predictive value reporting, performance thresholds, and clear follow-up obligations are needed before routine adoption, with support for family physicians and primary care clinicians to counsel patients.

**Keywords:** multi-cancer early detection, false positive, healthcare capacity, direct-to-consumer testing, primary care, shared decision-making, scenario model

---

## Introduction

Blood-based multi-cancer early detection (MCED) tests are increasingly advertised directly to consumers as a convenient “single blood draw” cancer screen [^1^]. Because most positive results in asymptomatic populations are false positives, each abnormal test generates a cascade of confirmatory imaging and specialist visits [^2^][^3^]. In this setting, where endoscopy and specialist visits are already constrained [^4^], widespread DTC use could displace routine care. Clinicians are increasingly asked to interpret or manage results from tests acquired outside clinical care [^5^]. Family physicians and primary care clinicians are often the first point of contact for patients with a positive result and are concerned about interpreting results, costs, and managing subsequent evaluations [^6^]. This burden was quantified as a function of follow-up behaviour, test specificity, and age structure.

## Methods

### Data sources

Cancer incidence by site, age, sex, and calendar year (2023) and the corresponding 2023 population by age and sex were taken from the National Cancer Center of Japan [^1^]. Annual volumes of CT, MRI, and upper/lower gastrointestinal endoscopies were derived from the 2023 Ministry of Health, Labour and Welfare Medical Facility Survey [^4^]. Test sensitivity and specificity ranges were informed by two recent systematic reviews of blood-based MCED tests [^2^][^3^], and real-world PPV evidence came from a nationwide PET/CT facility survey of N-NOSE-triggered examinations [^7^].

Specialist capacity was defined using NDB Open Data first/revisit outpatient patient counts and Japanese Board of Medical Specialties specialist counts [^8^][^9^]. Disease-specific baseline patient numbers for the case-per-specialist ratio were taken from the MHLW 2023 Patient Survey [^10^].

### Model

A deterministic expected-value cohort model was used. For each cancer type:

- Actual cases = screened population × prevalence per 100,000 / 100,000.
- True positives = actual cases × sensitivity.
- False positives = (screened population − actual cases) × (1 − specificity).

Each positive individual who followed up (follow-up rate, 0–100%) generated a primary care visit plus visits to CT, MRI, endoscopy, and specialist care according to cancer-specific pathway probabilities. Additional visits per true and false positive were added. Capacity utilisation for each resource was calculated as total visits divided by the annual capacity per 100,000 population. A full description of equations is available in `simulate.py`.

Prevalence was approximated by adult (20+) incidence because point prevalence of undiagnosed, screen-detectable cancers is not publicly reported. This is a conservative lower-bound for true positives and therefore a lower-bound for PPV and an upper-bound for FP/TP ratios. Pathway probabilities and the share of facility capacity available for a new DTC-related wave were scenario assumptions, documented in `parameters.yaml`.

### Specialist and primary care capacity definition

Baseline specialist capacity is defined as the annual outpatient caseload per cancer-relevant specialist. NDB Open Data unique first/revisit outpatient patient counts were used (April 2024–March 2025) divided by the total number of basic JMSB specialists, giving an average annual caseload per specialist [^8^][^9^]. This value was then multiplied by the number of cancer-relevant specialists per 100,000 population and applied the same 20% share assumed available for a DTC wave. The resulting `specialist_visits_per_year` is an illustrative capacity ceiling for a 100,000-person cohort.

The same approach was applied to primary care (internal medicine and general practice) specialists to derive `primary_care_visits_per_year`.

### Scenarios

Base-case sensitivity and specificity were 0.70 and 0.990. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. Japan was used as a case study because it has a large direct-to-consumer screening market and publicly available national data; the false-positive cascade is generalisable to other high-income settings. The available-for-cancer-workup share of national diagnostic capacity was set to 20%.

### Reporting

This scenario modelling study is reported in accordance with the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement and the Statistical Analyses and Methods in the Published Literature (SAMPL) guidelines where applicable.

## Results

### Scenario parameters

Table 1 summarises the data sources and base-case parameter values.

**Table 1. Data sources and scenario parameters.**

| Parameter | Value | Source / assumption |
|---|---|---|
| Screened population | 100,000 | Model cohort |
| Base sensitivity | 0.70 | Kahwati LC et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ 2025. https://www.ncbi.nlm.nih.gov/books/NBK618307/ |
| Base specificity | 0.990 | Kahwati LC et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ 2025. https://www.ncbi.nlm.nih.gov/books/NBK618307/ |
| CT capacity per 100k per year | 5676 | Ministry of Health, Labour and Welfare, 2023 Medical Facility Survey (Static/Dynamic), 05sisetu05.xlsx |
| MRI capacity per 100k per year | 2678 | Ministry of Health, Labour and Welfare, 2023 Medical Facility Survey (Static/Dynamic), 05sisetu05.xlsx |
| Endoscopy capacity per 100k per year | 2583 | Ministry of Health, Labour and Welfare, 2023 Medical Facility Survey (Static/Dynamic), 05sisetu05.xlsx |
| Specialist capacity per 100k per year | 7183 | Derived from NDB Open Data first/revisit outpatient patient counts (88,408,837 + 85,182,008) and 79,117 cancer-relevant JMSB specialists; 20% share assumed available for new cancer workups. |
| Primary care capacity per 100k per year | 11983 | Derived from NDB Open Data first/revisit outpatient patient counts (88,408,837 + 85,182,008) and 131,981 primary-care-relevant JMSB specialists (internal medicine and general practice); 20% share assumed available for new cancer workups. |
| Gastric prevalence (per 100k) | 84.3 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Colorectal prevalence (per 100k) | 123.8 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Lung prevalence (per 100k) | 99.7 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Breast prevalence (per 100k) | 83.2 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Prostate prevalence (per 100k) | 82.1 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Liver prevalence (per 100k) | 26.2 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Pancreatic prevalence (per 100k) | 38.2 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |
| Ovarian prevalence (per 100k) | 10.3 | National Cancer Center of Japan, Cancer Statistics in Japan 2016-2023 |

### Per-cancer burden at 50% follow-up

At a 50% follow-up rate, the model estimated 383.5 true positives and 7994.5 false positives across all eight cancers (Table 2). Colorectal had the highest age-distribution-weighted PPV (7.99%) and Ovarian the lowest (0.72%). The FP/TP ratio ranged from 11.5 to 137.4.

**Table 2. Per-cancer outcomes at 50% follow-up (per 100,000 screened).**

| Cancer | Prevalence per 100k | True positives | False positives | PPV (%) | FP/TP ratio | Primary care visits | Total visits | Max resource utilisation (%) |
|---|---|---|---|---|---|---|---|---|
| Gastric | 84.3 | 59.0 | 999.2 | 5.58 | 16.9 | 529.1 | 2613.4 | 19.4 |
| Colorectal | 123.8 | 86.7 | 998.8 | 7.99 | 11.5 | 542.7 | 2713.4 | 20.4 |
| Lung | 99.7 | 69.8 | 999.0 | 6.53 | 14.3 | 534.4 | 2830.1 | 23.8 |
| Breast | 83.2 | 58.2 | 999.2 | 5.51 | 17.2 | 528.7 | 2161.1 | 19.4 |
| Prostate | 82.1 | 57.5 | 999.2 | 5.44 | 17.4 | 528.3 | 2182.8 | 19.0 |
| Liver | 26.2 | 18.4 | 999.7 | 1.81 | 54.4 | 509.0 | 2211.9 | 18.0 |
| Pancreatic | 38.2 | 26.7 | 999.6 | 2.61 | 37.4 | 513.2 | 2657.3 | 22.0 |
| Ovarian | 10.3 | 7.2 | 999.9 | 0.72 | 137.4 | 503.5 | 2503.3 | 21.2 |

### Capacity impact

Total downstream visits rose from 0.0 at 0% follow-up to 39746.8 at 100% follow-up (Fig. 1). At 50% follow-up this included 4189.0 primary care visits (35.0% of the illustrative primary-care capacity). Resource utilisation by modality is shown in Fig. 2. The first illustrative capacity ceiling was exceeded at 40% (specialist total visits). At 50% follow-up maximum utilisation was 163.2%.

![Figure 1: Total downstream visits by follow-up rate](output/total_visits_by_followup.png)
**Fig. 1.** Total downstream diagnostic, primary care, and specialist visits generated by a blood-based MCED screening wave of 100,000 persons, by follow-up rate.

![Figure 2: Diagnostic capacity utilisation by follow-up rate](output/capacity_utilization.png)
**Fig. 2.** Capacity utilisation (%) for CT, MRI, endoscopy, specialist, and primary care visits as follow-up rate increases. Values above 100% indicate demand exceeding the illustrative annual capacity available for a DTC screening wave.

### Age-specific positive predictive value

PPV was strongly age-dependent (Fig. 3). In younger age groups PPV fell below 1% for several cancers, rising above 20% only in the oldest groups. This implies that if DTC MCED users are younger than the general screening population, aggregate PPV would be lower and the false-positive burden larger than the base-case estimate.

![Figure 3: Age-specific PPV by cancer type](output/ppv_by_age.png)
**Fig. 3.** Age-specific positive predictive value for each cancer, assuming sensitivity 0.70 and specificity 0.99.

### Sensitivity to test specificity

Lowering specificity from 99% to 95% reduced aggregate PPV to roughly 0.2 of the 99% value (from 4.58% to 0.95%) and dramatically increased total visits and capacity pressure (Fig. 4; Table 3).

**Table 3. Aggregate outcomes by follow-up rate (base-case specificity).**

| Follow-up rate | True positives | False positives | Total positives | PPV (%) | FP/TP ratio | Primary care visits | Total visits | Max capacity utilisation (%) |
|---|---|---|---|---|---|---|---|---|
| 0% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 0.0 | 0.0 | 0.0 |
| 10% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 837.8 | 3974.7 | 32.6 |
| 20% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 1675.6 | 7949.4 | 65.3 |
| 30% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 2513.4 | 11924.0 | 97.9 |
| 40% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 3351.2 | 15898.7 | 130.6 |
| 50% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 4189.0 | 19873.4 | 163.2 |
| 60% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 5026.8 | 23848.1 | 195.9 |
| 70% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 5864.6 | 27822.8 | 228.5 |
| 80% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 6702.4 | 31797.5 | 261.2 |
| 90% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 7540.2 | 35772.1 | 293.8 |
| 100% | 383.5 | 7994.5 | 8378.0 | 4.58 | 20.8 | 8378.0 | 39746.8 | 326.4 |

![Figure 4: PPV and total positives across specificity values](output/specificity_sweep.png)
**Fig. 4.** Aggregate positive predictive value (%) and total positive results per 100,000 screened across specificity values at a 70% follow-up rate.

### Specialist capacity and the false-positive cascade

Table 4 compares the MHLW Patient Survey 2023 baseline cancer case load per specialist with the additional false-positive specialist visits generated by a 100,000-person DTC wave at 50% follow-up. Across all cancer-relevant specialties, the baseline case load is about 35.1 patients per specialist; the DTC wave adds about 168.8 false-positive specialist visits per specialist, an increase of 481%.

**Table 4. Baseline cases per specialist and incremental false-positive burden at 50% follow-up.**

| Cancer | Relevant specialty | Baseline cases per specialist | False-positive specialist visits per specialist | Cases per specialist with FP | Increase (%) |
|---|---|---|---|---|---|
| Gastric | Gastroenterology | 11.9 | 65.51 | 77.4 | 552.7 |
| Colorectal | Gastrointestinal Surgery | 63.4 | 174.89 | 238.3 | 275.7 |
| Lung | Respiratory Medicine | 43.9 | 245.38 | 289.2 | 559.6 |
| Breast | Breast Surgery | 403.5 | 799.33 | 1202.8 | 198.1 |
| Prostate | Urology | 85.5 | 221.40 | 306.9 | 258.9 |
| Liver | Hepatology | 10.1 | 194.25 | 204.4 | 1918.5 |
| Pancreatic | Gastroenterology | 3.8 | 78.65 | 82.4 | 2095.0 |
| Ovarian | Obstetrics and Gynaecology | 2.2 | 84.85 | 87.0 | 3885.6 |

## Discussion

The scenario model shows that, even under optimistic assumptions for test accuracy, a DTC blood-based MCED screening wave can produce roughly 21 false-positive workups for every true cancer detected. At 50% follow-up the illustrative specialist capacity ceiling is exceeded by 63.2 percentage points, and the effective case load per cancer-relevant specialist rises by about 481% due to false-positive follow-up visits. The burden is not uniform: cancers with low prevalence (ovarian, liver, pancreatic) had the lowest PPV and the highest FP/TP ratios, while age strongly modulates PPV.

These findings align with real-world data from the N-NOSE PET/CT survey, in which the cancer discovery rate after a high-risk result was low and well below the company's advertised PPV [^7^].

### Additional scenario and sensitivity analyses

Aggregate PPV is highly sensitive to the age distribution of users. If direct-to-consumer purchasers are younger than the general population, the already low PPV falls further and the FP/TP ratio rises (Table S1). For example, a younger-purchaser profile yields an aggregate PPV of 0.56% and an FP/TP ratio of 176.3, compared with 4.58% and 20.8 under the 2023 national total-population age distribution.

**Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios.**

| Age distribution scenario | Aggregate PPV (%) | FP/TP ratio |
|---|---|---|
| 2023 total population | 4.58 | 20.8 |
| Adults 20+ | 5.39 | 17.5 |
| DTC bimodal (23andMe-like) | 1.94 | 50.5 |
| DTC younger purchasers | 0.56 | 176.3 |
| DTC screening-age purchasers | 4.05 | 23.7 |

Test specificity and follow-up behaviour are the dominant drivers of capacity pressure (Supplementary Table S2). At 50% follow-up, lowering specificity from 99.9% to 95.0% reduces aggregate PPV from 32.42% to 0.95% and raises maximum capacity utilisation from 28.6% to 761.4%. With 99% specificity, maximum utilisation ranges from 32.6% at 10% follow-up to 293.8% at 90% follow-up. If only 5% of the illustrative national capacity can be reallocated, the bottleneck reaches 653%; with a 50% share it stays at 65%. Tornado diagrams for capacity utilisation and PPV are provided as Supplementary Figures S1 and S2.

![Supplementary Figure S1. One-way sensitivity of maximum capacity utilisation](output/tornado_max_capacity.png)
**Fig. S1.** Tornado diagram showing the effect of varying specificity, follow-up rate, available capacity share, and sensitivity on maximum capacity utilisation (base case = 50% follow-up, 99% specificity, 20% capacity share).

![Supplementary Figure S2. One-way sensitivity of aggregate PPV](output/tornado_ppv.png)
**Fig. S2.** Tornado diagram showing the effect of the same four parameters on aggregate positive predictive value.

![Supplementary Figure S3. Aggregate PPV under alternative age-distribution scenarios](output/age_scenario_ppv.png)
**Fig. S3.** Aggregate PPV for each cancer type under the 2023 national total-population distribution and four hypothetical direct-to-consumer purchaser age profiles.

### Implications for primary care and shared decision-making

A positive MCED result frequently lands in primary care before any specialist is involved. Family physicians must explain an uncertain signal, weigh it against guideline-recommended screening, and coordinate confirmatory tests. In this role, shared decision-making is essential: patients considering a DTC blood test need transparent information on the low PPV in asymptomatic populations and the likely cascade of follow-up visits [^5^]. The present figures suggest that, at 50% follow-up, each true cancer detected is accompanied by about 21 false-positive workups. Primary care providers are already concerned about responsibility for interpreting results, costs, and managing subsequent evaluations [^6^], and health-system reviews identify anxiety, false reassurance, and displacement of guideline-based screening as potential harms [^11^]. From a community-health perspective, the workload is not evenly distributed: cancers with the lowest prevalence generate the highest false-positive ratios, and younger users—who are increasingly targeted by DTC advertising—face the lowest PPVs. Regulators and payers could reduce this burden by requiring pre-market performance thresholds, transparent PPV reporting by age and sex, and a clear follow-up pathway that keeps primary care from becoming the default safety net for unregulated screening.

### Limitations

The analysis intentionally uses scenario assumptions for test performance, diagnostic pathways, and the age distribution of DTC users, because these data are not publicly reported. Prevalence was approximated by adult incidence; true point prevalence of undiagnosed cancers may differ. Diagnostic capacity was annualised from a one-month facility survey and specialist capacity from NDB outpatient patient counts; both were reduced by an arbitrary available-for-cancer-workup share. Primary care capacity was derived using the same national outpatient caseload and 20% available-share assumption as specialist capacity; actual capacity depends on local demand for chronic disease and routine care. Sensitivity and specificity were assumed to be uniform across cancers; real tests may vary by site. No probabilistic sensitivity analysis was performed because empirical distributions for test performance, follow-up behaviour, and direct-to-consumer user age structure are not publicly available. The model is deterministic and does not capture stochastic variation, geographic maldistribution, or queueing effects.

### Conclusion

Without regulatory guardrails—clear performance thresholds, transparent PPV reporting, and follow-up obligations—direct-to-consumer MCED tests risk converting a marketing promise into a large-scale false-positive cascade that stresses primary care, specialty care, and diagnostic capacity.

## Author contributions

All authors contributed to the study design, data interpretation, and critical revision of the manuscript, and approved the final version.

## Acknowledgements

We thank colleagues in primary care and health services research for their comments on the manuscript.

## Funding

No external funding was received for this study.

## Competing interests

The authors declare no competing interests.

## Ethics approval

This study used only publicly available aggregate data and a deterministic simulation; ethics approval was not required.

## Patient and public involvement

Patients or members of the public were not directly involved in the design, conduct, reporting, or dissemination of this modelling study.

## Data availability

All data sources are publicly available and listed in Table 1. The main simulation outputs (by-cancer and aggregate follow-up sweep, specificity sweep, sensitivity summary, age-specific PPV, age-scenario PPV, and specialist capacity impact) are generated by the analysis scripts. Analysis code, parameters, and outputs are available at https://github.com/bougtoir/cancer-screening-burden-data-driven.


## References

1. National Cancer Center of Japan. Cancer Statistics in Japan 2016-2023. https://ganjoho.jp/reg_stat/statistics/data/dl/en.html

2. Kahwati LC, et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ Comparative Effectiveness Review No. 267; 2025. https://www.ncbi.nlm.nih.gov/books/NBK618307/

3. Schnabel JL, et al. Predictive Performance of Cell-Free Nucleic Acid-Based Multi-Cancer Early Detection Tests: A Systematic Review. Clin Chem. 2024;70(1):90-101. https://pubmed.ncbi.nlm.nih.gov/37791504/

4. Ministry of Health, Labour and Welfare. 2023 Medical Facility Survey (Static/Dynamic). https://www.mhlw.go.jp/toukei/saikin/hw/iryosd/23/

5. Church TR, Elkin EB, Etzioni RD, Guerra CE, Hoffman RM, Manassaram-Baptiste D, et al. Multicancer early detection testing: Guidance for primary care discussions with patients. Cancer. 2025;131(7). https://pubmed.ncbi.nlm.nih.gov/40170549/

6. Ueberroth BE, Presutti RJ, McGary A, Borad MJ, Agrwal N. Perspectives of primary care providers regarding multicancer early detection panels. Einstein (Sao Paulo). 2024;22:eAO0771. https://doi.org/10.31744/einstein_journal/2024AO0771

7. Nagamachi S, et al. Nationwide PET/CT facility survey on N-NOSE-triggered examinations (in Japanese). PET Society, Japanese Society of Nuclear Medicine; 2024. https://jcpet.jp/2024/10/senchu-chosa.html

8. Ministry of Health, Labour and Welfare. NDB Open Data 11th release (April 2024–March 2025). https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177179.html

9. Japanese Board of Medical Specialties. Overview of the Japanese specialist system 2025. https://jmsb.or.jp/wp-content/uploads/2026/03/gaiho_2025.pdf

10. Ministry of Health, Labour and Welfare. Patient Survey 2023 (r05syobyo.pdf). https://www.mhlw.go.jp/toukei/saikin/hw/kanja/10syoubyo/

11. Wade R, Nevitt S, Liu Y, Harden M, Khouja C, Raine G, et al. Multi-cancer early detection tests for general population screening: a systematic literature review. Health Technol Assess. 2025;29(2). https://doi.org/10.3310/DLMT1294
