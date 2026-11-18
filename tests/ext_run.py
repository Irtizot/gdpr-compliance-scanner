import json
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from common import ARGS, BASE, FIXTURES

HERE = Path(__file__).resolve().parent
EXT = str(HERE.parent / "src" / "extension")
PROFILE = tempfile.mkdtemp(prefix="extprofile_")
QUERY = ("async (u) => { const [t] = await chrome.tabs.query({url: u}); "
         "return t ? await buildReport(t.id) : {error: 'no_tab'}; }")


def settled(report):
    return "error" not in report and not report["scanning"] and not report["observationOpen"]


out = {}
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        PROFILE, headless=False, ignore_https_errors=True,
        args=ARGS + [f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
    worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
    warm = context.new_page()
    warm.goto(BASE + "nobanner.html", wait_until="domcontentloaded")
    time.sleep(5)
    warm.close()
    for name in FIXTURES:
        page = context.new_page()
        url = BASE + name + ".html"
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(5)
        report = worker.evaluate(QUERY, url)
        waited = 0
        while not settled(report) and waited < 40:
            time.sleep(2)
            waited += 2
            report = worker.evaluate(QUERY, url)
        out[name] = report
        page.close()
    context.close()

with open(HERE / "ext_out.json", "w") as f:
    json.dump(out, f, indent=1)
print("done")