// Screenshots of degraded HTML emails, taken the way the runner (scripts/compare-setf.ts, screenshotAll)
// takes them: headless Chromium (Playwright 1.56.1, chromium-1194), desktop viewport 700 x 900 and phone
// 375 x 800, device scale 1, file:// URL, waitUntil networkidle (60 s, errors ignored), 500 ms settle,
// full-page PNG. Also records the phone render's scroll width in render.json, as the runner does.
//
// usage: node render-degraded.mjs <jobs.json>   with jobs = [{ "html": "/abs/email.degraded.html", "outDir": "/abs/dir" }]
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("<home>/alpaca-relay/saas/next/email-platform/node_modules/.pnpm/playwright@1.56.1/node_modules/playwright");
const PHONE_WIDTH = 375;

const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const browser = await chromium.launch();
try {
	const desktop = await browser.newPage({ viewport: { width: 700, height: 900 } });
	const phone = await browser.newPage({ viewport: { width: PHONE_WIDTH, height: 800 } });
	for (const job of jobs) {
		if (!existsSync(job.html)) { console.log("missing", job.html); continue; }
		const png = path.join(job.outDir, "screenshot.png");
		await desktop.goto(`file://${job.html}`, { waitUntil: "networkidle", timeout: 60_000 }).catch(() => {});
		await desktop.waitForTimeout(500);
		await desktop.screenshot({ path: png, fullPage: true });
		const phonePng = path.join(job.outDir, "screenshot-phone.png");
		await phone.goto(`file://${job.html}`, { waitUntil: "networkidle", timeout: 60_000 }).catch(() => {});
		await phone.waitForTimeout(500);
		await phone.screenshot({ path: phonePng, fullPage: true });
		const info = { phoneScrollWidth: await phone.evaluate(() => document.documentElement.scrollWidth) };
		writeFileSync(path.join(job.outDir, "render.json"), JSON.stringify(info));
		console.log("ok", job.outDir, JSON.stringify(info));
	}
} finally {
	await browser.close();
}
