CORPUS FOR THE MSc DISSERTATION
GDPR Consent and Dark-Pattern Scanner
Student: Syed Irtiza Abbas. Supervisor: Dr Darren Hurley-Smith. University of Kent.

SOURCE
This is release v1.0 of https://github.com/Irtizot/gdpr-compliance-scanner.
The scanner revision used for the reported scans is 78e91a9b2629be76c9c28d66a8206b38d803862d (codebook-v1).

WHAT IS INSIDE
src/stage1_robots/    robots.txt checker
src/stage2_banner/    Playwright scanner (frozen as codebook-v1), analysis and evaluation scripts
src/extension/        Manifest V3 browser extension
src/extension_scans/  saved extension reports and the parity check
data/                 site lists and the tracker list (Disconnect services.json, retrieved 2026-10-29)
results/              scan outputs, reference labels, metrics, parity report, clean-run log
tests/                local test pages and the scanner and extension comparison scripts

NOT INCLUDED
Screenshots of websites are not included. The public banner wording is in the results CSV files.

HOW TO RUN
See README.md in this folder for setup, run commands and extension installation.
Short version, from the project root:
  pip install -r requirements.txt
  playwright install
  python src/stage2_banner/evaluate_eval.py
Local tests: pip install cryptography, run tests/make_fixtures.py once, then tests/run_all.py.

WHERE EACH REPORTED RESULT COMES FROM
Scan results (held-out and pilot):   results/eval_results.csv, results/pilot_rescan_results.csv
Reference labels:                    results/eval_labels_claude.csv (AI-assisted, 40 banners), results/eval_labels_me.csv (researcher, 12 banners)
Accuracy table (Chapter 5):          results/eval_metrics.csv, produced by src/stage2_banner/evaluate_eval.py
Parity check (Chapter 6):            results/parity_report.csv, produced by src/extension_scans/parity_check.py
Local test pages (Chapter 6):        tests/compare_output.txt
Installation in a fresh environment: results/clean_run_log.txt