import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_folder(name):
    for base in [Path.cwd(), HERE, *HERE.parents]:
        if (base / name).is_dir():
            return base / name
    return Path.cwd() / name


def find_results():
    for base in [Path.cwd(), HERE, *HERE.parents]:
        d = base / "results"
        if (d / "eval_results.csv").exists():
            return d
    return Path.cwd() / "results"


RESULTS_DIR = find_results()
FILES = ["eval_results.csv", "pilot_rescan_results.csv"]
FIELDS = [
    "url", "sector", "scanned_at", "robots_status", "http_status", "blocked", "page_loaded", "error",
    "banner_found", "banner_selector", "first_layer_pattern",
    "accept_found", "reject_found", "settings_found", "accept_label", "reject_label",
    "accept_area", "reject_area", "size_ratio", "size_flag",
    "accept_contrast", "reject_contrast", "contrast_diff", "contrast_flag",
    "accept_style", "reject_style", "style_asymmetry_flag",
    "checkboxes_total", "checkboxes_prechecked_nondisabled",
    "lang_confirmshaming", "lang_implied_consent", "lang_vague_purpose", "lang_pressure",
    "third_party_domains_pre_consent", "known_tracker_domains_pre_consent",
    "known_trackers", "cookies_total_pre_consent", "third_party_cookies_pre_consent",
    "banner_text", "all_labels", "lang_matches",
]


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def load():
    rows = {}
    for name in FILES:
        path = RESULTS_DIR / name
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8-sig") as f:
            data = list(csv.reader(f))
        if not data:
            continue
        if data[0] and data[0][0].strip().lower() == "url":
            header, body = data[0], data[1:]
        else:
            header, body = FIELDS, data
        for values in body:
            r = dict(zip(header, values))
            if r.get("url"):
                rows[r["url"]] = r
    return list(rows.values())


def show(title, rows):
    print(f"\n{title}")
    for r in rows:
        print(f"   {r['url']}   [{r.get('sector', '')}]")


def main():
    random.seed(7)
    all_rows = load()
    print("Results folder:", RESULTS_DIR)
    print("Rows read:", len(all_rows))
    loaded = [r for r in all_rows if truthy(r.get("page_loaded"))]
    banner = [r for r in loaded if truthy(r.get("banner_found"))]
    none = [r for r in loaded if not truthy(r.get("banner_found"))]
    ar = [r for r in banner if r.get("first_layer_pattern") == "accept_reject"]
    asets = [r for r in banner if r.get("first_layer_pattern") == "accept_settings"]
    odd = [r for r in banner if r.get("banner_selector", "").startswith(("iframe", "text"))]
    flagged = [r for r in banner if truthy(r.get("style_asymmetry_flag")) or truthy(r.get("size_flag")) or truthy(r.get("contrast_flag"))]
    chosen, seen = [], set()

    def take(pool, n, title):
        pool = [r for r in pool if r["url"] not in seen]
        pick = random.sample(pool, min(n, len(pool)))
        for r in pick:
            seen.add(r["url"])
        chosen.extend(pick)
        show(title, pick)

    print(f"Pages loaded by the scanner: {len(loaded)}, with banner: {len(banner)}, without: {len(none)}")
    take(ar, 3, "Banner with accept and reject")
    take(asets, 3, "Banner with accept and settings")
    take(odd, 2, "Banner found through an iframe or the text fallback")
    take(flagged, 2, "Flagged for size, contrast or style")
    take(none, 2, "No banner found by the scanner")
    print(f"\n{len(chosen)} sites chosen.")


if __name__ == "__main__":
    main()