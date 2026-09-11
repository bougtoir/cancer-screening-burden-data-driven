"""Build a Family Medicine and Community Health (FMCH) formatted manuscript.

This script reuses the analysis outputs and the generic build pipeline from
build_manuscript.py, then adjusts the front matter (Key points, structured
abstract with Keywords) and adds the required post-conclusion sections
(Author contributions, Acknowledgements, Funding, Competing interests,
Data availability).  No numeric results are hard-coded.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from build_manuscript import (
    build_figures_pptx,
    build_markdown,
    build_tables_docx,
    compute_per_cancer_at_followup,
    load_aggregate,
    load_capacity_summary,
    load_by_cancer,
    load_weighted_ppv,
    make_table_1,
    make_table_2,
    make_table_3,
    make_table_4,
    markdown_to_docx,
    format_markdown_table,
    _fp_to_tp_ratio,
    _ppv,
)
from simulate import choose_summary_rate, find_capacity_threshold


def _parse_capacity_threshold(agg: pd.DataFrame) -> tuple[str, str]:
    """Return (rate_str, resource) for the first capacity exceedance."""
    s = find_capacity_threshold(agg, threshold=100.0)
    if s.startswith("not"):
        return "not reached in the scanned range", ""
    m = re.search(r"([0-9]+)%\s*\(([^)]+)\)", s)
    if not m:
        return "unknown", ""
    return f"{int(m.group(1))}%", m.group(2).strip().lower()


def _compute_context(
    params: Dict[str, Any],
    agg: pd.DataFrame,
    by_cancer: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    capacity_impact: pd.DataFrame,
    capacity_summary: Dict[str, Any],
    output_dir: Path,
) -> Dict[str, Any]:
    """Compute all narrative numbers shared by the FMCH manuscript."""
    follow_up_rates = agg["follow_up_rate"].tolist()
    row_50 = agg[agg["follow_up_rate"] == choose_summary_rate(follow_up_rates, 0.5)].iloc[0]

    row_50_ppv = _ppv(row_50["true_positives"], row_50["false_positives"]) * 100
    row_50_fp_tp = _fp_to_tp_ratio(row_50["true_positives"], row_50["false_positives"])

    threshold_rate, threshold_resource = _parse_capacity_threshold(agg)
    threshold_str = (
        f"{threshold_rate} ({threshold_resource})"
        if threshold_resource
        else threshold_rate
    )

    weighted = weighted_ppv.copy()
    weighted["ppv"] = weighted.apply(
        lambda r: _ppv(r["true_positives"], r["false_positives"]), axis=1
    )
    weighted["fp_to_tp_ratio"] = weighted.apply(
        lambda r: _fp_to_tp_ratio(r["true_positives"], r["false_positives"]), axis=1
    )

    lowest_ppv = weighted.loc[weighted["ppv"].idxmin()]
    highest_ppv = weighted.loc[weighted["ppv"].idxmax()]

    # Specificity sweep.
    sweep = pd.read_csv(output_dir / "specificity_sweep.csv")
    sweep_agg = (
        sweep.groupby("sweep_specificity")[["true_positives", "false_positives"]]
        .sum()
        .reset_index()
    )
    sweep_agg["ppv"] = sweep_agg["true_positives"] / (
        sweep_agg["true_positives"] + sweep_agg["false_positives"]
    )
    spec_values = sweep_agg["sweep_specificity"].tolist()
    spec_95 = choose_summary_rate(spec_values, 0.95)
    spec_99 = choose_summary_rate(spec_values, 0.99)
    ppv_95 = sweep_agg[sweep_agg["sweep_specificity"] == spec_95]["ppv"].values[0] * 100
    ppv_99 = sweep_agg[sweep_agg["sweep_specificity"] == spec_99]["ppv"].values[0] * 100
    ppv_ratio = ppv_95 / ppv_99 if ppv_99 > 0 else 0.0

    baseline_cases = capacity_summary.get("baseline_cases_per_specialist", 0.0)
    fp_visits = capacity_summary.get("fp_visits_per_specialist", 0.0)
    total_cases = capacity_summary.get("cases_per_specialist_with_fp", baseline_cases + fp_visits)
    percent_change = capacity_summary.get("percent_change", 0.0)

    pc_visits = float(row_50.get("primary_care_visits", 0.0))
    pc_util = float(row_50.get("primary_care_visits_utilization_pct", 0.0))

    # Multi-way sensitivity summary.
    def _metric_at(df: pd.DataFrame, parameter: str, value: float, metric: str) -> float:
        sub = df[df["parameter"] == parameter]
        nearest = choose_summary_rate(sub["value"].tolist(), value)
        return float(sub[sub["value"] == nearest][metric].values[0])

    sens = pd.read_csv(output_dir / "sensitivity_summary.csv")
    ppv_spec_95 = _metric_at(sens, "specificity", 0.95, "ppv_pct")
    ppv_spec_999 = _metric_at(sens, "specificity", 0.999, "ppv_pct")
    max_util_spec_95 = _metric_at(sens, "specificity", 0.95, "max_capacity_utilization_pct")
    max_util_spec_999 = _metric_at(sens, "specificity", 0.999, "max_capacity_utilization_pct")
    max_util_share_05 = _metric_at(sens, "available_share", 0.05, "max_capacity_utilization_pct")
    max_util_share_50 = _metric_at(sens, "available_share", 0.50, "max_capacity_utilization_pct")
    max_util_follow_10 = _metric_at(sens, "follow_up_rate", 0.10, "max_capacity_utilization_pct")
    max_util_follow_90 = _metric_at(sens, "follow_up_rate", 0.90, "max_capacity_utilization_pct")

    # Age scenario PPVs (aggregate across cancers for each distribution).
    age_scenarios = pd.read_csv(output_dir / "age_scenarios.csv")
    age_agg = (
        age_scenarios.groupby("distribution")[["true_positives", "false_positives", "total_positives"]]
        .sum()
        .reset_index()
    )
    age_agg["ppv"] = age_agg["true_positives"] / age_agg["total_positives"]
    age_agg["fp_to_tp"] = age_agg["false_positives"] / age_agg["true_positives"]
    age_ppv = {
        row["distribution"]: row["ppv"] * 100.0
        for _, row in age_agg.iterrows()
    }
    age_fp_tp = {
        row["distribution"]: row["fp_to_tp"]
        for _, row in age_agg.iterrows()
    }

    return {
        "row_50": row_50,
        "row_50_ppv": row_50_ppv,
        "row_50_fp_tp": row_50_fp_tp,
        "threshold_str": threshold_str,
        "lowest_ppv": lowest_ppv,
        "highest_ppv": highest_ppv,
        "ppv_95": ppv_95,
        "ppv_99": ppv_99,
        "ppv_ratio": ppv_ratio,
        "baseline_cases": baseline_cases,
        "fp_visits": fp_visits,
        "total_cases": total_cases,
        "percent_change": percent_change,
        "primary_care_visits": pc_visits,
        "primary_care_utilization_pct": pc_util,
        "ppv_spec_95": ppv_spec_95,
        "ppv_spec_999": ppv_spec_999,
        "max_util_spec_95": max_util_spec_95,
        "max_util_spec_999": max_util_spec_999,
        "max_util_share_05": max_util_share_05,
        "max_util_share_50": max_util_share_50,
        "max_util_follow_10": max_util_follow_10,
        "max_util_follow_90": max_util_follow_90,
        "age_ppv": age_ppv,
        "age_fp_tp": age_fp_tp,
    }


def _fmch_abstract(ctx: Dict[str, Any], params: Dict[str, Any]) -> str:
    row = ctx["row_50"]
    return (
        "**Background:** Direct-to-consumer blood-based multi-cancer early detection "
        "(MCED) tests are advertised as a convenient single-blood-draw screen. In "
        "asymptomatic populations most positive results are false positives, each "
        "triggering primary care, imaging, endoscopy, and specialist follow-up visits.\n\n"
        "**Methods:** A deterministic expected-value model was parameterised with 2023 "
        "adult cancer incidence and population data, 2023 national diagnostic volumes, "
        "and primary care and specialist capacity derived from NDB Open Data outpatient counts and "
        "Japanese specialist-board counts. True positives, false positives, downstream "
        "visits, capacity utilisation, and per-specialist case load were estimated across "
        "follow-up rates of 0-100% and specificities of 95.0-99.9%.\n\n"
        f"**Results:** In a 100,000-person cohort at 50% follow-up and {params['cancers'][0]['specificity']:.3f} "
        f"specificity, the model generated {row['true_positives']:.1f} true positives and "
        f"{row['false_positives']:.1f} false positives (positive predictive value "
        f"{ctx['row_50_ppv']:.2f}%; false-positive/true-positive ratio "
        f"{ctx['row_50_fp_tp']:.1f}). Total downstream visits reached "
        f"{row['total_visits']:.1f}, including {ctx['primary_care_visits']:.1f} primary care visits "
        f"({ctx['primary_care_utilization_pct']:.1f}% of the illustrative primary-care capacity). "
        f"Maximum capacity utilisation was {row['max_capacity_utilization_pct']:.1f}% (specialist visits). The "
        f"illustrative capacity ceiling was exceeded at a follow-up rate of "
        f"{ctx['threshold_str']}. False-positive specialist visits added "
        f"{ctx['fp_visits']:.1f} visits per relevant specialist, raising the effective "
        f"cases per specialist from {ctx['baseline_cases']:.1f} to "
        f"{ctx['total_cases']:.1f} ({ctx['percent_change']:.0f}% increase).\n\n"
        "**Conclusions:** Even with optimistic 99% specificity, a direct-to-consumer "
        "MCED wave can trigger a false-positive cascade that exceeds outpatient and "
        "endoscopic capacity and overloads primary care. Transparent positive predictive "
        "value reporting, performance thresholds, and clear follow-up obligations are "
        "needed before routine adoption, with support for family physicians and primary "
        "care clinicians to counsel patients."
    )


def _key_points(ctx: Dict[str, Any]) -> str:
    row = ctx["row_50"]
    return (
        "### Key points\n\n"
        "- **Question:** What primary care, diagnostic, and specialist workload is generated when "
        "direct-to-consumer blood-based multi-cancer early detection (MCED) tests return "
        "positive results in an asymptomatic population?\n"
        f"- **Finding:** A 100,000-person MCED wave at 50% follow-up produced "
        f"{row['true_positives']:.0f} true positives and {row['false_positives']:.0f} "
        f"false positives (PPV {ctx['row_50_ppv']:.2f}%), generating {ctx['primary_care_visits']:.0f} primary care visits and "
        f"exceeding the illustrative specialist capacity ceiling once follow-up exceeded "
        f"{ctx['threshold_str'].split(' ')[0]}.\n"
        "- **Meaning:** Without regulatory guardrails on performance claims and "
        "follow-up obligations, widespread direct-to-consumer MCED screening could "
        "overload primary care, specialty care, and community health systems with "
        "unnecessary investigations."
    )


def _additional_references() -> list[str]:
    """Return FMCH-focused primary-care references to append after the generic list."""
    return [
        "Hoffman RM, Wolf AMD, Raoof S, Guerra CE, Church TR, Elkin EB, et al. "
        "Multicancer early detection testing: Guidance for primary care discussions with patients. "
        "Cancer. 2025;131(7):e35823. https://doi.org/10.1002/cncr.35823",
        "Ueberroth BE, Presutti RJ, McGary A, Borad MJ, Agrwal N. "
        "Perspectives of primary care providers regarding multicancer early detection panels. "
        "Einstein (Sao Paulo). 2024;22:eAO0771. https://doi.org/10.31744/einstein_journal/2024AO0771",
        "Wade R, Nevitt S, Liu Y, Harden M, Khouja C, Raine G, et al. "
        "Multi-cancer early detection tests for general population screening: a systematic literature review. "
        "Health Technol Assess. 2025;29(2). https://doi.org/10.3310/DLMT1294",
    ]


def _revise_body_for_fmch(body: str, ctx: Dict[str, Any], output_dir: Path) -> str:
    """Apply FMCH-specific language, primary-care framing, additional citations,
    and insert supplementary scenario analyses."""
    # Primary-care framing in the Introduction.
    body = body.replace(
        "We quantified this burden as a function of follow-up behaviour, test specificity, and age structure.",
        "Clinicians are increasingly asked to interpret or manage results from tests acquired outside "
        "clinical care [^9^]. Family physicians and primary care clinicians are often the first point of "
        "contact for patients with a positive result and are concerned about interpreting results, costs, "
        "and managing subsequent evaluations [^10^]. This burden was quantified as a function of follow-up "
        "behaviour, test specificity, and age structure.",
    )

    # Generalisability framing in the Scenarios paragraph.
    body = body.replace(
        "Base-case sensitivity and specificity were 0.70 and 0.990. We varied follow-up rate from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. The available-for-cancer-workup share of national diagnostic capacity was set to 20%.",
        "Base-case sensitivity and specificity were 0.70 and 0.990. Follow-up rate was varied from 0 to 100% and specificity from 0.950 to 0.999 in a sensitivity sweep. Japan was used as a case study because it has a large direct-to-consumer screening market and publicly available national data; the false-positive cascade is generalisable to other high-income settings. The available-for-cancer-workup share of national diagnostic capacity was set to 20%.",
    )

    # Active-voice / first-person revisions per FMCH style guidance.
    body = body.replace(
        "We used a deterministic expected-value cohort model.",
        "A deterministic expected-value cohort model was used.",
    )
    body = body.replace(
        "We define baseline specialist capacity",
        "Baseline specialist capacity is defined",
    )
    body = body.replace(
        "We used NDB Open Data unique first/revisit outpatient patients",
        "NDB Open Data unique first/revisit outpatient patient counts were used",
    )
    body = body.replace(
        "We then multiplied this by the number",
        "This value was then multiplied by the number",
    )
    body = body.replace(
        "Our scenario model shows",
        "The scenario model shows",
    )
    body = body.replace(
        "Our analysis intentionally uses",
        "The analysis intentionally uses",
    )

    # Scenario / sensitivity analyses section.
    age_ppv = ctx["age_ppv"]
    age_fp_tp = ctx["age_fp_tp"]
    age_table = [
        ["Age distribution scenario", "Aggregate PPV (%)", "FP/TP ratio"],
        ["2023 total population", f"{age_ppv.get('japan_total_2023', 0.0):.2f}", f"{age_fp_tp.get('japan_total_2023', 0.0):.1f}"],
        ["Adults 20+", f"{age_ppv.get('japan_adult_20plus', 0.0):.2f}", f"{age_fp_tp.get('japan_adult_20plus', 0.0):.1f}"],
        ["DTC bimodal (23andMe-like)", f"{age_ppv.get('dtc_bimodal_23andme', 0.0):.2f}", f"{age_fp_tp.get('dtc_bimodal_23andme', 0.0):.1f}"],
        ["DTC younger purchasers", f"{age_ppv.get('dtc_younger', 0.0):.2f}", f"{age_fp_tp.get('dtc_younger', 0.0):.1f}"],
        ["DTC screening-age purchasers", f"{age_ppv.get('dtc_screening_age', 0.0):.2f}", f"{age_fp_tp.get('dtc_screening_age', 0.0):.1f}"],
    ]
    scenario_section = (
        "### Additional scenario and sensitivity analyses\n\n"
        "Aggregate PPV is highly sensitive to the age distribution of users. If direct-to-consumer purchasers "
        "are younger than the general population, the already low PPV falls further and the FP/TP ratio rises "
        "(Table S1). For example, a younger-purchaser profile yields an aggregate PPV of "
        f"{age_ppv.get('dtc_younger', 0.0):.2f}% and an FP/TP ratio of {age_fp_tp.get('dtc_younger', 0.0):.1f}, compared with "
        f"{age_ppv.get('japan_total_2023', 0.0):.2f}% and {age_fp_tp.get('japan_total_2023', 0.0):.1f} under the 2023 national total-population age distribution.\n\n"
        "**Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios.**\n\n"
        f"{format_markdown_table(age_table)}\n\n"
        "Test specificity and follow-up behaviour are the dominant drivers of capacity pressure (Supplementary Table S2). At 50% follow-up, "
        f"lowering specificity from 99.9% to 95.0% reduces aggregate PPV from {ctx['ppv_spec_999']:.2f}% to "
        f"{ctx['ppv_spec_95']:.2f}% and raises maximum capacity utilisation from {ctx['max_util_spec_999']:.1f}% to "
        f"{ctx['max_util_spec_95']:.1f}%. With 99% specificity, maximum utilisation ranges from "
        f"{ctx['max_util_follow_10']:.1f}% at 10% follow-up to {ctx['max_util_follow_90']:.1f}% at 90% follow-up. "
        f"If only 5% of the illustrative national capacity can be reallocated, the bottleneck reaches "
        f"{ctx['max_util_share_05']:.0f}%; with a 50% share it stays at {ctx['max_util_share_50']:.0f}%. "
        "Tornado diagrams for capacity utilisation and PPV are provided as Supplementary Figures S1 and S2.\n\n"
        "![Supplementary Figure S1. One-way sensitivity of maximum capacity utilisation](output/tornado_max_capacity.png)\n"
        "**Fig. S1.** Tornado diagram showing the effect of varying specificity, follow-up rate, available capacity share, and sensitivity on maximum capacity utilisation (base case = 50% follow-up, 99% specificity, 20% capacity share).\n\n"
        "![Supplementary Figure S2. One-way sensitivity of aggregate PPV](output/tornado_ppv.png)\n"
        "**Fig. S2.** Tornado diagram showing the effect of the same four parameters on aggregate positive predictive value.\n\n"
        "![Supplementary Figure S3. Aggregate PPV under alternative age-distribution scenarios](output/age_scenario_ppv.png)\n"
        "**Fig. S3.** Aggregate PPV for each cancer type under the 2023 national total-population distribution and four hypothetical direct-to-consumer purchaser age profiles."
    )

    # Add a Discussion subsection on primary care / shared decision-making.
    pcare_section = (
        "### Implications for primary care and shared decision-making\n\n"
        "A positive MCED result frequently lands in primary care before any specialist is involved. "
        "Family physicians must explain an uncertain signal, weigh it against guideline-recommended "
        "screening, and coordinate confirmatory tests. In this role, shared decision-making is essential: "
        "patients considering a DTC blood test need transparent information on the low PPV in "
        "asymptomatic populations and the likely cascade of follow-up visits [^9^]. The present figures "
        f"suggest that, at 50% follow-up, each true cancer detected is accompanied by about {ctx['row_50_fp_tp']:.0f} false-positive "
        "workups. Primary care providers are already concerned about responsibility for interpreting "
        "results, costs, and managing subsequent evaluations [^10^], and health-system reviews identify "
        "anxiety, false reassurance, and displacement of guideline-based screening as potential harms [^11^]. "
        "From a community-health perspective, the workload is not evenly distributed: cancers with the "
        "lowest prevalence generate the highest false-positive ratios, and younger users, who are "
        "increasingly targeted by DTC advertising, face the lowest PPVs. Regulators and payers could reduce "
        "this burden by requiring pre-market performance thresholds, transparent PPV reporting by age and "
        "sex, and a clear follow-up pathway that keeps primary care from becoming the default safety net "
        "for unregulated screening."
    )
    body = body.replace(
        "\n### Limitations\n",
        f"\n{scenario_section}\n\n{pcare_section}\n\n### Limitations\n",
    )

    # Conclusion: explicitly name primary care alongside specialty care.
    body = body.replace(
        "direct-to-consumer MCED tests risk converting a marketing promise into a large-scale false-positive cascade that stresses diagnostic capacity.",
        "direct-to-consumer MCED tests risk converting a marketing promise into a large-scale false-positive cascade that stresses primary care, specialty care, and diagnostic capacity.",
    )

    # Expand Limitations with PSA caveats and the primary-care capacity assumption.
    body = body.replace(
        "The model is deterministic and does not capture stochastic variation, geographic maldistribution, or queueing effects.",
        "Primary care capacity was derived using the same national outpatient caseload and 20% available-share assumption as specialist capacity; actual capacity depends on local demand for chronic disease and routine care. "
        "Sensitivity and specificity were assumed to be uniform across cancers; real tests may vary by site. "
        "No probabilistic sensitivity analysis was performed because empirical distributions for test performance, follow-up behaviour, and direct-to-consumer user age structure are not publicly available. "
        "The model is deterministic and does not capture stochastic variation, geographic maldistribution, or queueing effects.",
    )

    return body


def _post_conclusion_sections() -> str:
    return (
        "## Author contributions\n\n"
        "All authors contributed to the study design, data interpretation, and critical "
        "revision of the manuscript, and approved the final version.\n\n"
        "## Acknowledgements\n\n"
        "We thank colleagues in primary care and health services research for their comments on "
        "the manuscript.\n\n"
        "## Funding\n\n"
        "No external funding was received for this study.\n\n"
        "## Competing interests\n\n"
        "The authors declare no competing interests.\n\n"
        "## Ethics approval\n\n"
        "This study used only publicly available aggregate data and a deterministic "
        "simulation; ethics approval was not required.\n\n"
        "## Patient and public involvement\n\n"
        "Patients or members of the public were not directly involved in the design, "
        "conduct, reporting, or dissemination of this modelling study.\n\n"
        "## Data availability\n\n"
        "All data sources are publicly available and listed in Table 1. The main simulation "
        "outputs (by-cancer and aggregate follow-up sweep, specificity sweep, sensitivity summary, "
        "age-specific PPV, age-scenario PPV, and specialist capacity impact) are generated by the "
        "analysis scripts. Analysis code, parameters, and outputs are available at "
        "https://github.com/bougtoir/cancer-screening-burden-data-driven."
    )


def _renumber_vancouver_references(md: str) -> str:
    """Reorder the reference list so that numbers match first appearance in the body.

    Also rewrites every [^N^] citation to the new sequential number and removes any
    references that are never cited.
    """
    split_mark = "\n## References\n\n"
    if split_mark not in md:
        return md
    body_part, refs_part = md.split(split_mark, 1)

    # 1. Determine first-appearance order of citations in the body.
    order: list[int] = []
    for m in re.finditer(r"\[\^(\d+)\^\]", body_part):
        num = int(m.group(1))
        if num not in order:
            order.append(num)

    # 2. Parse the existing reference entries.
    ref_map: dict[int, str] = {}
    for entry in refs_part.strip().split("\n\n"):
        entry = entry.strip()
        if not entry:
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", entry, re.DOTALL)
        if m:
            ref_map[int(m.group(1))] = m.group(2).strip()

    # 3. Build reordered list in first-appearance order.
    new_refs: list[str] = []
    for new_num, old_num in enumerate(order, start=1):
        text = ref_map.get(old_num)
        if text is None:
            continue
        new_refs.append(f"{new_num}. {text}")

    # 4. Replace citations in both body and references text.
    old_to_new = {old: str(new) for new, old in enumerate(order, start=1)}
    pattern = re.compile(r"\[\^(\d+)\^\]")
    def _replace_citation(m: re.Match[str]) -> str:
        return f"[^{old_to_new.get(int(m.group(1)), m.group(1))}^]"
    body_part = pattern.sub(_replace_citation, body_part)
    refs_text = "\n\n".join(new_refs)

    return f"{body_part}{split_mark}{refs_text}\n"


def build_fmch_markdown(
    params: Dict[str, Any],
    agg: pd.DataFrame,
    by_cancer_at_50: pd.DataFrame,
    weighted_ppv: pd.DataFrame,
    capacity_impact: pd.DataFrame,
    capacity_summary: Dict[str, Any],
    output_dir: Path,
) -> str:
    """Generate the FMCH-formatted Markdown manuscript."""
    ctx = _compute_context(
        params, agg, by_cancer_at_50, weighted_ppv, capacity_impact, capacity_summary, output_dir
    )

    # Reuse the generic manuscript for the body and references, then replace the
    # abstract and add FMCH-specific front/back matter.
    generic_md = build_markdown(
        params,
        agg,
        by_cancer_at_50,
        weighted_ppv,
        capacity_impact,
        capacity_summary,
        output_dir,
    )

    # FMCH-specific title and keywords.
    title = (
        "# False-positive cascade from direct-to-consumer multi-cancer early detection "
        "blood tests: implications for primary and specialty care"
    )
    keywords = "multi-cancer early detection, false positive, healthcare capacity, direct-to-consumer testing, primary care, shared decision-making, scenario model"

    # Locate the separator between abstract/keywords and the introduction.
    intro_match = re.search(r"\n---\n\n(## Introduction)", generic_md)
    if not intro_match:
        raise ValueError("Could not locate '---\n\n## Introduction' separator in generic manuscript.")
    body = generic_md[intro_match.start(1):]

    refs_match = re.search(r"\n## References\n\n", body)
    if not refs_match:
        raise ValueError("Could not locate '## References' in generic manuscript.")
    body_before_refs = body[: refs_match.start()].rstrip()

    # Insert a reporting-guidelines note immediately before the Results section.
    reporting = (
        "### Reporting\n\n"
        "This scenario modelling study is reported in accordance with the "
        "Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) "
        "statement and the Statistical Analyses and Methods in the Published Literature "
        "(SAMPL) guidelines where applicable."
    )
    body_before_refs = body_before_refs.replace(
        "\n## Results\n", f"\n{reporting}\n\n## Results\n"
    )

    # Apply FMCH-specific primary-care framing, active-voice edits, and scenario analyses.
    body_before_refs = _revise_body_for_fmch(body_before_refs, ctx, output_dir)

    references = body[refs_match.start():]

    # Append FMCH-focused primary-care references while preserving Vancouver numbering.
    ref_entries = re.findall(r"^\d+\. ", references, re.MULTILINE)
    next_num = len(ref_entries) + 1
    additional = _additional_references()
    extra_refs = ""
    for i, ref in enumerate(additional, start=next_num):
        extra_refs += f"\n\n{i}. {ref}"
    references = references.rstrip() + extra_refs

    fmch_md = (
        f"{title}\n\n"
        f"{_key_points(ctx)}\n\n"
        "## Abstract\n\n"
        f"{_fmch_abstract(ctx, params)}\n\n"
        f"**Keywords:** {keywords}\n\n"
        "---\n\n"
        f"{body_before_refs}\n\n"
        f"{_post_conclusion_sections()}\n\n"
        f"{references}"
    )
    # Renumber references to strict Vancouver order (first appearance in body).
    fmch_md = _renumber_vancouver_references(fmch_md)
    return fmch_md


def _make_supplementary_tables(output_dir: Path) -> Dict[str, List[List[str]]]:
    """Return supplementary tables formatted for a separate editable .docx."""
    age_scenarios = pd.read_csv(output_dir / "age_scenarios.csv")
    age_agg = (
        age_scenarios.groupby("distribution")[["true_positives", "false_positives", "total_positives"]]
        .sum()
        .reset_index()
    )
    age_agg["ppv_pct"] = age_agg["true_positives"] / age_agg["total_positives"] * 100.0
    age_agg["fp_tp"] = age_agg["false_positives"] / age_agg["true_positives"]

    label_map = {
        "japan_total_2023": "2023 total population",
        "japan_adult_20plus": "Adults 20+",
        "dtc_bimodal_23andme": "DTC bimodal (23andMe-like)",
        "dtc_younger": "DTC younger purchasers",
        "dtc_screening_age": "DTC screening-age purchasers",
    }

    s1 = [
        ["Age-distribution scenario", "Aggregate PPV (%)", "FP/TP ratio"],
    ]
    for _, row in age_agg.iterrows():
        s1.append(
            [
                label_map.get(str(row["distribution"]), str(row["distribution"])),
                f"{row['ppv_pct']:.2f}",
                f"{row['fp_tp']:.1f}",
            ]
        )

    sens = pd.read_csv(output_dir / "sensitivity_summary.csv")
    s2 = [
        ["Parameter", "Value", "Aggregate PPV (%)", "Max capacity utilisation (%)", "Total visits"],
    ]
    for _, row in sens.iterrows():
        s2.append(
            [
                str(row["parameter"]),
                f"{row['value']:.3f}",
                f"{row['ppv_pct']:.2f}",
                f"{row['max_capacity_utilization_pct']:.1f}",
                f"{row['total_visits']:.1f}",
            ]
        )

    return {
        "Supplementary Table S1. Aggregate PPV under alternative age-distribution scenarios": s1,
        "Supplementary Table S2. One-way sensitivity analysis": s2,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FMCH-formatted manuscript materials")
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

    md = build_fmch_markdown(
        params,
        agg,
        by_cancer_at_50,
        weighted_ppv,
        capacity_impact,
        capacity_summary,
        args.output,
    )
    (args.manuscript / "manuscript_fmch.md").write_text(md, encoding="utf-8")

    tables = {
        "Table 1. Data sources and scenario parameters": make_table_1(params),
        "Table 2. Per-cancer outcomes at 50% follow-up": make_table_2(by_cancer_at_50, weighted_ppv),
        "Table 3. Aggregate outcomes by follow-up rate": make_table_3(agg),
        "Table 4. Baseline cases per specialist and incremental false-positive burden": make_table_4(capacity_impact),
    }
    tables.update(_make_supplementary_tables(args.output))
    build_tables_docx(tables, args.manuscript / "manuscript_fmch_tables.docx")

    build_figures_pptx(args.output, args.manuscript / "manuscript_fmch_figures.pptx")

    markdown_to_docx(md, args.manuscript / "manuscript_fmch.docx", args.output)

    print(f"FMCH manuscript materials written to {args.manuscript.resolve()}")


if __name__ == "__main__":
    main()
