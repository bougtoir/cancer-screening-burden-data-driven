"""Urban cancer-screening burden simulation.

The model computes expected true positives, false positives, positive predictive
values, and downstream healthcare visits by cancer type under a range of
follow-up rates.  It is purely deterministic and uses only the parameters in
parameters.yaml; no real patient data is used.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml


def load_parameters(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def compute_outcomes(
    population: int,
    cancer: Dict[str, Any],
    follow_up_rate: float,
) -> Dict[str, float]:
    """Return expected outcomes for one cancer type and one follow-up rate."""
    prevalence = cancer["prevalence_per_100k"] / 100_000.0
    actual_cases = population * prevalence

    sensitivity = cancer["sensitivity"]
    specificity = cancer["specificity"]

    true_positives = actual_cases * sensitivity
    false_positives = (population - actual_cases) * (1.0 - specificity)
    total_positives = true_positives + false_positives

    ppv = true_positives / total_positives if total_positives > 0 else 0.0

    followed_positives = total_positives * follow_up_rate
    followed_tp = true_positives * follow_up_rate
    followed_fp = false_positives * follow_up_rate

    pathway = cancer["pathway"]
    modality_visits: Dict[str, float] = {}
    for modality, probability in pathway.items():
        modality_visits[f"{_camel_to_snake(modality)}_visits"] = (
            followed_positives * probability
        )

    additional_visits = (
        followed_tp * cancer["tp_additional_visits"]
        + followed_fp * cancer["fp_additional_visits"]
    )

    specialist_probability = pathway.get("specialist", 0.0)
    fp_specialist_visits = followed_fp * (
        specialist_probability + cancer["fp_additional_visits"]
    )
    tp_specialist_visits = followed_tp * (
        specialist_probability + cancer["tp_additional_visits"]
    )

    total_visits = sum(modality_visits.values()) + additional_visits

    fp_to_tp_ratio = false_positives / true_positives if true_positives > 0 else np.inf
    visits_per_detected_case = (
        total_visits / true_positives if true_positives > 0 else np.inf
    )

    return {
        "cancer": cancer["name"],
        "prevalence_per_100k": cancer["prevalence_per_100k"],
        "sensitivity": sensitivity,
        "specificity": specificity,
        "follow_up_rate": follow_up_rate,
        "actual_cases": actual_cases,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "total_positives": total_positives,
        "ppv": ppv,
        "followed_positives": followed_positives,
        "followed_true_positives": followed_tp,
        "followed_false_positives": followed_fp,
        "additional_visits": additional_visits,
        "fp_specialist_visits": fp_specialist_visits,
        "tp_specialist_visits": tp_specialist_visits,
        "total_visits": total_visits,
        "fp_to_tp_ratio": fp_to_tp_ratio,
        "visits_per_detected_case": visits_per_detected_case,
        **modality_visits,
    }


def run_follow_up_sweep(params: Dict[str, Any]) -> pd.DataFrame:
    """Run the main scenario: vary follow-up rate for each cancer type."""
    population = int(params["simulation"]["screened_population"])
    follow_up_rates = params["simulation"]["follow_up_rates"]
    cancers = params["cancers"]

    rows: List[Dict[str, float]] = []
    for cancer in cancers:
        for fu in follow_up_rates:
            rows.append(compute_outcomes(population, cancer, fu))

    return pd.DataFrame(rows)


def run_specificity_sweep(params: Dict[str, Any]) -> pd.DataFrame:
    """Run a sensitivity analysis: vary test specificity at a fixed follow-up rate.

    For this sweep the same specificity is applied to every cancer type so that
    the effect of overall test accuracy can be inspected independently.
    """
    population = int(params["simulation"]["screened_population"])
    sweep = params["specificity_sweep"]
    follow_up_rate = float(sweep["follow_up_rate"])
    specificity_values = sweep["specificity_values"]
    cancers = params["cancers"]

    rows: List[Dict[str, float]] = []
    for spec in specificity_values:
        for cancer in cancers:
            modified_cancer = {**cancer, "specificity": float(spec)}
            row = compute_outcomes(population, modified_cancer, follow_up_rate)
            row["sweep_specificity"] = spec
            rows.append(row)

    return pd.DataFrame(rows)


def add_capacity_metrics(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """Add capacity utilization percentages using baseline capacity values."""
    population = int(params["simulation"]["screened_population"])
    capacity = params["capacity"]
    scale = population / 100_000.0

    result = df.copy()
    modality_map = {
        "ct_visits": "ct_exams_per_year",
        "mri_visits": "mri_exams_per_year",
        "endoscopy_visits": "endoscopy_exams_per_year",
        "primary_care_visits": "primary_care_visits_per_year",
    }
    for visits_col, cap_col in modality_map.items():
        cap = capacity.get(cap_col, 0.0) * scale
        result[f"{visits_col}_utilization_pct"] = (
            100.0 * result[visits_col] / cap if cap > 0 else 0.0
        )

    # Specialist burden includes both the initial consultation and the
    # follow-up/oncology visits counted in additional_visits.
    if "specialist_visits" in result.columns and "additional_visits" in result.columns:
        result["specialist_total_visits"] = (
            result["specialist_visits"] + result["additional_visits"]
        )
        spec_cap = capacity["specialist_visits_per_year"] * scale
        result["specialist_total_visits_utilization_pct"] = (
            100.0 * result["specialist_total_visits"] / spec_cap if spec_cap > 0 else 0.0
        )

    # Overall strain = maximum utilization across the tracked resources.
    utilization_cols = [f"{c}_utilization_pct" for c in modality_map] + [
        "specialist_total_visits_utilization_pct"
    ]
    result["max_capacity_utilization_pct"] = result[utilization_cols].max(axis=1)

    return result


def aggregate_by_follow_up(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe aggregated across cancer types for each follow-up rate."""
    numeric_cols = [c for c in df.columns if c not in ("cancer", "follow_up_rate")]
    # Keep rate columns that make sense after summation.
    sum_cols = [
        "true_positives",
        "false_positives",
        "total_positives",
        "followed_positives",
        "followed_true_positives",
        "followed_false_positives",
        "additional_visits",
        "total_visits",
        "ct_visits",
        "mri_visits",
        "endoscopy_visits",
        "specialist_visits",
        "fp_specialist_visits",
        "tp_specialist_visits",
        "primary_care_visits",
    ]
    grouped = df.groupby("follow_up_rate", as_index=False)[sum_cols].sum()

    # Recompute aggregate PPV and ratios from the summed counts.
    grouped["ppv"] = grouped["true_positives"] / grouped["total_positives"]
    grouped["fp_to_tp_ratio"] = grouped["false_positives"] / grouped["true_positives"]
    grouped["visits_per_detected_case"] = (
        grouped["total_visits"] / grouped["true_positives"]
    )
    return grouped


def _save_plot(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=1000, bbox_inches="tight")
    plt.close(fig)


def plot_total_visits(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Stacked area chart: total downstream visits by cancer type and follow-up rate."""
    pivot = df.pivot(index="follow_up_rate", columns="cancer", values="total_visits")

    fig, ax = plt.subplots(figsize=(10, 6))
    pivot.plot.area(ax=ax, alpha=0.8, colormap="tab10")

    ax.set_xlabel("Follow-up rate after a positive test")
    ax.set_ylabel("Additional visits per 100,000 screened")
    ax.set_title(
        "Downstream healthcare visits generated by direct-to-consumer cancer blood tests"
    )
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    _save_plot(fig, output_path)


def plot_capacity_utilization(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Line chart of capacity utilization by modality versus follow-up rate."""
    agg = (
        df.groupby("follow_up_rate", as_index=False)[
            [
                "ct_visits_utilization_pct",
                "mri_visits_utilization_pct",
                "endoscopy_visits_utilization_pct",
                "specialist_total_visits_utilization_pct",
                "primary_care_visits_utilization_pct",
            ]
        ]
        .sum()
        .copy()
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    for col, label in [
        ("ct_visits_utilization_pct", "CT"),
        ("mri_visits_utilization_pct", "MRI"),
        ("endoscopy_visits_utilization_pct", "Endoscopy"),
        ("specialist_total_visits_utilization_pct", "Specialist visits (incl. follow-up)"),
        ("primary_care_visits_utilization_pct", "Primary care visits"),
    ]:
        ax.plot(
            agg["follow_up_rate"],
            agg[col],
            marker="o",
            label=label,
        )

    ax.axhline(100.0, color="red", linestyle="--", linewidth=1.2, label="100% capacity")
    ax.set_xlabel("Follow-up rate after a positive test")
    ax.set_ylabel("Capacity utilization (% of annual cancer-diagnostic baseline)")
    ax.set_title(
        "Capacity utilization of diagnostic resources by follow-up rate"
    )
    ax.legend()
    ax.set_ylim(bottom=0)
    _save_plot(fig, output_path)


def plot_ppv_by_cancer(
    df: pd.DataFrame,
    output_path: Path,
    follow_up_rate: float = 0.5,
) -> None:
    """Bar chart of PPV by cancer type at a chosen follow-up rate."""
    sub = df[df["follow_up_rate"] == follow_up_rate].copy()
    sub = sub.sort_values("ppv", ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(sub["cancer"], sub["ppv"] * 100.0, color="steelblue")
    ax.set_xlabel("Positive predictive value (%)")
    ax.set_title(f"PPV by cancer type at follow-up rate = {follow_up_rate:.0%}")
    max_ppv = max(sub["ppv"].max() * 100 * 1.1, 1.0)
    ax.set_xlim(0, min(100.0, max_ppv))
    _save_plot(fig, output_path)


def plot_false_positives_by_cancer(
    df: pd.DataFrame,
    output_path: Path,
    follow_up_rate: float = 0.5,
) -> None:
    """Bar chart of false positives vs true positives by cancer type."""
    sub = df[df["follow_up_rate"] == follow_up_rate].copy()
    sub = sub.sort_values("false_positives", ascending=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(sub))
    width = 0.35
    ax.barh(y - width / 2, sub["true_positives"], width, label="True positives", color="darkgreen")
    ax.barh(y + width / 2, sub["false_positives"], width, label="False positives", color="firebrick")
    ax.set_yticks(y)
    ax.set_yticklabels(sub["cancer"])
    ax.set_xlabel("Expected count per 100,000 screened")
    ax.set_title(f"True vs false positives at follow-up rate = {follow_up_rate:.0%}")
    ax.legend()
    _save_plot(fig, output_path)


def plot_specificity_sweep(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Total false positives and total visits as specificity varies."""
    agg = (
        df.groupby("sweep_specificity", as_index=False)[
            ["true_positives", "false_positives", "total_visits"]
        ]
        .sum()
        .copy()
    )

    fig, ax1 = plt.subplots(figsize=(9, 6))
    color = "firebrick"
    ax1.set_xlabel("Test specificity (assumed same for all cancers)")
    ax1.set_ylabel("False positives per 100,000 screened", color=color)
    ax1.plot(
        agg["sweep_specificity"],
        agg["false_positives"],
        marker="o",
        color=color,
        linewidth=2,
    )
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.set_ylim(bottom=0)

    ax2 = ax1.twinx()
    color = "steelblue"
    ax2.set_ylabel("Total downstream visits per 100,000 screened", color=color)
    ax2.plot(
        agg["sweep_specificity"],
        agg["total_visits"],
        marker="s",
        color=color,
        linewidth=2,
    )
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(bottom=0)

    ax1.set_title(
        "Impact of test specificity on false positives and downstream workload"
    )
    _save_plot(fig, output_path)


def format_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Round numeric columns for cleaner CSV output.

    Ratio columns (PPV, FP/TP, capacity utilisation percentages) are kept at
    higher precision so downstream prose can recompute consistent percentages.
    """
    out = df.copy()
    ratio_indicators = {"ppv", "fp_to_tp_ratio", "visits_per_detected_case"}
    for col in out.select_dtypes(include=[np.floating]).columns:
        if col in ratio_indicators or col.endswith("_utilization_pct"):
            out[col] = out[col].round(6)
        else:
            out[col] = out[col].round(3)
    return out


def find_capacity_threshold(df: pd.DataFrame, threshold: float = 100.0) -> str:
    """Return the lowest follow-up rate at which any resource exceeds threshold."""
    over = df[df["max_capacity_utilization_pct"] >= threshold]
    if over.empty:
        return "not reached in the scanned range"
    rate = over["follow_up_rate"].min()
    row = over[over["follow_up_rate"] == rate].iloc[0]

    utilization_cols = [c for c in row.index if c.endswith("_utilization_pct") and c != "max_capacity_utilization_pct"]
    constrained = row[utilization_cols].idxmax()
    resource = constrained.replace("_utilization_pct", "").replace("_", " ").title()
    return f"{rate:.0%} ({resource})"


def choose_summary_rate(follow_up_rates: List[float], target: float = 0.5) -> float:
    """Pick the follow-up rate in the list closest to the requested target."""
    if not follow_up_rates:
        raise ValueError("follow_up_rates must not be empty")
    return min(follow_up_rates, key=lambda r: abs(r - target))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate healthcare burden from direct-to-consumer cancer blood tests."
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=Path("parameters.yaml"),
        help="Path to parameters.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directory for CSV and PNG outputs",
    )
    args = parser.parse_args()

    params = load_parameters(args.params)
    args.output.mkdir(parents=True, exist_ok=True)

    # Main follow-up sweep.
    df = run_follow_up_sweep(params)
    df = add_capacity_metrics(df, params)

    agg = aggregate_by_follow_up(df)
    agg = add_capacity_metrics(agg, params)

    # Specificity sensitivity analysis.
    spec_df = run_specificity_sweep(params)
    spec_df = add_capacity_metrics(spec_df, params)

    # Save CSVs.
    format_csv(df).to_csv(args.output / "by_cancer_and_followup.csv", index=False)
    format_csv(agg).to_csv(args.output / "aggregate_by_followup.csv", index=False)
    format_csv(spec_df).to_csv(args.output / "specificity_sweep.csv", index=False)

    # Default summary at a representative follow-up rate.
    follow_up_rates = params["simulation"]["follow_up_rates"]
    default_rate = choose_summary_rate(follow_up_rates, target=0.5)
    summary = df[df["follow_up_rate"] == default_rate].copy()
    format_csv(summary).to_csv(args.output / "summary_default_followup.csv", index=False)

    # Plots.
    plot_total_visits(df, args.output / "total_visits_by_followup.png")
    plot_capacity_utilization(df, args.output / "capacity_utilization.png")
    plot_ppv_by_cancer(df, args.output / "ppv_by_cancer.png", default_rate)
    plot_false_positives_by_cancer(df, args.output / "false_positives_by_cancer.png", default_rate)
    plot_specificity_sweep(spec_df, args.output / "specificity_sweep.png")

    # Console summary for the user.
    print("=" * 60)
    print("Cancer-screening burden simulation")
    print("=" * 60)
    print(f"Screened population: {params['simulation']['screened_population']:,}")
    print(
        f"Annual baseline capacities (per 100,000): "
        f"CT={params['capacity']['ct_exams_per_year']:,}, "
        f"MRI={params['capacity']['mri_exams_per_year']:,}, "
        f"Endoscopy={params['capacity']['endoscopy_exams_per_year']:,}, "
        f"Specialist={params['capacity']['specialist_visits_per_year']:,}, "
        f"Primary care={params['capacity'].get('primary_care_visits_per_year', 0):,}"
    )
    print()

    print(f"At {default_rate:.0%} follow-up rate, per 100,000 screened:")
    row = agg[agg["follow_up_rate"] == default_rate].iloc[0]
    print(f"  True positives  : {row['true_positives']:.1f}")
    print(f"  False positives : {row['false_positives']:.1f}")
    print(f"  Total positives : {row['total_positives']:.1f}")
    print(f"  Overall PPV     : {row['ppv']*100:.2f}%")
    print(f"  Total visits    : {row['total_visits']:.1f}")
    print(f"  FP/TP ratio     : {row['fp_to_tp_ratio']:.1f}")
    print(f"  Max resource utilization: {row['max_capacity_utilization_pct']:.2f}%")
    print()
    print(
        f"Lowest follow-up rate where any illustrative capacity exceeds 100%: "
        f"{find_capacity_threshold(agg)}"
    )
    print(f"Outputs written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
