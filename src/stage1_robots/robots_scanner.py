"""
Stage 1: Robots.txt Configuration Scanner
-------------------------------------------
Purpose: For each candidate site, fetch and parse robots.txt to determine
whether/how cart, checkout, and account paths are restricted, BEFORE any
content scanning (Stage 2) is attempted.

Requires: pip install requests --break-system-packages
"""

import csv
import time
import urllib.robotparser
from urllib.parse import urljoin
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import requests


# Configuration


# scanner's identity used both to check rules and identity
USER_AGENT = "IrtizaMScDissertationBot/1.0 (+https://your-project-info-page-or-email.example)"

# Paths we care about for this project's Category 1 detection.
# Can be extended if needed later on if the project scope widens
PATHS_OF_INTEREST = {
    "cart": ["/cart", "/basket"],
    "checkout": ["/checkout", "/checkouts"],
    "account": ["/account", "/login", "/sign-in", "/profile"],
}

REQUEST_TIMEOUT_SECONDS = 10
POLITE_DELAY_SECONDS = 1.0  # being gentle between requests, independent of crawl-delay


@dataclass
class RobotsResult:
    site: str
    has_robots_txt: bool
    fetch_status: str            # "ok", "not_found", "error"
    blocks_cart: bool
    blocks_checkout: bool
    blocks_account: bool
    matched_disallow_rules: str  # semicolon-separated list, for transparency
    crawl_delay: str
    category: str                # fully_open / partially_restricted / fully_restricted / no_file
    scanned_at: str


def fetch_robots_txt(site: str) -> tuple[str, int | None]:
    """Fetch the raw robots.txt text for a site. Returns (text, status_code)."""
    url = urljoin(f"https://{site}", "/robots.txt")
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if resp.status_code == 200:
            return resp.text, resp.status_code
        return "", resp.status_code
    except requests.RequestException:
        return "", None


def check_paths_against_parser(parser: urllib.robotparser.RobotFileParser, site: str):
    """
    For each category (cart/checkout/account), have to check whether any of its
    candidate paths are disallowed for our user-agent. Also collects which
    specific rules matched, for transparency in the output dataset.
    """
    blocked = {}
    matched_rules = []

    for category, paths in PATHS_OF_INTEREST.items():
        category_blocked = False
        for path in paths:
            test_url = urljoin(f"https://{site}", path)
            allowed = parser.can_fetch(USER_AGENT, test_url)
            if not allowed:
                category_blocked = True
                matched_rules.append(f"{category}:{path}")
        blocked[category] = category_blocked

    return blocked, matched_rules


def classify(has_file: bool, blocked: dict) -> str:
    if not has_file:
        return "no_file"
    values = list(blocked.values())
    if not any(values):
        return "fully_open"
    if all(values):
        return "fully_restricted"
    return "partially_restricted"


def scan_site(site: str) -> RobotsResult:
    text, status_code = fetch_robots_txt(site)
    now = datetime.now(timezone.utc).isoformat()

    if status_code == 200 and text.strip():
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())

        blocked, matched_rules = check_paths_against_parser(parser, site)
        crawl_delay = parser.crawl_delay(USER_AGENT) or ""

        return RobotsResult(
            site=site,
            has_robots_txt=True,
            fetch_status="ok",
            blocks_cart=blocked["cart"],
            blocks_checkout=blocked["checkout"],
            blocks_account=blocked["account"],
            matched_disallow_rules="; ".join(matched_rules),
            crawl_delay=str(crawl_delay),
            category=classify(True, blocked),
            scanned_at=now,
        )

    # No robots.txt found (404) or fetch failed, treat as fully open by
    # convention (no file = no restriction), but will log it distinctly so we
    # can still tell "explicitly open" apart from "no file present" later.
    fetch_status = "not_found" if status_code == 404 else "error"
    return RobotsResult(
        site=site,
        has_robots_txt=False,
        fetch_status=fetch_status,
        blocks_cart=False,
        blocks_checkout=False,
        blocks_account=False,
        matched_disallow_rules="",
        crawl_delay="",
        category="no_file",
        scanned_at=now,
    )


def run_batch(sites: list[str], output_path: str = "robots_dataset.csv"):
    results = []
    for i, site in enumerate(sites, start=1):
        print(f"[{i}/{len(sites)}] Scanning {site} ...")
        result = scan_site(site)
        results.append(result)
        time.sleep(POLITE_DELAY_SECONDS)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nDone. Wrote {len(results)} rows to {output_path}")
    return results


if __name__ == "__main__":
    # Domain only, no scheme: e.g. "example.com" not "https://example.com".
    candidate_sites = [
        "etsy.com",
        # "somestore.com",
        # "anotherstore.co.uk",
    ]

    run_batch(candidate_sites)
