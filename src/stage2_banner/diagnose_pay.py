import os

from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT, SETTLE_MS, find_banner

SITES = ["https://www.dailymail.co.uk", "https://www.mirror.co.uk",
         "https://metro.co.uk", "https://www.wayfair.co.uk"]

SHOTS = os.path.join(os.path.dirname(__file__), "..", "..", "results", "shots")
os.makedirs(SHOTS, exist_ok=True)

DUMP_JS = """() => {
    const out = [];
    const walk = root => {
        for (const e of root.querySelectorAll('*')) {
            if (e.shadowRoot) walk(e.shadowRoot);
            const r = e.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0 || r.top > window.innerHeight || r.bottom < 0) continue;
            const t = (e.innerText || '').replace(/\\s+/g, ' ').trim();
            if (!t || t.length > 50) continue;
            const cur = getComputedStyle(e).cursor;
            if (!(e.matches('button, a, [role="button"], input, [onclick]') || cur === 'pointer')) continue;
            out.push(e.tagName + ' | ' + t + ' | ' + Math.round(r.width) + 'x' + Math.round(r.height)
                + ' | top=' + Math.round(r.top));
        }
    };
    walk(document);
    return out.slice(0, 60);
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    for url in SITES:
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(SETTLE_MS + 6000)
        element, selector, text = find_banner(page)
        name = url.split("//")[1].replace("www.", "").split(".")[0]
        page.screenshot(path=os.path.join(SHOTS, name + ".png"))
        print("=" * 60)
        print(url, "| finder:", selector or "nothing")
        print("banner text:", (text or "")[:300].replace("\n", " "))
        for line in page.evaluate(DUMP_JS):
            print("  ", line)
        context.close()
    browser.close()