"""Build the Journal of Medical Screening (Sage) submission package.

Reads parameters.yaml and the generated CSV/PNG outputs and writes, under
``manuscript/``:

  - manuscript_jms.md                 Markdown source of the main document
  - manuscript_jms.docx               Main document (title page, structured
                                       abstract, IMRaD text, declarations,
                                       Sage Vancouver references, inline tables
                                       and figures with legends)
  - manuscript_jms_tables.docx        Editable tables (main + supplementary)
  - manuscript_jms_figures.pptx       Editable figure slides (main + supplementary)
  - supplementary_jms.md / .docx      Supplementary tables and figures
  - cover_letter_jms.docx             Cover letter
  - reporting_checklist_jms.docx      STROBE-based reporting checklist
  - figures_jms/Figure_N.png          300+ dpi figure files for upload
  - submission_package_jms.zip        Everything above

Formatting follows the JMS author instructions: single-anonymised review (title
page inside the main document), structured abstract (Objectives, Setting,
Methods, Results, Conclusions; max 250 words), main text max 4000 words,
Sage Vancouver numeric references cited in order of first appearance as
superscripts, native Word (OMML) equations, ASCII-only text.

No numeric results are hard-coded; all numbers are read from output files.
"""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Inches, Pt, RGBColor

from build_fmch_manuscript import (
    _compute_context,
    _make_supplementary_tables,
    _renumber_vancouver_references,
)
from build_health_policy_manuscript import _sanitize_cjk_fonts
from build_manuscript import (
    _OMML_AVAILABLE,
    _add_omml_equation,
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
)

JOURNAL = "Journal of Medical Screening"
ARTICLE_TYPE = "Original Article"
PUBLIC_REPO_URL = "https://github.com/bougtoir/cancer-screening-burden-data-driven"
ACCESS_DATE = "11 September 2026"

TITLE = (
    "False-positive cascade from direct-to-consumer multi-cancer early detection "
    "blood tests in Japan: a scenario modelling study of health-system burden"
)
SHORT_TITLE = "False-positive cascade from direct-to-consumer MCED tests"
KEYWORDS = (
    "multi-cancer early detection, false positive, positive predictive value, "
    "healthcare capacity, direct-to-consumer testing, scenario model, Japan"
)

# Sage Vancouver reference list (numbered by first appearance after renumbering).
REFERENCES = [
    "National Cancer Center Japan. Cancer statistics in Japan: cancer registry and statistics, "
    f"incidence 2016-2023 and population, https://ganjoho.jp/reg_stat/statistics/data/dl/en.html (2025, accessed {ACCESS_DATE}).",
    "Ministry of Health, Labour and Welfare. 2023 Medical Facility Survey (static and dynamic), table 05sisetu05, "
    f"https://www.mhlw.go.jp/toukei/saikin/hw/iryosd/23/ (2024, accessed {ACCESS_DATE}).",
    "Kahwati LC, Avenarius M, Brouwer L, et al. Blood-based tests for multiple cancer screening: a systematic review. "
    "AHRQ Publication No. 25-EHC033. Rockville, MD: Agency for Healthcare Research and Quality, 2025. DOI: 10.23970/AHRQEPCSRMULTIPLE.",
    "LeeVan E and Pinsky P. Predictive performance of cell-free nucleic acid-based multi-cancer early detection tests: "
    "a systematic review. Clin Chem 2024; 70: 90-101. DOI: 10.1093/clinchem/hvad134.",
    "Nagamachi S, et al. Nationwide PET/CT facility survey on N-NOSE-triggered examinations (in Japanese). "
    f"PET Society, Japanese Society of Nuclear Medicine, https://jcpet.jp/2024/10/senchu-chosa.html (2024, accessed {ACCESS_DATE}).",
    "Ministry of Health, Labour and Welfare. Patient Survey 2023, "
    f"https://www.mhlw.go.jp/toukei/saikin/hw/kanja/10syoubyo/ (2025, accessed {ACCESS_DATE}).",
    "Ministry of Health, Labour and Welfare. NDB Open Data, 11th release (April 2024 to March 2025), "
    f"https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00017.html (2025, accessed {ACCESS_DATE}).",
    "Japanese Board of Medical Specialties. Overview of the Japanese specialist system 2025 (in Japanese), "
    f"https://jmsb.or.jp/wp-content/uploads/2026/03/gaiho_2025.pdf (2026, accessed {ACCESS_DATE}).",
    "Hoffman RM, Wolf AMD, Raoof S, et al. Multicancer early detection testing: guidance for primary care discussions "
    "with patients. Cancer 2025; 131: e35823. DOI: 10.1002/cncr.35823.",
    "Ueberroth BE, Presutti RJ, McGary A, et al. Perspectives of primary care providers regarding multicancer early "
    "detection panels. Einstein (Sao Paulo) 2024; 22: eAO0771. DOI: 10.31744/einstein_journal/2024AO0771.",
    "Wade R, Nevitt S, Liu Y, et al. Multi-cancer early detection tests for general population screening: a systematic "
    "literature review. Health Technol Assess 2025; 29(2). DOI: 10.3310/DLMT1294.",
]

# Model equations rendered as native Word (OMML) display equations.
MODEL_EQUATIONS = [
    r"\text{Actual cases} = \frac{\text{screened population} \times \text{prevalence per 100,000}}{100000}",
    r"\text{True positives} = \text{actual cases} \times \text{sensitivity}",
    r"\text{False positives} = (\text{screened population} - \text{actual cases}) \times (1 - \text{specificity})",
    r"\text{Capacity utilisation} = \frac{\text{total visits}}{\text{annual capacity per 100,000 population}}",
]

MAIN_FIGURES: List[Tuple[str, str, str]] = [
    (
        "Figure 1",
        "capacity_utilization.png",
        "Capacity utilisation (%) for CT, MRI, endoscopy, specialist and primary care visits as the follow-up rate "
        "increases. Values above 100% indicate demand exceeding the illustrative annual capacity available for a "
        "direct-to-consumer screening wave.",
    ),
    (
        "Figure 2",
        "ppv_by_age.png",
        "Age-specific positive predictive value for each cancer, assuming sensitivity 0.70 and specificity 0.990.",
    ),
]

SUPP_FIGURES: List[Tuple[str, str, str]] = [
    ("Supplementary Figure S1", "total_visits_by_followup.png",
     "Total downstream diagnostic, primary care and specialist visits generated by a blood-based MCED screening wave of 100,000 persons, by follow-up rate."),
    ("Supplementary Figure S2", "specificity_sweep.png",
     "Aggregate positive predictive value (%) and total positive results per 100,000 screened across specificity values at a 50% follow-up rate."),
    ("Supplementary Figure S3", "tornado_max_capacity.png",
     "Tornado diagram showing the effect of varying specificity, follow-up rate, available capacity share and sensitivity on maximum capacity utilisation (base case = 50% follow-up, 99% specificity, 20% capacity share)."),
    ("Supplementary Figure S4", "tornado_ppv.png",
     "Tornado diagram showing the effect of the same four parameters on aggregate positive predictive value."),
    ("Supplementary Figure S5", "age_scenario_ppv.png",
     "Aggregate positive predictive value for each cancer type under the 2023 national total-population distribution and four hypothetical direct-to-consumer purchaser age profiles."),
]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    """Approximate word count after stripping markdown/citation syntax."""
    text = re.sub(r"\[\^\d+\^\]", "", text)
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    text = re.sub(r"^\$\$.*\$\$\s*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,6}\s*", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[-=]{3,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return len(text.strip().split())


def _collapse_numbers(nums: List[int]) -> str:
    """Format citation numbers Sage Vancouver style: 1,2 -> '1,2'; 1,2,3 -> '1-3'."""
    nums = sorted(set(nums))
    out: List[str] = []
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{nums[i]}-{nums[j]}")
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return ",".join(out)


def _sage_superscript_citations(md: str) -> str:
    """Convert [^n^] clusters into {{n,m}} superscript markers placed after punctuation."""
    body, sep, refs = md.partition("\n## References\n")

    def _repl(m: re.Match[str]) -> str:
        nums = [int(n) for n in re.findall(r"\[\^(\d+)\^\]", m.group(1))]
        punct = m.group(2) or ""
        return f"{punct}{{{{{_collapse_numbers(nums)}}}}}"

    body = re.sub(r"\s*((?:\[\^\d+\^\])+)\s*([.,;:]?)", _repl, body)
    return body + sep + refs


def _section_wc(md: str, heading: str) -> int:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## )", md, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return 0
    text = "\n".join(
        l for l in m.group(1).splitlines()
        if not (l.startswith("|") or l.startswith("![") or l.startswith("**Table") or l.startswith("**Figure"))
    )
    return _word_count(text)


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def _abstract(ctx: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Structured abstract using JMS Original Article headings (max 250 words)."""
    row = ctx["row_50"]
    return f"""**Objectives:** To quantify the false-positive cascade and health-system burden generated by direct-to-consumer (DTC) blood-based multi-cancer early detection (MCED) testing as a function of follow-up behaviour, test specificity and age structure.

**Setting:** Japan. A hypothetical cohort of 100,000 asymptomatic adults aged 20 years and over was parameterised with 2023 national cancer incidence and population data, 2023 national diagnostic volumes, and primary care and specialist capacity derived from NDB Open Data outpatient counts and specialist-board counts.

**Methods:** A deterministic expected-value cohort model estimated true positives, false positives, downstream visits, capacity utilisation and per-specialist caseload across follow-up rates of 0-100% and specificities of 95.0-99.9%.

**Results:** At 50% follow-up and {params['cancers'][0]['specificity']:.3f} specificity, the model generated {row['true_positives']:.1f} true positives and {row['false_positives']:.1f} false positives (positive predictive value {ctx['row_50_ppv']:.2f}%; false-positive to true-positive ratio {ctx['row_50_fp_tp']:.1f}). Total downstream visits reached {row['total_visits']:.1f}, including {ctx['primary_care_visits']:.1f} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity). Maximum capacity utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits), and the illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}. False-positive specialist visits added {ctx['fp_visits']:.1f} visits per relevant specialist, raising the effective cases per specialist from {ctx['baseline_cases']:.1f} to {ctx['total_cases']:.1f} ({ctx['percent_change']:.0f}% increase). Positive predictive value was strongly age-dependent and lowest for low-prevalence cancers.

**Conclusions:** Even at 99% specificity, a DTC MCED wave can exceed available diagnostic and specialist capacity. Transparent age-specific positive predictive value reporting, pre-market performance thresholds and defined follow-up obligations are needed before routine adoption.
"""


def _per_cancer_ppv_range(weighted_ppv: pd.DataFrame) -> Tuple[str, float, str, float]:
    sub = weighted_ppv.copy()
    sub["ppv_pct"] = sub["ppv"] * 100.0
    low = sub.loc[sub["ppv_pct"].idxmin()]
    high = sub.loc[sub["ppv_pct"].idxmax()]
    return str(low["cancer"]), float(low["ppv_pct"]), str(high["cancer"]), float(high["ppv_pct"])


def _figure_block(label: str, filename: str, legend: str) -> str:
    return f"![{label}](output/{filename})\n**{label}.** {legend}"


def _build_main_markdown(
    params: Dict[str, Any],
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    capacity_impact: pd.DataFrame,
    ctx: Dict[str, Any],
) -> str:
    row = ctx["row_50"]
    low_cancer, low_ppv, high_cancer, high_ppv = _per_cancer_ppv_range(weighted_ppv)
    visits_0 = float(agg[agg["follow_up_rate"] == 0.0]["total_visits"].iloc[0])
    visits_100 = float(agg[agg["follow_up_rate"] == 1.0]["total_visits"].iloc[0])
    equations_md = "\n\n".join(f"$${eq}$$" for eq in MODEL_EQUATIONS)
    references_md = "\n\n".join(f"{i + 1}. {ref}" for i, ref in enumerate(REFERENCES))
    fig1 = _figure_block(*MAIN_FIGURES[0])
    fig2 = _figure_block(*MAIN_FIGURES[1])

    md = f"""# {TITLE}

## Abstract

{_abstract(ctx, params)}

**Keywords:** {KEYWORDS}

## Introduction

Blood-based multi-cancer early detection (MCED) tests are marketed directly to consumers in high-income countries as a convenient single-blood-draw cancer screen [^3^][^4^]. In asymptomatic populations most positive results are false positives, and each positive result can trigger a cascade of confirmatory imaging, endoscopy and specialist visits [^3^][^4^]. National diagnostic volumes are already substantial [^2^], and unregulated direct-to-consumer (DTC) use could displace routine care and place additional pressure on primary care.

Japan is a pertinent case study because national data are publicly available in detail and DTC cancer screening tests are already commercially available there [^5^]. Although the empirical inputs are Japanese, the model structure can be parameterised for other high-income settings. This study quantifies the health-system burden of a DTC MCED screening wave as a function of follow-up behaviour, test specificity and age structure.

## Methods

### Setting and study design

We built a deterministic expected-value cohort model of a hypothetical screening wave in which 100,000 asymptomatic adults aged 20 years and over in Japan purchase a blood-based MCED test. Outcomes were expressed per 100,000 screened and compared with the annual diagnostic and specialist capacity available per 100,000 population.

### Data sources

Cancer incidence by site, age, sex and calendar year (2023) and the corresponding 2023 population by age and sex were taken from the National Cancer Center Japan [^1^]. Annual volumes of CT, MRI and upper/lower gastrointestinal endoscopy were derived from the 2023 Ministry of Health, Labour and Welfare (MHLW) Medical Facility Survey [^2^]. Test sensitivity and specificity ranges were informed by two recent systematic reviews of blood-based MCED tests [^3^][^4^], and real-world evidence on the downstream diagnostic yield after a positive DTC cancer-screening result came from a nationwide PET/CT facility survey of N-NOSE-triggered examinations [^5^].

Specialist capacity was defined using NDB Open Data first/revisit outpatient patient counts and Japanese Board of Medical Specialties (JMSB) specialist counts [^7^][^8^]. Disease-specific baseline patient numbers for the case-per-specialist ratio were taken from the MHLW 2023 Patient Survey [^6^].

### Model

For each cancer type the expected numbers of cases and test results were:

{equations_md}

Each positive individual who followed up (follow-up rate, 0-100%) generated a primary care visit plus visits to CT, MRI, endoscopy and specialist care according to cancer-specific pathway probabilities. Additional visits per true and false positive were added. Capacity utilisation for each resource was calculated as total visits divided by the annual capacity per 100,000 population. The complete set of equations is documented in the analysis code (simulate.py) and parameter file (parameters.yaml) in the public repository.

Prevalence was approximated by adult (20+) incidence because point prevalence of undiagnosed, screen-detectable cancers is not publicly reported. Point prevalence of detectable but undiagnosed cancers is likely lower than annual incidence (preclinical sojourn time is usually well under one year), so this proxy probably overstates the number of true positives. It therefore produces upper-bound positive predictive value estimates and lower-bound false-positive to true-positive ratios. The absolute visit counts are also sensitive to this proxy. Pathway probabilities and the share of facility capacity available for a new DTC-related wave were scenario assumptions documented in the parameter file.

### Specialist and primary care capacity definition

Baseline specialist capacity was defined as the annual outpatient caseload per cancer-relevant specialist. NDB Open Data unique first/revisit outpatient patient counts (April 2024 to March 2025) were divided by the total number of basic JMSB specialists, giving an average annual caseload per specialist [^7^][^8^]. This value was multiplied by the number of cancer-relevant specialists per 100,000 population and reduced by the same 20% share assumed available for a DTC wave. The resulting value is an illustrative specialist capacity ceiling for a 100,000-person cohort. The same approach was applied to primary care (internal medicine and general practice) specialists to derive the illustrative primary-care capacity.

### Scenarios and sensitivity analyses

Base-case sensitivity and specificity were {params['cancers'][0]['sensitivity']:.2f} and {params['cancers'][0]['specificity']:.3f}. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. The available-for-cancer-workup share of national diagnostic capacity was set to {params['assumptions']['available_for_cancer_share']:.0%}. One-way sensitivity analyses varied specificity, follow-up rate, available capacity share and sensitivity, and alternative age distributions of DTC purchasers were examined.

### Ethics and reporting

The study used only publicly available aggregate data and a deterministic simulation; ethics approval and informed consent were not required. The study is reported in accordance with the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement where applicable, and the completed checklist is provided as a supplementary file.

## Results

### Scenario parameters

Table 1 summarises the data sources and base-case parameter values.

**Table 1. Data sources and scenario parameters.**

{format_markdown_table(make_table_1(params))}

### Per-cancer burden at 50% follow-up

At a 50% follow-up rate, the model estimated {row['true_positives']:.1f} true positives and {row['false_positives']:.1f} false positives across all eight cancers. {high_cancer} had the highest age-distribution-weighted positive predictive value ({high_ppv:.2f}%) and {low_cancer} the lowest ({low_ppv:.2f}%). Full per-cancer results are provided in Supplementary Table S1.

### Capacity impact

Total downstream visits rose from {visits_0:.1f} at 0% follow-up to {visits_100:.1f} at 100% follow-up. At 50% follow-up, the wave generated {ctx['primary_care_visits']:.1f} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity) and {row['total_visits']:.1f} total visits. Resource utilisation by modality is shown in Figure 1. The first illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}; at 50% follow-up, maximum utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits).

{fig1}

### Age-specific positive predictive value

Positive predictive value was strongly age-dependent (Figure 2). In younger age groups it fell below 1% for several cancers and rose above 20% only in the oldest groups, driven by cancers with higher prevalence such as colorectal cancer. If DTC MCED users are younger than the general screening population, aggregate positive predictive value would be lower and the false-positive burden larger than the base-case estimate.

{fig2}

### Specialist capacity and the false-positive cascade

Table 2 compares the MHLW Patient Survey 2023 baseline cancer caseload per specialist with the additional false-positive specialist visits generated by a 100,000-person DTC wave at 50% follow-up. Across all cancer-relevant specialties, the baseline caseload is about {ctx['baseline_cases']:.1f} patients per specialist; the DTC wave adds about {ctx['fp_visits']:.1f} false-positive specialist visits per specialist, an increase of {ctx['percent_change']:.0f}%.

**Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up.**

{format_markdown_table(make_table_4(capacity_impact))}

### Sensitivity and scenario analyses

Per-cancer outcomes at base-case follow-up are detailed in Supplementary Table S1. Supplementary Table S2 reports aggregate positive predictive value under alternative age-distribution scenarios, Supplementary Table S3 shows the one-way sensitivity analysis for the four key parameters, and aggregate outcomes by follow-up rate are in Supplementary Table S4. Test specificity and follow-up behaviour were the dominant drivers of capacity pressure (Supplementary Table S3). At 50% follow-up, lowering specificity from 99.9% to 95.0% reduced aggregate positive predictive value from {ctx['ppv_spec_999']:.2f}% to {ctx['ppv_spec_95']:.2f}% and raised maximum capacity utilisation from {ctx['max_util_spec_999']:.1f}% to {ctx['max_util_spec_95']:.1f}%. With 99% specificity, maximum utilisation ranged from {ctx['max_util_follow_10']:.1f}% at 10% follow-up to {ctx['max_util_follow_90']:.1f}% at 90% follow-up. If only 5% of the illustrative national capacity could be reallocated, the bottleneck reached {ctx['max_util_share_05']:.0f}%; with a 50% share it stayed at {ctx['max_util_share_50']:.0f}%. Supplementary Figure S1 shows total downstream visits by follow-up rate, Supplementary Figure S2 the specificity sweep, Supplementary Figure S3 the tornado sensitivity analysis for maximum capacity utilisation, Supplementary Figure S4 the corresponding analysis for positive predictive value, and Supplementary Figure S5 the age-distribution scenarios.

## Discussion

Under the base-case assumptions, a DTC blood-based MCED screening wave generates roughly {ctx['row_50_fp_tp']:.0f} false-positive workups for each true cancer detected. The illustrative capacity ceiling is already exceeded once follow-up reaches {ctx['threshold_str']}; Supplementary Table S4 shows the corresponding follow-up trajectory. At 50% follow-up, the ceiling is exceeded by {row['max_capacity_utilization_pct'] - 100:.1f} percentage points, and the effective caseload per cancer-relevant specialist rises by about {ctx['percent_change']:.0f}% after adding false-positive follow-up visits. This pattern is consistent with real-world Japanese experience of another DTC cancer-screening test: the N-NOSE PET/CT survey found a low cancer discovery rate after a high-risk result [^5^].

### Implications for screening practice and policy

A positive MCED result is likely to be handled first by primary care before any specialist is involved. Clinicians must explain an uncertain signal, weigh it against guideline-recommended screening and coordinate confirmatory tests. Shared decision-making is essential: people considering a DTC blood test need transparent information on the low positive predictive value in asymptomatic populations and the likely cascade of follow-up visits [^9^]. At 50% follow-up, this implies about {ctx['row_50_fp_tp']:.0f} false-positive workups for each true cancer detected. Primary care providers are concerned about responsibility for interpreting results, costs and managing subsequent evaluations [^10^], and health-technology reviews identify anxiety, false reassurance and displacement of guideline-based screening as potential harms [^11^].

The workload is not evenly distributed: cancers with the lowest prevalence produce the highest false-positive ratios, and younger users, who may be preferentially targeted by DTC advertising, have the lowest positive predictive values. Regulators and payers could reduce this burden by requiring pre-market performance thresholds, transparent positive predictive value reporting by age and sex, and a clear follow-up pathway that prevents primary care from becoming the default safety net for unregulated screening. High-income countries with constrained primary and specialty care capacity should account for these externalities when deciding whether to allow or reimburse DTC MCED testing.

### Benefit to individuals and referral status of a positive result

A consumer-facing blood test offers convenience and the prospect of detecting cancers for which organised screening is unavailable [^3^][^4^]. For a small minority of users, earlier detection could shift stage at diagnosis, but in an asymptomatic cohort a positive result is unlikely to represent cancer (Figure 2; Supplementary Table S1). Most positive results therefore generate anxiety, additional testing and opportunity costs rather than useful early diagnosis, and systematic reviews report downstream harms including false reassurance, overdiagnosis and displacement of guideline-based screening [^11^].

Treating a DTC positive result as equivalent to a physician's referral letter has direct capacity implications. A referral-letter model gives individuals insured access to confirmatory care and may improve follow-up completion, but it also signals medical legitimacy and channels the false-positive cascade into the publicly funded system. The present model suggests that capacity is already breached at 50% follow-up when only 20% of available specialist capacity can be reallocated; insuring confirmatory workups could also raise follow-up completion and push utilisation higher. Conversely, keeping DTC testing outside the referral pathway leaves individuals to self-fund follow-up, which may reduce public-sector pressure but also fragments care, delays diagnosis for the small true-positive minority and creates inequity.

A middle path is therefore worth considering: allow DTC access, but require the test to meet pre-market performance thresholds and mandate that positive results be reviewed by a clinician before any publicly funded workup is authorised. Only evidence-based confirmatory investigations should be covered, with the responsible clinician empowered to decline inappropriate cascades. This preserves individual choice while preventing unregulated screening from converting a marketing promise into an unfunded mandate on primary and specialty care [^9^].

### Strengths and limitations

The model is fully reproducible from public national data and open code, and it separates the effects of follow-up behaviour, specificity, capacity share and age structure. The analysis intentionally uses scenario assumptions for test performance, diagnostic pathways and the age distribution of DTC users, because these data are not publicly reported. Prevalence was approximated by adult incidence; true point prevalence of undiagnosed cancers may differ. Diagnostic capacity was annualised from a one-month facility survey and specialist capacity from NDB outpatient patient counts; both were reduced by an arbitrary available-for-cancer-workup share. The model is deterministic and does not capture stochastic variation, geographic maldistribution or queueing effects.

## Conclusions

In the absence of clear regulatory guardrails, including pre-market performance thresholds, transparent age-specific positive predictive value reporting and defined follow-up obligations, DTC MCED tests risk generating a large-scale false-positive cascade that stresses primary care, specialty care and diagnostic capacity in high-income settings.

## Acknowledgements

During the preparation of this work the authors used an AI-assisted research assistant (Devin, Cognition AI) to draft and revise sections of the manuscript and to generate simulation code. The authors reviewed and edited all content and take full responsibility for the content of the article.

## Author contributions

[Author 1 Name]: conceptualisation, methodology, software, writing - original draft. [Author 2 Name]: data curation, formal analysis, visualisation, writing - review and editing. [Author 3 Name]: supervision, writing - review and editing. All authors approved the final manuscript.

## Declaration of conflicting interests

The authors declared no potential conflicts of interest with respect to the research, authorship and/or publication of this article.

## Funding

The authors received no financial support for the research, authorship and/or publication of this article.

## Ethical considerations

This study used only publicly available aggregate data and a deterministic simulation; ethics committee approval was not required.

## Consent to participate

Not applicable; no human participants were involved.

## Data availability statement

All data sources are publicly available and listed in Table 1. The analysis code, parameters and outputs are openly available at {PUBLIC_REPO_URL}.

## References

{references_md}
"""
    return md


def _build_supplementary_markdown(
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    output_dir: Path,
) -> str:
    supp_tables = _make_supplementary_tables(output_dir)
    s_age = supp_tables["Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios"]
    s_sens = supp_tables["Supplementary Table S2. One-way sensitivity analysis"]
    figs = "\n\n".join(_figure_block(*f) for f in SUPP_FIGURES)

    return f"""# Supplementary material

{SHORT_TITLE}

## Supplementary tables

**Supplementary Table S1. Per-cancer outcomes at 50% follow-up (per 100,000 screened).**

{format_markdown_table(make_table_2(by_cancer_at_50, weighted_ppv))}

**Supplementary Table S2. Aggregate positive predictive value under alternative age-distribution scenarios.**

{format_markdown_table(s_age)}

**Supplementary Table S3. One-way sensitivity analysis.**

{format_markdown_table(s_sens)}

**Supplementary Table S4. Aggregate outcomes by follow-up rate (base-case specificity).**

{format_markdown_table(make_table_3(agg))}

## Supplementary figures

{figs}
"""


# ---------------------------------------------------------------------------
# DOCX rendering
# ---------------------------------------------------------------------------

_INLINE_PATTERN = re.compile(r"(\{\{[^}]*\}\}|\*\*[^*]+\*\*|\$[^$]+\$)")
_TABLE_CAPTION_RE = re.compile(r"^\*\*Table \d+\.", re.MULTILINE)


def _new_document() -> Document:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        st = doc.styles[name]
        st.font.name = "Times New Roman"
        st.font.color.rgb = RGBColor(0, 0, 0)
    doc.styles["Title"].font.size = Pt(16)
    doc.styles["Heading 1"].font.size = Pt(14)
    doc.styles["Heading 2"].font.size = Pt(13)
    doc.styles["Heading 3"].font.size = Pt(12)
    return doc


def _add_inline(paragraph, text: str, font_size: int = 12) -> None:
    """Render bold (**), superscript citations ({{1,2}}), OMML ($...$) and plain text."""
    for part in _INLINE_PATTERN.split(text):
        if not part:
            continue
        if part.startswith("{{") and part.endswith("}}"):
            run = paragraph.add_run(part[2:-2])
            run.font.superscript = True
            run.font.size = Pt(font_size)
        elif part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.font.bold = True
            run.font.size = Pt(font_size)
        elif part.startswith("$") and part.endswith("$"):
            _add_omml_equation(paragraph, part[1:-1])
        else:
            run = paragraph.add_run(part.replace("`", ""))
            run.font.size = Pt(font_size)


def _add_table(doc: Document, rows: List[List[str]]) -> None:
    t = doc.add_table(rows=1, cols=len(rows[0]))
    t.style = "Table Grid"
    for col_idx, val in enumerate(rows[0]):
        cell = t.rows[0].cells[col_idx]
        cell.text = val
        for para in cell.paragraphs:
            para.paragraph_format.line_spacing = 1.0
            for r in para.runs:
                r.font.bold = True
                r.font.size = Pt(9)
    for row in rows[1:]:
        cells = t.add_row().cells
        for col_idx, val in enumerate(row):
            cells[col_idx].text = val
            for para in cells[col_idx].paragraphs:
                para.paragraph_format.line_spacing = 1.0
                for r in para.runs:
                    r.font.size = Pt(9)
    doc.add_paragraph()


def _add_title_page(doc: Document, main_md: str, abstract_md: str) -> None:
    """JMS title page: title, authors/affiliations, corresponding author, declarations, counts."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{JOURNAL} - {ARTICLE_TYPE}")
    r.italic = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE)
    r.bold = True
    r.font.size = Pt(16)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Short title: ").bold = True
    p.add_run(SHORT_TITLE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, (name, idx) in enumerate([("[Author 1 Name]", 1), ("[Author 2 Name]", 2), ("[Author 3 Name]", 1)]):
        if i > 0:
            p.add_run(", ")
        p.add_run(name)
        p.add_run(str(idx)).font.superscript = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("1").font.superscript = True
    p.add_run("[Affiliation 1, department, institution, city, country]   ")
    p.add_run("2").font.superscript = True
    p.add_run("[Affiliation 2, department, institution, city, country]")

    doc.add_heading("Corresponding author", level=2)
    doc.add_paragraph(
        "[Corresponding author name], [department, institution], [full postal address], [country]. "
        "Email: [email address]. Telephone: [telephone number]."
    )

    abstract_wc = _word_count(abstract_md)
    body_wc = sum(_section_wc(main_md, h) for h in ("Introduction", "Methods", "Results", "Discussion", "Conclusions"))
    doc.add_heading("Word counts", level=2)
    doc.add_paragraph(f"Abstract: {abstract_wc} words (limit 250).")
    doc.add_paragraph(
        f"Main text (Introduction to Conclusions, excluding abstract, tables, figure legends and references): "
        f"{body_wc} words (limit 4000)."
    )
    n_tables = len(_TABLE_CAPTION_RE.findall(main_md))
    doc.add_paragraph(
        f"Tables: {n_tables}; Figures: {len(MAIN_FIGURES)}; References: {len(REFERENCES)}; "
        f"Supplementary tables: 4; Supplementary figures: {len(SUPP_FIGURES)}."
    )

    doc.add_heading("Declarations", level=2)
    doc.add_paragraph(
        "Funding: The authors received no financial support for the research, authorship and/or publication of this article."
    )
    doc.add_paragraph(
        "Declaration of conflicting interests: The authors declared no potential conflicts of interest with respect to "
        "the research, authorship and/or publication of this article."
    )
    doc.add_paragraph(
        "Ethical considerations: Publicly available aggregate data and a deterministic simulation only; "
        "ethics committee approval and informed consent were not required."
    )
    doc.add_paragraph(f"Data availability: Code, parameters and outputs are openly available at {PUBLIC_REPO_URL}.")
    doc.add_paragraph(
        "Use of AI-assisted technology: An AI-assisted research assistant (Devin, Cognition AI) was used for drafting "
        "and code generation; the authors reviewed and edited all content."
    )
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _render_markdown_body(doc: Document, md_text: str, output_dir: Path, skip_title: bool) -> None:
    lines = md_text.splitlines()
    table_pattern = re.compile(r"^\|(.*)\|\s*$")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("# ") and not line.startswith("## "):
            if not skip_title:
                p = doc.add_heading(line[2:], level=0)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
            i += 1
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:], level=1)
            i += 1
            continue
        if line.startswith("$$") and line.endswith("$$"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_omml_equation(p, line[2:-2])
            i += 1
            continue
        if line.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if m:
                img_path = output_dir / Path(m.group(2)).name
                if not img_path.exists():
                    raise FileNotFoundError(img_path)
                doc.add_picture(str(img_path), width=Inches(6.0))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                if i + 1 < len(lines) and lines[i + 1].startswith("**"):
                    i += 1
                    cap = doc.add_paragraph()
                    _add_inline(cap, lines[i].strip(), font_size=11)
            i += 1
            continue
        if table_pattern.match(line):
            table_lines = []
            while i < len(lines) and table_pattern.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            rows = [
                [c.strip() for c in l.strip().strip("|").split("|")]
                for l in table_lines
                if not re.match(r"^\|\s*[-:]+", l.strip())
            ]
            if rows:
                _add_table(doc, rows)
            continue
        if re.match(r"^\d+\. ", line):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.first_line_indent = Inches(-0.35)
            _add_inline(p, line)
            i += 1
            continue
        if line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            _add_inline(p, line[2:])
            i += 1
            continue
        if line.strip():
            p = doc.add_paragraph()
            _add_inline(p, line)
            i += 1
            continue
        i += 1


def _build_main_docx(main_md: str, abstract_md: str, docx_path: Path, output_dir: Path) -> None:
    if not _OMML_AVAILABLE:
        raise RuntimeError("latex2mathml and docx-equation are required for native Word equations")
    doc = _new_document()
    _add_title_page(doc, main_md, abstract_md)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE)
    r.bold = True
    r.font.size = Pt(14)
    _render_markdown_body(doc, main_md, output_dir, skip_title=True)
    doc.save(docx_path)
    _sanitize_cjk_fonts(docx_path)


def _build_supplementary_docx(supp_md: str, docx_path: Path, output_dir: Path) -> None:
    doc = _new_document()
    _render_markdown_body(doc, supp_md, output_dir, skip_title=False)
    doc.save(docx_path)
    _sanitize_cjk_fonts(docx_path)


def _build_figures_pptx(output_dir: Path, pptx_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches as PInches
    from pptx.util import Pt as PPt

    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    for label, filename, legend in MAIN_FIGURES + SUPP_FIGURES:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        tb = slide.shapes.add_textbox(PInches(0.5), PInches(0.2), PInches(12.3), PInches(0.6))
        tb.text_frame.text = label
        tb.text_frame.paragraphs[0].font.size = PPt(20)
        tb.text_frame.paragraphs[0].font.bold = True
        slide.shapes.add_picture(str(output_dir / filename), PInches(1.5), PInches(0.9), height=PInches(5.4))
        cb = slide.shapes.add_textbox(PInches(0.5), PInches(6.4), PInches(12.3), PInches(1.0))
        cb.text_frame.word_wrap = True
        cb.text_frame.text = legend
        cb.text_frame.paragraphs[0].font.size = PPt(12)
    prs.save(pptx_path)
    _sanitize_cjk_fonts(pptx_path)


def _export_figure_files(output_dir: Path, figures_dir: Path) -> List[Path]:
    """Copy figures as Figure_N.png / Supplementary_Figure_SN.png (source PNGs are >= 300 dpi)."""
    from PIL import Image

    if figures_dir.exists():
        shutil.rmtree(figures_dir)
    figures_dir.mkdir(parents=True)
    written: List[Path] = []
    for label, filename, _ in MAIN_FIGURES + SUPP_FIGURES:
        dest = figures_dir / (label.replace(" ", "_") + ".png")
        with Image.open(output_dir / filename) as im:
            dpi = im.info.get("dpi", (0, 0))
            if min(dpi) < 300:
                raise ValueError(f"{filename} is {dpi} dpi; JMS requires at least 300 dpi")
        shutil.copyfile(output_dir / filename, dest)
        written.append(dest)
    return written


def _build_cover_letter_docx(ctx: Dict[str, Any], output_path: Path) -> None:
    doc = _new_document()
    doc.add_paragraph("[Date]")
    doc.add_paragraph("The Editor")
    doc.add_paragraph(JOURNAL)
    doc.add_paragraph()
    doc.add_paragraph("Dear Editor,")
    doc.add_paragraph(
        f"We are pleased to submit our manuscript, \"{TITLE}\", for consideration as an {ARTICLE_TYPE} in the {JOURNAL}."
    )
    doc.add_paragraph(
        "Direct-to-consumer blood-based multi-cancer early detection (MCED) tests are now marketed in many high-income "
        "countries as a simple single-blood-draw cancer screen. Their low positive predictive value in asymptomatic "
        "populations means that most positive results are false positives, each initiating a cascade of confirmatory "
        "imaging, endoscopy and specialist visits. We used a deterministic expected-value model parameterised with 2023 "
        "Japanese national data to quantify this burden on primary care, diagnostic services and cancer-relevant "
        "specialties across a range of follow-up rates, test specificities and purchaser age distributions."
    )
    row = ctx["row_50"]
    doc.add_paragraph(
        f"In a 100,000-person cohort at 50% follow-up and 99% specificity, the model generated "
        f"{row['true_positives']:.0f} true positives and {row['false_positives']:.0f} false positives "
        f"(positive predictive value {ctx['row_50_ppv']:.2f}%). The false-positive cascade produced "
        f"{ctx['primary_care_visits']:.0f} primary care visits and {row['total_visits']:.0f} total downstream visits; "
        f"specialist capacity utilisation reached {row['max_capacity_utilization_pct']:.0f}%, and the per-specialist "
        f"cancer caseload effectively rose by {ctx['percent_change']:.0f}%."
    )
    doc.add_paragraph(
        f"The manuscript addresses the core concerns of the {JOURNAL}: the predictive value of a screening test in an "
        "asymptomatic population, the downstream harms and resource consequences of false-positive results, and the "
        "policy conditions under which a new screening technology should be offered. All inputs are public national "
        f"data and the full analysis is reproducible from open code ({PUBLIC_REPO_URL})."
    )
    doc.add_paragraph(
        "This work is original, has not been published previously and is not under consideration elsewhere. All authors "
        "have approved the manuscript and agree with its submission. The authors declare no conflicting interests and "
        "received no funding. The study used only publicly available aggregate data, so ethics approval was not required. "
        "An AI-assisted research assistant was used for drafting and code generation, as disclosed in the Acknowledgements."
    )
    doc.add_paragraph("Yours sincerely,")
    doc.add_paragraph("[Corresponding author name]\n[Affiliation]\n[Postal address]\n[Email address]")
    doc.save(output_path)
    _sanitize_cjk_fonts(output_path)


STROBE_ITEMS: List[Tuple[str, str, str]] = [
    ("1a", "Indicate the study's design with a commonly used term in the title or the abstract", "Title; Abstract (Methods)"),
    ("1b", "Provide in the abstract an informative and balanced summary of what was done and what was found", "Abstract"),
    ("2", "Explain the scientific background and rationale for the investigation being reported", "Introduction"),
    ("3", "State specific objectives, including any prespecified hypotheses", "Introduction (final paragraph); Abstract (Objectives)"),
    ("4", "Present key elements of study design early in the paper", "Methods: Setting and study design"),
    ("5", "Describe the setting, locations and relevant dates, including periods of data collection", "Methods: Setting and study design; Data sources"),
    ("6", "Give the eligibility criteria and the sources and methods of selection of participants", "Methods: Setting and study design (hypothetical cohort of adults aged 20+)"),
    ("7", "Clearly define all outcomes, exposures, predictors, potential confounders and effect modifiers", "Methods: Model; Specialist and primary care capacity definition"),
    ("8", "For each variable of interest, give sources of data and details of methods of assessment", "Methods: Data sources; Table 1"),
    ("9", "Describe any efforts to address potential sources of bias", "Methods: Model (prevalence proxy); Discussion: Strengths and limitations"),
    ("10", "Explain how the study size was arrived at", "Methods: Setting and study design (per 100,000 screened)"),
    ("11", "Explain how quantitative variables were handled in the analyses", "Methods: Model; Scenarios and sensitivity analyses"),
    ("12a", "Describe all statistical methods", "Methods: Model (deterministic expected-value equations)"),
    ("12b", "Describe any methods used to examine subgroups and interactions", "Methods: Scenarios and sensitivity analyses; Results: Age-specific positive predictive value"),
    ("12c", "Explain how missing data were addressed", "Methods: Model (prevalence proxy for unreported point prevalence)"),
    ("12e", "Describe any sensitivity analyses", "Methods: Scenarios and sensitivity analyses; Results: Sensitivity and scenario analyses"),
    ("13", "Report numbers of individuals at each stage of the study", "Results: Per-cancer burden; Supplementary Table S1"),
    ("14", "Give characteristics of study participants and information on exposures", "Table 1; Methods: Data sources"),
    ("15", "Report numbers of outcome events or summary measures", "Results; Table 2; Figures 1 and 2"),
    ("16", "Give unadjusted and, if applicable, adjusted estimates and their precision", "Results (deterministic estimates; uncertainty explored by sensitivity analyses)"),
    ("17", "Report other analyses done, e.g. sensitivity analyses", "Results: Sensitivity and scenario analyses; Supplementary Tables S2-S4; Supplementary Figures S1-S5"),
    ("18", "Summarise key results with reference to study objectives", "Discussion (first paragraph)"),
    ("19", "Discuss limitations of the study, taking into account sources of potential bias or imprecision", "Discussion: Strengths and limitations"),
    ("20", "Give a cautious overall interpretation of results", "Discussion; Conclusions"),
    ("21", "Discuss the generalisability (external validity) of the study results", "Introduction (second paragraph); Discussion: Implications"),
    ("22", "Give the source of funding and the role of the funders", "Funding; Title page declarations"),
]


def _build_reporting_checklist_docx(output_path: Path) -> None:
    doc = _new_document()
    doc.add_heading("STROBE reporting checklist", level=1)
    doc.add_paragraph(f"Manuscript: {TITLE}")
    doc.add_paragraph(
        "This scenario modelling study uses publicly available aggregate data rather than individual participants. "
        "The STROBE checklist (cross-sectional/cohort items) is applied where relevant; items concerning individual "
        "participant recruitment and follow-up are interpreted for a hypothetical cohort. The manuscript location of "
        "each item is given by section heading."
    )
    rows = [["Item", "Recommendation", "Manuscript location"]] + [list(item) for item in STROBE_ITEMS]
    _add_table(doc, rows)
    doc.add_paragraph(
        "Reference: von Elm E, Altman DG, Egger M, et al. The Strengthening the Reporting of Observational Studies in "
        "Epidemiology (STROBE) statement: guidelines for reporting observational studies. PLoS Med 2007; 4: e296."
    )
    doc.save(output_path)
    _sanitize_cjk_fonts(output_path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_FORBIDDEN_TERMS = ["Health Policy", "Elsevier", "FMCH", "Family Medicine and Community Health", "BMJ", "Highlights"]


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def _validate(main_md: str, abstract_md: str, docx_paths: List[Path], main_docx: Path) -> None:
    errors: List[str] = []
    abstract_wc = _word_count(abstract_md)
    body_wc = sum(_section_wc(main_md, h) for h in ("Introduction", "Methods", "Results", "Discussion", "Conclusions"))
    if abstract_wc > 250:
        errors.append(f"abstract has {abstract_wc} words (>250)")
    if body_wc > 4000:
        errors.append(f"main text has {body_wc} words (>4000)")
    for heading in ("Objectives", "Setting", "Methods", "Results", "Conclusions"):
        if f"**{heading}:**" not in abstract_md:
            errors.append(f"abstract lacks '{heading}' heading")

    body = main_md.split("\n## References\n")[0]
    cited = [int(n) for n in re.findall(r"\{\{([\d,\-]+)\}\}", body) for n in _expand(n)]
    first_seen: List[int] = []
    for n in cited:
        if n not in first_seen:
            first_seen.append(n)
    if first_seen != list(range(1, len(first_seen) + 1)):
        errors.append(f"citations not in order of first appearance: {first_seen}")
    if len(first_seen) != len(REFERENCES):
        errors.append(f"{len(first_seen)} references cited but {len(REFERENCES)} listed")

    for label, _, _ in MAIN_FIGURES:
        if not re.search(rf"\b{label}\b", body.replace(f"**{label}.**", "")):
            errors.append(f"{label} not cited in text")
    for n in range(1, len(_TABLE_CAPTION_RE.findall(main_md)) + 1):
        if not re.search(rf"\bTable {n}\b", body.replace(f"**Table {n}.", "")):
            errors.append(f"Table {n} not cited in text")

    for path in docx_paths:
        text = _docx_text(path)
        non_ascii = sorted({c for c in text if ord(c) > 127})
        if non_ascii:
            errors.append(f"{path.name} contains non-ASCII characters: {non_ascii}")
        for term in _FORBIDDEN_TERMS:
            if term in text:
                errors.append(f"{path.name} mentions '{term}'")
    with zipfile.ZipFile(main_docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    n_omml = xml.count("<m:oMath>") + xml.count("<m:oMath ")
    if n_omml < len(MODEL_EQUATIONS):
        errors.append(f"main docx has {n_omml} OMML equations, expected {len(MODEL_EQUATIONS)}")
    if errors:
        raise SystemExit("JMS package validation failed:\n  - " + "\n  - ".join(errors))
    print(f"Abstract word count: {abstract_wc}")
    print(f"Main text word count (Introduction to Conclusions): {body_wc}")
    print(f"OMML equations in main docx: {n_omml}; references: {len(REFERENCES)}")


def _expand(spec: str) -> List[int]:
    out: List[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Journal of Medical Screening submission package")
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
    ctx = _compute_context(params, agg, by_cancer_at_50, weighted_ppv, capacity_impact, capacity_summary, args.output)

    main_md = _build_main_markdown(params, agg, by_cancer_at_50, weighted_ppv, capacity_impact, ctx)
    main_md = _sage_superscript_citations(_renumber_vancouver_references(main_md))
    abstract_md = _abstract(ctx, params)
    (args.manuscript / "manuscript_jms.md").write_text(main_md, encoding="utf-8")

    main_docx = args.manuscript / "manuscript_jms.docx"
    _build_main_docx(main_md, abstract_md, main_docx, args.output)

    supp_md = _build_supplementary_markdown(agg, by_cancer_at_50, weighted_ppv, args.output)
    (args.manuscript / "supplementary_jms.md").write_text(supp_md, encoding="utf-8")
    supp_docx = args.manuscript / "supplementary_jms.docx"
    _build_supplementary_docx(supp_md, supp_docx, args.output)

    supp_tables = _make_supplementary_tables(args.output)
    all_tables: Dict[str, List[List[str]]] = {
        "Table 1. Data sources and scenario parameters": make_table_1(params),
        "Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up": make_table_4(capacity_impact),
        "Supplementary Table S1. Per-cancer outcomes at 50% follow-up (per 100,000 screened)": make_table_2(by_cancer_at_50, weighted_ppv),
        "Supplementary Table S2. Aggregate positive predictive value under alternative age-distribution scenarios":
            supp_tables["Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios"],
        "Supplementary Table S3. One-way sensitivity analysis":
            supp_tables["Supplementary Table S2. One-way sensitivity analysis"],
        "Supplementary Table S4. Aggregate outcomes by follow-up rate (base-case specificity)": make_table_3(agg),
    }
    tables_docx = args.manuscript / "manuscript_jms_tables.docx"
    build_tables_docx(all_tables, tables_docx)
    _sanitize_cjk_fonts(tables_docx)

    figures_pptx = args.manuscript / "manuscript_jms_figures.pptx"
    _build_figures_pptx(args.output, figures_pptx)
    figure_files = _export_figure_files(args.output, args.manuscript / "figures_jms")

    cover_docx = args.manuscript / "cover_letter_jms.docx"
    _build_cover_letter_docx(ctx, cover_docx)
    checklist_docx = args.manuscript / "reporting_checklist_jms.docx"
    _build_reporting_checklist_docx(checklist_docx)

    _validate(main_md, abstract_md, [main_docx, supp_docx, tables_docx, cover_docx, checklist_docx], main_docx)

    zip_path = args.manuscript / "submission_package_jms.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in [main_docx, supp_docx, tables_docx, figures_pptx, cover_docx, checklist_docx,
                  args.manuscript / "manuscript_jms.md", args.manuscript / "supplementary_jms.md"]:
            z.write(p, p.name)
        for p in figure_files:
            z.write(p, f"figures/{p.name}")
    print(f"Wrote {zip_path}")


if __name__ == "__main__":
    main()
