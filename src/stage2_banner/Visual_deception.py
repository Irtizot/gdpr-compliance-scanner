"""
Stage 2, Part B: Visual Deception Detection

Purpose: Given a page where the Accept/Reject buttons have already been
located (Part A), extracts their COMPUTED CSS styles and compare them to
detect visual manipulation e.g. Accept being much larger, higher
contrast, or more visually prominent than Reject.

This directly implements the "visual deception" detection category
discussed in the project proposal, addressing the text-only blind spot
identified in the critique of Mathur et al. (2019).
"""

from playwright.sync_api import sync_playwright, Page, Locator
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import csv
import time
import math

USER_AGENT = "IrtizaMScDissertationBot/1.0"

ACCEPT_TEXT_PATTERNS = ["accept all", "accept additional cookies", "accept cookies", "i agree", "allow all", "accept"]
REJECT_TEXT_PATTERNS = ["reject all", "reject additional cookies", "decline", "manage preferences", "necessary only", "reject"]


@dataclass
class VisualStyle:
    width: float
    height: float
    area: float
    font_size: float
    background_color: str
    text_color: str
    contrast_ratio: float | None  # None if colors couldn't be parsed


@dataclass
class VisualDeceptionResult:
    site: str
    accept_found: bool
    reject_found: bool
    accept_area: float
    reject_area: float
    size_ratio: float | None       # accept_area / reject_area
    accept_contrast: float | None
    reject_contrast: float | None
    size_flag: bool                # True if accept is larger
    contrast_flag: bool            # True if accept has notably higher self-contrast (more visually loud)
    error: str
    scanned_at: str



# Colour / contrast helpers
def _parse_rgb(css_color: str) -> tuple[int, int, int] | None:
    """
    Parse a CSS rgb()/rgba() string (what getComputedStyle returns) into
    an (r, g, b) tuple. Returns None if it can't be parsed (e.g. 'transparent').
    """
    if not css_color or "rgb" not in css_color:
        return None
    try:
        nums = css_color[css_color.find("(") + 1: css_color.find(")")]
        parts = [float(x.strip()) for x in nums.split(",")]
        r, g, b = parts[0], parts[1], parts[2]
        return int(r), int(g), int(b)
    except Exception:
        return None


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG relative luminance formula, standard measure of perceived brightness."""
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    """WCAG contrast ratio between two colors, the same formula browsers/accessibility tools use."""
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def get_computed_style(page: Page, locator: Locator, debug_label: str = "") -> VisualStyle | None:
    """
    Pull bounding box + computed CSS style for a given element via a single
    page.evaluate() call.
    """
    try:
        handle = locator.element_handle(timeout=3000)
        if handle is None:
            print(f"   [debug] element_handle() returned None for {debug_label}")
            return None
        print(f"   [debug] {debug_label} matched element, checking size...")
        data = page.evaluate(
            """(el) => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return {
                    width: rect.width,
                    height: rect.height,
                    fontSize: parseFloat(style.fontSize),
                    backgroundColor: style.backgroundColor,
                    color: style.color
                };
            }""",
            handle,
        )
        print(f"   [debug] {debug_label} raw data: {data}")
        bg_rgb = _parse_rgb(data["backgroundColor"])
        text_rgb = _parse_rgb(data["color"])
        contrast = _contrast_ratio(bg_rgb, text_rgb) if (bg_rgb and text_rgb) else None

        return VisualStyle(
            width=data["width"],
            height=data["height"],
            area=data["width"] * data["height"],
            font_size=data["fontSize"],
            background_color=data["backgroundColor"],
            text_color=data["color"],
            contrast_ratio=contrast,
        )
    except Exception as e:
        print(f"   [debug] get_computed_style() for {debug_label} raised: {e}")
        return None


def find_button_by_text(page: Page, patterns: list[str], debug_label: str = "") -> Locator | None:
    for pattern in patterns:
        try:
            locator = page.get_by_role("button", name=pattern).first
            if locator.is_visible(timeout=1000):
                return locator
        except Exception as e:
            print(f"   [debug] get_by_role('button') '{pattern}' for {debug_label} raised: {e}")
            continue
    for pattern in patterns:
        try:
            text_locator = page.get_by_text(pattern, exact=False).first
            if not text_locator.is_visible(timeout=1000):
                continue
            button_ancestor = text_locator.locator(
                "xpath=ancestor-or-self::button | ancestor-or-self::a | ancestor-or-self::*[@role='button']"
            ).first
            if button_ancestor.is_visible(timeout=1000):
                return button_ancestor
        except Exception as e:
            print(f"   [debug] fallback ancestor search '{pattern}' for {debug_label} raised: {e}")
            continue

    print(f"   [debug] no pattern matched for {debug_label}")
    return None

# Main scan logic
SIZE_RATIO_FLAG_THRESHOLD = 1.5   # Accept flagged if its area is >=1.5x Reject's
CONTRAST_DIFF_FLAG_THRESHOLD = 2.0  # Accept flagged if its own contrast ratio is notably higher (more visually "loud")


def scan_site(site_url: str, headless: bool = True) -> VisualDeceptionResult:
    now = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            page.goto(site_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)

            accept_locator = find_button_by_text(page, ACCEPT_TEXT_PATTERNS, debug_label="ACCEPT")
            reject_locator = find_button_by_text(page, REJECT_TEXT_PATTERNS, debug_label="REJECT")

            accept_style = get_computed_style(page, accept_locator, debug_label="ACCEPT") if accept_locator else None
            reject_style = get_computed_style(page, reject_locator, debug_label="REJECT") if reject_locator else None

            browser.close()

            accept_area = accept_style.area if accept_style else 0.0
            reject_area = reject_style.area if reject_style else 0.0
            size_ratio = (accept_area / reject_area) if (accept_area and reject_area) else None

            accept_contrast = accept_style.contrast_ratio if accept_style else None
            reject_contrast = reject_style.contrast_ratio if reject_style else None

            size_flag = bool(size_ratio and size_ratio >= SIZE_RATIO_FLAG_THRESHOLD)
            contrast_flag = bool(
                accept_contrast and reject_contrast
                and (accept_contrast - reject_contrast) >= CONTRAST_DIFF_FLAG_THRESHOLD
            )

            return VisualDeceptionResult(
                site=site_url,
                accept_found=accept_style is not None,
                reject_found=reject_style is not None,
                accept_area=round(accept_area, 1),
                reject_area=round(reject_area, 1),
                size_ratio=round(size_ratio, 2) if size_ratio else None,
                accept_contrast=round(accept_contrast, 2) if accept_contrast else None,
                reject_contrast=round(reject_contrast, 2) if reject_contrast else None,
                size_flag=size_flag,
                contrast_flag=contrast_flag,
                error="",
                scanned_at=now,
            )

        except Exception as e:
            browser.close()
            return VisualDeceptionResult(
                site=site_url, accept_found=False, reject_found=False,
                accept_area=0.0, reject_area=0.0, size_ratio=None,
                accept_contrast=None, reject_contrast=None,
                size_flag=False, contrast_flag=False,
                error=str(e), scanned_at=now,
            )


def run_batch(site_urls: list[str], output_path: str = "visual_deception_dataset.csv", headless: bool = True):
    results = []
    for i, url in enumerate(site_urls, start=1):
        print(f"[{i}/{len(site_urls)}] Scanning {url} ...")
        result = scan_site(url, headless=headless)
        results.append(result)
        print(f"   -> accept_area={result.accept_area}, reject_area={result.reject_area}, "
              f"size_ratio={result.size_ratio}, size_flag={result.size_flag}, "
              f"contrast_flag={result.contrast_flag}")
        if result.error:
            print(f"   -> ERROR: {result.error}")
        time.sleep(1.0)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nDone. Wrote {len(results)} rows to {output_path}")
    return results


if __name__ == "__main__":
    test_sites = [
        "https://www.bbc.co.uk",
    ]
    run_batch(test_sites, headless=False)