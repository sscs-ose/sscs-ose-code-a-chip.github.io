"""Reuse the reviewed actual-Magic-paint renderer for compact placement."""
from pathlib import Path

DEST = Path(__file__).resolve().parent
renderer = DEST.parent/'clock_layout_review/plot_layout.py'
source = renderer.read_text()
assert source.count("source = DEST/'provenance/microrobot_clock.mag'") == 1
source = source.replace("source = DEST/'provenance/microrobot_clock.mag'", "source = DEST/'physical/microrobot_clock.mag'")
source = source.replace('Actual full-clock Magic layout — prototype floorplan',
                        'Compact clock placement — actual Magic paint')
exec(compile(source, str(renderer), 'exec'), {'__file__':str(DEST/'plot_layout.py'), '__name__':'__main__'})
