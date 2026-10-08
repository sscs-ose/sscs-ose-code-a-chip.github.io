import argparse
from dataclasses import asdict
import json

from .experiments import run_experiment, summary
from .plots import render
from .spice import ROOT, Point, Simulator, measure


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible SKY130 comparator experiments")
    parser.add_argument("command", choices=(
        "smoke", "run", "render", "summary", "optimize", "study", "comparison", "stress", "report",
    ))
    parser.add_argument("--profile", choices=("quick", "full"), default="quick")
    args = parser.parse_args()
    output = ROOT / "results" / args.profile
    if args.command == "stress":
        from .stress import run_stress
        print(run_stress())
    elif args.command == "report":
        from .study_report import render_study
        print(render_study())
    elif args.command == "comparison":
        from .stress import verified_comparison
        print(verified_comparison().to_string())
    elif args.command in ("optimize", "study"):
        from .study import comparison, optimize, validate_full
        if args.command == "optimize":
            print(optimize())
        elif args.command == "study":
            print(validate_full())
            print("Initial fixed-step screening only; run stress and comparison for numerically verified results.")
            print(comparison().to_string())
    elif args.command == "smoke":
        sim = Simulator(output / "runs")
        for differential in (-0.03, 0.03):
            trace = sim.run(Point(differential_v=differential))
            result = measure(trace, 2)
            if result.outcome != "correct":
                raise RuntimeError(f"Comparator polarity smoke failed: {result}")
            print(json.dumps({"input_mv": 1000 * differential, **asdict(result)}, indent=2))
    elif args.command == "run":
        run_experiment(args.profile)
        print(summary(output).to_string())
        print(f"Report: {render(output)}")
    elif args.command == "render":
        print(render(output))
    else:
        print(summary(output).to_string())


if __name__ == "__main__":
    main()
