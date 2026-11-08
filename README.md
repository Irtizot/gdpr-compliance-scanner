# GDPR Consent and Dark-Pattern Scanner

MSc Cybersecurity dissertation project, University of Kent
Student: Syed Irtiza Abbas | Supervisor: Dr Darren Hurley-Smith

A passive scanner and Manifest V3 browser extension that observe how websites present cookie consent. They report signals such as a missing reject option, button size and color differences, manipulative wording and trackers contacted before consent. They report signals, not legal verdicts.

The scanner visits one landing page per site, clicks nothing, uses only publicly accessible pages, respects robots.txt and identifies itself in its user agent.

## Folders

- `src/stage1_robots/`: robots.txt checker
- `src/stage2_banner/`: Playwright scanner (frozen as `codebook-v1`) plus analysis and evaluation scripts
- `src/extension/`: browser extension
- `src/extension_scans/`: saved extension reports for the parity check
- `data/`: site lists and the tracker list
- `results/`: scan outputs, labels, metrics and the parity report
- `docs/`, `tests/`: supporting files

## Run

```
pip install -r requirements.txt
playwright install
python src/stage1_robots/robots_scanner.py
python src/stage2_banner/run_batch.py
python src/stage2_banner/split_results.py
python src/stage2_banner/analyse_results.py
python src/stage2_banner/evaluate_eval.py
```

Run from the project root. Results vary slightly between runs because ad and tracker requests differ.

## Extension

1. Open `chrome://extensions` and turn on Developer mode.
2. Choose Load unpacked and select the `src/extension` folder.
3. Visit a site, wait about 25 seconds, then open the extension popup.

## Notes

- The reference labels were produced with AI assistance from screenshots and checked by the researcher on 12 sites. The dissertation explains the limits.
- Screenshots of websites are not included in this repository. Scan results include the public banner wording.
- Tracker classification uses the Disconnect `services.json` list (retrieved 2026-10-29, CC BY-NC-SA 4.0, Disconnect, Inc.). Its license terms apply to that file.

## Citation

Abbas, S. I., "GDPR Consent and Dark-Pattern Scanner," release v1.0, https://github.com/Irtizot/gdpr-compliance-scanner