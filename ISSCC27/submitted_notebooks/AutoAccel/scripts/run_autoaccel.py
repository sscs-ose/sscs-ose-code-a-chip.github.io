
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_step(description, command):
    print(f"\n{'=' * 68}", flush=True)
    print(f"STEP: {description}", flush=True)
    print(f"{'=' * 68}", flush=True)

    result = subprocess.run(command, cwd=ROOT)

    if result.returncode != 0:
        print(
            f"\nFAILED: {description} "
            f"(exit code {result.returncode})"
        )
        sys.exit(result.returncode)

    print(f"\nPASSED: {description}", flush=True)


def main():
    python = sys.executable

    run_step(
        "Synthesis",
        [python, str(SCRIPTS / "run_synthesis.py")],
    )

    run_step(
        "Result comparison",
        [python, str(SCRIPTS / "compare_results.py")],
    )

    run_step(
        "Generate graphs",
        [python, str(SCRIPTS / "plot_results.py")],
    )

    run_step(
        "Architecture selection",
        [python, str(SCRIPTS / "select_architecture.py")],
    )

    run_step(
        "Selector unit tests",
        [
            python,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(SCRIPTS),
            "-p",
            "test_select_architecture.py",
            "-v",
        ],
    )

    run_step(
        "Generate project summary",
        [python, str(SCRIPTS / "generate_summary.py")],
    )

    print(f"\n{'=' * 68}")
    print("AUTOACCEL WORKFLOW COMPLETED SUCCESSFULLY")
    print("Review the generated CSV files, logs, and graphs.")
    print(f"{'=' * 68}")


if __name__ == "__main__":
    main()

