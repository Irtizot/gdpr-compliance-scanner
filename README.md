# GDPR Consent and Dark-Pattern Scanner

MSc Cybersecurity dissertation project, University of Kent
Student: Syed Irtiza Abbas | Supervisor: Dr Darren Hurley-Smith

## Project summary

A passive scanner and browser extension that observe how websites present cookie consent. For each page they record observable signals and report them with the GDPR and ePrivacy provisions they relate to. They report signals, not legal verdicts.

Signals covered:
- Consent banner design: missing reject option on the first layer, pre-ticked boxes, filled accept versus non-filled reject, accept contrast, accept size
- Banner wording: confirmshaming, implied consent, vague purpose, pressure
- Early third-party activity: known tracker domains contacted and third-party cookies set during page load and the following four seconds

The scanner visits one landing page per site, clicks nothing, and uses only publicly accessible pages. It respects robots.txt and identifies itself in its user agent.

## Project structure

- `src/stage1_robots/`: robots.txt checker. Records each candidate site's robots.txt status before any page is loaded.
- `src/stage2_banner/`: the Playwright scanner (frozen as `codebook-v1`) and the analysis and evaluation scripts.
  - `pipeline.py`: banner finder, button classification, measures, wording lexicon, tracker summary
  - `run_batch.py`: scans the site list and writes the results CSV
  - `split_results.py`, `analyse_results.py`: split and summarize the evaluation and pilot results
  - `review_eval.py`, `label_shots.py`, `label_eval.py`, `label_12.py`: no-banner review and reference-label tools
  - `evaluate_eval.py`: precision, recall, false positive rate, Wilson intervals and agreement
  - `pick_sites.py`, `parity_check.py`: choose sites for, and run, the extension parity check
- `src/extension/`: Manifest V3 browser extension (content script, background worker, popup, `mapping.json`, bundled tracker list).
- `src/extension_scans/`: saved extension reports used in the parity check.
- `src/shared/`: shared utilities.
- `data/`: site lists (`sites_pilot.csv`, `sites_eval.csv`, `sites_all.csv`) and the tracker list.
- `results/`: scan outputs, labels, metrics and the parity report.
- `docs/`: proposal, GDPR provisions table, early deliverable, logbook.
- `tests/`: test scripts and extension test pages.

## Setup

```
pip install -r requirements.txt
playwright install
```

Run the scripts from the project root so relative paths resolve.

## Reproducing the scan and evaluation

1. Scan: `python src/stage2_banner/run_batch.py` (reads `data/output/sites_all.csv`, writes `results/all_results.csv`)
2. Split into the 60 held-out evaluation sites and the 110 pilot sites: `python src/stage2_banner/split_results.py`
3. Summarize: `python src/stage2_banner/analyse_results.py`
4. Evaluate against the reference labels: `python src/stage2_banner/evaluate_eval.py`

The scanner runs a headed Chromium with a fresh browser context per site. Results vary slightly between runs because ad and tracker requests differ from one page load to the next.

## Installing the extension

1. Open `chrome://extensions` and turn on Developer mode.
2. Choose Load unpacked and select the `src/extension` folder (the one that contains `manifest.json`).
3. Visit a site in a fresh or Incognito window, wait about 25 seconds, then open the extension popup.

To test in Incognito, allow the extension there under its Details page. Cookie choices saved on an earlier visit can make early tracker activity look consent-based, so use a clean profile for clean readings.

## Status

- Project proposal finalized
- GDPR provisions mapped to detection categories
- Early deliverable (critical review) submitted
- Stage 1: robots.txt scanner built
- Stage 2: banner and tracker scanner built and frozen (`codebook-v1`)
- Scan of 170 sites complete: 110 pilot sites (descriptive and development use) and 60 held-out evaluation sites
- Evaluation against reference labels complete (40 evaluation banners)
- Browser extension built and tested on 8 local test pages and 12 real sites
- Dissertation write-up in progress

## Results at a glance

On the held-out evaluation set, banner detection reached 100% precision and 91% recall (40 banners found of 44 present). Indicator results range from strong (for example size and style asymmetry under the broad definition) to weak (vague purpose, 29% precision and 44% recall), and several indicators have too few positive cases to evaluate. Full tables, intervals and limitations are in the dissertation.

The extension matched the scanner on all banner detection and design fields across the 12 parity sites. Third-party cookie presence agreed on 9 of 12 sites, probably because the extension counts Set-Cookie headers while the scanner counts stored cookies.

## Method notes and limitations

- The reference labels were produced with AI assistance from screenshots. The researcher independently labeled a random sample of 12 sites. First-pass agreement was 68%, and kappa was near zero on most questions because most answers were "no". The dissertation reports this in full.
- Wording lexicons are English only. Second-layer settings are not opened. Only a single landing-page visit is made.
- The reject-option matcher reads wordings such as "Accept only essential" or "Essential cookies only" as non-reject, and counts "Pay to Reject" as a reject.
- The contrast measure compares text with its background. It does not capture how much a whole button stands out.
- Button fills drawn with pseudo-elements or background images are not read, so some filled buttons measure as plain (Etsy is an example).
- Some banners were missed by the finder or blocked by the site.

## Data and ethics

- Only publicly accessible pages are scanned, passively, with robots.txt respected.
- Tracker classification uses the Disconnect `services.json` list (retrieved 2026-10-29, CC BY-NC-SA 4.0), bundled as `data/trackers/tracker_domains.txt` and in the extension.

## Citation and archive

A tagged release and Zenodo archive (DOI) will be added after submission.