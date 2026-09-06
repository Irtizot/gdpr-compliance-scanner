"""
Stage 2, Part A: Page Loader + Cookie Banner Detection
Purpose: For each site cleared by Stage 1 (robots.txt scanner), loads the
page with a real rendering engine (Playwright) and locate the cookie
consent banner, including banners that load asynchronously after initial
page load.

This is the base for the rest of Stage 2 — text extraction, visual
style extraction, and tracker timing all depend on first reliably finding
the banner and its Accept/Reject elements.

installed packages doc:
    pip install playwright --break-system-packages
    playwright install chromium
"""

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import csv
import time



# Configuration


USER_AGENT = "IrtizaMScDissertationBot/1.0"

# How long to wait for a banner to appear after page load, in milliseconds.
# Many banners load after a short delay (fade-in, scroll-trigger, etc.),
# so it don't just check immediately on page load.
BANNER_WAIT_TIMEOUT_MS = 5000

# Common selectors used by major consent management platforms (CMPs).
# custom rules. We can Expand this list as we test against real sites.
BANNER_SELECTOR_CANDIDATES = [
    "#onetrust-banner-sdk",           # OneTrust
    "#CybotCookiebotDialog",          # Cookiebot
    "[id*='cookie' i]",               # generic: any id containing "cookie"
    "[class*='cookie' i]",            # generic: any class containing "cookie"
    "[id*='consent' i]",              # generic: any id containing "consent"
    "[class*='consent' i]",           # generic: any class containing "consent"
]

# Common text patterns used on Accept / Reject buttons, used as a fallback
# when structural selectors don't match a known CMP.
ACCEPT_TEXT_PATTERNS = ["accept all", "accept cookies", "i agree", "allow all", "accept"]
REJECT_TEXT_PATTERNS = ["reject all", "decline", "manage preferences", "necessary only", "reject"]


@dataclass
class BannerDetectionResult:
    site: str
    url: str
    page_loaded: bool
    banner_found: bool
    banner_selector_matched: str   # which selector/rule found it, for transparency
    accept_button_found: bool
    reject_button_found: bool
    accept_button_text: str
    reject_button_text: str
    error: str
    scanned_at: str


def find_banner(page: Page) -> tuple[bool, str]:
    for selector in BANNER_SELECTOR_CANDIDATES:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=BANNER_WAIT_TIMEOUT_MS)
            return True, selector
        except PWTimeoutError:
            continue
    return False, ""


def find_button_by_text(page: Page, patterns: list[str]) -> tuple[bool, str]:
    """
    Looks for a visible button/link whose text matches one of the given
    patterns (case-insensitive). Returns (found, matched_text).
    """
    for pattern in patterns:
        try:
            # Playwright's text= selector does case-insensitive substring
            # matching when wrapped like this.
            locator = page.get_by_text(pattern, exact=False).first
            if locator.is_visible(timeout=1000):
                actual_text = locator.inner_text().strip()
                return True, actual_text
        except Exception:
            continue
    return False, ""


def scan_site(site_url: str, headless: bool = True) -> BannerDetectionResult:
    now = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            page.goto(site_url, wait_until="domcontentloaded", timeout=20000)
            page_loaded = True
        except Exception as e:
            browser.close()
            return BannerDetectionResult(
                site=site_url, url=site_url, page_loaded=False,
                banner_found=False, banner_selector_matched="",
                accept_button_found=False, reject_button_found=False,
                accept_button_text="", reject_button_text="",
                error=str(e), scanned_at=now,
            )

        # Give the page a moment to settle and any delayed banner to appear.
        page.wait_for_timeout(2000)

        banner_found, matched_selector = find_banner(page)
        accept_found, accept_text = find_button_by_text(page, ACCEPT_TEXT_PATTERNS)
        reject_found, reject_text = find_button_by_text(page, REJECT_TEXT_PATTERNS)

        result = BannerDetectionResult(
            site=site_url,
            url=site_url,
            page_loaded=page_loaded,
            banner_found=banner_found,
            banner_selector_matched=matched_selector,
            accept_button_found=accept_found,
            reject_button_found=reject_found,
            accept_button_text=accept_text,
            reject_button_text=reject_text,
            error="",
            scanned_at=now,
        )

        browser.close()
        return result


def run_batch(site_urls: list[str], output_path: str = "banner_detection_dataset.csv", headless: bool = True):
    results = []
    for i, url in enumerate(site_urls, start=1):
        print(f"[{i}/{len(site_urls)}] Scanning {url} ...")
        result = scan_site(url, headless=headless)
        results.append(result)
        time.sleep(1.0)  # polite delay between sites

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nDone. Wrote {len(results)} rows to {output_path}")
    return results


if __name__ == "__main__":
    # Uses full URLs (with https://)
    test_sites = [
        "https://www.bbc.co.uk",
    ]

    run_batch(test_sites, headless=False)