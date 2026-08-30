# GDPR Compliance Scanner (Browser Extension)

MSc Cybersecurity dissertation project at University of Kent
Student: Syed Irtiza Abbas | Supervisor: Dr Darren Hurley-Smith

## Project summary

A browser extension that automatically detects likely GDPR compliance
issues on websites covering cookie consent behaviour, dark pattern
language, privacy policy accessibility, and third-party tracker
enumeration and maps detected issues to the specific GDPR provisions
they relate to.

## Project structure

- `src/stage1_robots/`:robots.txt configuration scanner. Checks each
  candidate site's robots.txt for restrictions on cart/checkout/account
  paths before any content scanning is attempted. Requests-only, no
  browser rendering needed.
- `src/stage2_content/`:(in progress) Playwright-based content scanner.
  Only scans sites/paths cleared by Stage 1. Handles text extraction,
  computed-style extraction (visual deception detection), and network
  request logging (tracker enumeration).
- `src/shared/`:shared utilities used by both stages.
- `data/`:candidate site lists and scan output datasets.
- `docs/`:proposal, GDPR provisions table, early deliverable, logbook.
- `tests/`:test scripts.

## Setup

```bash
pip install -r requirements.txt
playwright install
```

## Status

- [x] Project proposal finalised
- [x] GDPR provisions mapped to detection categories
- [x] Early Deliverable (critical review) submitted
- [x] Stage 1: robots.txt scanner built
- [ ] Stage 2: content scanner (Playwright) / in progress
- [ ] Scoring/reporting layer
- [ ] Evaluation against sample site set
