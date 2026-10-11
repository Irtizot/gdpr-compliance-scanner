import csv
import os
import random
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from pipeline import (USER_AGENT, SETTLE_MS, check_robots, find_banner, classify_buttons,
                      first_layer_pattern, compare_buttons, watch_requests, summarise_tracking,
                      wording_flags)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SITES_FILE = os.path.join(ROOT, "data", "output", "sites_pilot.csv")
OUT_FILE = os.path.join(ROOT, "results", "pilot_results.csv")
HEADLESS = False
MIN_DELAY_S = 2
MAX_DELAY_S = 5
LIMIT = 5

FIELDS = [
    "url", "sector", "scanned_at", "robots_status", "page_loaded", "error",
    "banner_found", "banner_selector", "first_layer_pattern",
    "accept_found", "reject_found", "settings_found", "accept_label", "reject_label",
    "accept_area", "reject_area", "size_ratio", "size_flag",
    "accept_contrast", "reject_contrast", "contrast_diff", "contrast_flag",
    "accept_style", "reject_style", "style_asymmetry_flag",
    "checkboxes_total", "checkboxes_prechecked_nondisabled",
    "lang_confirmshaming", "lang_implied_consent", "lang_vague_purpose", "lang_pressure",
    "third_party_domains_pre_consent", "known_tracker_domains_pre_consent",
    "known_trackers", "cookies_total_pre_consent", "third_party_cookies_pre_consent",
]


def count_checkboxes(banner):
    total, prechecked = 0, 0
    boxes = banner.locator("input[type='checkbox']")
    try:
        n = min(boxes.count(), 30)
    except Exception:
        return 0, 0
    for i in range(n):
        try:
            box = boxes.nth(i)
            total += 1
            if box.is_checked() and not box.is_disabled():
                prechecked += 1
        except Exception:
            continue
    return total, prechecked


def empty_row(url, sector):
    row = {f: "" for f in FIELDS}
    row.update({"url": url, "sector": sector, "page_loaded": False, "banner_found": False,
                "scanned_at": datetime.now(timezone.utc).isoformat()})
    return row


def scan_site(browser, url, sector):
    row = empty_row(url, sector)
    row["robots_status"] = check_robots(url)
    if row["robots_status"] in ("disallowed", "unreachable"):
        return row

    context = browser.new_context(user_agent=USER_AGENT)
    try:
        page = context.new_page()
        hosts = watch_requests(page)
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(SETTLE_MS)
        row["page_loaded"] = True

        tracking = summarise_tracking(url, hosts, context.cookies())
        row["third_party_domains_pre_consent"] = tracking["third_party_domains"]
        row["known_tracker_domains_pre_consent"] = len(tracking["known_trackers"])
        row["known_trackers"] = ";".join(tracking["known_trackers"])
        row["cookies_total_pre_consent"] = tracking["cookies_total"]
        row["third_party_cookies_pre_consent"] = tracking["third_party_cookies"]

        element, selector, text = find_banner(page)
        if element is None:
            return row

        row["banner_found"] = True
        row["banner_selector"] = selector
        found = classify_buttons(element)
        row["first_layer_pattern"] = first_layer_pattern(found)
        row["accept_found"] = bool(found["accept"])
        row["reject_found"] = bool(found["reject"])
        row["settings_found"] = bool(found["settings"])
        row["accept_label"] = found["accept"][0] if found["accept"] else ""
        row["reject_label"] = found["reject"][0] if found["reject"] else ""

        v = compare_buttons(found)
        for side in ("accept", "reject"):
            m = v[side]
            if m:
                row[f"{side}_area"] = m["area"]
                row[f"{side}_contrast"] = m["contrast"]
                row[f"{side}_style"] = m["style"]
        row["size_ratio"] = v["size_ratio"] if v["size_ratio"] is not None else ""
        row["contrast_diff"] = v["contrast_diff"] if v["contrast_diff"] is not None else ""
        row["size_flag"] = v["size_flag"]
        row["contrast_flag"] = v["contrast_flag"]
        row["style_asymmetry_flag"] = v["style_asymmetry_flag"]

        total, prechecked = count_checkboxes(element)
        row["checkboxes_total"] = total
        row["checkboxes_prechecked_nondisabled"] = prechecked

        flags = wording_flags(text, found)
        row["lang_confirmshaming"] = flags["confirmshaming"]
        row["lang_implied_consent"] = flags["implied_consent"]
        row["lang_vague_purpose"] = flags["vague_purpose"]
        row["lang_pressure"] = flags["pressure"]
    except Exception as e:
        row["error"] = str(e).splitlines()[0][:150] if str(e) else type(e).__name__
    finally:
        context.close()
    return row


def already_done():
    if not os.path.exists(OUT_FILE):
        return set()
    with open(OUT_FILE, newline="", encoding="utf-8") as f:
        return {r["url"] for r in csv.DictReader(f)}


def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(SITES_FILE, newline="", encoding="utf-8") as f:
        sites = list(csv.DictReader(f))
    done = already_done()
    todo = [s for s in sites if s["url"] not in done]
    if LIMIT:
        todo = todo[:LIMIT]
    print(f"{len(sites)} sites in file, {len(done)} already done, {len(todo)} to scan")

    new_file = not os.path.exists(OUT_FILE)
    with open(OUT_FILE, "a", newline="", encoding="utf-8") as out, sync_playwright() as p:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch(headless=HEADLESS)
        for i, site in enumerate(todo, start=1):
            row = scan_site(browser, site["url"], site.get("sector", ""))
            writer.writerow(row)
            out.flush()
            print(f"[{i}/{len(todo)}] {site['url']}  robots={row['robots_status']}  "
                  f"banner={row['banner_found']}  pattern={row['first_layer_pattern']}  "
                  f"error={row['error'] or '-'}")
            time.sleep(random.uniform(MIN_DELAY_S, MAX_DELAY_S))
        browser.close()
    print(f"\nDone. Results in {OUT_FILE}")


if __name__ == "__main__":
    main()