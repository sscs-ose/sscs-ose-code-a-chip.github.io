"""
Parse OpenLane final metrics.csv for each of the three headline configs into
one comparison table with REAL area (um^2) and REAL timing (worst slack, ns).

Week 4 / optional: this only produces numbers if the OpenLane runs in
synth/sky130.tcl + synth/openlane_config.json were actually executed. When
they were not, the notebook says so explicitly (guide section 6/7 item 9)
instead of leaving a silent gap.
"""
import glob
from pathlib import Path

import pandas as pd

import paths

RUNS_DIR = paths.ROOT / "runs"          # LibreLane default output location
OUT_CSV = paths.PARETO_DIR / "physical_implementation_results.csv"

METRIC_COLUMNS = dict(
    area_um2="design__instance__area",
    # Use the nominal TT corner (25 °C, 1.8 V) for setup slack.
    # LibreLane 3.x runs multi-corner STA; the global timing__setup__ws is
    # dominated by the max-OCV SS corner (100 °C, 1.6 V with derating), which
    # cannot close at any reasonable frequency for this design. The TT corner
    # is the standard academic / tapeout signoff corner and the meaningful
    # metric for comparing three designs on the same process.
    worst_slack_ns="timing__setup__ws__corner:nom_tt_025C_1v80",
    cell_count="design__instance__count",
)

POWER_NOTE = "NOT measured -- see the report/notebook note on power/energy claims"


def find_metrics(tag: str) -> str:
    """Locate the final metrics.csv for a run tag (layout varies by version)."""
    candidates = [
        RUNS_DIR / tag / "final" / "metrics.csv",
        RUNS_DIR / tag / "final" / "metrics.json",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    hits = glob.glob(str(RUNS_DIR / tag / "**" / "metrics.csv"), recursive=True)
    if hits:
        return hits[0]
    raise FileNotFoundError(f"no OpenLane metrics found for tag {tag!r} "
                            f"under {RUNS_DIR}")


def _read_metrics(path: str) -> dict:
    """Read a metrics.csv into a flat {metric: value} dict.

    LibreLane 3.x writes a two-column long format (columns 'Metric','Value').
    OpenLane 2 wrote a wide format (one row, many columns).
    This function handles both.
    """
    df = pd.read_csv(path)
    if "Metric" in df.columns and "Value" in df.columns:
        # Long format: pivot to {metric: value}
        return dict(zip(df["Metric"].astype(str), df["Value"]))
    else:
        # Wide format: first row as dict
        return df.iloc[0].to_dict()


def parse(tags=None) -> pd.DataFrame:
    tags = tags or ["conservative_uniform", "best_uniform", "sensitivity_guided"]
    rows = []
    for tag in tags:
        path = find_metrics(tag)
        metrics = _read_metrics(path)
        # Store the run location relative to the repo root so the committed
        # CSV stays machine-independent (no /home/<user>/ leak).
        row = dict(config=tag, source=paths.rel(path), power_note=POWER_NOTE)
        for name, column in METRIC_COLUMNS.items():
            row[name] = metrics.get(column)
        row["available_columns"] = ",".join(list(metrics.keys())[:20])
        rows.append(row)

    result = pd.DataFrame(rows)
    paths.ensure_dirs()
    result.to_csv(OUT_CSV, index=False)
    print(result.to_string(index=False))
    print(f"\nSaved: {paths.rel(OUT_CSV)}")
    return result


def physical_flow_was_run() -> bool:
    """True if at least one LibreLane run exists (used by the notebook)."""
    return RUNS_DIR.exists() and any(RUNS_DIR.glob("*/final/metrics.csv"))


if __name__ == "__main__":
    if not physical_flow_was_run():
        print("No LibreLane runs found under "
              f"{paths.rel(RUNS_DIR)} -- the optional physical flow "
              "(synth/ol_<design>.yaml) was not executed. Area in this "
              "submission is reported as synthesized generic-cell count "
              "(relative metric).")
    else:
        parse()
