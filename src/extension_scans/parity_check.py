import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent


def find_folder(name):
    for base in [Path.cwd(), HERE, *HERE.parents]:
        if (base / name).is_dir():
            return base / name
    return Path.cwd() / name


SCANS_DIR = find_folder("extension_scans")
RESULTS_DIR = find_folder("results")
SCANNER_FILES = [RESULTS_DIR / "eval_results.csv", RESULTS_DIR / "pilot_rescan_results.csv"]
REPORT_FILE = RESULTS_DIR / "parity_report.csv"

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


def truthy(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def host_key(url):
    host = (urlparse(url if "//" in url else "//" + url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def clean_json_text(text):
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
    return text.strip()


def load_scanner_rows():
    rows = {}
    for path in SCANNER_FILES:
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
        if not reader:
            continue
        if reader[0] and reader[0][0].strip().lower() == "url":
            header, body = reader[0], reader[1:]
        else:
            header, body = FIELDS, reader
        for values in body:
            row = dict(zip(header, values))
            key = host_key(row.get("url", ""))
            if key:
                rows[key] = row
    return rows


def load_extension_scans():
    scans = {}
    for path in sorted(SCANS_DIR.glob("*.json")):
        try:
            data = json.loads(clean_json_text(path.read_text(encoding="utf-8-sig")))
        except Exception as e:
            print(f"Could not read {path.name}: {e}")
            continue
        scans[host_key(data.get("url", "") or data.get("host", ""))] = (path.name, data)
    return scans


def first(values):
    return values[0].strip().lower() if values else ""


def compare(row, data):
    b = data.get("banner") or {}
    m = b.get("measures") or {}
    acc, rej = m.get("accept") or {}, m.get("reject") or {}
    lang = b.get("lang") or {}
    t = data.get("tracking") or {}
    s_found = truthy(row.get("banner_found"))
    e_found = bool(data.get("bannerFound"))
    out = {"banner_found": (s_found, e_found)}
    s_trackers = {x for x in (row.get("known_trackers") or "").split(";") if x}
    e_trackers = set(t.get("known_trackers") or [])
    out["any_known_tracker"] = (len(s_trackers) > 0, len(e_trackers) > 0)
    out["any_third_party_cookie"] = (
        str(row.get("third_party_cookies_pre_consent") or "0") not in ("", "0"),
        (t.get("third_party_cookies") or 0) > 0)
    if s_found and e_found:
        out["first_layer_pattern"] = (row.get("first_layer_pattern"), b.get("pattern"))
        out["accept_label"] = (first([row.get("accept_label", "")]), first(b.get("accept") or []))
        out["reject_label"] = (first([row.get("reject_label", "")]), first(b.get("reject") or []))
        out["accept_style"] = (row.get("accept_style") or "", acc.get("style") or "")
        out["reject_style"] = (row.get("reject_style") or "", rej.get("style") or "")
        out["size_flag"] = (truthy(row.get("size_flag")), bool(b.get("size_flag")))
        out["contrast_flag"] = (truthy(row.get("contrast_flag")), bool(b.get("contrast_flag")))
        out["style_asymmetry_flag"] = (truthy(row.get("style_asymmetry_flag")), bool(b.get("style_asymmetry_flag")))
        out["prechecked_box"] = (
            str(row.get("checkboxes_prechecked_nondisabled") or "0") not in ("", "0"),
            (b.get("checkboxes_prechecked") or 0) > 0)
        for name in ("confirmshaming", "implied_consent", "vague_purpose", "pressure"):
            out["lang_" + name] = (truthy(row.get("lang_" + name)), bool(lang.get(name)))
    return out, s_trackers, e_trackers

    print("Scans folder:", SCANS_DIR)
    print("Results folder:", RESULTS_DIR)

def main():
    scanner = load_scanner_rows()
    scans = load_extension_scans()
    if not scans:
        print(f"No JSON files found in {SCANS_DIR}.")
        return
    totals = {}
    report = []
    unmatched = []
    for key, (name, data) in scans.items():
        row = scanner.get(key)
        if row is None:
            unmatched.append(name)
            continue
        if not truthy(row.get("page_loaded")):
            report.append({"site": key, "file": name, "field": "(scanner did not load page)", "scanner": "", "extension": "", "match": ""})
            continue
        cmp, s_tr, e_tr = compare(row, data)
        print(f"\n{key}")
        for field, (s, e) in cmp.items():
            ok = s == e
            totals.setdefault(field, [0, 0])
            totals[field][0] += 1
            totals[field][1] += ok
            report.append({"site": key, "file": name, "field": field, "scanner": s, "extension": e, "match": ok})
            if not ok:
                print(f"   differs  {field}: scanner={s!r} extension={e!r}")
        both = s_tr | e_tr
        overlap = round(100 * len(s_tr & e_tr) / len(both)) if both else 100
        print(f"   tracker domains: scanner {len(s_tr)}, extension {len(e_tr)}, overlap {overlap}%")
    print("\nAgreement by field")
    for field, (n, ok) in totals.items():
        print(f"   {field:26} {ok}/{n}  ({round(100 * ok / n)}%)")
    if unmatched:
        print("\nNo scanner row found for:", ", ".join(unmatched))
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["site", "file", "field", "scanner", "extension", "match"])
        w.writeheader()
        w.writerows(report)
    print(f"\nSaved {REPORT_FILE}")


if __name__ == "__main__":
    main()