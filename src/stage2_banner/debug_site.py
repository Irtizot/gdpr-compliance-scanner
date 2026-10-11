"""
Diagnostic: shows what a page contains, to explain why no banner was found.
"""
import sys

from playwright.sync_api import sync_playwright

from pipeline import USER_AGENT

url = sys.argv[1]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(6000)

    print("page title:", page.title())
    print("frames on the page:")
    for frame in page.frames:
        print("   ", frame.url[:110])
    print("elements with 'cookie' in id or class:",
          page.locator("[id*='cookie' i], [class*='cookie' i]").count())
    print("elements containing the text 'cookie':",
          page.get_by_text("cookie", exact=False).count())

    input("Look at the browser window, then press Enter here to close it...")
    browser.close()