"""Static screenshot of an interactive GlitchScope report (for viewers that do not run scripts, e.g. GitHub).

    python scripts/report_screenshot.py data/notebook/mac_flow/report.html data/notebook/mac_flow/report.png
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 770}, device_scale_factor=1)
        pg.emulate_media(color_scheme="light")
        pg.goto(src.as_uri())
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(dst), full_page=False)
        b.close()
    print("wrote", dst)


if __name__ == "__main__":
    main()
