# False-positive cascade from direct-to-consumer multi-cancer early detection blood tests in Japan: a scenario modelling study of health-system burden

## Abstract

**Background:** Direct-to-consumer (DTC) blood-based multi-cancer early detection (MCED) tests are marketed as a convenient cancer screen that requires only a single blood draw. In asymptomatic populations most positive results are false positives, each of which can trigger a cascade of primary care, imaging, endoscopy, and specialist visits.

**Objective:** To quantify the health-system burden of a DTC MCED screening wave in Japan as a function of follow-up behaviour, test specificity, and age structure.

**Methods:** A deterministic expected-value cohort model was parameterised with 2023 adult cancer incidence and population data from Japan, 2023 national diagnostic volumes, and primary care and specialist capacity derived from NDB Open Data outpatient counts and Japanese specialist-board counts. True positives, false positives, downstream visits, capacity utilisation, and per-specialist case load were estimated across follow-up rates of 0-100% and specificities of 95.0-99.9%.

**Results:** In a 100,000-person cohort at 50% follow-up and 0.990 specificity, the model generated 383.5 true positives and 7994.5 false positives (positive predictive value 4.58%; false-positive/true-positive ratio 20.8). Total downstream visits reached 19873.4, including 4189.0 primary care visits (35.0% of the illustrative primary-care capacity). Maximum capacity utilisation was 163.2% (specialist visits). The illustrative capacity ceiling was exceeded at a follow-up rate of 40% (specialist total visits). False-positive specialist visits added 168.8 visits per relevant specialist, raising the effective cases per specialist from 35.1 to 204.0 (481% increase).

**Conclusions:** Transparent positive predictive value reporting, pre-market performance thresholds, and defined follow-up obligations are needed before routine DTC MCED adoption.


**Keywords:** multi-cancer early detection, false positive, health policy, healthcare capacity, direct-to-consumer testing, scenario model

---

## Research in context

- **What is already known about the topic?** DTC blood-based MCED tests are marketed to asymptomatic consumers, and their low positive predictive value means most positive results can trigger confirmatory imaging, endoscopy, and specialist visits.
- **What does this study add to the literature?** Using Japanese public data, this study quantifies the expected false-positive cascade, resource utilisation, per-specialist workload, and age-distribution effects across a range of follow-up rates and specificities.
- **What are the policy implications?** Pre-market performance thresholds, transparent age- and sex-specific positive predictive value reporting, and a clearly assigned follow-up pathway are needed to prevent primary and specialty care from being overloaded.

## Introduction

Blood-based multi-cancer early detection (MCED) tests are marketed directly to consumers in high-income countries as a convenient single-blood-draw cancer screen [^1^][^2^]. In asymptomatic populations most positive results are false positives, and each positive result can trigger a cascade of confirmatory imaging, endoscopy, and specialist visits [^1^][^2^]. National diagnostic volumes are already substantial [^3^], and unregulated DTC use could displace routine care and place additional pressure on primary care.

Japan is a pertinent case study because national data are publicly available in detail and direct-to-consumer cancer screening tests are already commercially available there [^4^]. Although the empirical inputs are Japanese, the model structure can be parameterised for other high-income settings. This study quantifies the health-system burden as a function of follow-up behaviour, test specificity, and age structure.

## Methods

### Data sources

Cancer incidence by site, age, sex, and calendar year (2023) and the corresponding 2023 population by age and sex were taken from the National Cancer Center of Japan [^5^]. Annual volumes of CT, MRI, and upper/lower gastrointestinal endoscopies were derived from the 2023 Ministry of Health, Labour and Welfare Medical Facility Survey [^3^]. Test sensitivity and specificity ranges were informed by two recent systematic reviews of blood-based MCED tests [^1^][^2^], and real-world evidence on the downstream diagnostic yield after a positive DTC cancer-screening result came from a nationwide PET/CT facility survey of N-NOSE-triggered examinations [^4^].

Specialist capacity was defined using NDB Open Data first/revisit outpatient patient counts and Japanese Board of Medical Specialties specialist counts [^6^][^7^]. Disease-specific baseline patient numbers for the case-per-specialist ratio were taken from the MHLW 2023 Patient Survey [^8^].

### Model

A deterministic expected-value cohort model was used. For each cancer type:

- Actual cases = screened population x prevalence per 100,000 / 100,000.
- True positives = actual cases x sensitivity.
- False positives = (screened population - actual cases) x (1 - specificity).

Each positive individual who followed up (follow-up rate, 0-100%) generated a primary care visit plus visits to CT, MRI, endoscopy, and specialist care according to cancer-specific pathway probabilities. Additional visits per true and false positive were added. Capacity utilisation for each resource was calculated as total visits divided by the annual capacity per 100,000 population. The complete set of equations is documented in `simulate.py` and `parameters.yaml`.

Prevalence was approximated by adult (20+) incidence because point prevalence of undiagnosed, screen-detectable cancers is not publicly reported. Point prevalence of detectable but undiagnosed cancers is likely lower than annual incidence (preclinical sojourn time is usually well under one year), so this proxy probably overstates the number of true positives. It therefore produces upper-bound positive predictive value estimates and lower-bound false-positive/true-positive ratios. The absolute visit counts are also sensitive to this proxy. Pathway probabilities and the share of facility capacity available for a new DTC-related wave were scenario assumptions, documented in `parameters.yaml`.

### Specialist and primary care capacity definition

Baseline specialist capacity was defined as the annual outpatient caseload per cancer-relevant specialist. NDB Open Data unique first/revisit outpatient patient counts were used (April 2024-March 2025) divided by the total number of basic JMSB specialists, giving an average annual caseload per specialist [^6^][^7^]. This value was then multiplied by the number of cancer-relevant specialists per 100,000 population and applied the same 20% share assumed available for a DTC wave. The resulting `specialist_visits_per_year` is an illustrative capacity ceiling for a 100,000-person cohort. The same approach was applied to primary care (internal medicine and general practice) specialists to derive `primary_care_visits_per_year`.

### Scenarios

Base-case sensitivity and specificity were 0.70 and 0.990. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. The available-for-cancer-workup share of national diagnostic capacity was set to 20%.

### Reporting

This scenario modelling study is reported in accordance with the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement and the Statistical Analyses and Methods in the Published Literature (SAMPL) guidelines where applicable.

## Results

### Scenario parameters

Table 1 summarises the data sources and base-case parameter values.

**Table 1. Data sources and scenario parameters.**

| Parameter | Value | Source / assumption |
|---|---|---|
| Screened population | 100,000 | Model cohort |
| Base sensitivity | 0.70 | Kahwati LC, Avenarius M, Brouwer L, et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ Publication No. 25-EHC033. Rockville (MD): Agency for Healthcare Research and Quality; 2025. https://doi.org/10.23970/AHRQEPCSRMULTIPLE |
| Base specificity | 0.990 | Kahwati LC, Avenarius M, Brouwer L, et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ Publication No. 25-EHC033. Rockville (MD): Agency for Healthcare Research and Quality; 2025. https://doi.org/10.23970/AHRQEPCSRMULTIPLE |
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

At a 50% follow-up rate, the model estimated 383.5 true positives and 7994.5 false positives across all eight cancers. Colorectal had the highest age-distribution-weighted positive predictive value (7.99%) and Ovarian the lowest (0.72%). Full per-cancer results are provided in Supplementary Table S1.

### Capacity impact

Total downstream visits rose from 0.0 at 0% follow-up to 39746.8 at 100% follow-up. At 50% follow-up, the wave generated 4189.0 primary care visits (35.0% of the illustrative primary-care capacity) and 19873.4 total visits. Resource utilisation by modality is shown in Fig. 1. The first illustrative capacity ceiling was exceeded at a follow-up rate of 40% (specialist total visits); at 50% follow-up, maximum utilisation was 163.2% (specialist visits).

![Figure 1: Diagnostic capacity utilisation by follow-up rate](output/capacity_utilization.png)
**Fig. 1.** Capacity utilisation (%) for CT, MRI, endoscopy, specialist, and primary care visits as follow-up rate increases. Values above 100% indicate demand exceeding the illustrative annual capacity available for a DTC screening wave.

### Age-specific positive predictive value

Positive predictive value was strongly age-dependent (Fig. 2). In younger age groups it fell below 1% for several cancers, and rose above 20% only in the oldest groups, driven by cancers with higher prevalence such as colorectal cancer. If DTC MCED users are younger than the general screening population, aggregate positive predictive value would be lower and the false-positive burden larger than the base-case estimate.

![Figure 2: Age-specific PPV by cancer type](output/ppv_by_age.png)
**Fig. 2.** Age-specific positive predictive value for each cancer, assuming sensitivity 0.70 and specificity 0.990.

### Specialist capacity and the false-positive cascade

Table 2 compares the MHLW Patient Survey 2023 baseline cancer case load per specialist with the additional false-positive specialist visits generated by a 100,000-person DTC wave at 50% follow-up. Across all cancer-relevant specialties, the baseline case load is about 35.1 patients per specialist; the DTC wave adds about 168.8 false-positive specialist visits per specialist, an increase of 481%.

**Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up.**

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

### Sensitivity and scenario analyses

Per-cancer outcomes at base-case follow-up are detailed in Supplementary Table S1. Supplementary Table S2 reports aggregate positive predictive value under alternative age-distribution scenarios. Supplementary Table S3 shows the one-way sensitivity analysis for the four key parameters, and aggregate outcomes by follow-up rate are in Supplementary Table S4. Test specificity and follow-up behaviour were the dominant drivers of capacity pressure (Supplementary Table S3). At 50% follow-up, lowering specificity from 99.9% to 95.0% reduced aggregate positive predictive value from 32.42% to 0.95% and raised maximum capacity utilisation from 28.6% to 761.4%. With 99% specificity, maximum utilisation ranged from 32.6% at 10% follow-up to 293.8% at 90% follow-up. If only 5% of the illustrative national capacity could be reallocated, the bottleneck reached 653%; with a 50% share it stayed at 65%. Supplementary Figure S1 shows total downstream visits by follow-up rate, Supplementary Figure S2 shows the specificity sweep, Supplementary Figure S3 shows the tornado sensitivity analysis for maximum capacity utilisation, Supplementary Figure S4 shows the corresponding analysis for positive predictive value, and Supplementary Figure S5 visualises the age-distribution scenarios.

## Discussion

Under the base-case assumptions, a DTC blood-based MCED screening wave generates roughly 21 false-positive workups for each true cancer detected. The illustrative capacity ceiling is already exceeded once follow-up reaches 40% (specialist total visits); Supplementary Table S4 shows the corresponding follow-up trajectory. At 50% follow-up, the ceiling is exceeded by 63.2 percentage points, and the effective case load per cancer-relevant specialist rises by about 481% after adding false-positive follow-up visits. This pattern is consistent with real-world Japanese experience of another direct-to-consumer cancer-screening test: the N-NOSE PET/CT survey found a low cancer discovery rate after a high-risk result [^4^].

### Policy implications

A positive MCED result is likely to be handled first by primary care before any specialist is involved. Clinicians must explain an uncertain signal, weigh it against guideline-recommended screening, and coordinate confirmatory tests. Shared decision-making is essential: patients considering a DTC blood test need transparent information on the low positive predictive value in asymptomatic populations and the likely cascade of follow-up visits [^9^]. At 50% follow-up, this implies about 21 false-positive workups for each true cancer detected. Primary care providers are concerned about responsibility for interpreting results, costs, and managing subsequent evaluations [^10^], and health-system reviews identify anxiety, false reassurance, and displacement of guideline-based screening as potential harms [^11^].

From a policy perspective, the workload is not evenly distributed: cancers with the lowest prevalence produce the highest false-positive ratios, and younger users, who may be preferentially targeted by DTC advertising, have the lowest positive predictive values. Regulators and payers could reduce this burden by requiring pre-market performance thresholds, transparent positive predictive value reporting by age and sex, and a clear follow-up pathway that prevents primary care from becoming the default safety net for unregulated screening. High-income countries with constrained primary and specialty care capacity should account for these externalities when deciding whether to allow or reimburse DTC MCED testing.

### Patient benefit and referral-letter status

A consumer-facing blood test offers convenience and the prospect of detecting cancers for which organised screening is unavailable [^1^][^2^]. For a small minority of users, earlier detection could shift stage at diagnosis, but in an asymptomatic cohort a positive result is unlikely to represent cancer (Fig. 2; Supplementary Table S1). Most positive results therefore generate anxiety, additional testing, and opportunity costs rather than useful early diagnosis, and systematic reviews report downstream harms including false reassurance, overdiagnosis, and displacement of guideline-based screening [^11^].

Treating a DTC positive result as equivalent to a physician's referral letter has direct capacity implications. A referral-letter model gives patients insured access to confirmatory care and may improve follow-up completion, but it also signals medical legitimacy and channels the false-positive cascade into the publicly funded system. The present model suggests that capacity is already breached at 50% follow-up when only 20% of available specialist capacity can be reallocated; insuring confirmatory workups could also raise follow-up completion and push utilisation higher. Conversely, keeping DTC testing outside the referral pathway leaves patients to self-fund follow-up, which may reduce public-sector pressure but also fragments care, delays diagnosis for the small true-positive minority, and creates inequity.

A middle path is therefore worth considering: allow DTC access, but require the test to meet pre-market performance thresholds and mandate that positive results be reviewed by a clinician before any publicly funded workup is authorised. Only evidence-based confirmatory investigations should be covered, with the responsible clinician empowered to decline inappropriate cascades. This preserves patient choice while preventing unregulated screening from converting a marketing promise into an unfunded mandate on primary and specialty care [^9^].

### Limitations

The analysis intentionally uses scenario assumptions for test performance, diagnostic pathways, and the age distribution of DTC users, because these data are not publicly reported. Prevalence was approximated by adult incidence; true point prevalence of undiagnosed cancers may differ. Diagnostic capacity was annualised from a one-month facility survey and specialist capacity from NDB outpatient patient counts; both were reduced by an arbitrary available-for-cancer-workup share. The model is deterministic and does not capture stochastic variation, geographic maldistribution, or queueing effects.

### Conclusion

In the absence of clear regulatory guardrails, including pre-market performance thresholds, transparent positive predictive value reporting, and defined follow-up obligations, direct-to-consumer MCED tests risk generating a large-scale false-positive cascade that stresses primary care, specialty care, and diagnostic capacity in high-income settings.

## Ethics approval

This study used only publicly available aggregate data and a deterministic simulation; ethics approval was not required.

## Patient and public involvement

Patients or members of the public were not directly involved in the design, conduct, reporting, or dissemination of this modelling study.

## Data availability

All data sources are publicly available and listed in Table 1. The analysis code, parameters, and outputs are available at https://github.com/bougtoir/cancer-screening-burden-data-driven.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work the author(s) used an AI-assisted research assistant (Devin, Cognition AI) to draft and revise sections of the manuscript and to generate simulation code. After using this tool, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the published article.

## References

1. Kahwati LC, Avenarius M, Brouwer L, et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ Publication No. 25-EHC033. Rockville (MD): Agency for Healthcare Research and Quality; 2025. https://doi.org/10.23970/AHRQEPCSRMULTIPLE

2. LeeVan E, Pinsky P. Predictive Performance of Cell-Free Nucleic Acid-Based Multi-Cancer Early Detection Tests: A Systematic Review. Clin Chem. 2024;70(1):90-101. https://doi.org/10.1093/clinchem/hvad134

3. Ministry of Health, Labour and Welfare. 2023 Medical Facility Survey (Static/Dynamic), 05sisetu05.xlsx. https://www.mhlw.go.jp/toukei/saikin/hw/iryosd/23/

4. Nagamachi S, et al. Nationwide PET/CT facility survey on N-NOSE-triggered examinations (in Japanese). PET Society, Japanese Society of Nuclear Medicine; 2024. https://jcpet.jp/2024/10/senchu-chosa.html

5. National Cancer Center of Japan. Cancer Statistics in Japan 2016-2023. https://ganjoho.jp/reg_stat/statistics/data/dl/en.html

6. Ministry of Health, Labour and Welfare. NDB Open Data 11th release (April 2024-March 2025). https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00017.html

7. Japanese Board of Medical Specialties. Overview of the Japanese specialist system 2025. https://jmsb.or.jp/wp-content/uploads/2026/03/gaiho_2025.pdf

8. Ministry of Health, Labour and Welfare. Patient Survey 2023. https://www.mhlw.go.jp/toukei/saikin/hw/kanja/10syoubyo/

9. Hoffman RM, Wolf AMD, Raoof S, Guerra CE, Church TR, Elkin EB, et al. Multicancer early detection testing: Guidance for primary care discussions with patients. Cancer. 2025;131(7):e35823. https://doi.org/10.1002/cncr.35823

10. Ueberroth BE, Presutti RJ, McGary A, Borad MJ, Agrwal N. Perspectives of primary care providers regarding multicancer early detection panels. Einstein (Sao Paulo). 2024;22:eAO0771. https://doi.org/10.31744/einstein_journal/2024AO0771

11. Wade R, Nevitt S, Liu Y, Harden M, Khouja C, Raine G, et al. Multi-cancer early detection tests for general population screening: a systematic literature review. Health Technol Assess. 2025;29(2). https://doi.org/10.3310/DLMT1294
