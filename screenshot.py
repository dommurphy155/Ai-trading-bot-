# screenshots.py

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime

async def capture_screenshot(url: str, output_dir: str = "screenshots") -> str:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.screenshot(path=filepath, full_page=True)
        await browser.close()

    return filepath

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python screenshots.py <url>")
        exit(1)

    url = sys.argv[1]
    path = asyncio.run(capture_screenshot(url))
    print(f"Screenshot saved to {path}")
