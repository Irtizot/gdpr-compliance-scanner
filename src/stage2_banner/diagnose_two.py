from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT, SETTLE_MS, find_banner

SITES = ["https://www.shein.com", "https://www.adobe.com"]

DUMP_JS = """() => {
    const out = [];
    const walk = root => {
        for (const e of root.querySelectorAll('*')) {
            if (e.shadowRoot) walk(e.shadowRoot);
            const r = e.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) continue;
            const t = (e.innerText || '').replace(/\\s+/g, ' ').trim();
            if (!t || t.length > 40) continue;
            const cur = getComputedStyle(e).cursor;
            const clickable = e.matches('button, a, [role="button"], input, [onclick]') || cur === 'pointer';
            if (!clickable) continue;
            if (!/accept|agree|allow|reject|decline|deny|ok|got it|continue|necessary|essential|all|cookie/i.test(t)) continue;
            out.push(e.tagName + ' | ' + t + ' | cursor=' + cur + ' | ' + Math.round(r.width) + 'x' + Math.round(r.height)
                + ' | top=' + Math.round(r.top) + ' | footer=' + !!e.closest('footer, [role="contentinfo"]'));
        }
    };
    walk(document);
    return out.slice(0, 40);
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    for url in SITES:
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(SETTLE_MS + 4000)
        element, selector, text = find_banner(page)
        print("=" * 60)
        print(url, "| finder:", selector or "nothing")
        for line in page.evaluate(DUMP_JS):
            print("  ", line)
        context.close()
    browser.close()