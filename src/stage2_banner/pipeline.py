import re
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

SETTLE_MS = 4000            # wait after page load for banners that appear late
MIN_BANNER_AREA_PX = 4000   # ignores tiny matches such as icons or hidden wrappers
MAX_BANNER_TEXT_CHARS = 6000  # ignores whole-page wrappers
BANNER_KEYWORDS = ("cookie", "consent", "privacy")

BANNER_SELECTORS = [
    "#onetrust-banner-sdk", "#CybotCookiebotDialog", "#didomi-popup", "#didomi-host",
    ".qc-cmp2-container", "#truste-consent-track", "#cookiescript_injected",
    "[id*='cookie' i]", "[class*='cookie' i]",
    "[id*='consent' i]", "[class*='consent' i]",
    "[aria-label*='cookie' i]", "[aria-label*='consent' i]",
    "[role='dialog']", "[aria-modal='true']",
]


def find_banner(page: Page):
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


def find_banner_by_text(page: Page):
    matches = page.get_by_text(re.compile(r"cookie|consent", re.I))
    try:
        count = min(matches.count(), 15)
    except Exception:
        return None, "", ""
    for i in range(count):
        container = matches.nth(i)
        try:
            if not container.is_visible():
                continue
            if len((container.inner_text(timeout=1000) or "").strip()) < 40:
                continue
        except Exception:
            continue
        for _ in range(MAX_LEVELS_UP + 4):
            try:
                if container.evaluate("e => e.tagName") in ("BODY", "HTML"):
                    break
                text = (container.inner_text(timeout=1500) or "").lower()
                if len(text) > MAX_BANNER_TEXT_CHARS:
                    break
                box = container.bounding_box()
                if box and box["width"] * box["height"] >= MIN_BANNER_AREA_PX:
                    if scan_buttons(container)["accept"]:
                        return container, "text-fallback", text
                container = container.locator("xpath=..")
            except Exception:
                break
    return None, "", ""

REJECT_RE = re.compile(
    r"\b(reject|decline|deny|refuse|disagree|no,? thanks|do not (consent|accept|agree)|"
    r"don['’]?t (consent|accept|agree)|necessary only|only necessary|essential only|"
    r"only essential|continue without (accepting|agreeing))\b", re.I)
SETTINGS_RE = re.compile(
    r"\b(manage|settings|preferences|customi[sz]e|options|more info|more options|choose|"
    r"personali[sz]e)\b", re.I)
ACCEPT_RE = re.compile(
    r"\b(accept|agree|allow|ok|okay|got it|i understand|yes,? i['’]?m happy|consent)\b", re.I)

MAX_LEVELS_UP = 4


def scan_buttons(container):
    found = {"accept": [], "reject": [], "settings": [], "elements": {}}
    candidates = container.locator("button, a, [role='button'], input[type='button'], input[type='submit']")
    try:
        count = min(candidates.count(), 30)
    except Exception:
        return found
    for i in range(count):
        element = candidates.nth(i)
        try:
            if not element.is_visible():
                continue
            label = (element.inner_text(timeout=800) or element.get_attribute("value")
                     or element.get_attribute("aria-label") or "").strip()
            label = re.sub(r"\s+", " ", label)
            if not label or len(label) > 60:
                continue
            if REJECT_RE.search(label):
                found["reject"].append(label)
                found["elements"].setdefault("reject", element)
            elif SETTINGS_RE.search(label):
                found["settings"].append(label)
            elif ACCEPT_RE.search(label):
                found["accept"].append(label)
                found["elements"].setdefault("accept", element)
        except Exception:
            continue
    return found


def classify_buttons(banner):
    container = banner
    found = {"accept": [], "reject": [], "settings": [], "elements": {}}
    for _ in range(MAX_LEVELS_UP + 1):
        found = scan_buttons(container)
        if found["accept"] or found["reject"] or found["settings"]:
            return found
        try:
            parent = container.locator("xpath=..")
            if parent.evaluate("e => e.tagName") in ("BODY", "HTML"):
                break
            container = parent
        except Exception:
            break
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

KNOWN_TRACKERS = (
    "google-analytics.com", "googletagmanager.com", "doubleclick.net", "googlesyndication.com",
    "googleadservices.com", "facebook.net", "connect.facebook.net", "hotjar.com", "criteo.com",
    "criteo.net", "taboola.com", "outbrain.com", "adnxs.com", "scorecardresearch.com",
    "amazon-adsystem.com", "analytics.tiktok.com", "clarity.ms", "ads.linkedin.com",
    "bat.bing.com", "quantserve.com", "rubiconproject.com", "pubmatic.com", "casalemedia.com",
    "openx.net", "moatads.com", "chartbeat.com", "segment.io", "mixpanel.com", "optimizely.com",
)


def registered_domain(host):
    parts = _extract(host or "")
    if not parts.suffix:
        return host or ""
    return getattr(parts, "top_domain_under_public_suffix", None) or parts.registered_domain


def watch_requests(page):
    seen = []
    page.on("request", lambda r: seen.append(urlparse(r.url).hostname or ""))
    return seen


def is_known_tracker(host):
    return any(host == t or host.endswith("." + t) for t in KNOWN_TRACKERS)


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
        r"by (continuing|using|browsing|closing|clicking)[^.]{0,80}(you )?(agree|consent|accept)",
        r"if you continue (to )?(use|browse)", r"continued use of (this|our) (site|website)",
        r"(closing|dismissing) this (banner|message|notice)[^.]{0,40}(agree|accept|consent)",
    ],
    "vague_purpose": [
        r"(improve|enhance|enrich) (your|the) (browsing )?experience", r"better experience",
        r"(various|certain|other) purposes", r"personali[sz]e (your )?(experience|content)",
        r"tailor(ed)? (your )?(experience|content)",
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
    flags = {}
    for name, patterns in LEXICON.items():
        flags[name] = False
        for p in patterns:
            m = p.search(corpus)
            if m:
                flags[name] = True
                print("      matched", name, "->", repr(m.group(0)))
    return flags


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