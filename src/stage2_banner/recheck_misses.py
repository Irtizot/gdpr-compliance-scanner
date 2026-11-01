import pipeline
from playwright.sync_api import sync_playwright

from pipeline import (USER_AGENT, SETTLE_MS, find_banner, classify_buttons,
                      first_layer_pattern)

print("USING:", pipeline.__file__, "| fixed version:", hasattr(pipeline, "collect_buttons"))

MISSED = [
    "https://www.dailymail.co.uk", "https://www.mirror.co.uk", "https://metro.co.uk",
    "https://www.wayfair.co.uk", "https://www.adobe.com", "https://www.kayak.co.uk",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    hits = 0
    for url in MISSED:
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(SETTLE_MS)
            element, selector, text = find_banner(page)
        except Exception as e:
            print(url, "-> error:", str(e).splitlines()[0][:80])
            context.close()
            continue
        if element is None:
            print(url, "-> STILL NO BANNER")
        else:
            hits += 1
            found = classify_buttons(element)
            print(url, "->", selector, "|", first_layer_pattern(found),
                  "| accept", found["accept"], "reject", found["reject"], "settings", found["settings"])
        context.close()
    browser.close()
    print(f"\nFound {hits} of {len(MISSED)}")