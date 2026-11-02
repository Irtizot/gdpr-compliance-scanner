import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SITES = os.path.join(ROOT, "data", "output", "sites_all.csv")
ALL = os.path.join(ROOT, "results", "all_results.csv")
EVAL_OUT = os.path.join(ROOT, "results", "eval_results.csv")
PILOT_OUT = os.path.join(ROOT, "results", "pilot_rescan_results.csv")


def key(url):
    return url.strip().lower().rstrip("/")


with open(SITES, newline="", encoding="utf-8-sig") as f:
    which = {key(r["url"]): r["set"] for r in csv.DictReader(f)}

with open(ALL, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

eval_rows = [r for r in rows if which.get(key(r["url"])) == "eval"]
pilot_rows = [r for r in rows if which.get(key(r["url"])) == "pilot"]
unknown = [r["url"] for r in rows if key(r["url"]) not in which]

for path, subset in ((EVAL_OUT, eval_rows), (PILOT_OUT, pilot_rows)):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(subset)

print(f"{len(rows)} rows in all_results.csv")
print(f"{len(eval_rows)} eval rows written to {EVAL_OUT}")
print(f"{len(pilot_rows)} pilot rows written to {PILOT_OUT}")
if unknown:
    print("not found in sites_all.csv:", unknown)