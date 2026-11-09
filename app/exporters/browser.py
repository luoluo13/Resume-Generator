from __future__ import annotations

from contextlib import asynccontextmanager

from playwright.async_api import Page, async_playwright


@asynccontextmanager
async def browser_page(*, width: int, height: int, scale: float = 1):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--font-render-hinting=none", "--disable-lcd-text"],
        )
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await browser.close()


async def wait_for_document(page: Page) -> None:
    await page.wait_for_load_state("networkidle")
    await page.evaluate("document.fonts && document.fonts.ready ? document.fonts.ready.then(() => true) : true")
    await page.evaluate(
        """() => Promise.all(
            Array.from(document.images)
                .filter(img => !img.complete)
                .map(img => new Promise(resolve => { img.onload = img.onerror = resolve; }))
        )"""
    )
    await page.wait_for_timeout(120)
