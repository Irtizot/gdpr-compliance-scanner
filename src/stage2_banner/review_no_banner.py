import csv
import os

from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT, SETTLE_MS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IN_FILE = os.path.join(ROOT, "results", "no_banner_sites.csv")
OUT_FILE = os.path.join(ROOT, "results", "no_banner_review.csv")
HEADLESS = False  # False so we can see the window


def main():
    with open(IN_FILE, newline="", encoding="utf-8") as f:
        sites = list(csv.DictReader(f))
    sites.sort(key=lambda s: (s["sector"] != "game-boosting", s["sector"]))

    done = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, newline="", encoding="utf-8") as f:
            done = {r["url"] for r in csv.DictReader(f)}
    todo = [s for s in sites if s["url"] not in done]
    print(f"{len(sites)} sites, {len(done)} already reviewed, {len(todo)} to review\n")

    new_file = not os.path.exists(OUT_FILE)
    with open(OUT_FILE, "a", newline="", encoding="utf-8") as out, sync_playwright() as p:
        writer = csv.writer(out)
        if new_file:
            writer.writerow(["url", "sector", "banner_visible"])
        browser = p.chromium.launch(headless=HEADLESS)
        for i, site in enumerate(todo, start=1):
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            try:
                page.goto(site["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(SETTLE_MS)
            except Exception as e:
                print("   (page problem:", str(e).splitlines()[0][:80], ")")
            answer = ""
            while answer not in ("y", "n", "b", "q"):
                answer = input(f"[{i}/{len(todo)}] {site['url']} ({site['sector']})\n"
                               f"   Cookie banner visible in the window? y = yes, n = no, "
                               f"b = blocked / error page, q = quit: ").strip().lower()
            context.close()
            if answer == "q":
                break
            writer.writerow([site["url"], site["sector"], {"y": "yes", "n": "no", "b": "blocked"}[answer]])
            out.flush()
        browser.close()
    print(f"\nSaved answers to {OUT_FILE}")


if __name__ == "__main__":
    main()