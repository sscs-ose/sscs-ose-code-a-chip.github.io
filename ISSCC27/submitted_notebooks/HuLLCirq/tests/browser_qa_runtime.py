"""Optional local browser-fixture dependency; no download or product connection."""
import os
from pathlib import Path


def browser_environment():
    environment = os.environ.copy()
    if not environment.get('HULLCIRQ_PLAYWRIGHT_PATH'):
        bundled = (Path.home() / '.cache/codex-runtimes/codex-primary-runtime'
                   / 'dependencies/node/node_modules/playwright')
        if bundled.is_dir():
            environment['HULLCIRQ_PLAYWRIGHT_PATH'] = str(bundled)
    return environment
