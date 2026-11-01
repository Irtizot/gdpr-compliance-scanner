import hashlib
import json
import os
from datetime import date

import requests

URL = "https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json"
CATEGORIES = ("Advertising", "Analytics", "Social", "FingerprintingInvasive", "FingerprintingGeneral")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "data", "trackers")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    raw = requests.get(URL, timeout=60).content
    today = date.today().isoformat()
    with open(os.path.join(OUT_DIR, f"disconnect_services_{today}.json"), "wb") as f:
        f.write(raw)

    data = json.loads(raw)
    domains = set()
    for category in CATEGORIES:
        for entry in data["categories"].get(category, []):
            for company, sites in entry.items():
                if not isinstance(sites, dict):
                    continue
                for site, hosts in sites.items():
                    if isinstance(hosts, list):
                        domains.update(h.strip().lower() for h in hosts if h.strip())

    with open(os.path.join(OUT_DIR, "tracker_domains.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(domains)) + "\n")

    meta = {
        "source": URL,
        "retrieved": today,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "categories_used": list(CATEGORIES),
        "domains": len(domains),
        "license": "CC BY-NC-SA 4.0 (Disconnect, Inc.)",
    }
    with open(os.path.join(OUT_DIR, "tracker_list_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {len(domains)} tracker domains to {OUT_DIR}")


if __name__ == "__main__":
    main()