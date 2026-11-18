import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src" / "stage2_banner"))

import pipeline as P
from playwright.sync_api import sync_playwright
from common import ARGS, BASE, FIXTURES


def count_checkboxes(banner):
    total = pre = 0
    boxes = banner.locator("input[type='checkbox']")
    for i in range(min(boxes.count(), 30)):
        box = boxes.nth(i)
        total += 1
        if box.is_checked() and not box.is_disabled():
            pre += 1
    return total, pre


out = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=ARGS)
    for name in FIXTURES:
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        hosts = P.watch_requests(page)
        url = BASE + name + ".html"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(P.SETTLE_MS)
        tracking = P.summarise_tracking(url, hosts, context.cookies())
        element, selector, text = P.find_banner(page)
        result = {"banner": element is not None, "tracking": tracking}
        if element is not None:
            found = P.classify_buttons(element)
            measures = P.compare_buttons(found)
            total, pre = count_checkboxes(element)
            result.update(
                selector=selector,
                pattern=P.first_layer_pattern(found),
                accept=found["accept"],
                reject=found["reject"],
                settings=found["settings"],
                acc_style=(measures["accept"] or {}).get("style"),
                rej_style=(measures["reject"] or {}).get("style"),
                size_ratio=measures["size_ratio"],
                contrast_diff=measures["contrast_diff"],
                size_flag=measures["size_flag"],
                contrast_flag=measures["contrast_flag"],
                style_flag=measures["style_asymmetry_flag"],
                cb=[total, pre],
                lang=P.wording_flags(text, found),
            )
        out[name] = result
        context.close()
    browser.close()

with open(HERE / "py_out.json", "w") as f:
    json.dump(out, f, indent=1)
print("done")