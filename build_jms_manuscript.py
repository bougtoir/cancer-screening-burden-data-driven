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
  - figures_jms/Figure_N.png/.tif     300+ dpi figure files for upload (PNG and LZW TIFF)
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
    "Nagamachi S, Jinnouchi S, Tashiro K, et al. Multicentre survey of PET cancer screening and nematode (N-NOSE) testing "
    "(in Japanese). Rinsho Kaku Igaku 2024; 57(5). Summary: PET Nuclear Medicine Subcommittee, Japanese Society of Nuclear Medicine, "
    f"https://jcpet.jp/2024/10/senchu-chosa.html (2024, accessed {ACCESS_DATE}).",
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
    "literature review. Health Technol Assess 2025; 29(2): 1-105. DOI: 10.3310/DLMT1294.",
    "Wilson JMG and Jungner G. Principles and practice of screening for disease. Public Health Papers No. 34. "
    "Geneva: World Health Organization, 1968.",
    "Schrag D, Beer TM, McDonnell CH, et al. Blood-based tests for multicancer early detection (PATHFINDER): "
    "a prospective cohort study. Lancet 2023; 402: 1251-1260. DOI: 10.1016/S0140-6736(23)01700-2.",
    "Caro JJ, Briggs AH, Siebert U, et al. Modeling good research practices - overview: a report of the ISPOR-SMDM "
    "Modeling Good Research Practices Task Force-1. Med Decis Making 2012; 32: 667-677. DOI: 10.1177/0272989X12454577.",
]

# Reference-list index (1-based, pre-renumbering) used for Table 1 source citations.
_REF_INCIDENCE, _REF_FACILITY, _REF_AHRQ, _REF_NDB, _REF_JMSB = 1, 2, 3, 7, 8

# Model equations rendered as native Word (OMML) display equations.
MODEL_EQUATIONS = [
    r"\text{Actual cases} = \frac{\text{screened population} \times \text{prevalence per 100,000}}{100000}",
    r"\text{True positives} = \text{actual cases} \times \text{sensitivity}",
    r"\text{False positives} = (\text{screened population} - \text{actual cases}) \times (1 - \text{specificity})",
    r"\text{Capacity utilisation} = \frac{\text{total visits}}{\text{annual capacity per 100,000 population}}",
]

JMS_FIGURE_SUBDIR = "jms_figures"

MAIN_FIGURES: List[Tuple[str, str, str]] = [
    (
        "Figure 1",
        "capacity_utilisation.png",
        "Capacity utilisation (%) for CT, MRI, endoscopy, specialist and primary care visits as the follow-up rate "
        "increases. Values above 100% indicate demand exceeding the illustrative annual capacity available for a "
        "direct-to-consumer screening wave.",
    ),
    (
        "Figure 2",
        "ppv_by_age.png",
        "Age-specific positive predictive value for each cancer among adults aged 20 years and over, assuming "
        "sensitivity 0.70 and specificity 0.990 and using 2023 age-specific incidence as the prevalence proxy.",
    ),
]

SUPP_FIGURES: List[Tuple[str, str, str]] = [
    ("Supplementary Figure S1", "total_visits_by_followup.png",
     "Total downstream diagnostic, primary care and specialist visits generated by a blood-based MCED screening wave of 100,000 persons, by follow-up rate."),
    ("Supplementary Figure S2", "specificity_sweep.png",
     "False positives and total downstream visits per 100,000 screened across test specificity values (0.950-0.999) at a 50% follow-up rate."),
    ("Supplementary Figure S3", "tornado_max_capacity.png",
     "Tornado diagram showing the effect of varying specificity, follow-up rate, available capacity share and sensitivity on maximum capacity utilisation (base case = 50% follow-up, 0.990 specificity, 0.70 sensitivity, 20% capacity share). Parameters are ordered by the width of their effect."),
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
        trail = " " if m.group(3) else ""
        return f"{punct}{{{{{_collapse_numbers(nums)}}}}}{trail}"

    body = re.sub(r"\s*((?:\[\^\d+\^\])+)(?:\s*([.,;:]))?([ \t]*)", _repl, body)
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

**Results:** At 50% follow-up and {params['cancers'][0]['specificity']:.3f} specificity, the model estimated {_n(row['true_positives'])} true positives and {_n(row['false_positives'])} false positives per 100,000 screened (positive predictive value {ctx['row_50_ppv']:.2f}%; {ctx['row_50_fp_tp']:.1f} false positives per true positive). Total downstream visits reached {_n(row['total_visits'])}, including {_n(ctx['primary_care_visits'])} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity). Maximum capacity utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits), and the illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}. False-positive specialist visits added {ctx['fp_visits']:.1f} visits per relevant specialist, raising the effective cases per specialist from {ctx['baseline_cases']:.1f} to {ctx['total_cases']:.1f} ({ctx['percent_change']:.0f}% increase). Positive predictive value was strongly age-dependent and lowest for low-prevalence cancers; capacity results were insensitive to a two-fold change in prevalence.

**Conclusions:** In this scenario model, even at 99% specificity a DTC MCED wave can exceed available diagnostic and specialist capacity. Transparent age-specific positive predictive value reporting, pre-market performance thresholds and defined follow-up obligations are needed before routine adoption.
"""


def _per_cancer_ppv_range(weighted_ppv: pd.DataFrame) -> Tuple[str, float, str, float]:
    sub = weighted_ppv.copy()
    sub["ppv_pct"] = sub["ppv"] * 100.0
    low = sub.loc[sub["ppv_pct"].idxmin()]
    high = sub.loc[sub["ppv_pct"].idxmax()]
    return str(low["cancer"]), float(low["ppv_pct"]), str(high["cancer"]), float(high["ppv_pct"])


def _figure_block(label: str, filename: str, legend: str) -> str:
    return f"![{label}](output/{JMS_FIGURE_SUBDIR}/{filename})\n**{label}.** {legend}"


def _n(value: float, decimals: int = 1) -> str:
    """Thousands-separated number for prose (expected values keep one decimal)."""
    return f"{value:,.{decimals}f}"


def _short_ref(ref_index: int, label: str) -> str:
    return f"{label} [^{ref_index}^]"


def make_table_1_jms(params: Dict[str, Any]) -> List[List[str]]:
    """Table 1 with sources given as short labels plus reference numbers."""
    cap = params["capacity"]
    share = params["assumptions"]["available_for_cancer_share"]
    facility = _short_ref(_REF_FACILITY, "MHLW 2023 Medical Facility Survey; annualised national volume per 100,000 population")
    capacity_note = (
        f"; {share:.0%} share assumed available for new cancer work-ups (scenario assumption)"
    )
    table = [
        ["Parameter", "Base-case value", "Source / assumption"],
        ["Screened population", f"{params['simulation']['screened_population']:,}", "Hypothetical single screening wave of adults aged 20+ years"],
        ["Test sensitivity (all cancers)", f"{params['cancers'][0]['sensitivity']:.2f}", _short_ref(_REF_AHRQ, "Systematic review of blood-based MCED tests") + "; scenario value within reported range"],
        ["Test specificity (all cancers)", f"{params['cancers'][0]['specificity']:.3f}", _short_ref(_REF_AHRQ, "Systematic review of blood-based MCED tests") + "; scenario value within reported range"],
        ["Follow-up rate after a positive result", "50% (varied 0-100%)", "Scenario assumption"],
        ["CT capacity per 100,000 per year", f"{cap['ct_exams_per_year']:,.0f}", facility + capacity_note],
        ["MRI capacity per 100,000 per year", f"{cap['mri_exams_per_year']:,.0f}", facility + capacity_note],
        ["Endoscopy capacity per 100,000 per year", f"{cap['endoscopy_exams_per_year']:,.0f}", facility + capacity_note],
        ["Specialist capacity per 100,000 per year", f"{cap['specialist_visits_per_year']:,.0f}",
         _short_ref(_REF_NDB, "NDB Open Data first/revisit outpatient counts") + " divided by " + _short_ref(_REF_JMSB, "JMSB cancer-relevant specialist counts") + capacity_note],
        ["Primary care capacity per 100,000 per year", f"{cap.get('primary_care_visits_per_year', 0.0):,.0f}",
         _short_ref(_REF_NDB, "NDB Open Data first/revisit outpatient counts") + " divided by " + _short_ref(_REF_JMSB, "JMSB internal medicine and general practice specialist counts") + capacity_note],
    ]
    for cancer in params["cancers"]:
        table.append([
            f"{cancer['name']} prevalence proxy (per 100,000)",
            f"{cancer['prevalence_per_100k']:.1f}",
            _short_ref(_REF_INCIDENCE, "2023 adult (20+) incidence, National Cancer Center Japan"),
        ])
    return table


def make_table_2_jms(capacity_impact: pd.DataFrame) -> List[List[str]]:
    """Table 4 of the generic builder with all numeric columns at one decimal place."""
    rows = make_table_4(capacity_impact)
    for r in rows[1:]:
        r[3] = f"{float(r[3]):.1f}"
    return rows


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
    visits_100 = float(agg[agg["follow_up_rate"] == 1.0]["total_visits"].iloc[0])
    pc_util_100 = float(agg[agg["follow_up_rate"] == 1.0]["primary_care_visits_utilization_pct"].iloc[0])
    pc_over = agg[agg["primary_care_visits_utilization_pct"] > 100.0]
    pc_ceiling = (
        f"exceeded at a follow-up rate of {float(pc_over['follow_up_rate'].iloc[0]):.0%}" if len(pc_over)
        else f"not exceeded even at 100% follow-up ({pc_util_100:.1f}% utilisation)"
    )
    prev = ctx["prevalence_sens"]
    p_lo = prev[prev["prevalence_multiplier"] == prev["prevalence_multiplier"].min()].iloc[0]
    p_hi = prev[prev["prevalence_multiplier"] == prev["prevalence_multiplier"].max()].iloc[0]
    util_by_mult = prev.set_index("prevalence_multiplier")["max_capacity_utilization_pct"]
    two_fold_pp = max(
        abs(util_by_mult[1.0] - util_by_mult[0.5]),
        abs(util_by_mult[2.0] - util_by_mult[1.0]),
    )
    age_ppv = ctx["age_ppv"].copy()
    age_ppv["age_start"] = age_ppv["age_group"].str.extract(r"^(\d+)").astype(int)
    age_ppv["ppv_pct"] = age_ppv["ppv"] * 100
    adult = age_ppv[age_ppv["age_start"] >= 20]
    under40_max = adult[adult["age_start"] < 40]["ppv_pct"].max()
    over20 = adult[adult["ppv_pct"] > 20].sort_values("age_start")
    over20_age = int(over20["age_start"].iloc[0])
    over20_cancers = " and ".join(sorted(over20["cancer"].str.lower().unique()))
    equations_md = "\n\n".join(f"$${eq}$$" for eq in MODEL_EQUATIONS)
    references_md = "\n\n".join(f"{i + 1}. {ref}" for i, ref in enumerate(REFERENCES))
    fig1 = _figure_block(*MAIN_FIGURES[0])
    fig2 = _figure_block(*MAIN_FIGURES[1])

    md = f"""# {TITLE}

## Abstract

{_abstract(ctx, params)}

**Keywords:** {KEYWORDS}

## Introduction

Blood-based multi-cancer early detection (MCED) tests are marketed directly to consumers in high-income countries as a convenient single-blood-draw cancer screen [^3^][^4^]. In asymptomatic populations most positive results are false positives, and each positive result can trigger a cascade of confirmatory imaging, endoscopy and specialist visits [^3^][^4^]. Classical screening principles require that facilities for diagnosis and treatment be available before a screening programme is offered [^12^], yet direct-to-consumer (DTC) testing bypasses programme governance entirely: the purchaser, not the health system, decides who is screened, and the health system inherits the confirmatory work-up. National diagnostic volumes are already substantial [^2^], so unregulated DTC use could displace routine care and place additional pressure on primary care.

Prospective MCED studies have so far enrolled older, risk-enriched populations within organised follow-up pathways [^13^], and the capacity consequences of unselected consumer uptake have not been quantified. Japan is a useful setting for this question because national incidence, population, diagnostic-volume and workforce data are publicly available in detail and DTC cancer screening tests are already commercially available there [^5^]. Although the empirical inputs are Japanese, the model structure can be parameterised for other high-income settings. This study quantifies the health-system burden of a DTC MCED screening wave as a function of follow-up behaviour, test specificity and age structure, and identifies the follow-up rate at which illustrative diagnostic and specialist capacity is exceeded.

## Methods

### Setting and study design

We built a deterministic expected-value cohort model of a hypothetical screening wave in which 100,000 asymptomatic adults aged 20 years and over in Japan purchase a blood-based MCED test. Outcomes were expressed per 100,000 screened and compared with the annual diagnostic and specialist capacity available per 100,000 population.

### Data sources

Cancer incidence by site, age, sex and calendar year (2023) and the corresponding 2023 population by age and sex were taken from the National Cancer Center Japan [^1^]. Annual volumes of CT, MRI and upper/lower gastrointestinal endoscopy were derived from the 2023 Ministry of Health, Labour and Welfare (MHLW) Medical Facility Survey [^2^]. Test sensitivity and specificity ranges were informed by two recent systematic reviews of blood-based MCED tests [^3^][^4^], and real-world evidence on the downstream diagnostic yield after a positive DTC cancer-screening result came from a nationwide PET/CT facility survey of N-NOSE-triggered examinations [^5^].

Specialist capacity was defined using NDB Open Data first/revisit outpatient patient counts and Japanese Board of Medical Specialties (JMSB) specialist counts [^7^][^8^]. Disease-specific baseline patient numbers for the case-per-specialist ratio were taken from the MHLW 2023 Patient Survey [^6^].

### Model

For each cancer type the expected numbers of cases and test results were:

{equations_md}

Sensitivity and specificity were applied per cancer, so each cancer contributed its own true and false positives and the aggregate counts are sums across the eight cancers; a single MCED assay reporting one overall result at the same specificity would generate roughly one-eighth as many false-positive individuals, each still requiring a multi-site work-up. Each positive result that was followed up (follow-up rate, 0-100%, applied equally to true and false positives) generated a primary care visit plus visits to CT, MRI, endoscopy and specialist care according to cancer-specific pathway probabilities. Additional visits per true and false positive were added. Capacity utilisation for each resource was calculated as total visits divided by the annual capacity per 100,000 population. The complete set of equations is documented in the analysis code (simulate.py) and parameter file (parameters.yaml) in the public repository.

Prevalence was approximated by adult (20+) incidence because point prevalence of undiagnosed, screen-detectable cancers is not publicly reported. Point prevalence of detectable but undiagnosed cancers is likely lower than annual incidence (preclinical sojourn time is usually well under one year), so this proxy probably overstates the number of true positives. It therefore produces upper-bound positive predictive value estimates and lower-bound false-positive to true-positive ratios. Because the direction of this bias is known but its size is not, the prevalence proxy was scaled from 0.25 to 2.0 times the incidence-based value in a dedicated sensitivity analysis. Pathway probabilities and the share of facility capacity available for a new DTC-related wave were scenario assumptions documented in the parameter file.

### Specialist and primary care capacity definition

Baseline specialist capacity was defined as the annual outpatient caseload per cancer-relevant specialist. NDB Open Data unique first/revisit outpatient patient counts (April 2024 to March 2025) were divided by the total number of basic JMSB specialists, giving an average annual caseload per specialist [^7^][^8^]. This value was multiplied by the number of cancer-relevant specialists per 100,000 population and reduced by the same 20% share assumed available for a DTC wave. The resulting value is an illustrative specialist capacity ceiling for a 100,000-person cohort. The same approach was applied to primary care (internal medicine and general practice) specialists to derive the illustrative primary-care capacity.

### Scenarios and sensitivity analyses

Base-case sensitivity and specificity were {params['cancers'][0]['sensitivity']:.2f} and {params['cancers'][0]['specificity']:.3f}. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. The available-for-cancer-workup share of national diagnostic capacity was set to {params['assumptions']['available_for_cancer_share']:.0%}. One-way sensitivity analyses varied specificity, follow-up rate, available capacity share and sensitivity, and alternative age distributions of DTC purchasers were examined. The model is deterministic; results are expected values and no confidence intervals are reported, with parameter uncertainty explored through these scenario and one-way analyses.

### Ethics and reporting

The study used only publicly available aggregate data and a deterministic simulation; ethics approval and informed consent were not required. Model structure, parameter sourcing and transparency follow the ISPOR-SMDM modelling good research practices [^14^]. Because no dedicated EQUATOR checklist exists for deterministic scenario models, the study is reported in accordance with the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement where applicable, and the completed checklist is provided as a supplementary file.

## Results

### Scenario parameters

Table 1 summarises the data sources and base-case parameter values, distinguishing empirical inputs from scenario assumptions.

**Table 1. Data sources and scenario parameters.**

{format_markdown_table(make_table_1_jms(params))}

### Per-cancer burden at 50% follow-up

At a 50% follow-up rate, the model estimated {_n(row['true_positives'])} true positives and {_n(row['false_positives'])} false positives across all eight cancers (aggregate positive predictive value {ctx['row_50_ppv']:.2f}%; {ctx['row_50_fp_tp']:.1f} false positives per true positive). {high_cancer} cancer had the highest age-distribution-weighted positive predictive value ({high_ppv:.2f}%) and {low_cancer.lower()} cancer the lowest ({low_ppv:.2f}%). Full per-cancer results are provided in Supplementary Table S1.

### Capacity impact

Total downstream visits rose linearly with follow-up to {_n(visits_100)} at 100% follow-up. At 50% follow-up, the wave generated {_n(ctx['primary_care_visits'])} primary care visits ({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity) and {_n(row['total_visits'])} total visits. Resource utilisation by modality is shown in Figure 1. The first illustrative capacity ceiling was exceeded at a follow-up rate of {ctx['threshold_str']}; at 50% follow-up, maximum utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits), whereas CT, MRI and endoscopy remained below their ceilings and the illustrative primary-care ceiling was {pc_ceiling}.

{fig1}

### Age-specific positive predictive value

Positive predictive value was strongly age-dependent (Figure 2). Below 40 years of age it was under {under40_max:.1f}% for every cancer, and it exceeded 20% only from {over20_age} years onwards, for {over20_cancers} cancer. If DTC MCED users are younger than the general screening population, aggregate positive predictive value would be lower and the false-positive burden larger than the base-case estimate.

{fig2}

### Specialist capacity and the false-positive cascade

Table 2 compares the MHLW Patient Survey 2023 baseline cancer caseload per specialist with the additional false-positive specialist visits generated by a 100,000-person DTC wave at 50% follow-up. Across all cancer-relevant specialties, the baseline caseload is about {ctx['baseline_cases']:.1f} patients per specialist; the DTC wave adds about {ctx['fp_visits']:.1f} false-positive specialist visits per specialist, an increase of {ctx['percent_change']:.0f}%. Relative increases are largest for specialties whose baseline cancer caseload per specialist is small (hepatology, gastroenterology for pancreatic cancer, and obstetrics and gynaecology), where the denominator is a few cases per specialist per year.

**Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up.**

{format_markdown_table(make_table_2_jms(capacity_impact))}

### Sensitivity and scenario analyses

Per-cancer outcomes at base-case follow-up are detailed in Supplementary Table S1. Supplementary Table S2 reports aggregate positive predictive value under alternative age-distribution scenarios, Supplementary Table S3 shows the one-way sensitivity analysis for the four key parameters, and aggregate outcomes by follow-up rate are in Supplementary Table S4. Test specificity and follow-up behaviour were the dominant drivers of capacity pressure (Supplementary Table S3). At 50% follow-up, lowering specificity from 99.9% to 95.0% reduced aggregate positive predictive value from {ctx['ppv_spec_999']:.2f}% to {ctx['ppv_spec_95']:.2f}% and raised maximum capacity utilisation from {ctx['max_util_spec_999']:.1f}% to {ctx['max_util_spec_95']:.1f}%. With 99% specificity, maximum utilisation ranged from {ctx['max_util_follow_10']:.1f}% at 10% follow-up to {ctx['max_util_follow_90']:.1f}% at 90% follow-up. If only 5% of the illustrative national capacity could be reallocated, the bottleneck reached {ctx['max_util_share_05']:.0f}%; with a 50% share it stayed at {ctx['max_util_share_50']:.0f}%. Scaling the incidence-based prevalence proxy from {p_lo['prevalence_multiplier']:.2f} to {p_hi['prevalence_multiplier']:.1f} times its base value changed aggregate positive predictive value from {p_lo['ppv_pct']:.2f}% to {p_hi['ppv_pct']:.2f}% and the false-positive to true-positive ratio from {p_lo['fp_tp_ratio']:.1f} to {p_hi['fp_tp_ratio']:.1f}, but maximum capacity utilisation moved only from {p_lo['max_capacity_utilization_pct']:.1f}% to {p_hi['max_capacity_utilization_pct']:.1f}% (Supplementary Table S5), because the visit cascade is driven by false positives whose number depends on specificity rather than prevalence. Supplementary Figure S1 shows total downstream visits by follow-up rate, Supplementary Figure S2 the specificity sweep, Supplementary Figure S3 the tornado sensitivity analysis for maximum capacity utilisation, Supplementary Figure S4 the corresponding analysis for positive predictive value, and Supplementary Figure S5 the age-distribution scenarios.

## Discussion

Under the base-case assumptions, a DTC blood-based MCED screening wave generates roughly {ctx['row_50_fp_tp']:.0f} false-positive workups for each true cancer detected. The illustrative capacity ceiling is already exceeded once follow-up reaches {ctx['threshold_str']}; Supplementary Table S4 shows the corresponding follow-up trajectory. At 50% follow-up, the ceiling is exceeded by {row['max_capacity_utilization_pct'] - 100:.1f} percentage points, and the effective caseload per cancer-relevant specialist rises by about {ctx['percent_change']:.0f}% after adding false-positive follow-up visits. This pattern is consistent with real-world Japanese experience of another DTC cancer-screening test: the N-NOSE PET/CT survey found a low cancer discovery rate after a high-risk result [^5^].

The modelled aggregate positive predictive value ({ctx['row_50_ppv']:.1f}%) is far below the 38% reported in the PATHFINDER cohort [^13^]. The two figures are not in conflict: PATHFINDER enrolled adults aged 50 years and over, many with elevated risk, within a protocolised follow-up pathway, whereas the present model assumes unselected adult purchasers aged 20 years and over and a per-cancer specificity of {params['cancers'][0]['specificity']:.3f}. The age-specific results (Figure 2) show that restricting uptake to older adults would move positive predictive value toward the trial estimate, while marketing to younger consumers would move it further away. The capacity results are much less sensitive to this uncertainty: halving or doubling the prevalence proxy shifted maximum utilisation by at most {two_fold_pp:.1f} percentage points (Supplementary Table S5), because the cascade is dominated by false positives.

### Implications for screening practice and policy

A positive MCED result is likely to be handled first by primary care before any specialist is involved. Clinicians must explain an uncertain signal, weigh it against guideline-recommended screening and coordinate confirmatory tests. People considering a DTC blood test need clear information on the low positive predictive value in asymptomatic populations and the likely cascade of follow-up visits [^9^]. Primary care providers are concerned about responsibility for interpreting results, costs and managing subsequent evaluations [^10^], and health-technology reviews identify anxiety, false reassurance and displacement of guideline-based screening as potential harms [^11^].

The workload is not evenly distributed: cancers with the lowest prevalence produce the highest false-positive ratios, and younger users, who may be preferentially targeted by DTC advertising, have the lowest positive predictive values. Regulators and payers could reduce this burden by requiring pre-market performance thresholds, transparent positive predictive value reporting by age and sex, and a clear follow-up pathway that prevents primary care from becoming the default safety net for unregulated screening. High-income countries with constrained primary and specialty care capacity should account for these externalities when deciding whether to allow or reimburse DTC MCED testing.

### Benefit to individuals and referral status of a positive result

A consumer-facing blood test offers convenience and the prospect of detecting cancers for which organised screening is unavailable [^3^][^4^]. For a small minority of users, earlier detection could shift stage at diagnosis, but in an asymptomatic cohort a positive result is unlikely to represent cancer (Figure 2; Supplementary Table S1). Most positive results therefore generate anxiety, additional testing and opportunity costs rather than useful early diagnosis, and systematic reviews report downstream harms including false reassurance, overdiagnosis and displacement of guideline-based screening [^11^].

Treating a DTC positive result as equivalent to a physician's referral letter has direct capacity implications. A referral-letter model gives individuals insured access to confirmatory care and may improve follow-up completion, but it also signals medical legitimacy and channels the false-positive cascade into the publicly funded system. In the present model the illustrative specialist ceiling was breached once follow-up reached {ctx['threshold_str']} with {params['assumptions']['available_for_cancer_share']:.0%} of national capacity assumed available; insuring confirmatory workups would be expected to raise follow-up completion and push utilisation higher still. Conversely, keeping DTC testing outside the referral pathway leaves individuals to self-fund follow-up, which may reduce public-sector pressure but also fragments care, delays diagnosis for the small true-positive minority and creates inequity.

An intermediate arrangement would allow DTC access but require the test to meet pre-market performance thresholds, and require clinician review of positive results before any publicly funded workup is authorised. Only evidence-based confirmatory investigations would be covered, and the responsible clinician would be able to decline inappropriate cascades. This preserves individual choice without shifting the full cost of unregulated screening onto primary and specialty care [^9^].

### Strengths and limitations

The model is fully reproducible from public national data and open code, and it separates the effects of follow-up behaviour, specificity, capacity share, prevalence and age structure. Its simple structure also brings several limitations. First, the analysis uses scenario assumptions for test performance, diagnostic pathways and the age distribution of DTC users, because these data are not publicly reported; a single sensitivity and specificity were applied to all eight cancers, whereas real assays differ by cancer and by stage. Second, prevalence was approximated by adult incidence, which likely overstates true positives; the direction of the bias is known and its effect on capacity results was shown to be small. Third, positives were summed across cancers, so an assay reporting one overall result and a cancer signal origin would generate fewer positive individuals but a comparable number of confirmatory investigations per positive. Fourth, the model represents a single screening wave of 100,000 purchasers; repeated annual testing, incidental findings, overdiagnosis, costs and the downstream benefit of any true positive were not modelled. Fifth, diagnostic capacity was annualised from a one-month facility survey and specialist capacity from NDB outpatient patient counts, both reduced by an assumed available-for-cancer-workup share that is itself a scenario parameter. Finally, the model is deterministic and does not capture stochastic variation, geographic maldistribution, waiting-time dynamics or queueing effects; the follow-up rate was applied equally to true and false positives.

## Conclusions

In a fully reproducible scenario model parameterised with Japanese national data, a single DTC MCED screening wave of 100,000 adults generated about {ctx['row_50_fp_tp']:.0f} false positives per detected cancer and exceeded illustrative specialist capacity once {ctx['threshold_str'].split(' ')[0]} of positive results were followed up, a conclusion that was robust to a two-fold uncertainty in prevalence. In the absence of clear regulatory guardrails, including pre-market performance thresholds, transparent age-specific positive predictive value reporting and defined follow-up obligations, DTC MCED tests risk generating a large-scale false-positive cascade that stresses primary care, specialty care and diagnostic capacity in high-income settings.

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


def make_prevalence_table(prev: pd.DataFrame) -> List[List[str]]:
    rows = [["Prevalence multiplier", "True positives", "False positives", "PPV (%)", "FP/TP ratio", "Max capacity utilisation (%)"]]
    for _, r in prev.iterrows():
        rows.append([
            f"{r['prevalence_multiplier']:.2f}", f"{r['true_positives']:,.1f}", f"{r['false_positives']:,.1f}",
            f"{r['ppv_pct']:.2f}", f"{r['fp_tp_ratio']:.1f}", f"{r['max_capacity_utilization_pct']:.1f}",
        ])
    return rows


def _build_supplementary_markdown(
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    ctx: Dict[str, Any],
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

**Supplementary Table S5. Sensitivity of base-case results (50% follow-up, specificity 0.990, sensitivity 0.70) to scaling the incidence-based prevalence proxy.**

{format_markdown_table(make_prevalence_table(ctx["prevalence_sens"]))}

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


def _fill_cell(cell, text: str, size: int, bold: bool = False) -> None:
    para = cell.paragraphs[0]
    para.paragraph_format.line_spacing = 1.0
    _add_inline(para, text, font_size=size)
    if bold:
        for r in para.runs:
            r.font.bold = True


def _add_table(doc: Document, rows: List[List[str]], size: int = 9) -> None:
    t = doc.add_table(rows=1, cols=len(rows[0]))
    t.style = "Table Grid"
    for col_idx, val in enumerate(rows[0]):
        _fill_cell(t.rows[0].cells[col_idx], val, size, bold=True)
    for row in rows[1:]:
        cells = t.add_row().cells
        for col_idx, val in enumerate(row):
            _fill_cell(cells[col_idx], val, size)
    if rows[0][0] == "Parameter" and len(rows[0]) == 3:
        t.autofit = False
        for col, width in zip(t.columns, (Inches(2.0), Inches(1.1), Inches(3.4))):
            for cell in col.cells:
                cell.width = width
    doc.add_paragraph()


def _table_rows_from_md(md: str, caption_prefix: str) -> List[List[str]]:
    """Return the rows of the first Markdown table following a bold caption (post-renumbering)."""
    start = md.index(caption_prefix)
    rows: List[List[str]] = []
    for line in md[start:].splitlines()[1:]:
        if line.startswith("|"):
            if re.match(r"^\|\s*[-:]+", line.strip()):
                continue
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif rows:
            break
    return rows


def _build_tables_docx(tables: Dict[str, List[List[str]]], docx_path: Path) -> None:
    doc = _new_document()
    for title, rows in tables.items():
        doc.add_heading(title, level=2)
        _add_table(doc, rows, size=10)
    doc.save(docx_path)
    _sanitize_cjk_fonts(docx_path)


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
        f"Supplementary tables: 5; Supplementary figures: {len(SUPP_FIGURES)}."
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
    """Write Figure_N.png/.tif and Supplementary_Figure_SN.png/.tif (source PNGs are >= 300 dpi)."""
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
            im.convert("RGB").save(
                dest.with_suffix(".tif"), format="TIFF", compression="tiff_lzw", dpi=dpi
            )
        shutil.copyfile(output_dir / filename, dest)
        written.extend([dest, dest.with_suffix(".tif")])
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
        f"In a modelled 100,000-person cohort at 50% follow-up and 99% specificity, the model estimated "
        f"{row['true_positives']:,.0f} true positives and {row['false_positives']:,.0f} false positives "
        f"(positive predictive value {ctx['row_50_ppv']:.2f}%). The false-positive cascade produced "
        f"{ctx['primary_care_visits']:,.0f} primary care visits and {row['total_visits']:,.0f} total downstream visits; "
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
    ("9", "Describe any efforts to address potential sources of bias", "Methods: Model (prevalence proxy); Results: Sensitivity and scenario analyses (Supplementary Table S5); Discussion: Strengths and limitations"),
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
    ("17", "Report other analyses done, e.g. sensitivity analyses", "Results: Sensitivity and scenario analyses; Supplementary Tables S2-S5; Supplementary Figures S1-S5"),
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


def _validate(main_md: str, abstract_md: str, supp_md: str, docx_paths: List[Path], main_docx: Path) -> None:
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
    supp_labels = [lbl for lbl, _, _ in SUPP_FIGURES] + [
        f"Supplementary Table S{n}" for n in range(1, supp_md.count("**Supplementary Table S") + 1)
    ]
    for label in supp_labels:
        if label not in body:
            errors.append(f"{label} not cited in main text")
        if f"**{label}." not in supp_md:
            errors.append(f"{label} missing from supplementary file")
    if re.search(r"\butiliz", main_md + supp_md):
        errors.append("American spelling 'utiliz-' found; use 'utilis-' throughout")
    prose = "\n".join(l for l in body.splitlines() if not l.startswith("$$"))
    if re.search(r"\b\d{5,}\b", prose):
        errors.append("five-digit number without thousands separator in main text")

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
    ctx["prevalence_sens"] = pd.read_csv(args.output / "jms_prevalence_sensitivity.csv")
    ctx["age_ppv"] = pd.read_csv(args.output / "age_specific_ppv.csv")
    fig_dir = args.output / JMS_FIGURE_SUBDIR
    if not fig_dir.is_dir():
        raise FileNotFoundError(f"{fig_dir} missing: run jms_analysis.py first")

    main_md = _build_main_markdown(params, agg, by_cancer_at_50, weighted_ppv, capacity_impact, ctx)
    main_md = _sage_superscript_citations(_renumber_vancouver_references(main_md))
    abstract_md = _abstract(ctx, params)
    (args.manuscript / "manuscript_jms.md").write_text(main_md, encoding="utf-8")

    main_docx = args.manuscript / "manuscript_jms.docx"
    _build_main_docx(main_md, abstract_md, main_docx, fig_dir)

    supp_md = _build_supplementary_markdown(agg, by_cancer_at_50, weighted_ppv, ctx, args.output)
    (args.manuscript / "supplementary_jms.md").write_text(supp_md, encoding="utf-8")
    supp_docx = args.manuscript / "supplementary_jms.docx"
    _build_supplementary_docx(supp_md, supp_docx, fig_dir)

    supp_tables = _make_supplementary_tables(args.output)
    all_tables: Dict[str, List[List[str]]] = {
        "Table 1. Data sources and scenario parameters": _table_rows_from_md(main_md, "**Table 1."),
        "Table 2. Baseline cases per specialist and incremental false-positive burden at 50% follow-up": make_table_4(capacity_impact),
        "Supplementary Table S1. Per-cancer outcomes at 50% follow-up (per 100,000 screened)": make_table_2(by_cancer_at_50, weighted_ppv),
        "Supplementary Table S2. Aggregate positive predictive value under alternative age-distribution scenarios":
            supp_tables["Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios"],
        "Supplementary Table S3. One-way sensitivity analysis":
            supp_tables["Supplementary Table S2. One-way sensitivity analysis"],
        "Supplementary Table S4. Aggregate outcomes by follow-up rate (base-case specificity)": make_table_3(agg),
        "Supplementary Table S5. Sensitivity of base-case results to the prevalence proxy": make_prevalence_table(ctx["prevalence_sens"]),
    }
    tables_docx = args.manuscript / "manuscript_jms_tables.docx"
    _build_tables_docx(all_tables, tables_docx)

    figures_pptx = args.manuscript / "manuscript_jms_figures.pptx"
    _build_figures_pptx(fig_dir, figures_pptx)
    figure_files = _export_figure_files(fig_dir, args.manuscript / "figures_jms")

    cover_docx = args.manuscript / "cover_letter_jms.docx"
    _build_cover_letter_docx(ctx, cover_docx)
    checklist_docx = args.manuscript / "reporting_checklist_jms.docx"
    _build_reporting_checklist_docx(checklist_docx)

    _validate(main_md, abstract_md, supp_md, [main_docx, supp_docx, tables_docx, cover_docx, checklist_docx], main_docx)

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
