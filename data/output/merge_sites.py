import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "output"

rows = []
for name, label in (("sites_pilot.csv", "pilot"), ("sites_eval.csv", "eval")):
    with open(OUT_DIR / name, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({"url": r["url"].strip(), "sector": r["sector"].strip(), "set": label})

seen = set()
unique = []
for r in rows:
    key = r["url"].lower().rstrip("/")
    if key in seen:
        print("duplicate skipped:", r["url"], r["set"])
        continue
    seen.add(key)
    unique.append(r)

with open(OUT_DIR / "sites_all.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["url", "sector", "set"])
    w.writeheader()
    w.writerows(unique)

print(len(unique), "sites written to", OUT_DIR / "sites_all.csv")