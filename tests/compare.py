import json
py = json.load(open("py_out.json")); ex = json.load(open("ext_out.json"))
bad = 0
for f in py:
    p, e = py[f], ex[f]
    if "error" in e:
        print(f"{f:14} NO EXTENSION DATA ({e['error']})")
        bad += 1
        continue
    b = e.get("banner")
    rows = [("banner", p["banner"], e.get("bannerFound")),
            ("3p domains", p["tracking"]["third_party_domains"], e["tracking"]["third_party_domains"]),
            ("trackers", p["tracking"]["known_trackers"], e["tracking"]["known_trackers"]),
            ("cookies", p["tracking"]["cookies_total"], e["tracking"]["cookies_total"]),
            ("3p cookies", p["tracking"]["third_party_cookies"], e["tracking"]["third_party_cookies"])]
    if p["banner"] and b:
        rows += [("selector", p["selector"], b["selector"]), ("pattern", p["pattern"], b["pattern"]),
                 ("accept", p["accept"], b["accept"]), ("reject", p["reject"], b["reject"]), ("settings", p["settings"], b["settings"]),
                 ("acc_style", p["acc_style"], (b["measures"]["accept"] or {}).get("style")),
                 ("rej_style", p["rej_style"], (b["measures"]["reject"] or {}).get("style")),
                 ("size_flag", p["size_flag"], b["size_flag"]), ("contrast_flag", p["contrast_flag"], b["contrast_flag"]),
                 ("style_flag", p["style_flag"], b["style_asymmetry_flag"]),
                 ("checkboxes", p["cb"], [b["checkboxes_total"], b["checkboxes_prechecked"]]),
                 ("lang", {k: v for k, v in p["lang"]["flags"].items()} if "flags" in p["lang"] else p["lang"], b["lang"])]
    diffs = [(k, a, c) for k, a, c in rows if a != c]
    print(f"{f:14} {'OK' if not diffs else 'DIFF'}")
    for d in diffs: print("    ", d); bad += 1
print("differences:", bad)