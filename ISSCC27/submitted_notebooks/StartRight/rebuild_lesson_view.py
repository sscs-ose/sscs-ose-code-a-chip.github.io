"""Rebuild the saved-data browser lesson and overview, without running SPICE.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import json
import matplotlib.pyplot as plt
from reference_evidence import audit
from lesson_decision import overview, export_browser
from check_lesson_decision import checks


def main():
    here = Path(__file__).resolve().parent
    record = audit()
    print(json.dumps(checks(record), indent=2))
    folder = here / 'figures'; folder.mkdir(exist_ok=True)
    figure = overview(record)
    figure.savefig(folder / 'decision_overview.png', dpi=160)
    plt.close(figure)
    export_browser(record, here)
    print('Rebuilt Explore_reset.html, lesson_view.json and the measured overview from saved audited data.')


if __name__ == '__main__':
    main()
