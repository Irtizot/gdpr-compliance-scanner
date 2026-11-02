import csv
import os
import random
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "results", "eval_results.csv")
SHOTS_DIR = os.path.join(ROOT, "results", "eval_shots")
OUT_PATH = os.path.join(ROOT, "results", "eval_labels_me.csv")
TARGET = 12

QUESTIONS = [
    ("banner_real", "Is this a real cookie or consent banner?"),
    ("no_reject_option", "Is there NO button or link on this first layer that rejects non-essential cookies? (Reject, Decline, Only necessary. 'Reject and Pay' counts as a reject option.)"),
    ("prechecked_box", "Is any non-essential checkbox already ticked?"),
    ("filled_vs_link", "Is the accept option a filled button while the reject option is only a plain link or plain text?"),
    ("accept_more_contrast", "Does the accept option clearly stand out more than the reject option in color or contrast?"),
    ("accept_much_larger", "Is the accept option clearly much larger than the reject option (about 1.5 times or more)?"),
    ("confirmshaming", "Does the wording of the reject option shame or guilt the user?"),
    ("implied_consent", "Does the text say that continuing, closing or browsing counts as consent?"),
    ("vague_purpose", "Does the text describe purposes only vaguely, such as 'improve your experience', without naming specific purposes?"),
    ("pressure", "Does the text use urgency or pressure to push the user to accept?"),
]
FIELDS = ["url", "sector"] + [k for k, _ in QUESTIONS]


def shot_path(url):
    name = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_") + ".png"
    return os.path.join(SHOTS_DIR, name)


def ask(prompt):
    while True:
        ans = input(f"  {prompt}\n    y = yes, n = no, u = unclear, q = quit: ").strip().lower()
        if ans in ("y", "n", "u", "q"):
            return ans


def main():
    with open(RESULTS, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if str(r["banner_found"]).lower() == "true"]
    random.Random(42).shuffle(rows)
    sample = rows[:TARGET]

    done = set()
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, newline="", encoding="utf-8") as f:
            done = {r["url"] for r in csv.DictReader(f)}
    todo = [r for r in sample if r["url"] not in done]
    print(f"{len(sample)} sites in your sample, {len(done)} already labeled, {len(todo)} to label")
    if not todo:
        print("All done. Rerun evaluate_eval.py.")
        return

    new_file = not os.path.exists(OUT_PATH)
    with open(OUT_PATH, "a", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for i, r in enumerate(todo, start=1):
            print(f"\n[{i}/{len(todo)}] {r['url']}")
            path = shot_path(r["url"])
            if os.path.exists(path):
                try:
                    os.startfile(path)
                except Exception:
                    print("  screenshot:", path)
            else:
                print("  no screenshot saved for this site, use the text below")
            print("  Banner text:", r["banner_text"][:1500])
            answers = {"url": r["url"], "sector": r["sector"]}
            quit_now = False
            for key, question in QUESTIONS:
                ans = ask(question)
                if ans == "q":
                    quit_now = True
                    break
                answers[key] = ans
                if key == "banner_real" and ans == "n":
                    break
            if quit_now:
                break
            for key, _ in QUESTIONS:
                answers.setdefault(key, "")
            writer.writerow(answers)
            out.flush()
    print("\nSaved", OUT_PATH)


if __name__ == "__main__":
    main()