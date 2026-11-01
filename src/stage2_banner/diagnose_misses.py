import os

from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT, SETTLE_MS, find_banner

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_FILE = os.path.join(ROOT, "results", "miss_diagnostics.txt")

MISSED = [
    "https://eloboss.net", "https://wise.com", "https://www.bet365.com",
    "https://www.aliexpress.com", "https://www.shein.com", "https://www.dropbox.com",
    "https://www.adobe.com", "https://www.booking.com", "https://www.airbnb.co.uk",
]

CANDIDATES_JS = """() => {
    const found = [];
    const visit = (root, inShadow) => {
        for (const e of root.querySelectorAll('*')) {
            if (e.shadowRoot) visit(e.shadowRoot, true);
            const t = (e.innerText || '').trim();
            if (t.length < 40 || t.length > 1500 || !/cookie|consent/i.test(t)) continue;
            const r = e.getBoundingClientRect();
            if (r.width < 50 || r.height < 20) continue;
            found.push({tag: e.tagName, id: e.id || '', cls: String(e.className || '').slice(0, 60),
                        shadow: inShadow, w: Math.round(r.width), h: Math.round(r.height),
                        pos: getComputedStyle(e).position, role: e.getAttribute('role') || '',
                        len: t.length, text: t.replace(/\\s+/g, ' ').slice(0, 70)});
        }
    };
    visit(document, false);
    found.sort((a, b) => a.len - b.len);
    return found.slice(0, 6);
}"""


def main():
    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        for url in MISSED:
            say("=" * 70)
            say(url)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(SETTLE_MS)
                say(f"final url: {page.url}")
                element, selector, text = find_banner(page)
                say(f"find_banner: {'FOUND ' + selector if element is not None else 'nothing'}")
                say("frames:")
                for frame in page.frames[1:]:
                    try:
                        body = frame.locator("body").inner_text(timeout=1500)
                        if "cookie" in body.lower() or "consent" in body.lower():
                            say(f"   {frame.url[:90]}  (cookie/consent text, {len(body)} chars)")
                    except Exception:
                        pass
                say("candidates (smallest first):")
                for c in page.evaluate(CANDIDATES_JS):
                    say(f"   <{c['tag']}> id='{c['id']}' class='{c['cls']}' shadow={c['shadow']} "
                        f"{c['w']}x{c['h']} pos={c['pos']} role='{c['role']}' len={c['len']}")
                    say(f"      text: {c['text']}")
            except Exception as e:
                say(f"   (problem: {str(e).splitlines()[0][:100]})")
            context.close()
        browser.close()

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nSaved to {OUT_FILE}")


if __name__ == "__main__":
    main()