// Prints the built HTML to PDF once the fonts are actually ready.
//
// Chrome's own --print-to-pdf does not wait for a web font: a face that is
// first needed on a later page misses the print and the text comes out in a
// system font, or not at all. Driving the same Chrome through the DevTools
// protocol lets us wait for document.fonts.ready first.
//
// Called from build.sh, which installs puppeteer-core into a temporary folder
// and points NODE_PATH at it, so nothing is added to the repository.
const puppeteer = require("puppeteer-core");

const CHROME = process.env.CHROME ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

(async () => {
  const [html, out] = process.argv.slice(2);
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--allow-file-access-from-files", "--disable-gpu"],
  });
  const page = await browser.newPage();
  await page.goto("file://" + html, { waitUntil: "networkidle0", timeout: 180000 });
  await page.evaluateHandle("document.fonts.ready");
  await page.pdf({
    path: out,
    printBackground: true,
    preferCSSPageSize: true,
    timeout: 300000,
  });
  await browser.close();
})();
