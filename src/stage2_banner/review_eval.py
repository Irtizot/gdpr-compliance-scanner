import csv
import os

from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "results", "eval_results.csv")
REVIEW = os.path.join(ROOT, "results", "eval_no_banner_review.csv")
WAIT_MS = 15000

FIELDS = ["url", "sector", "verdict"]
VERDICTS = {"y": "banner_visible", "n": "no_banner", "b": "blocked_or_broken"}


def load_candidates():
    with open(RESULTS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows
            if str(r["page_loaded"]).lower() == "true" and str(r["banner_found"]).lower() != "true"]


def load_done():
    if not os.path.exists(REVIEW):
        return set()
    with open(REVIEW, newline="", encoding="utf-8") as f:
        return {r["url"] for r in csv.DictReader(f)}


def main():
    candidates = load_candidates()
    done = load_done()
    todo = [r for r in candidates if r["url"] not in done]
    print(f"{len(candidates)} sites, {len(done)} already reviewed, {len(todo)} to review")
    if not todo:
        return

    new_file = not os.path.exists(REVIEW)
    with open(REVIEW, "a", newline="", encoding="utf-8") as out, sync_playwright() as p:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch(headless=False)
        for i, r in enumerate(todo, start=1):
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            print(f"\n[{i}/{len(todo)}] {r['url']}")
            try:
                page.goto(r["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(WAIT_MS)
            except Exception as e:
                print("  load problem:", str(e).splitlines()[0][:100])
            while True:
                ans = input("  Is a cookie banner visible? y = yes, n = no banner, b = blocked or broken, q = quit: ").strip().lower()
                if ans in VERDICTS or ans == "q":
                    break
            context.close()
            if ans == "q":
                break
            writer.writerow({"url": r["url"], "sector": r["sector"], "verdict": VERDICTS[ans]})
            out.flush()
        browser.close()

    with open(REVIEW, newline="", encoding="utf-8") as f:
        counts = {}
        for r in csv.DictReader(f):
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\nReview so far:", counts)


if __name__ == "__main__":
    main()