import csv
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "results", "eval_results.csv")
LABELS = os.path.join(ROOT, "results", "eval_labels_claude.csv")
SECOND = os.path.join(ROOT, "results", "eval_labels_me.csv")
METRICS = os.path.join(ROOT, "results", "eval_metrics.csv")

LABEL_TEXT = """url,sector,banner_real,no_reject_option,prechecked_box,filled_vs_link,accept_more_contrast,accept_much_larger,confirmshaming,implied_consent,vague_purpose,pressure
https://www.ft.com,news,y,n,n,n,n,n,n,n,n,n
https://www.dailystar.co.uk,news,y,n,u,u,u,u,n,n,n,n
https://www.lbc.co.uk,news,y,n,n,n,n,n,n,n,n,n
https://www.bloomberg.com,news,y,n,n,n,n,n,n,n,n,n
https://www.asda.com,retail,y,n,n,n,n,n,n,n,n,n
https://www.ikea.com,retail,y,n,n,n,n,n,n,n,n,n
https://www.halfords.com,retail,y,n,n,n,y,n,n,n,y,n
https://www.boohoo.com,retail,y,n,n,n,n,n,n,n,n,n
https://www.prettylittlething.com,retail,y,n,n,n,n,n,n,n,n,n
https://www.virginatlantic.com,travel,y,n,n,n,n,n,n,n,n,n
https://www.nationalexpress.com,travel,y,n,n,n,y,n,n,n,n,n
https://www.opodo.co.uk,travel,y,n,n,y,y,y,n,n,n,n
https://www.playstation.com,gaming,y,n,n,n,n,n,n,n,n,n
https://www.xbox.com,gaming,y,n,n,n,n,n,n,n,n,n
https://www.nintendo.com,gaming,y,n,n,n,n,n,n,n,n,n
https://www.gamesradar.com,gaming,y,n,n,n,y,n,n,n,n,n
https://www.polygon.com,gaming,y,y,n,u,u,u,n,n,n,n
https://www.greenmangaming.com,gaming,y,n,n,n,y,n,n,n,n,n
https://www.santander.co.uk,finance,y,n,n,n,n,n,n,n,y,n
https://www.tsb.co.uk,finance,y,u,u,u,u,u,u,u,u,u
https://www.moneysupermarket.com,finance,y,n,n,n,y,n,n,n,n,n
https://www.experian.co.uk,finance,y,n,n,n,n,n,n,n,y,n
https://www.hl.co.uk,finance,y,n,n,n,y,n,n,n,y,n
https://www.coventrybuildingsociety.co.uk,finance,y,n,n,n,y,n,n,n,n,n
https://www.atlassian.com,software,y,n,n,n,y,n,n,n,n,n
https://www.shopify.com,software,y,n,n,n,n,n,n,n,n,n
https://www.wordpress.com,software,y,n,n,n,y,n,n,n,y,n
https://www.duolingo.com,software,y,n,n,n,n,n,n,n,n,n
https://www.cam.ac.uk,public,y,n,n,n,n,n,n,n,y,n
https://www.ucas.com,public,y,n,u,u,u,u,n,n,n,n
https://www.nationaltrust.org.uk,public,y,n,n,n,n,n,n,n,n,n
https://www.bl.uk,public,y,u,u,u,u,u,u,u,u,u
https://wecoach.gg,game-boosting,y,n,n,n,y,n,n,n,y,n
https://www.ggboost.com,game-boosting,y,n,n,n,y,n,n,n,y,n
https://www.u7buy.com,game-boosting,y,n,n,n,n,n,n,y,y,n
https://www.z2u.com,game-boosting,y,n,n,n,y,n,n,n,n,n
https://www.ladbrokes.com,gambling,y,n,n,n,n,n,n,n,n,n
https://www.coral.co.uk,gambling,y,n,n,n,n,n,n,n,n,n
https://www.betfair.com,gambling,y,n,n,n,n,n,n,n,n,n
https://www.nowtv.com,streaming,y,n,n,n,n,n,n,n,n,n"""

FIELDS = ["url", "sector", "banner_real", "no_reject_option", "prechecked_box", "filled_vs_link",
          "accept_more_contrast", "accept_much_larger", "confirmshaming", "implied_consent",
          "vague_purpose", "pressure"]
VISUAL = ("filled_vs_link", "accept_more_contrast", "accept_much_larger")


def truthy(v):
    return str(v).strip().lower() == "true"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


SCANNER = {
    "no_reject_option": lambda r: truthy(r["accept_found"]) and not truthy(r["reject_found"]),
    "prechecked_box": lambda r: num(r["checkboxes_prechecked_nondisabled"]) > 0,
    "filled_vs_link": lambda r: truthy(r["style_asymmetry_flag"]) and r["reject_style"] == "plain",
    "accept_more_contrast": lambda r: truthy(r["contrast_flag"]),
    "accept_much_larger": lambda r: truthy(r["size_flag"]),
    "confirmshaming": lambda r: truthy(r["lang_confirmshaming"]),
    "implied_consent": lambda r: truthy(r["lang_implied_consent"]),
    "vague_purpose": lambda r: truthy(r["lang_vague_purpose"]),
    "pressure": lambda r: truthy(r["lang_pressure"]),
}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fmt(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})"


def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None, None
    agree = sum(1 for a, b in pairs if a == b) / n
    pa = sum(1 for a, _ in pairs if a == "y") / n
    pb = sum(1 for _, b in pairs if b == "y") / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    k = 1.0 if pe == 1 else (agree - pe) / (1 - pe)
    return k, agree


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if not os.path.exists(LABELS):
    with open(LABELS, "w", newline="", encoding="utf-8") as f:
        f.write(LABEL_TEXT.strip() + "\n")

scan = {r["url"]: r for r in read(RESULTS)}
labels = read(LABELS)

real = sum(1 for l in labels if l["banner_real"] == "y")
notreal = sum(1 for l in labels if l["banner_real"] == "n")
print(f"Banners labeled: {len(labels)}  real: {real}  not a banner: {notreal}")
print(f"Banner detection precision: {fmt(real, real + notreal)}")
print("Banner detection recall: 40 found of 44 real (4 missed in the no-banner review)\n")

print(f"{'indicator':22} {'TP':>3} {'FP':>3} {'FN':>3} {'TN':>3}  {'precision':>16} {'recall':>16} {'FPR':>16}")
out = []
for k, flag in SCANNER.items():
    tp = fp = fn = tn = 0
    for l in labels:
        if l["banner_real"] != "y" or l[k] not in ("y", "n"):
            continue
        if k in VISUAL and l["no_reject_option"] != "n":
            continue
        s = scan.get(l["url"])
        if s is None:
            continue
        p, t = flag(s), l[k] == "y"
        tp += p and t
        fp += p and not t
        fn += (not p) and t
        tn += (not p) and not t
    print(f"{k:22} {tp:>3} {fp:>3} {fn:>3} {tn:>3}  {fmt(tp, tp + fp):>16} {fmt(tp, tp + fn):>16} {fmt(fp, fp + tn):>16}")
    out.append({"indicator": k, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                "precision": fmt(tp, tp + fp), "recall": fmt(tp, tp + fn), "FPR": fmt(fp, fp + tn)})

with open(METRICS, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
print("\nSaved", METRICS)

if os.path.exists(SECOND):
    mine = {r["url"]: r for r in read(SECOND)}
    print("\nAgreement between the two label sets (kappa, raw agreement, n):")
    for k in FIELDS[2:]:
        pairs = [(l[k], mine[l["url"]][k]) for l in labels
                 if l["url"] in mine and l[k] in ("y", "n") and mine[l["url"]][k] in ("y", "n")]
        kap, agree = kappa(pairs)
        if kap is not None:
            print(f"  {k:22} kappa {kap:5.2f}  agreement {100 * agree:3.0f}%  n={len(pairs)}")