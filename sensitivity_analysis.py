"""Multi-way sensitivity analysis for the cancer-screening burden model.

Vary specificity, follow-up rate, available-for-cancer-workup share, and sensitivity
across plausible ranges.  Outputs a summary CSV and tornado charts showing the effect
of each parameter on aggregate PPV and maximum capacity utilisation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import yaml

from simulate import compute_outcomes, add_capacity_metrics, aggregate_by_follow_up
from prepare_parameters import AVAILABLE_CANCER_SHARE


def _scale_capacity_for_share(params: Dict[str, Any], share: float) -> Dict[str, Any]:
    """Return capacity scaled from the base-case share to the requested share."""
    base_share = float(
        params["assumptions"].get("available_for_cancer_share", AVAILABLE_CANCER_SHARE)
    )
    if base_share <= 0:
        raise ValueError("base available_for_cancer_share must be positive")

    cap = params["capacity"].copy()
    scaled: Dict[str, float] = {}
    for key, value in cap.items():
        if isinstance(value, (int, float)):
            scaled[key] = float(value) / base_share * share
        else:
            scaled[key] = value
    return scaled


def simulate_aggregate(
    params: Dict[str, Any],
    specificity: float,
    follow_up_rate: float,
    available_share: float,
    sensitivity: float | None = None,
) -> pd.Series:
    """Return aggregate metrics for a single parameter combination."""
    population = int(params["simulation"]["screened_population"])

    modified_params = params.copy()
    modified_params["capacity"] = _scale_capacity_for_share(params, available_share)

    rows: List[Dict[str, float]] = []
    for cancer in params["cancers"]:
        mod_cancer = {
            **cancer,
            "specificity": float(specificity),
        }
        if sensitivity is not None:
            mod_cancer["sensitivity"] = float(sensitivity)
        rows.append(compute_outcomes(population, mod_cancer, follow_up_rate))

    df = pd.DataFrame(rows)
    df = add_capacity_metrics(df, modified_params)
    agg = aggregate_by_follow_up(df)
    agg = add_capacity_metrics(agg, modified_params)
    return agg.iloc[0]


def _add_metric_cols(row: pd.Series) -> Dict[str, float]:
    """Select and rename aggregate metrics for the summary table."""
    tp = float(row["true_positives"])
    fp = float(row["false_positives"])
    positives = tp + fp
    ppv = tp / positives if positives > 0 else 0.0
    fp_tp = fp / tp if tp > 0 else float("inf")
    return {
        "ppv_pct": ppv * 100.0,
        "fp_tp_ratio": fp_tp,
        "total_positives": positives,
        "total_visits": float(row["total_visits"]),
        "primary_care_visits": float(row.get("primary_care_visits", 0.0)),
        "primary_care_utilization_pct": float(
            row.get("primary_care_visits_utilization_pct", 0.0)
        ),
        "specialist_total_visits_utilization_pct": float(
            row.get("specialist_total_visits_utilization_pct", 0.0)
        ),
        "max_capacity_utilization_pct": float(row["max_capacity_utilization_pct"]),
    }


def run_sensitivity_grid(params: Dict[str, Any]) -> pd.DataFrame:
    """Run one-way sensitivity analyses for four parameters."""
    base = {
        "specificity": 0.990,
        "follow_up_rate": 0.50,
        "available_share": float(
            params["assumptions"].get("available_for_cancer_share", AVAILABLE_CANCER_SHARE)
        ),
        "sensitivity": 0.70,
    }

    grids = {
        "specificity": [0.950, 0.980, 0.990, 0.995, 0.999],
        "follow_up_rate": [0.10, 0.30, 0.50, 0.70, 0.90],
        "available_share": [0.05, 0.10, 0.20, 0.30, 0.50],
        "sensitivity": [0.50, 0.60, 0.70, 0.80, 0.90],
    }

    records: List[Dict[str, Any]] = []
    for parameter, values in grids.items():
        for value in values:
            kwargs = base.copy()
            kwargs[parameter] = value
            row = simulate_aggregate(
                params,
                specificity=kwargs["specificity"],
                follow_up_rate=kwargs["follow_up_rate"],
                available_share=kwargs["available_share"],
                sensitivity=kwargs["sensitivity"],
            )
            metrics = _add_metric_cols(row)
            records.append(
                {
                    "parameter": parameter,
                    "value": value,
                    **metrics,
                }
            )
    return pd.DataFrame(records)


def _metric_at_base(params: Dict[str, Any]) -> pd.Series:
    base_spec = 0.990
    base_fu = 0.50
    base_share = float(
        params["assumptions"].get("available_for_cancer_share", AVAILABLE_CANCER_SHARE)
    )
    base_sens = 0.70
    row = simulate_aggregate(
        params,
        specificity=base_spec,
        follow_up_rate=base_fu,
        available_share=base_share,
        sensitivity=base_sens,
    )
    return _add_metric_cols(row)


def plot_tornado(
    params: Dict[str, Any],
    output_path: Path,
    metric: str,
    ylabel: str,
    title: str,
) -> None:
    """Plot a tornado diagram for a selected aggregate metric."""
    base = _metric_at_base(params)
    base_value = base[metric]

    grids = {
        "specificity": [0.950, 0.999],
        "follow_up_rate": [0.10, 0.90],
        "available_share": [0.05, 0.50],
        "sensitivity": [0.50, 0.90],
    }

    effects: List[Dict[str, Any]] = []
    for parameter, values in grids.items():
        for value in values:
            kwargs = {
                "specificity": 0.990,
                "follow_up_rate": 0.50,
                "available_share": float(
                    params["assumptions"].get(
                        "available_for_cancer_share", AVAILABLE_CANCER_SHARE
                    )
                ),
                "sensitivity": 0.70,
            }
            kwargs[parameter] = value
            row = simulate_aggregate(
                params,
                specificity=kwargs["specificity"],
                follow_up_rate=kwargs["follow_up_rate"],
                available_share=kwargs["available_share"],
                sensitivity=kwargs["sensitivity"],
            )
            value_metrics = _add_metric_cols(row)
            effects.append(
                {
                    "parameter": parameter,
                    "value": value,
                    metric: value_metrics[metric],
                }
            )

    eff = pd.DataFrame(effects)
    low = (
        eff.groupby("parameter")[metric]
        .min()
        .reindex(["specificity", "follow_up_rate", "available_share", "sensitivity"])
    )
    high = (
        eff.groupby("parameter")[metric]
        .max()
        .reindex(["specificity", "follow_up_rate", "available_share", "sensitivity"])
    )

    labels = {
        "specificity": "Specificity",
        "follow_up_rate": "Follow-up rate",
        "available_share": "Available capacity share",
        "sensitivity": "Sensitivity",
    }

    fig, ax = plt.subplots(figsize=(9, 5))
    y_pos = range(len(low))
    ax.barh(y_pos, high - base_value, left=base_value, color="steelblue", label="High")
    ax.barh(y_pos, low - base_value, left=base_value, color="coral", label="Low")
    ax.axvline(base_value, color="black", linestyle="--", label="Base case")
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels([labels[p] for p in low.index])
    ax.set_xlabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=1000, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-way sensitivity analysis")
    parser.add_argument("--params", type=Path, default=Path("parameters.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    with open(args.params, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    args.output.mkdir(parents=True, exist_ok=True)

    summary = run_sensitivity_grid(params)
    summary.to_csv(args.output / "sensitivity_summary.csv", index=False)

    plot_tornado(
        params,
        args.output / "tornado_max_capacity.png",
        metric="max_capacity_utilization_pct",
        ylabel="Maximum capacity utilisation (%)",
        title="One-way sensitivity: maximum capacity utilisation",
    )
    plot_tornado(
        params,
        args.output / "tornado_ppv.png",
        metric="ppv_pct",
        ylabel="Aggregate PPV (%)",
        title="One-way sensitivity: positive predictive value",
    )

    print("=" * 60)
    print("Multi-way sensitivity analysis")
    print("=" * 60)
    print(summary.to_string(index=False))
    print(f"\nOutputs written to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
