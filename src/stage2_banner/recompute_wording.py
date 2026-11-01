import csv
import os
import re

from pipeline import LEXICON

csv.field_size_limit(10 ** 7)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FILE = os.path.join(ROOT, "results", "pilot_results.csv")


def corpus_for(row):
    labels = re.sub(r"(accept|reject|settings): ", "", row.get("all_labels", ""))
    labels = labels.replace(" | ", " ").replace("; ", " ")
    return re.sub(r"\s+", " ", (row.get("banner_text", "") + " " + labels))


def main():
    with open(FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    changed = 0
    for row in rows:
        if row["banner_found"] != "True":
            continue
        corpus = corpus_for(row)
        hits = []
        for name, patterns in LEXICON.items():
            matched = None
            for p in patterns:
                m = p.search(corpus)
                if m:
                    matched = m.group(0)
                    hits.append(f"{name}: {matched}")
                    break
            new = str(matched is not None)
            if row["lang_" + name] != new:
                changed += 1
            row["lang_" + name] = new
        row["lang_matches"] = " || ".join(hits)

    tmp = FILE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, FILE)
    print(f"Recomputed wording flags for {sum(r['banner_found'] == 'True' for r in rows)} banners; "
          f"{changed} flag values changed.")
    for name in LEXICON:
        n = sum(r["lang_" + name] == "True" for r in rows if r["banner_found"] == "True")
        print(f"  {name}: {n} sites")


if __name__ == "__main__":
    main()