"""Export representative SVG scenes and create the concise launch notebook."""

from pathlib import Path
import argparse
import shutil
import subprocess
import tempfile

import nbformat

from riscv_memory_visualizer.simulation.teaching import SRAMTeachingController
from riscv_memory_visualizer.visualization.schematic_svg import render_scene


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "00_launch_visualizer.ipynb"
ADVANCED = ROOT / "notebooks" / "01_development_walkthrough.ipynb"
PREVIEWS = ROOT / "docs" / "previews" / "teaching"


def main(*, previews_only=False):
    if not previews_only:
        if not ADVANCED.exists():
            shutil.copy2(NOTEBOOK, ADVANCED)
        notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell("# Inside SRAM\n\nExplore one memory access through decoding, a selected 6T bitcell, and its logical read or write sequence. Use **Previous**, **Next**, and **Restart** to control the lesson."),
        nbformat.v4.new_markdown_cell("## Launch Interactive Teaching Mode"),
        nbformat.v4.new_code_cell("from riscv_memory_visualizer.ui.teaching_app import SRAMTeachingApp\n\napp = SRAMTeachingApp()\napp.display()"),
        nbformat.v4.new_markdown_cell("## Optional Technical Details\n\nExpand **Technical Details** in the app for access metadata. The [development walkthrough](01_development_walkthrough.ipynb) preserves the detailed demonstrations. The earlier dashboard remains available with `from riscv_memory_visualizer.ui.app import RiscVMemoryVisualizerApp`. Logical timing is not analog SPICE timing."),
        ])
        nbformat.write(notebook, NOTEBOOK)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    read = SRAMTeachingController("READ")
    write = SRAMTeachingController("WRITE")
    choices = [
        ("slide_02_sram_macro", read.steps[1]),
        ("slide_03_address_decode", read.steps[2]),
        ("slide_04_selected_row", read.steps[3]),
        ("slide_05_selected_column", read.steps[4]),
        ("slide_06_selected_bitcell", read.steps[5]),
        ("slide_07_bitcell_closeup", read.steps[6]),
        ("slide_08_cross_coupled_inverters", read.steps[7]),
        ("slide_12_bit_line_pair", read.steps[11]),
        ("read_slide_13_precharge", read.steps[12]),
        ("read_slide_16_sense_amplifier", read.steps[15]),
        ("write_slide_13_write_driver", write.steps[12]),
        ("write_slide_16_cell_overwrite", write.steps[15]),
        ("read_slide_18_summary", read.steps[-1]),
        ("write_slide_18_summary", write.steps[-1]),
    ]
    for name, step in choices:
        (PREVIEWS / f"{name}.svg").write_text(render_scene(step), encoding="utf-8")
    (PREVIEWS / "README.md").write_text(
        "# Teaching scene previews\n\nThese fourteen SVGs were exported from real controller snapshots. "
        "The read demo uses `lw x5,8(x2)` with explicitly seeded address 8 = 1. "
        "The write demo uses `sw x1,8(x2)` after loading x1 = 1. "
        "All circuit states are logical educational states. Matching PNGs are "
        "rendered when CairoSVG or headless Chrome is available.\n", encoding="utf-8")
    try:
        import cairosvg
    except (ImportError, OSError):
        cairosvg = None
    if cairosvg is not None:
        for name, _ in choices:
            cairosvg.svg2png(url=str(PREVIEWS / f"{name}.svg"),
                             write_to=str(PREVIEWS / f"{name}.png"), output_width=960, output_height=540)
        return
    browser = next((path for path in (
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    ) if path.exists()), None)
    if browser is None:
        return
    with tempfile.TemporaryDirectory(prefix="sram-preview-") as profile:
        for name, _ in choices:
            subprocess.run([
                str(browser), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                f"--user-data-dir={profile}", "--virtual-time-budget=4500",
                "--window-size=960,540",
                f"--screenshot={PREVIEWS / (name + '.png')}",
                (PREVIEWS / f"{name}.svg").resolve().as_uri(),
            ], check=True, capture_output=True, timeout=30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previews-only", action="store_true", help="Keep the source notebook unchanged")
    args = parser.parse_args()
    main(previews_only=args.previews_only)
