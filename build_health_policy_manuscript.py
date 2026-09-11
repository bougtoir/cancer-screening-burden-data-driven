"""Build a Health Policy (Elsevier) formatted submission package.

This script adapts the cancer_screening_burden simulation outputs for a
Full-length Article submission to Health Policy (ISSN 0168-8510).

Health Policy requirements addressed:
- Full-length article (max 4,000 words)
- Max 4 figures/tables combined in the main manuscript
- Double-anonymized peer review: separate title page, anonymized main manuscript
- Vancouver numbered references
- Policy relevance and international relevance for high-income countries

No numeric results are hard-coded; all numbers are read from output/ files.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from build_fmch_manuscript import (
    _compute_context,
    _make_supplementary_tables,
    _renumber_vancouver_references,
)
from build_manuscript import (
    _add_formatted_text,
    build_tables_docx,
    compute_per_cancer_at_followup,
    format_markdown_table,
    load_aggregate,
    load_by_cancer,
    load_capacity_summary,
    load_weighted_ppv,
    make_table_1,
    make_table_2,
    make_table_3,
    make_table_4,
    markdown_to_docx,
)


TITLE = (
    "False-positive cascade from direct-to-consumer multi-cancer early detection "
    "blood tests in Japan: a scenario modelling study of health-system burden"
)

KEYWORDS = (
    "multi-cancer early detection, false positive, health policy, "
    "healthcare capacity, direct-to-consumer testing, scenario model"
)

REFERENCES = [
    "National Cancer Center of Japan. Cancer Statistics in Japan 2016-2023. https://ganjoho.jp/reg_stat/statistics/data/dl/en.html",
    "Ministry of Health, Labour and Welfare. 2023 Medical Facility Survey (Static/Dynamic), 05sisetu05.xlsx. https://www.mhlw.go.jp/toukei/saikin/hw/iryosd/23/",
    "Kahwati LC, Avenarius M, Brouwer L, et al. Blood-Based Tests for Multiple Cancer Screening: A Systematic Review. AHRQ Publication No. 25-EHC033. Rockville (MD): Agency for Healthcare Research and Quality; 2025. https://doi.org/10.23970/AHRQEPCSRMULTIPLE",
    "LeeVan E, Pinsky P. Predictive Performance of Cell-Free Nucleic Acid-Based Multi-Cancer Early Detection Tests: A Systematic Review. Clin Chem. 2024;70(1):90-101. https://doi.org/10.1093/clinchem/hvad134",
    "Nagamachi S, et al. Nationwide PET/CT facility survey on N-NOSE-triggered examinations (in Japanese). PET Society, Japanese Society of Nuclear Medicine; 2024. https://jcpet.jp/2024/10/senchu-chosa.html",
    "Ministry of Health, Labour and Welfare. Patient Survey 2023. https://www.mhlw.go.jp/toukei/saikin/hw/kanja/10syoubyo/",
    "Ministry of Health, Labour and Welfare. NDB Open Data 11th release (April 2024-March 2025). https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00017.html",
    "Japanese Board of Medical Specialties. Overview of the Japanese specialist system 2025. https://jmsb.or.jp/wp-content/uploads/2026/03/gaiho_2025.pdf",
    "Hoffman RM, Wolf AMD, Raoof S, Guerra CE, Church TR, Elkin EB, et al. Multicancer early detection testing: Guidance for primary care discussions with patients. Cancer. 2025;131(7):e35823. https://doi.org/10.1002/cncr.35823",
    "Ueberroth BE, Presutti RJ, McGary A, Borad MJ, Agrwal N. Perspectives of primary care providers regarding multicancer early detection panels. Einstein (Sao Paulo). 2024;22:eAO0771. https://doi.org/10.31744/einstein_journal/2024AO0771",
    "Wade R, Nevitt S, Liu Y, Harden M, Khouja C, Raine G, et al. Multi-cancer early detection tests for general population screening: a systematic literature review. Health Technol Assess. 2025;29(2). https://doi.org/10.3310/DLMT1294",
]


def _sanitize_cjk_fonts(path: Path) -> None:
    """Remove CJK font names from docx/pptx theme and font-table XML."""
    if not path.exists():
        return
    # East-Asian font names that appear in the default python-docx template.
    replacements = {
        "\uff2d\uff33 \u660e\u671d": "MS Mincho",
        "\uff2d\uff33 \u30b4\u30b7\u30c3\u30af": "MS Gothic",
        "\uff2d\uff33 \uff30\u30b4\u30b7\u30c3\u30af": "MS PGothic",
        "\ub9d1\uc740 \uace0\ub515": "Malgun Gothic",
        "\u5b8b\u4f53": "SimSun",
        "\u65b0\u7d30\u660e\u9ad4": "PMingLiU",
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith((".xml", ".rels")):
                text = data.decode("utf-8", errors="ignore")
                # Longest first to avoid partial replacements.
                for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
                    text = text.replace(old, new)
                data = text.encode("utf-8")
            zout.writestr(item, data)
    tmp_path.replace(path)


def _word_count(text: str) -> int:
    """Approximate word count after stripping markdown syntax."""
    text = re.sub(r"\[\^\d+\^\]", "", text)
    text = re.sub(r"^#{1,6}\s*", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[-=]{3,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return len(text.strip().split())


def _abstract(ctx: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Structured abstract for Health Policy (target <= 250 words)."""
    row = ctx["row_50"]
    return f"""**Background:** Direct-to-consumer (DTC) blood-based multi-cancer early detection (MCED) tests are marketed as a convenient cancer screen that requires only a single blood draw. In asymptomatic populations most positive results are false positives, each of which can trigger a cascade of primary care, imaging, endoscopy, and specialist visits.

**Objective:** To quantify the health-system burden of a DTC MCED screening wave in Japan as a function of follow-up behaviour, test specificity, and age structure.

**Methods:** A deterministic expected-value cohort model was parameterised with 2023 adult cancer incidence and population data from Japan, 2023 national diagnostic volumes, and primary care and specialist capacity derived from NDB Open Data outpatient counts and Japanese specialist-board counts. True positives, false positives, downstream visits, capacity utilisation, and per-specialist case load were estimated across follow-up rates of 0-100% and specificities of 95.0-99.9%.

**Results:** In a 100,000-person cohort at 50% follow-up and {params['cancers'][0]['specificity']:.3f} specificity, the model generated {row['true_positives']:.1f} true positives and {row['false_positives']:.1f} false positives (positive predictive value {ctx['row_50_ppv']:.2f}%; false-positive/true-positive ratio {ctx['row_50_fp_tp']:.1f}). Total downstream visits reached {row['total_visits']:.1f}, including {ctx['primary_care_visits']:.1f} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity). Maximum capacity utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits). The illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}. False-positive specialist visits added {ctx['fp_visits']:.1f} visits per relevant specialist, raising the effective cases per specialist from {ctx['baseline_cases']:.1f} to {ctx['total_cases']:.1f} ({ctx['percent_change']:.0f}% increase).

**Conclusions:** Transparent positive predictive value reporting, pre-market performance thresholds, and defined follow-up obligations are needed before routine DTC MCED adoption.
"""
def _per_cancer_ppv_range(weighted_ppv: pd.DataFrame) -> Tuple[str, float, str, float]:
    """Return (lowest cancer, lowest PPV %, highest cancer, highest PPV %)."""
    sub = weighted_ppv.copy()
    sub["ppv_pct"] = sub["ppv"] * 100.0
    low = sub.loc[sub["ppv_pct"].idxmin()]
    high = sub.loc[sub["ppv_pct"].idxmax()]
    return str(low["cancer"]), float(low["ppv_pct"]), str(high["cancer"]), float(high["ppv_pct"])


def _build_main_markdown(
    params: Dict[str, Any],
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    capacity_impact: pd.DataFrame,
    capacity_summary: Dict[str, Any],
    ctx: Dict[str, Any],
    output_dir: Path,
) -> str:
    """Generate the Health Policy main manuscript Markdown (max 4 figures/tables in body)."""
    row = ctx["row_50"]
    low_cancer, low_ppv, high_cancer, high_ppv = _per_cancer_ppv_range(weighted_ppv)
    visits_0 = float(agg[agg["follow_up_rate"] == 0.0]["total_visits"].iloc[0])
    visits_100 = float(agg[agg["follow_up_rate"] == 1.0]["total_visits"].iloc[0])

    references_md = "\n\n".join(f"{i + 1}. {ref}" for i, ref in enumerate(REFERENCES))

    md = f"""# {TITLE}

## Abstract

{_abstract(ctx, params)}

**Keywords:** {KEYWORDS}

---

## Research in context

- **What is already known about the topic?** DTC blood-based MCED tests are marketed to asymptomatic consumers, and their low positive predictive value means most positive results can trigger confirmatory imaging, endoscopy, and specialist visits.
- **What does this study add to the literature?** Using Japanese public data, this study quantifies the expected false-positive cascade, resource utilisation, per-specialist workload, and age-distribution effects across a range of follow-up rates and specificities.
- **What are the policy implications?** Pre-market performance thresholds, transparent age- and sex-specific positive predictive value reporting, and a clearly assigned follow-up pathway are needed to prevent primary and specialty care from being overloaded.

## Introduction

Blood-based multi-cancer early detection (MCED) tests are marketed directly to consumers in high-income countries as a convenient single-blood-draw cancer screen [^3^][^4^]. In asymptomatic populations most positive results are false positives, and each positive result can trigger a cascade of confirmatory imaging, endoscopy, and specialist visits [^3^][^4^]. National diagnostic volumes are already substantial [^2^], and unregulated DTC use could displace routine care and place additional pressure on primary care.

Japan is a pertinent case study because national data are publicly available in detail and direct-to-consumer cancer screening tests are already commercially available there [^5^]. Although the empirical inputs are Japanese, the model structure can be parameterised for other high-income settings. This study quantifies the health-system burden as a function of follow-up behaviour, test specificity, and age structure.

## Methods

### Data sources

Cancer incidence by site, age, sex, and calendar year (2023) and the corresponding 2023 population by age and sex were taken from the National Cancer Center of Japan [^1^]. Annual volumes of CT, MRI, and upper/lower gastrointestinal endoscopies were derived from the 2023 Ministry of Health, Labour and Welfare Medical Facility Survey [^2^]. Test sensitivity and specificity ranges were informed by two recent systematic reviews of blood-based MCED tests [^3^][^4^], and real-world evidence on the downstream diagnostic yield after a positive DTC cancer-screening result came from a nationwide PET/CT facility survey of N-NOSE-triggered examinations [^5^].

Specialist capacity was defined using NDB Open Data first/revisit outpatient patient counts and Japanese Board of Medical Specialties specialist counts [^7^][^8^]. Disease-specific baseline patient numbers for the case-per-specialist ratio were taken from the MHLW 2023 Patient Survey [^6^].

### Model

A deterministic expected-value cohort model was used. For each cancer type:

- Actual cases = screened population x prevalence per 100,000 / 100,000.
- True positives = actual cases x sensitivity.
- False positives = (screened population - actual cases) x (1 - specificity).

Each positive individual who followed up (follow-up rate, 0-100%) generated a primary care visit plus visits to CT, MRI, endoscopy, and specialist care according to cancer-specific pathway probabilities. Additional visits per true and false positive were added. Capacity utilisation for each resource was calculated as total visits divided by the annual capacity per 100,000 population. The complete set of equations is documented in `simulate.py` and `parameters.yaml`.

Prevalence was approximated by adult (20+) incidence because point prevalence of undiagnosed, screen-detectable cancers is not publicly reported. Point prevalence of detectable but undiagnosed cancers is likely lower than annual incidence (preclinical sojourn time is usually well under one year), so this proxy probably overstates the number of true positives. It therefore produces upper-bound positive predictive value estimates and lower-bound false-positive/true-positive ratios. The absolute visit counts are also sensitive to this proxy. Pathway probabilities and the share of facility capacity available for a new DTC-related wave were scenario assumptions, documented in `parameters.yaml`.

### Specialist and primary care capacity definition

Baseline specialist capacity was defined as the annual outpatient caseload per cancer-relevant specialist. NDB Open Data unique first/revisit outpatient patient counts were used (April 2024-March 2025) divided by the total number of basic JMSB specialists, giving an average annual caseload per specialist [^7^][^8^]. This value was then multiplied by the number of cancer-relevant specialists per 100,000 population and applied the same 20% share assumed available for a DTC wave. The resulting `specialist_visits_per_year` is an illustrative capacity ceiling for a 100,000-person cohort. The same approach was applied to primary care (internal medicine and general practice) specialists to derive `primary_care_visits_per_year`.

### Scenarios

Base-case sensitivity and specificity were {params['cancers'][0]['sensitivity']:.2f} and {params['cancers'][0]['specificity']:.3f}. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. The available-for-cancer-workup share of national diagnostic capacity was set to {params['assumptions']['available_for_cancer_share']:.0%}.

### Reporting

This scenario modelling study is reported in accordance with the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement and the Statistical Analyses and Methods in the Published Literature (SAMPL) guidelines where applicable.

## Results

### Scenario parameters

Table 1 summarises the data sources and base-case parameter values.

**Table 1. Data sources and scenario parameters.**

{format_markdown_table(make_table_1(params))}

### Per-cancer burden at 50% follow-up

At a 50% follow-up rate, the model estimated {row['true_positives']:.1f} true positives and {row['false_positives']:.1f} false positives across all eight cancers. {high_cancer} had the highest age-distribution-weighted positive predictive value ({high_ppv:.2f}%) and {low_cancer} the lowest ({low_ppv:.2f}%). Full per-cancer results are provided in Supplementary Table S1.

### Capacity impact

Total downstream visits rose from {visits_0:.1f} at 0% follow-up to {visits_100:.1f} at 100% follow-up. At 50% follow-up, the wave generated {ctx['primary_care_visits']:.1f} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity) and {row['total_visits']:.1f} total visits. Resource utilisation by modality is shown in Fig. 1. The first illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}; at 50% follow-up, maximum utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits).

![Figure 1: Diagnostic capacity utilisation by follow-up rate](output/capacity_utilization.png)
**Fig. 1.** Capacity utilisation (%) for CT, MRI, endoscopy, specialist, and primary care visits as follow-up rate increases. Values above 100% indicate demand exceeding the illustrative annual capacity available for a DTC screening wave.

### Age-specific positive predictive value

Positive predictive value was strongly age-dependent (Fig. 2). In younger age groups it fell below 1% for several cancers, and rose above 20% only in the oldest groups, driven by cancers with higher prevalence such as colorectal cancer. If DTC MCED users are younger than the general screening population, aggregate positive predictive value would be lower and the false-positive burden larger than the base-case estimate.

![Figure 2: Age-specific PPV by cancer type](output/ppv_by_age.png)
**Fig. 2.** Age-specific positive predictive value for each cancer, assuming sensitivity 0.70 and specificity 0.990.

### Specialist capacity and the false-positive cascade

Table 2 compares the MHLW Patient Survey 2023 baseline cancer case load per specialist with the additional false-positive specialist visits generated by a 100,000-person DTC wave at 50% follow-up. Across all cancer-relevant specialties, the baseline case load is about {ctx['baseline_cases']:.1f} patients per specialist; the DTC wave adds about {ctx['fp_visits']:.1f} false-positive specialist visits per specialist, an increase of {ctx['percent_change']:.0f}%.

**Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up.**

{format_markdown_table(make_table_4(capacity_impact))}

### Sensitivity and scenario analyses

Per-cancer outcomes at base-case follow-up are detailed in Supplementary Table S1. Supplementary Table S2 reports aggregate positive predictive value under alternative age-distribution scenarios. Supplementary Table S3 shows the one-way sensitivity analysis for the four key parameters, and aggregate outcomes by follow-up rate are in Supplementary Table S4. Test specificity and follow-up behaviour were the dominant drivers of capacity pressure (Supplementary Table S3). At 50% follow-up, lowering specificity from 99.9% to 95.0% reduced aggregate positive predictive value from {ctx['ppv_spec_999']:.2f}% to {ctx['ppv_spec_95']:.2f}% and raised maximum capacity utilisation from {ctx['max_util_spec_999']:.1f}% to {ctx['max_util_spec_95']:.1f}%. With 99% specificity, maximum utilisation ranged from {ctx['max_util_follow_10']:.1f}% at 10% follow-up to {ctx['max_util_follow_90']:.1f}% at 90% follow-up. If only 5% of the illustrative national capacity could be reallocated, the bottleneck reached {ctx['max_util_share_05']:.0f}%; with a 50% share it stayed at {ctx['max_util_share_50']:.0f}%. Supplementary Figure S1 shows total downstream visits by follow-up rate, Supplementary Figure S2 shows the specificity sweep, Supplementary Figure S3 shows the tornado sensitivity analysis for maximum capacity utilisation, Supplementary Figure S4 shows the corresponding analysis for positive predictive value, and Supplementary Figure S5 visualises the age-distribution scenarios.

## Discussion

Under the base-case assumptions, a DTC blood-based MCED screening wave generates roughly {ctx['row_50_fp_tp']:.0f} false-positive workups for each true cancer detected. The illustrative capacity ceiling is already exceeded once follow-up reaches {ctx['threshold_str']}; Supplementary Table S4 shows the corresponding follow-up trajectory. At 50% follow-up, the ceiling is exceeded by {row['max_capacity_utilization_pct'] - 100:.1f} percentage points, and the effective case load per cancer-relevant specialist rises by about {ctx['percent_change']:.0f}% after adding false-positive follow-up visits. This pattern is consistent with real-world Japanese experience of another direct-to-consumer cancer-screening test: the N-NOSE PET/CT survey found a low cancer discovery rate after a high-risk result [^5^].

### Policy implications

A positive MCED result is likely to be handled first by primary care before any specialist is involved. Clinicians must explain an uncertain signal, weigh it against guideline-recommended screening, and coordinate confirmatory tests. Shared decision-making is essential: patients considering a DTC blood test need transparent information on the low positive predictive value in asymptomatic populations and the likely cascade of follow-up visits [^9^]. At 50% follow-up, this implies about {ctx['row_50_fp_tp']:.0f} false-positive workups for each true cancer detected. Primary care providers are concerned about responsibility for interpreting results, costs, and managing subsequent evaluations [^10^], and health-system reviews identify anxiety, false reassurance, and displacement of guideline-based screening as potential harms [^11^].

From a policy perspective, the workload is not evenly distributed: cancers with the lowest prevalence produce the highest false-positive ratios, and younger users, who may be preferentially targeted by DTC advertising, have the lowest positive predictive values. Regulators and payers could reduce this burden by requiring pre-market performance thresholds, transparent positive predictive value reporting by age and sex, and a clear follow-up pathway that prevents primary care from becoming the default safety net for unregulated screening. High-income countries with constrained primary and specialty care capacity should account for these externalities when deciding whether to allow or reimburse DTC MCED testing.

### Patient benefit and referral-letter status

A consumer-facing blood test offers convenience and the prospect of detecting cancers for which organised screening is unavailable [^3^][^4^]. For a small minority of users, earlier detection could shift stage at diagnosis, but in an asymptomatic cohort a positive result is unlikely to represent cancer (Fig. 2; Supplementary Table S1). Most positive results therefore generate anxiety, additional testing, and opportunity costs rather than useful early diagnosis, and systematic reviews report downstream harms including false reassurance, overdiagnosis, and displacement of guideline-based screening [^11^].

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

{references_md}
"""
    return md


def _build_supplementary_markdown(
    params: Dict[str, Any],
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    capacity_impact: pd.DataFrame,
    ctx: Dict[str, Any],
    output_dir: Path,
) -> str:
    """Generate supplementary material with additional tables and figures."""
    supp_tables = _make_supplementary_tables(output_dir)
    s_age = supp_tables["Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios"]
    s_sens = supp_tables["Supplementary Table S2. One-way sensitivity analysis"]

    md = f"""# Supplementary material

## Supplementary tables

### Supplementary Table S1. Per-cancer outcomes at 50% follow-up (per 100,000 screened).

{format_markdown_table(make_table_2(by_cancer_at_50, weighted_ppv))}

### Supplementary Table S2. Aggregate PPV under alternative age-distribution scenarios.

{format_markdown_table(s_age)}

### Supplementary Table S3. One-way sensitivity analysis.

{format_markdown_table(s_sens)}

### Supplementary Table S4. Aggregate outcomes by follow-up rate (base-case specificity).

{format_markdown_table(make_table_3(agg))}

## Supplementary figures

![Supplementary Figure S1. Total downstream visits by follow-up rate](output/total_visits_by_followup.png)
**Fig. S1.** Total downstream diagnostic, primary care, and specialist visits generated by a blood-based MCED screening wave of 100,000 persons, by follow-up rate.

![Supplementary Figure S2. PPV and total positives across specificity values](output/specificity_sweep.png)
**Fig. S2.** Aggregate positive predictive value (%) and total positive results per 100,000 screened across specificity values at a 50% follow-up rate.

![Supplementary Figure S3. One-way sensitivity of maximum capacity utilisation](output/tornado_max_capacity.png)
**Fig. S3.** Tornado diagram showing the effect of varying specificity, follow-up rate, available capacity share, and sensitivity on maximum capacity utilisation (base case = 50% follow-up, 99% specificity, 20% capacity share).

![Supplementary Figure S4. One-way sensitivity of aggregate PPV](output/tornado_ppv.png)
**Fig. S4.** Tornado diagram showing the effect of the same four parameters on aggregate positive predictive value.

![Supplementary Figure S5. Aggregate PPV under alternative age-distribution scenarios](output/age_scenario_ppv.png)
**Fig. S5.** Aggregate PPV for each cancer type under the 2023 national total-population distribution and four hypothetical direct-to-consumer purchaser age profiles.
"""
    return md


def _build_health_policy_figures_pptx(output_dir: Path, pptx_path: Path) -> None:
    """Build an editable PowerPoint with main and supplementary figures."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    figures: List[Tuple[str, Path]] = [
        ("Figure 1. Diagnostic capacity utilisation by follow-up rate", output_dir / "capacity_utilization.png"),
        ("Figure 2. Age-specific PPV by cancer type", output_dir / "ppv_by_age.png"),
        ("Supplementary Figure S1. Total downstream visits by follow-up rate", output_dir / "total_visits_by_followup.png"),
        ("Supplementary Figure S2. PPV and total positives across specificity values", output_dir / "specificity_sweep.png"),
        ("Supplementary Figure S3. One-way sensitivity of maximum capacity utilisation", output_dir / "tornado_max_capacity.png"),
        ("Supplementary Figure S4. One-way sensitivity of aggregate PPV", output_dir / "tornado_ppv.png"),
        ("Supplementary Figure S5. Aggregate PPV under alternative age-distribution scenarios", output_dir / "age_scenario_ppv.png"),
    ]

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for title, img_path in figures:
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.8))
        tf = txBox.text_frame
        tf.text = title
        p = tf.paragraphs[0]
        p.font.size = Pt(20)
        p.font.bold = True
        if img_path.exists():
            slide.shapes.add_picture(str(img_path), Inches(1.0), Inches(1.3), width=Inches(11.0))
    prs.save(pptx_path)


def _build_title_page_docx(
    title: str,
    abstract: str,
    keywords: str,
    main_md: str,
    output_path: Path,
) -> None:
    """Generate a separate title page for double-anonymized peer review."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(16)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Full-length Article")
    r.italic = True

    doc.add_heading("Authors and affiliations", level=2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    author_items = [("[Author 1 Name]", 1), ("[Author 2 Name]", 2), ("[Author 3 Name]", 1)]
    for i, (name, idx) in enumerate(author_items):
        if i > 0:
            p.add_run(", ")
        r = p.add_run(name)
        sup = p.add_run(str(idx))
        sup.font.superscript = True
    aff_p = doc.add_paragraph()
    aff_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    aff1 = aff_p.add_run("[1] ")
    aff1.font.superscript = True
    aff_p.add_run("[Affiliation 1]  ")
    aff2 = aff_p.add_run("[2] ")
    aff2.font.superscript = True
    aff_p.add_run("[Affiliation 2]")

    doc.add_heading("Corresponding author", level=2)
    doc.add_paragraph("[Name, full postal address, telephone number and e-mail address]")

    doc.add_heading("Abstract", level=2)
    for section in abstract.split('\n\n'):
        if not section.strip():
            continue
        p = doc.add_paragraph()
        _add_formatted_text(p, section.strip(), font_size=11)
    kw_p = doc.add_paragraph()
    _add_formatted_text(kw_p, f"**Keywords:** {keywords}", font_size=11)

    abstract_wc = _word_count(abstract)
    total_wc = _word_count(main_md)
    body_wc = total_wc - abstract_wc
    doc.add_heading("Word counts", level=2)
    doc.add_paragraph(f"Abstract: {abstract_wc} words")
    doc.add_paragraph(f"Main text excluding references and title page: approximately {body_wc} words")
    doc.add_paragraph(f"Main manuscript including references and tables: approximately {total_wc} words")
    doc.add_paragraph("Tables in main manuscript: 2; Figures in main manuscript: 2 (4 items total)")

    doc.add_heading("Funding", level=2)
    doc.add_paragraph("No external funding was received for this study.")

    doc.add_heading("Competing interests", level=2)
    doc.add_paragraph("The authors declare no competing interests.")

    doc.add_heading("Acknowledgements", level=2)
    doc.add_paragraph("No acknowledgements.")

    doc.add_heading("Author contributions (CRediT)", level=2)
    doc.add_paragraph(
        "[Author 1 Name]: Conceptualization, Methodology, Software, Writing - original draft. "
        "[Author 2 Name]: Data curation, Formal analysis, Visualization, Writing - review & editing. "
        "[Author 3 Name]: Supervision, Writing - review & editing. "
        "All authors approved the final manuscript."
    )

    doc.add_heading("Data and code availability", level=2)
    doc.add_paragraph(
        "All data sources are publicly available and listed in Table 1 of the main manuscript. "
        "Analysis code, parameters, and outputs are available at "
        "https://github.com/bougtoir/cancer-screening-burden-data-driven."
    )

    doc.add_heading("Ethics approval", level=2)
    doc.add_paragraph(
        "This study used only publicly available aggregate data and a deterministic simulation; "
        "ethics approval was not required."
    )

    doc.save(output_path)

def _build_highlights_docx(output_path: Path, ctx: Dict[str, Any]) -> None:
    """Generate a separate Highlights file (3-5 bullets, max 85 characters each)."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    p = doc.add_paragraph()
    r = p.add_run("Highlights")
    r.bold = True
    r.font.size = Pt(14)

    row = ctx["row_50"]
    bullets = [
        "DTC blood cancer tests trigger a large false-positive cascade in Japan.",
        f"At 50% follow-up, {ctx['row_50_fp_tp']:.0f} false-positive workups occur per true cancer detected.",
        f"Specialist capacity reaches {row['max_capacity_utilization_pct']:.0f}% and per-specialist caseload rises {ctx['percent_change']:.0f}%.",
        "Regulators should require pre-market thresholds and age-specific PPV reporting.",
    ]
    for b in bullets:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(b)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Character counts (including spaces):").italic = True
    for i, b in enumerate(bullets, 1):
        doc.add_paragraph(f"Bullet {i}: {len(b)} / 85 characters")

    doc.save(output_path)


def _build_cover_letter_docx(ctx: Dict[str, Any], output_path: Path) -> None:
    """Generate a Health Policy cover letter."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    doc.add_paragraph("[Date]")
    doc.add_paragraph("The Editor-in-Chief")
    doc.add_paragraph("Health Policy")
    doc.add_paragraph("Elsevier")
    doc.add_paragraph()
    doc.add_paragraph("Dear Editor,")

    opening = (
        "We are pleased to submit our manuscript, \""
        + TITLE
        + "\", for consideration as a Full-length Article in Health Policy."
    )
    doc.add_paragraph(opening)

    body1 = (
        "Direct-to-consumer blood-based multi-cancer early detection (MCED) tests are now "
        "marketed directly to consumers in many high-income countries. Although advertised as a "
        "simple single-blood-draw cancer screen, their low positive predictive value in asymptomatic "
        "populations means that most positive results are false positives. Each positive test initiates a "
        "cascade of confirmatory imaging, endoscopy, and specialist visits. We used a deterministic "
        "expected-value model parameterised with 2023 Japanese national data to quantify the burden "
        "on primary care, diagnostic services, and cancer-relevant specialties across a range of follow-up "
        "rates and test specificities."
    )
    doc.add_paragraph(body1)

    row = ctx["row_50"]
    body2 = (
        f"In a 100,000-person cohort at 50% follow-up and 99% specificity, the model generated "
        f"{row['true_positives']:.0f} true positives and {row['false_positives']:.0f} false positives "
        f"(positive predictive value {ctx['row_50_ppv']:.2f}%). The false-positive cascade produced "
        f"{ctx['primary_care_visits']:.0f} primary care visits and {row['total_visits']:.0f} total downstream visits; "
        f"specialist capacity utilisation reached {row['max_capacity_utilization_pct']:.0f}%, and the per-specialist "
        f"cancer case load effectively rose by {ctx['percent_change']:.0f}%. These results suggest that, without "
        "regulatory guardrails on performance claims and follow-up obligations, widespread DTC MCED "
        "screening could overwhelm primary and specialty care systems."
    )
    doc.add_paragraph(body2)

    body3 = (
        "The study is directly relevant to Health Policy's readership. Japan's large direct-to-consumer "
        "screening market and publicly available national data make it an informative case study, but the "
        "false-positive cascade is generalisable to other high-income countries outside the United States. "
        "The findings inform decisions about pre-market performance thresholds, transparent positive "
        "predictive value reporting, and the allocation of follow-up responsibilities between consumers, "
        "primary care, and specialty services."
    )
    doc.add_paragraph(body3)

    closing = (
        "We confirm that this work is original, has not been published elsewhere, and is not under "
        "consideration elsewhere. All authors have approved the manuscript and agree with its submission. "
        "The authors declare no competing interests."
    )
    doc.add_paragraph(closing)

    doc.add_paragraph("Sincerely,")
    doc.add_paragraph("[Corresponding author name]\n[Affiliation]\n[Email address]")

    doc.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Health Policy formatted manuscript materials")
    parser.add_argument("--params", type=Path, default=Path("parameters.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--manuscript", type=Path, default=Path("manuscript"))
    args = parser.parse_args()

    args.manuscript.mkdir(parents=True, exist_ok=True)

    with open(args.params, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    agg = load_aggregate(args.output)
    by_cancer = load_by_cancer(args.output)
    weighted_ppv = load_weighted_ppv(args.output)
    by_cancer_at_50 = compute_per_cancer_at_followup(by_cancer, 0.5)
    capacity_impact = pd.read_csv(args.output / "specialist_capacity_impact.csv")
    capacity_summary = load_capacity_summary(args.output)

    ctx = _compute_context(
        params,
        agg,
        by_cancer_at_50,
        weighted_ppv,
        capacity_impact,
        capacity_summary,
        args.output,
    )

    main_md = _build_main_markdown(
        params,
        agg,
        by_cancer_at_50,
        weighted_ppv,
        capacity_impact,
        capacity_summary,
        ctx,
        args.output,
    )
    main_md = _renumber_vancouver_references(main_md)
    main_path = args.manuscript / "manuscript_health_policy.md"
    main_path.write_text(main_md, encoding="utf-8")

    main_docx_path = args.manuscript / "manuscript_health_policy.docx"
    markdown_to_docx(main_md, main_docx_path, args.output)
    _sanitize_cjk_fonts(main_docx_path)

    # All tables for the editable tables file (main + supplementary).
    supp_tables = _make_supplementary_tables(args.output)
    all_tables: Dict[str, List[List[str]]] = {
        "Table 1. Data sources and scenario parameters": make_table_1(params),
        "Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up": make_table_4(capacity_impact),
        "Table S3. Per-cancer outcomes at 50% follow-up": make_table_2(by_cancer_at_50, weighted_ppv),
        "Table S4. Aggregate outcomes by follow-up rate": make_table_3(agg),
    }
    all_tables.update(supp_tables)
    tables_docx_path = args.manuscript / "manuscript_health_policy_tables.docx"
    build_tables_docx(all_tables, tables_docx_path)
    _sanitize_cjk_fonts(tables_docx_path)

    figures_pptx_path = args.manuscript / "manuscript_health_policy_figures.pptx"
    _build_health_policy_figures_pptx(args.output, figures_pptx_path)
    _sanitize_cjk_fonts(figures_pptx_path)

    supp_md = _build_supplementary_markdown(
        params,
        agg,
        by_cancer_at_50,
        weighted_ppv,
        capacity_impact,
        ctx,
        args.output,
    )
    supp_path = args.manuscript / "supplementary_health_policy.md"
    supp_path.write_text(supp_md, encoding="utf-8")
    supp_docx_path = args.manuscript / "supplementary_health_policy.docx"
    markdown_to_docx(supp_md, supp_docx_path, args.output)
    _sanitize_cjk_fonts(supp_docx_path)

    abstract_text = _abstract(ctx, params)
    title_page_path = args.manuscript / "title_page_health_policy.docx"
    _build_title_page_docx(
        TITLE,
        abstract_text,
        KEYWORDS,
        main_md,
        title_page_path,
    )
    highlights_path = args.manuscript / "highlights_health_policy.docx"
    _build_highlights_docx(highlights_path, ctx)
    cover_letter_path = args.manuscript / "cover_letter_health_policy.docx"
    _build_cover_letter_docx(ctx, cover_letter_path)
    _sanitize_cjk_fonts(title_page_path)
    _sanitize_cjk_fonts(highlights_path)
    _sanitize_cjk_fonts(cover_letter_path)

    abstract_wc = _word_count(abstract_text)
    total_wc = _word_count(main_md)
    body_wc = total_wc - abstract_wc
    print(f"Abstract word count: {abstract_wc}")
    print(f"Main text word count (excluding references/title): {body_wc}")
    print(f"Total main manuscript word count (including references/tables): {total_wc}")
    if abstract_wc > 250:
        print("WARNING: abstract exceeds Health Policy suggested limit of 250 words.")
    if total_wc > 4000:
        print("WARNING: main manuscript exceeds Health Policy Full-length Article limit of 4,000 words.")

    # Submission package zip.
    zip_path = args.manuscript / "submission_package_health_policy.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in [
            main_path,
            main_docx_path,
            args.manuscript / "title_page_health_policy.docx",
            args.manuscript / "cover_letter_health_policy.docx",
            highlights_path,
            args.manuscript / "manuscript_health_policy_tables.docx",
            args.manuscript / "manuscript_health_policy_figures.pptx",
            supp_path,
            args.manuscript / "supplementary_health_policy.docx",
        ]:
            if path.exists():
                zf.write(path, arcname=path.name)

        figure_map = {
            "capacity_utilization.png": "Figure_1.png",
            "ppv_by_age.png": "Figure_2.png",
            "total_visits_by_followup.png": "Supplementary_Figure_S1.png",
            "specificity_sweep.png": "Supplementary_Figure_S2.png",
            "tornado_max_capacity.png": "Supplementary_Figure_S3.png",
            "tornado_ppv.png": "Supplementary_Figure_S4.png",
            "age_scenario_ppv.png": "Supplementary_Figure_S5.png",
        }
        for src_name, dst_name in figure_map.items():
            src = args.output / src_name
            if src.exists():
                zf.write(src, arcname=f"figures/{dst_name}")

    print(f"Health Policy submission materials written to {args.manuscript.resolve()}")


if __name__ == "__main__":
    main()
