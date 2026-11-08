import csv
import os
import time
import urllib.robotparser
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "IrtizaMScDissertationBot/1.0 (+mailto:sa137@kent.ac.uk)"
UA_PRODUCT_TOKEN = "IrtizaMScDissertationBot"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SITES_FILE = os.path.join(ROOT, "data", "output", "sites_all.csv")
OUT_FILE = os.path.join(HERE, "robots_dataset_rescan.csv")

PATHS_OF_INTEREST = {
    "cart": ["/cart", "/basket"],
    "checkout": ["/checkout", "/checkouts"],
    "account": ["/account", "/login", "/sign-in", "/profile"],
}

REQUEST_TIMEOUT_SECONDS = 10
POLITE_DELAY_SECONDS = 1.0


@dataclass
class RobotsResult:
    site: str
    has_robots_txt: bool
    fetch_status: str
    blocks_cart: bool
    blocks_checkout: bool
    blocks_account: bool
    matched_disallow_rules: str
    crawl_delay: str
    category: str
    scanned_at: str


def read_sites():
    sites = []
    seen = set()
    with open(SITES_FILE, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            url = (row.get("url") or "").strip()
            if not url:
                continue
            host = urlparse(url if "//" in url else "https://" + url).netloc.lower()
            if host and host not in seen:
                seen.add(host)
                sites.append(host)
    return sites


def fetch_robots_txt(site):
    url = urljoin(f"https://{site}", "/robots.txt")
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return resp.text, resp.status_code
        return "", resp.status_code
    except requests.RequestException:
        return "", None


def check_paths(parser, site):
    blocked = {}
    matched = []
    for category, paths in PATHS_OF_INTEREST.items():
        category_blocked = False
        for path in paths:
            if not parser.can_fetch(UA_PRODUCT_TOKEN, urljoin(f"https://{site}", path)):
                category_blocked = True
                matched.append(f"{category}:{path}")
        blocked[category] = category_blocked
    return blocked, matched


def classify(has_file, blocked):
    if not has_file:
        return "no_file"
    values = list(blocked.values())
    if not any(values):
        return "fully_open"
    if all(values):
        return "fully_restricted"
    return "partially_restricted"


def scan_site(site):
    text, status_code = fetch_robots_txt(site)
    now = datetime.now(timezone.utc).isoformat()

    if status_code == 200 and text.strip():
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())
        blocked, matched = check_paths(parser, site)
        crawl_delay = parser.crawl_delay(UA_PRODUCT_TOKEN) or ""
        return RobotsResult(
            site=site,
            has_robots_txt=True,
            fetch_status="ok",
            blocks_cart=blocked["cart"],
            blocks_checkout=blocked["checkout"],
            blocks_account=blocked["account"],
            matched_disallow_rules="; ".join(matched),
            crawl_delay=str(crawl_delay),
            category=classify(True, blocked),
            scanned_at=now,
        )

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


def main():
    sites = read_sites()
    print(f"{len(sites)} sites read from {SITES_FILE}")
    fields = list(RobotsResult.__dataclass_fields__.keys())
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, site in enumerate(sites, start=1):
            print(f"[{i}/{len(sites)}] Scanning {site} ...")
            writer.writerow(asdict(scan_site(site)))
            f.flush()
            time.sleep(POLITE_DELAY_SECONDS)
    print(f"\nDone. Wrote {len(sites)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()