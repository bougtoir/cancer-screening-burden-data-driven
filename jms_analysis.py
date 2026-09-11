"""Journal-specific supplementary analysis and figure rendering for the JMS package.

Reads parameters.yaml and the CSV outputs written by simulate.py,
age_analysis.py and sensitivity_analysis.py, and writes to ``output/``:

  - jms_prevalence_sensitivity.csv   Aggregate outcomes when the incidence-based
                                      prevalence proxy is scaled by 0.25-2.0x
  - jms_figures/*.png                 Re-rendered figures (UK spelling, no
                                      in-figure titles, 600 dpi) used by
                                      build_jms_manuscript.py

Model logic is reused from simulate.py / sensitivity_analysis.py; nothing is
recomputed by hand.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from prepare_parameters import ADULT_COLS, AVAILABLE_CANCER_SHARE  # noqa: E402
from sensitivity_analysis import _add_metric_cols, simulate_aggregate  # noqa: E402

PREVALENCE_MULTIPLIERS = [0.25, 0.5, 1.0, 1.5, 2.0]
FIGURE_DPI = 600

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def _base_kwargs(params: Dict[str, Any]) -> Dict[str, float]:
    return {
        "specificity": 0.990,
        "follow_up_rate": 0.50,
        "available_share": float(params["assumptions"].get("available_for_cancer_share", AVAILABLE_CANCER_SHARE)),
        "sensitivity": 0.70,
    }


def run_prevalence_sensitivity(params: Dict[str, Any]) -> pd.DataFrame:
    """Scale every cancer's prevalence proxy by a common multiplier and re-run the base case."""
    records: List[Dict[str, Any]] = []
    for mult in PREVALENCE_MULTIPLIERS:
        scaled = dict(params)
        scaled["cancers"] = [
            {**c, "prevalence_per_100k": float(c["prevalence_per_100k"]) * mult} for c in params["cancers"]
        ]
        row = simulate_aggregate(scaled, **_base_kwargs(params))
        metrics = _add_metric_cols(row)
        records.append({"prevalence_multiplier": mult, "true_positives": float(row["true_positives"]),
                        "false_positives": float(row["false_positives"]), **metrics})
    return pd.DataFrame(records)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def fig_capacity_utilisation(agg: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for col, label in [
        ("ct_visits_utilization_pct", "CT"),
        ("mri_visits_utilization_pct", "MRI"),
        ("endoscopy_visits_utilization_pct", "Endoscopy"),
        ("specialist_total_visits_utilization_pct", "Specialist visits (incl. follow-up)"),
        ("primary_care_visits_utilization_pct", "Primary care visits"),
    ]:
        ax.plot(agg["follow_up_rate"] * 100, agg[col], marker="o", markersize=3.5, label=label)
    ax.axhline(100.0, color="red", linestyle="--", linewidth=1.0, label="100% of illustrative capacity")
    ax.set_xlabel("Follow-up rate after a positive test (%)")
    ax.set_ylabel("Capacity utilisation (% of illustrative annual capacity)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)
    _save(fig, path)


def fig_ppv_by_age(age_df: pd.DataFrame, path: Path) -> None:
    adult = [a for a in ADULT_COLS if a in age_df["age_group"].unique()]
    sub_all = age_df[age_df["age_group"].isin(adult)].copy()
    sub_all["age_group"] = pd.Categorical(sub_all["age_group"], categories=adult, ordered=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for cancer in sorted(sub_all["cancer"].unique()):
        sub = sub_all[sub_all["cancer"] == cancer].sort_values("age_group")
        ax.plot([a.replace(" yrs.", "") for a in sub["age_group"].astype(str)], sub["ppv"] * 100.0,
                marker="o", markersize=3.5, label=cancer)
    ax.set_xlabel("Age group (years)")
    ax.set_ylabel("Positive predictive value (%)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _save(fig, path)


def fig_total_visits(by_cancer: pd.DataFrame, path: Path) -> None:
    pivot = by_cancer.pivot(index="follow_up_rate", columns="cancer", values="total_visits")
    pivot.index = pivot.index * 100
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    pivot.plot.area(ax=ax, alpha=0.85, colormap="tab10")
    ax.set_xlabel("Follow-up rate after a positive test (%)")
    ax.set_ylabel("Downstream visits per 100,000 screened")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0), title="Cancer")
    _save(fig, path)


def fig_specificity_sweep(sweep: pd.DataFrame, path: Path) -> None:
    agg = sweep.groupby("sweep_specificity", as_index=False)[["true_positives", "false_positives", "total_visits"]].sum()
    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.plot(agg["sweep_specificity"], agg["false_positives"], marker="o", color="firebrick", linewidth=2)
    ax1.set_xlabel("Test specificity (assumed identical for all cancers)")
    ax1.set_ylabel("False positives per 100,000 screened", color="firebrick")
    ax1.tick_params(axis="y", labelcolor="firebrick")
    ax1.set_ylim(bottom=0)
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(agg["sweep_specificity"], agg["total_visits"], marker="s", color="steelblue", linewidth=2)
    ax2.set_ylabel("Total downstream visits per 100,000 screened", color="steelblue")
    ax2.tick_params(axis="y", labelcolor="steelblue")
    ax2.set_ylim(bottom=0)
    _save(fig, path)


_TORNADO_LABELS = {
    "specificity": "Specificity (0.950-0.999)",
    "follow_up_rate": "Follow-up rate (10-90%)",
    "available_share": "Available capacity share (5-50%)",
    "sensitivity": "Sensitivity (0.50-0.90)",
}


def fig_tornado(params: Dict[str, Any], sens: pd.DataFrame, metric: str, xlabel: str, path: Path) -> None:
    base = _add_metric_cols(simulate_aggregate(params, **_base_kwargs(params)))[metric]
    low = sens.groupby("parameter")[metric].min().reindex(list(_TORNADO_LABELS))
    high = sens.groupby("parameter")[metric].max().reindex(list(_TORNADO_LABELS))
    order = (high - low).sort_values().index
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    y = range(len(order))
    ax.barh(y, high[order] - base, left=base, color="steelblue", label="Upper bound of range")
    ax.barh(y, low[order] - base, left=base, color="coral", label="Lower bound of range")
    ax.axvline(base, color="black", linestyle="--", linewidth=1, label="Base case")
    ax.set_yticks(list(y))
    ax.set_yticklabels([_TORNADO_LABELS[p] for p in order])
    ax.set_xlabel(xlabel)
    ax.legend(frameon=False, loc="lower right")
    _save(fig, path)


_SCENARIO_LABELS = {
    "japan_total_2023": "Japan total population 2023",
    "japan_adult_20plus": "Japan adults (20+)",
    "dtc_bimodal_23andme": "DTC bimodal",
    "dtc_younger": "DTC younger",
    "dtc_screening_age": "DTC screening age",
}


def fig_age_scenarios(scen: pd.DataFrame, path: Path) -> None:
    cancers = sorted(scen["cancer"].unique())
    dists = list(dict.fromkeys(scen["distribution"]))
    width = 0.8 / len(dists)
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for i, dist in enumerate(dists):
        sub = scen[scen["distribution"] == dist].set_index("cancer").reindex(cancers)
        ax.bar([p + width * (i - (len(dists) - 1) / 2) for p in range(len(cancers))], sub["ppv"] * 100.0,
               width=width, label=_SCENARIO_LABELS.get(str(dist), str(dist)))
    ax.set_xticks(range(len(cancers)))
    ax.set_xticklabels(cancers)
    ax.set_ylabel("Aggregate positive predictive value (%)")
    ax.set_xlabel("Cancer")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)
    _save(fig, path)


def render_figures(params: Dict[str, Any], output: Path, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    agg = pd.read_csv(output / "aggregate_by_followup.csv")
    by_cancer = pd.read_csv(output / "by_cancer_and_followup.csv")
    age_df = pd.read_csv(output / "age_specific_ppv.csv")
    sweep = pd.read_csv(output / "specificity_sweep.csv")
    sens = pd.read_csv(output / "sensitivity_summary.csv")
    scen = pd.read_csv(output / "age_scenarios.csv")

    fig_capacity_utilisation(agg, fig_dir / "capacity_utilisation.png")
    fig_ppv_by_age(age_df, fig_dir / "ppv_by_age.png")
    fig_total_visits(by_cancer, fig_dir / "total_visits_by_followup.png")
    fig_specificity_sweep(sweep, fig_dir / "specificity_sweep.png")
    fig_tornado(params, sens, "max_capacity_utilization_pct",
                "Maximum capacity utilisation (%)", fig_dir / "tornado_max_capacity.png")
    fig_tornado(params, sens, "ppv_pct", "Aggregate positive predictive value (%)", fig_dir / "tornado_ppv.png")
    fig_age_scenarios(scen, fig_dir / "age_scenario_ppv.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="JMS-specific supplementary analysis and figures")
    parser.add_argument("--params", type=Path, default=Path("parameters.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    with open(args.params, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    prev = run_prevalence_sensitivity(params)
    prev.to_csv(args.output / "jms_prevalence_sensitivity.csv", index=False)
    print(prev[["prevalence_multiplier", "ppv_pct", "fp_tp_ratio", "max_capacity_utilization_pct"]].to_string(index=False))

    render_figures(params, args.output, args.output / "jms_figures")
    print(f"Wrote {args.output / 'jms_figures'}")


if __name__ == "__main__":
    main()
