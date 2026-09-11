"""Age-stratified positive predictive value (PPV) analysis.

The simulation uses an age-distribution-weighted aggregate prevalence. This script shows why the
aggregate matters: PPV is extremely low in younger age groups and rises with age.
All inputs are the same public data sources used by prepare_parameters.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from simulate import format_csv
from prepare_parameters import (
    AGE_COLS,
    CHILD_TEEN_COLS,
    POPULATION_2023,
    load_incidence_rate,
    load_pop,
)


def compute_age_group_ppv(
    cancer: Dict[str, Any], age_group: str, incidence_per_100k: float
) -> Dict[str, float]:
    """Return PPV metrics for a single cancer and age group, per 100,000 in that group."""
    population = 100_000.0
    actual_cases = incidence_per_100k
    sensitivity = cancer["sensitivity"]
    specificity = cancer["specificity"]

    tp = actual_cases * sensitivity
    fp = (population - actual_cases) * (1.0 - specificity)
    positives = tp + fp
    ppv = tp / positives if positives > 0 else 0.0
    fp_to_tp = fp / tp if tp > 0 else float("inf")

    return {
        "cancer": cancer["name"],
        "age_group": age_group,
        "incidence_per_100k": incidence_per_100k,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "true_positives": tp,
        "false_positives": fp,
        "total_positives": positives,
        "ppv": ppv,
        "fp_to_tp_ratio": fp_to_tp,
    }


def build_age_specific_table(cancers: List[Dict[str, Any]]) -> pd.DataFrame:
    """Build a table of age-specific PPVs for all cancers and all age groups.

    Incidence rates for sex-specific cancers are expressed per 100,000 total
    population in each age group so that the aggregate PPV matches the main
    simulation.
    """
    pop_both = load_pop("Both")
    pop_male = load_pop("Male")
    pop_female = load_pop("Female")
    sex_pop = {"Both": pop_both, "Male": pop_male, "Female": pop_female}

    rows = []
    for cancer in cancers:
        sex = cancer["sex"]
        site = cancer["site"]
        rate_row = load_incidence_rate(sex, site)
        for age_group in AGE_COLS:
            rate = rate_row[age_group]
            if pd.isna(rate) or rate == "-":
                continue
            total_pop = float(pop_both[age_group])
            sex_p = float(sex_pop[sex][age_group])
            # Convert rate per 100,000 of the sex group to rate per 100,000 total.
            incidence_per_100k_total = float(rate) * sex_p / total_pop if total_pop > 0 else 0.0
            rows.append(compute_age_group_ppv(cancer, age_group, incidence_per_100k_total))
    return pd.DataFrame(rows)


def weighted_ppv_for_distribution(
    cancers: List[Dict[str, Any]],
    age_distribution: Dict[str, float],
    age_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return aggregate PPV for each cancer under the supplied age distribution.

    age_distribution: {age_group: population_share} where shares sum to 1.
    age_df: optional pre-built age-specific table (avoids recomputing it).
    """
    if age_df is None:
        age_df = build_age_specific_table(cancers)
    rows = []
    for cancer in cancers:
        sub = age_df[age_df["cancer"] == cancer["name"]].copy()
        sub["weight"] = sub["age_group"].map(age_distribution)
        sub = sub[sub["weight"].notna()]
        if sub.empty:
            continue
        tp = (sub["true_positives"] * sub["weight"]).sum()
        fp = (sub["false_positives"] * sub["weight"]).sum()
        positives = tp + fp
        rows.append(
            {
                "cancer": cancer["name"],
                "distribution": "custom",
                "true_positives": tp,
                "false_positives": fp,
                "total_positives": positives,
                "ppv": tp / positives if positives > 0 else 0.0,
                "fp_to_tp_ratio": fp / tp if tp > 0 else float("inf"),
            }
        )
    return pd.DataFrame(rows)


def plot_ppv_by_age(age_df: pd.DataFrame, output_path: Path) -> None:
    """Line plot of PPV by age group for each cancer (adults 20+ only)."""
    from prepare_parameters import ADULT_COLS
    adult_ages = [a for a in ADULT_COLS if a in age_df["age_group"].unique()]
    age_df = age_df[age_df["age_group"].isin(adult_ages)].copy()
    age_df["age_group"] = pd.Categorical(age_df["age_group"], categories=adult_ages, ordered=True)

    fig, ax = plt.subplots(figsize=(11, 6))
    for cancer in sorted(age_df["cancer"].unique()):
        sub = age_df[age_df["cancer"] == cancer].sort_values("age_group")
        ax.plot(sub["age_group"].astype(str), sub["ppv"] * 100.0, marker="o", label=cancer)

    ax.set_xlabel("Age group")
    ax.set_ylabel("Positive predictive value (%)")
    ax.set_title("Age-specific PPV of a blood-based MCED test (sensitivity=0.70, specificity=0.990)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    ax.set_ylim(bottom=0)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(output_path, dpi=1000, bbox_inches="tight")
    plt.close(fig)


def _scenario_distributions(pop_both: pd.Series) -> Dict[str, Dict[str, float]]:
    """Return age-weight scenarios for DTC user composition sensitivity analysis.

    Weights are assigned to the same age-group labels used by `AGE_COLS`.
    'japan_total_2023' uses the full population; 'japan_adult_20plus' restricts to
    20 years and older; the DTC scenarios approximate younger, bimodal, and
    screening-age purchasers.
    """
    # Base population distributions
    japan_total = {col: float(pop_both[col]) for col in AGE_COLS}
    total_pop = sum(japan_total.values())
    japan_total = {k: v / total_pop for k, v in japan_total.items()}

    japan_adult = {k: v for k, v in japan_total.items() if k not in CHILD_TEEN_COLS}
    adult_pop = sum(japan_adult.values())
    japan_adult = {k: v / adult_pop for k, v in japan_adult.items()}
    # Keep the same keys with zero weights for children/teens so alignment is safe
    for col in CHILD_TEEN_COLS:
        japan_adult[col] = 0.0

    def _norm(weights: Dict[str, float]) -> Dict[str, float]:
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    # Approximate 23andMe-style bimodal pattern: peaks around 30-34 and 50-54 yrs
    dtc_bimodal = {col: 0.0 for col in AGE_COLS}
    dtc_bimodal["20-24 yrs."] = 0.05
    dtc_bimodal["25-29 yrs."] = 0.10
    dtc_bimodal["30-34 yrs."] = 0.20
    dtc_bimodal["35-39 yrs."] = 0.10
    dtc_bimodal["40-44 yrs."] = 0.10
    dtc_bimodal["45-49 yrs."] = 0.10
    dtc_bimodal["50-54 yrs."] = 0.15
    dtc_bimodal["55-59 yrs."] = 0.10
    dtc_bimodal["60-64 yrs."] = 0.05
    dtc_bimodal["65-69 yrs."] = 0.03
    dtc_bimodal["70-74 yrs."] = 0.01
    dtc_bimodal["75-79 yrs."] = 0.01
    dtc_bimodal = _norm(dtc_bimodal)

    # Younger DTC purchaser profile
    dtc_younger = {col: 0.0 for col in AGE_COLS}
    dtc_younger["20-24 yrs."] = 0.15
    dtc_younger["25-29 yrs."] = 0.25
    dtc_younger["30-34 yrs."] = 0.25
    dtc_younger["35-39 yrs."] = 0.15
    dtc_younger["40-44 yrs."] = 0.10
    dtc_younger["45-49 yrs."] = 0.05
    dtc_younger["50-54 yrs."] = 0.03
    dtc_younger["55-59 yrs."] = 0.01
    dtc_younger["60-64 yrs."] = 0.01
    dtc_younger = _norm(dtc_younger)

    # Screening-age DTC purchasers (40-69 yrs), roughly uniform
    dtc_screening = {col: 0.0 for col in AGE_COLS}
    dtc_screening["40-44 yrs."] = 0.15
    dtc_screening["45-49 yrs."] = 0.15
    dtc_screening["50-54 yrs."] = 0.15
    dtc_screening["55-59 yrs."] = 0.15
    dtc_screening["60-64 yrs."] = 0.15
    dtc_screening["65-69 yrs."] = 0.15
    dtc_screening["35-39 yrs."] = 0.05
    dtc_screening["70-74 yrs."] = 0.03
    dtc_screening["75-79 yrs."] = 0.02
    dtc_screening = _norm(dtc_screening)

    return {
        "japan_total_2023": japan_total,
        "japan_adult_20plus": japan_adult,
        "dtc_bimodal_23andme": dtc_bimodal,
        "dtc_younger": dtc_younger,
        "dtc_screening_age": dtc_screening,
    }


def plot_age_scenario_ppv(scenario_df: pd.DataFrame, output_path: Path) -> None:
    """Bar plot of aggregate PPV by cancer under each age distribution."""
    scenario_df = scenario_df.copy()
    scenario_df["ppv_pct"] = scenario_df["ppv"] * 100.0
    scenario_df["distribution"] = pd.Categorical(
        scenario_df["distribution"],
        categories=scenario_df["distribution"].unique(),
        ordered=True,
    )

    cancers = sorted(scenario_df["cancer"].unique())
    distributions = scenario_df["distribution"].unique().tolist()

    label_map = {
        "japan_total_2023": "Japan total 2023",
        "japan_adult_20plus": "Japan adult (20+)",
        "dtc_bimodal_23andme": "DTC bimodal",
        "dtc_younger": "DTC younger",
        "dtc_screening_age": "DTC screening age",
    }

    x = range(len(cancers))
    width = 0.15
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, dist in enumerate(distributions):
        sub = scenario_df[scenario_df["distribution"] == dist]
        sub = sub.set_index("cancer").reindex(cancers)
        label = label_map.get(str(dist), str(dist))
        ax.bar([p + width * (i - len(distributions) / 2) for p in x], sub["ppv_pct"], width=width, label=label)

    ax.set_xticks(list(x))
    ax.set_xticklabels(cancers)
    ax.set_ylabel("Aggregate PPV (%)")
    ax.set_xlabel("Cancer")
    ax.set_title("Aggregate PPV under alternative age-distribution scenarios")
    ax.legend(loc="upper right")
    ax.set_ylim(bottom=0)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(output_path, dpi=1000, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Age-stratified PPV analysis")
    parser.add_argument("--params", type=Path, default=Path("parameters.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    with open(args.params, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    args.output.mkdir(parents=True, exist_ok=True)

    cancers = params["cancers"]

    # Age-specific PPV table.
    age_df = build_age_specific_table(cancers)
    age_df = format_csv(age_df)
    age_df.to_csv(args.output / "age_specific_ppv.csv", index=False)

    # Weighted PPV using the full 2023 Japanese age distribution (all ages).
    # This matches the per-100,000 total-population rates used by the main simulation.
    pop_both = load_pop("Both")
    total_distribution = {}
    for col in AGE_COLS:
        total_distribution[col] = float(pop_both[col])
    total_pop = sum(total_distribution.values())
    total_distribution = {k: v / total_pop for k, v in total_distribution.items()}

    weighted = weighted_ppv_for_distribution(cancers, total_distribution, age_df=age_df)
    weighted["distribution"] = "japan_total_2023"
    weighted = format_csv(weighted)
    weighted.to_csv(args.output / "weighted_ppv_by_distribution.csv", index=False)

    # Scenario distributions
    scenario_records: List[Dict[str, Any]] = []
    for dist_name, dist in _scenario_distributions(pop_both).items():
        df = weighted_ppv_for_distribution(cancers, dist, age_df=age_df)
        df["distribution"] = dist_name
        scenario_records.append(df)
    scenario_df = pd.concat(scenario_records, ignore_index=True)
    scenario_df = format_csv(scenario_df)
    scenario_df.to_csv(args.output / "age_scenarios.csv", index=False)

    # Plots.
    plot_ppv_by_age(age_df, args.output / "ppv_by_age.png")
    plot_age_scenario_ppv(scenario_df, args.output / "age_scenario_ppv.png")

    # Console summary.
    print("=" * 60)
    print("Age-stratified PPV analysis")
    print("=" * 60)
    print(f"Outputs written to: {args.output.resolve()}")
    print("\nAggregate PPV under 2023 Japanese total population age distribution:")
    for _, row in weighted.iterrows():
        print(f"  {row['cancer']}: PPV={row['ppv']*100:.2f}%, FP/TP={row['fp_to_tp_ratio']:.1f}")
    print("\nAggregate PPV under alternative age distributions:")
    for _, row in scenario_df.iterrows():
        print(f"  {row['distribution']} / {row['cancer']}: PPV={row['ppv']*100:.2f}%")


if __name__ == "__main__":
    main()
