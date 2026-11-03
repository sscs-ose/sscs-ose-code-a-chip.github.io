// Render the 50 reference schematics (Analog Canvas SVG exports) to PNG thumbnails.
// Usage: node tools/render_thumbnails.mjs SVG_DIR OUT_DIR [WIDTH]   (needs the playwright package)
import { chromium } from "playwright";
import { readdirSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
const [src, out, width] = [process.argv[2], process.argv[3], Number(process.argv[4] || 560)];
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });
for (const f of readdirSync(src).filter((n) => n.endsWith(".svg")).sort()) {
  await page.setContent(`<html><body style="margin:0;background:#fff"><img id="s" src="data:image/svg+xml;base64,${readFileSync(join(src, f)).toString("base64")}" style="width:${width}px;display:block"></body></html>`);
  await page.waitForFunction(() => document.getElementById("s").complete);
  await page.locator("#s").screenshot({ path: join(out, f.replace(/\.svg$/, ".png")) });
}
await browser.close();
console.log("done");
