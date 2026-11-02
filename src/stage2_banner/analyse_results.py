import csv
import os
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
IN_FILE = os.path.join(ROOT, "results", "eval_results.csv")
OUT_FILE = os.path.join(ROOT, "results", "eval_category_summary.csv")
NO_BANNER_FILE = os.path.join(ROOT, "results", "eval_no_banner_sites.csv")

MIN_TESTABLE = 20
MIN_FLAGGED = 5


def truthy(v):
    return str(v).strip().lower() == "true"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def g(r, key):
    return r.get(key, "")


def indicators():
    banner = lambda r: truthy(g(r, "banner_found"))
    loaded = lambda r: truthy(g(r, "page_loaded"))
    both = lambda r: truthy(g(r, "accept_found")) and truthy(g(r, "reject_found"))
    return [
        ("consent behavior", "no reject option on first layer",
         lambda r: banner(r) and truthy(g(r, "accept_found")),
         lambda r: not truthy(g(r, "reject_found"))),
        ("consent behavior", "pre-ticked non-essential checkbox",
         lambda r: banner(r) and num(g(r, "checkboxes_total")) > 0,
         lambda r: num(g(r, "checkboxes_prechecked_nondisabled")) > 0),
        ("visual deception", "accept much larger than reject", both, lambda r: truthy(g(r, "size_flag"))),
        ("visual deception", "accept higher contrast than reject", both, lambda r: truthy(g(r, "contrast_flag"))),
        ("visual deception", "accept filled, reject link-style", both, lambda r: truthy(g(r, "style_asymmetry_flag"))),
        ("dark pattern language", "confirmshaming wording", banner, lambda r: truthy(g(r, "lang_confirmshaming"))),
        ("dark pattern language", "implied consent wording", banner, lambda r: truthy(g(r, "lang_implied_consent"))),
        ("dark pattern language", "vague purpose wording", banner, lambda r: truthy(g(r, "lang_vague_purpose"))),
        ("dark pattern language", "pressure wording", banner, lambda r: truthy(g(r, "lang_pressure"))),
        ("tracker activity", "known tracker contacted before consent", loaded,
         lambda r: num(g(r, "known_tracker_domains_pre_consent")) > 0),
        ("tracker activity", "third-party cookie set before consent", loaded,
         lambda r: num(g(r, "third_party_cookies_pre_consent")) > 0),
    ]


def main():
    with open(IN_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    robots_skipped = [r for r in rows if g(r, "robots_status") in ("disallowed", "unreachable")]
    blocked = [r for r in rows if truthy(g(r, "blocked"))]
    loaded = [r for r in rows if truthy(g(r, "page_loaded"))]
    banners = [r for r in loaded if truthy(g(r, "banner_found"))]
    no_banner = [r for r in loaded if not truthy(g(r, "banner_found"))]

    print(f"\nSites in file: {len(rows)}")
    print(f"  skipped by robots.txt (disallowed or unreachable): {len(robots_skipped)}")
    print(f"  blocked by the site (access denied / bot wall):     {len(blocked)}")
    print(f"  pages loaded and analyzable:                        {len(loaded)}")
    print(f"     banner found:     {len(banners)} ({100 * len(banners) / len(loaded) if loaded else 0:.0f}%)")
    print(f"     no banner found:  {len(no_banner)}")

    print("\nFirst-layer pattern (sites with a banner):")
    for pattern, n in Counter(g(r, "first_layer_pattern") for r in banners).most_common():
        print(f"  {pattern:18} {n}")

    out_rows = []
    print(f"\n{'category':22} {'indicator':40} {'testable':>8} {'flagged':>8} {'%':>5}  ready?")
    for cat, name, testable, flagged in indicators():
        t = [r for r in rows if testable(r)]
        f = [r for r in t if flagged(r)]
        pct = 100 * len(f) / len(t) if t else 0
        ready = len(t) >= MIN_TESTABLE and len(f) >= MIN_FLAGGED
        out_rows.append({"category": cat, "indicator": name, "n_testable": len(t),
                         "n_flagged": len(f), "pct_flagged": round(pct, 1), "ready": ready})
        print(f"{cat:22} {name:40} {len(t):>8} {len(f):>8} {pct:>5.0f}  {'YES' if ready else 'no'}")

    print("\nCategory readiness (at least one indicator ready):")
    by_cat = defaultdict(list)
    for o in out_rows:
        by_cat[o["category"]].append(o["ready"])
    for cat, flags in by_cat.items():
        print(f"  {cat:22} {'READY' if any(flags) else 'not yet'}")

    sectors = defaultdict(lambda: [0, 0, 0])
    for r in loaded:
        s = g(r, "sector") or "unlabeled"
        sectors[s][0] += 1
        if truthy(g(r, "banner_found")):
            sectors[s][1] += 1
        if any(t(r) and fl(r) for _, _, t, fl in indicators()):
            sectors[s][2] += 1
    print("\nBy sector (loaded / banner found / at least one flagged indicator):")
    for s, (tot, b, fl) in sorted(sectors.items()):
        print(f"  {s:22} {tot:>3} / {b:>3} / {fl:>3}")

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    with open(NO_BANNER_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "sector", "checked_by_eye", "banner_visible_to_me"])
        for r in no_banner:
            w.writerow([g(r, "url"), g(r, "sector"), "", ""])
    print(f"\nSaved {OUT_FILE}")
    print(f"Saved {NO_BANNER_FILE}  (sites to check by eye for missed banners)")


if __name__ == "__main__":
    main()