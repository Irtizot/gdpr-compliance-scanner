# Consent Banner Signals (Manifest V3)

Passive, local-only browser extension. It reads the page you are already viewing, finds the cookie banner, measures design and wording signals, and records which third-party hosts and Set-Cookie responses appeared during page load. Nothing is sent anywhere and nothing is clicked.

## Install (Chrome or Edge)
1. Unzip the folder.
2. Open chrome://extensions and turn on Developer mode.
3. Choose Load unpacked and select the unzipped folder.
4. Visit a site, wait about 10 to 20 seconds, then click the extension icon.

## What it reports
Eleven signals: no reject option, pre-ticked box, filled accept vs plain reject, accept contrast, accept size, confirmshaming, implied consent, vague purpose, pressure wording, known trackers, third-party cookies. Each card shows the signal, why it may matter, and a caution. It reports signals, not legal verdicts. Mappings to GDPR, ePrivacy and EDPB guidance live in `mapping.json`.

## Method (ported from the Python scanner, codebook-v1)
- Banner finder order: CSS selectors (open shadow DOM included), iframes, text fallback.
- Button classification: reject, then settings, then accept, with the same widening step.
- Measures: size ratio 1.5, contrast difference 2.0, filled distance 40, WCAG contrast.
- Network window: navigation start to DOMContentLoaded plus 4 seconds.
- Tracker list: Disconnect services.json (3555 domains, retrieved 2026-10-29, CC BY-NC-SA 4.0).

## Known limits
- If you accepted cookies on an earlier visit, early requests may be consent-based. Use a fresh profile or clear site data for a clean read.
- Only cookies set by HTTP Set-Cookie headers are seen. Script-set cookies are missed. A cookie the browser later blocks is still counted.
- English phrase lists only. Single page load. Second-layer settings are not opened.
- Registered domains use a small built-in suffix list, not the full Public Suffix List.
