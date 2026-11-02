import csv
import os
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS = os.path.join(ROOT, "results", "eval_results.csv")
SHOTS_DIR = os.path.join(ROOT, "results", "eval_shots")
OUT_DIR = os.path.join(ROOT, "results", "eval_shots_labeled")
MAX_W = 1000
BAR_H = 56


def load_font(size):
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


os.makedirs(OUT_DIR, exist_ok=True)
with open(RESULTS, newline="", encoding="utf-8") as f:
    rows = [r for r in csv.DictReader(f) if str(r["banner_found"]).lower() == "true"]

font = load_font(30)
made, missing = 0, []
for i, r in enumerate(rows, start=1):
    name = re.sub(r"[^a-z0-9]+", "_", r["url"].lower()).strip("_") + ".png"
    path = os.path.join(SHOTS_DIR, name)
    if not os.path.exists(path):
        missing.append(r["url"])
        continue
    img = Image.open(path).convert("RGB")
    if img.width > MAX_W:
        img = img.resize((MAX_W, int(img.height * MAX_W / img.width)))
    width = max(img.width, 520)
    canvas = Image.new("RGB", (width, img.height + BAR_H), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, width, BAR_H], fill=(20, 20, 20))
    draw.text((12, 10), f"{i:02d}  {r['url']}", fill="white", font=font)
    canvas.paste(img, (0, BAR_H))
    canvas.save(os.path.join(OUT_DIR, f"{i:02d}_{name}"))
    made += 1

print(f"{made} labeled screenshots saved in {OUT_DIR}")
if missing:
    print("no screenshot saved for:", missing)