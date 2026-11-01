import re
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import requests
import tldextract
from playwright.sync_api import sync_playwright, Page

USER_AGENT = "IrtizaMScDissertationBot/1.0 (+mailto:sa137@kent.ac.uk)"
UA_PRODUCT_TOKEN = "IrtizaMScDissertationBot"


def check_robots(url: str) -> str:
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        response = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=10)
    except Exception:
        return "unreachable"

    if 400 <= response.status_code < 500:
        return "unavailable_4xx"
    if response.status_code >= 500:
        return "unreachable"

    parser = robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return "allowed" if parser.can_fetch(UA_PRODUCT_TOKEN, url) else "disallowed"


SETTLE_MS = 4000
MIN_BANNER_AREA_PX = 4000
MAX_BANNER_TEXT_CHARS = 6000
BANNER_KEYWORDS = ("cookie", "consent", "privacy")

BANNER_SELECTORS = [
    "#onetrust-banner-sdk", "#CybotCookiebotDialog", "#didomi-popup", "#didomi-host",
    ".qc-cmp2-container", "#truste-consent-track", "#cookiescript_injected",
    "[id*='cookie' i]", "[class*='cookie' i]",
    "[id*='consent' i]", "[class*='consent' i]",
    "[aria-label*='cookie' i]", "[aria-label*='consent' i]",
    "[role='dialog']", "[aria-modal='true']",
]


BANNER_WAIT_EXTRA_MS = 14000
BANNER_POLL_MS = 2000


def find_banner(page: Page):
    result = _find_banner_once(page)
    waited = 0
    while result[0] is None and waited < BANNER_WAIT_EXTRA_MS:
        page.wait_for_timeout(BANNER_POLL_MS)
        waited += BANNER_POLL_MS
        result = _find_banner_once(page)
    return result


def _find_banner_once(page: Page):
    for selector in BANNER_SELECTORS:
        matches = page.locator(selector)
        try:
            count = min(matches.count(), 8)
        except Exception:
            continue
        for i in range(count):
            element = matches.nth(i)
            try:
                if not element.is_visible():
                    continue
                if element.evaluate("e => e.tagName") in ("BODY", "HTML"):
                    continue
                box = element.bounding_box()
                if not box or box["width"] * box["height"] < MIN_BANNER_AREA_PX:
                    continue
                text = (element.inner_text(timeout=1500) or "").lower()
                if len(text) > MAX_BANNER_TEXT_CHARS:
                    continue
                if not any(word in text for word in BANNER_KEYWORDS):
                    continue
                return element, selector, text
            except Exception:
                continue

    for frame in page.frames[1:]:
        try:
            frame_box_element = frame.frame_element()
            if not frame_box_element.is_visible():
                continue
            box = frame_box_element.bounding_box()
            if not box or box["width"] * box["height"] < MIN_BANNER_AREA_PX:
                continue
            body = frame.locator("body")
            text = (body.inner_text(timeout=1500) or "").lower()
            if len(text) > MAX_BANNER_TEXT_CHARS:
                continue
            if not any(word in text for word in BANNER_KEYWORDS):
                continue
            host = urlparse(frame.url).hostname or "unknown"
            return body, f"iframe:{host}", text
        except Exception:
            continue
    return find_banner_by_text(page)


FIND_BANNER_JS = """() => {
    const WANT = /cookie|consent/i;
    const GOOD = /\\b(accept|agree|allow|enable|got it|i understand|ok|okay|reject|decline|deny|refuse|essential only|necessary only)\\b/i;
    const BAD = /policy|preferences|settings|manage|notice|learn more|more info/i;
    const MAX_TEXT = 2000, MIN_AREA = 4000, MAX_UP = 10;
    document.querySelectorAll('[data-scan-banner]').forEach(e => e.removeAttribute('data-scan-banner'));
    const parentOf = n => n.parentElement || (n.getRootNode() instanceof ShadowRoot ? n.getRootNode().host : null);
    const shown = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const all = [];
    const collect = root => {
        for (const e of root.querySelectorAll('*')) { all.push(e); if (e.shadowRoot) collect(e.shadowRoot); }
    };
    collect(document);
    const clickable = e => e.matches('button, a, [role="button"], input[type="button"], input[type="submit"], [onclick]')
        || getComputedStyle(e).cursor === 'pointer';
    let best = null, bestArea = Infinity;
    for (const b of all) {
        if (!clickable(b) || !shown(b)) continue;
        if (b.closest('footer, [role="contentinfo"]')) continue;
        const label = ((b.innerText || b.value || b.getAttribute('aria-label') || '') + '').replace(/\\s+/g, ' ').trim();
        if (!label || label.length > 30 || !GOOD.test(label) || BAD.test(label)) continue;
        let c = parentOf(b);
        for (let i = 0; c && i < MAX_UP; i++, c = parentOf(c)) {
            if (c === document.body || c === document.documentElement) break;
            const t = (c.innerText || '').trim();
            if (t.length > MAX_TEXT) break;
            if (t.length >= 40 && WANT.test(t) && shown(c)) {
                const r = c.getBoundingClientRect();
                const area = r.width * r.height;
                if (area >= MIN_AREA && area < bestArea) { best = c; bestArea = area; }
                break;
            }
        }
    }
    if (!best) return false;
    best.setAttribute('data-scan-banner', '1');
    return true;
}"""


def find_banner_by_text(page: Page):
    try:
        if not page.evaluate(FIND_BANNER_JS):
            return None, "", ""
        element = page.locator("[data-scan-banner='1']").first
        text = (element.inner_text(timeout=1500) or "").lower()
        return element, "text-fallback", text
    except Exception:
        return None, "", ""


REJECT_RE = re.compile(
    r"\b(reject|decline|deny|refuse|disagree|no,? thanks|do not (consent|accept|agree)|"
    r"don['’]?t (consent|accept|agree|enable|allow)|do not (enable|allow)|necessary only|only necessary|essential only|"
    r"only essential|continue without (accepting|agreeing))\b", re.I)
SETTINGS_RE = re.compile(
    r"\b(manage|settings|preferences|customi[sz]e|options|more info|more options|choose|"
    r"personali[sz]e)\b", re.I)
ACCEPT_RE = re.compile(
    r"\b(accept|agree|allow|enable|ok|okay|got it|i understand|yes,? i['’]?m happy|consent)\b", re.I)

MAX_LEVELS_UP = 4

MARK_CLICKABLE_JS = """c => {
    const ok = new Set();
    for (const e of c.querySelectorAll('*')) {
        const t = (e.innerText || '').trim();
        if (t && t.length <= 60 && getComputedStyle(e).cursor === 'pointer') ok.add(e);
    }
    for (const e of ok) {
        if (!(e.parentElement && ok.has(e.parentElement))) e.setAttribute('data-scan-click', '1');
    }
}"""


def read_label(element):
    label = (element.inner_text(timeout=800) or element.get_attribute("value")
             or element.get_attribute("aria-label") or "").strip()
    return re.sub(r"\s+", " ", label)


def collect_buttons(candidates, cap, found, only_missing):
    try:
        count = min(candidates.count(), cap)
    except Exception:
        return
    for i in range(count):
        element = candidates.nth(i)
        try:
            if not element.is_visible():
                continue
            label = read_label(element)
            if not label or len(label) > 60:
                continue
            if REJECT_RE.search(label):
                kind = "reject"
            elif SETTINGS_RE.search(label):
                kind = "settings"
            elif ACCEPT_RE.search(label):
                kind = "accept"
            else:
                continue
            if only_missing and found[kind]:
                continue
            found[kind].append(label)
            if kind in ("accept", "reject"):
                found["elements"].setdefault(kind, element)
        except Exception:
            continue


def scan_buttons(container):
    found = {"accept": [], "reject": [], "settings": [], "elements": {}}
    collect_buttons(container.locator(
        "button, a, [role='button'], input[type='button'], input[type='submit']"), 30, found, False)
    if found["accept"] and found["reject"]:
        return found
    try:
        container.evaluate(MARK_CLICKABLE_JS)
    except Exception:
        return found
    collect_buttons(container.locator("[data-scan-click='1']"), 120, found, True)
    return found


WIDEN_MAX_TEXT = 5000


def parent_of(container):
    try:
        parent = container.locator("xpath=..")
        if parent.evaluate("e => e.tagName") in ("BODY", "HTML"):
            return None
        return parent
    except Exception:
        return None


def classify_buttons(banner):
    container = banner
    found = {"accept": [], "reject": [], "settings": [], "elements": {}}
    for _ in range(MAX_LEVELS_UP + 1):
        found = scan_buttons(container)
        if found["accept"] or found["reject"] or found["settings"]:
            break
        container = parent_of(container)
        if container is None:
            return found
    else:
        return found
    if found["reject"] or not found["accept"]:
        return found
    for _ in range(MAX_LEVELS_UP):
        container = parent_of(container)
        if container is None:
            break
        try:
            if len(container.inner_text(timeout=1500)) > WIDEN_MAX_TEXT:
                break
        except Exception:
            break
        wider = scan_buttons(container)
        if wider["accept"] and wider["reject"]:
            return wider
    return found


SIZE_RATIO = 1.5
CONTRAST_DIFF = 2.0
FILLED_DISTANCE = 40

MEASURE_JS = """e => {
    const s = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    const isClear = c => /rgba\\(.*,\\s*0\\)$/.test(c) || c === "transparent";
    let anc = e.parentElement, ancBg = "rgb(255, 255, 255)";
    while (anc) {
        const c = getComputedStyle(anc).backgroundColor;
        if (!isClear(c)) { ancBg = c; break; }
        anc = anc.parentElement;
    }
    return {
        width: r.width, height: r.height, fontSize: parseFloat(s.fontSize),
        color: s.color, bg: s.backgroundColor, ancBg: ancBg,
        border: parseFloat(s.borderTopWidth) || 0, tag: e.tagName
    };
}"""


def parse_colour(css):
    nums = re.findall(r"[\d.]+", css or "")
    if len(nums) < 3:
        return None
    alpha = float(nums[3]) if len(nums) > 3 else 1.0
    return float(nums[0]), float(nums[1]), float(nums[2]), alpha


def luminance(c):
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(c1, c2):
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def measure_button(element):
    try:
        d = element.evaluate(MEASURE_JS)
    except Exception:
        return None
    text, bg, anc = parse_colour(d["color"]), parse_colour(d["bg"]), parse_colour(d["ancBg"])
    if not text or not anc:
        return None
    own_bg_visible = bg is not None and bg[3] > 0.05
    effective_bg = bg if own_bg_visible else anc
    dist = sum((bg[i] - anc[i]) ** 2 for i in range(3)) ** 0.5 if own_bg_visible else 0
    if own_bg_visible and dist > FILLED_DISTANCE:
        style = "filled"
    elif d["border"] > 0:
        style = "outlined"
    else:
        style = "plain"
    return {
        "area": round(d["width"] * d["height"]),
        "font_size": d["fontSize"],
        "contrast": round(contrast(text, effective_bg), 2),
        "style": style,
    }


def compare_buttons(found):
    acc = measure_button(found["elements"]["accept"]) if "accept" in found["elements"] else None
    rej = measure_button(found["elements"]["reject"]) if "reject" in found["elements"] else None
    result = {"accept": acc, "reject": rej, "size_ratio": None, "contrast_diff": None,
              "size_flag": False, "contrast_flag": False, "style_asymmetry_flag": False}
    if acc and rej:
        if rej["area"] > 0:
            result["size_ratio"] = round(acc["area"] / rej["area"], 2)
            result["size_flag"] = result["size_ratio"] >= SIZE_RATIO
        result["contrast_diff"] = round(acc["contrast"] - rej["contrast"], 2)
        result["contrast_flag"] = result["contrast_diff"] >= CONTRAST_DIFF
        result["style_asymmetry_flag"] = acc["style"] == "filled" and rej["style"] != "filled"
    return result


_extract = tldextract.TLDExtract(suffix_list_urls=())

TRACKER_FILE = Path(__file__).resolve().parents[2] / "data" / "trackers" / "tracker_domains.txt"


def load_tracker_domains():
    if not TRACKER_FILE.exists():
        raise FileNotFoundError(f"{TRACKER_FILE} not found. Run build_tracker_list.py first.")
    with open(TRACKER_FILE, encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


KNOWN_TRACKERS = load_tracker_domains()


def registered_domain(host):
    parts = _extract(host or "")
    return parts.top_domain_under_public_suffix if parts.suffix else (host or "")


def watch_requests(page):
    seen = []
    page.on("request", lambda r: seen.append(urlparse(r.url).hostname or ""))
    return seen


def is_known_tracker(host):
    parts = (host or "").lower().split(".")
    return any(".".join(parts[i:]) in KNOWN_TRACKERS for i in range(len(parts) - 1))


def summarise_tracking(site_url, hosts, cookies):
    site_domain = registered_domain(urlparse(site_url).hostname)
    third_hosts = sorted({h for h in hosts if h and registered_domain(h) != site_domain})
    trackers = [h for h in third_hosts if is_known_tracker(h)]
    third_cookies = [c for c in cookies if registered_domain(c["domain"].lstrip(".")) != site_domain]
    return {
        "third_party_domains": len({registered_domain(h) for h in third_hosts}),
        "known_trackers": sorted({registered_domain(h) for h in trackers}),
        "cookies_total": len(cookies),
        "third_party_cookies": len(third_cookies),
    }


LEXICON = {
    "confirmshaming": [
        r"no,? i (don['’]?t|do not) (want|like|care)", r"i (prefer|choose) to (pay|miss|lose)",
        r"no thanks,? i('| wi)ll (pay|miss)", r"i('| a)m not interested in (saving|privacy|deals)",
        r"i (hate|don['’]?t like) (saving|deals|discounts)",
    ],
    "implied_consent": [
        r"by (continuing|using|browsing|closing|scrolling|dismissing)[^.]{0,80}?(you )?(agree|consent|accept)",
        r"if you continue (to )?(use|browse)", r"continued use of (this|our) (site|website)",
        r"(closing|dismissing) this (banner|message|notice)[^.]{0,40}(agree|accept|consent)",
    ],
    "vague_purpose": [
        r"(improve|enhance|enrich|optimi[sz]e) (your|the) (browsing )?experience",
        r"(better|improved|enhanced) (browsing )?experience",
        r"(various|certain|other) purposes(?!,? (including|such as|namely))",
        r"(personali[sz]e|tailor)(ed)? your (browsing )?experience",
    ],
    "pressure": [
        r"you must (accept|agree|consent)", r"don['’]?t miss out", r"limited time",
        r"last chance", r"act now", r"required to (continue|proceed|access)",
    ],
}
LEXICON = {k: [re.compile(p, re.I) for p in v] for k, v in LEXICON.items()}


def wording_flags(banner_text, found):
    corpus = " ".join([banner_text] + found["accept"] + found["reject"] + found["settings"])
    corpus = re.sub(r"\s+", " ", corpus)
    return {name: any(p.search(corpus) for p in patterns) for name, patterns in LEXICON.items()}


def first_layer_pattern(found: dict) -> str:
    accept, reject, settings = bool(found["accept"]), bool(found["reject"]), bool(found["settings"])
    if accept and reject:
        return "accept_reject"
    if accept and settings:
        return "accept_settings"
    if accept:
        return "accept_only"
    return "other"


if __name__ == "__main__":
    test_sites = [
        "https://www.bbc.co.uk",
        "https://www.theguardian.com",
        "https://www.amazon.co.uk",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        for site in test_sites:
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            hosts = watch_requests(page)
            page.goto(site, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(SETTLE_MS)
            element, selector, text = find_banner(page)
            print(site)
            print("   banner found:", element is not None)
            t = summarise_tracking(site, hosts, context.cookies())
            print("   third-party domains contacted:", t["third_party_domains"])
            print("   known trackers contacted:", t["known_trackers"])
            print("   cookies set:", t["cookies_total"], "of which third-party:", t["third_party_cookies"])
            if element is not None:
                found = classify_buttons(element)
                print("   selector:", selector)
                print("   accept buttons:  ", found["accept"])
                print("   reject buttons:  ", found["reject"])
                print("   settings buttons:", found["settings"])
                print("   first-layer pattern:", first_layer_pattern(found))
                v = compare_buttons(found)
                print("   accept measures:", v["accept"])
                print("   reject measures:", v["reject"])
                print("   size ratio:", v["size_ratio"], "flag:", v["size_flag"])
                print("   contrast diff:", v["contrast_diff"], "flag:", v["contrast_flag"])
                print("   filled vs link-style flag:", v["style_asymmetry_flag"])
                print("   wording flags:", wording_flags(text, found))
            context.close()
        browser.close()