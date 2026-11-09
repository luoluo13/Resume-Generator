from __future__ import annotations

from pathlib import Path

from app.exporters.browser import browser_page, wait_for_document


async def export_pdf(url: str, output: Path, margin_mm: int) -> Path:
    async with browser_page(width=794, height=1123) as page:
        await page.goto(url, wait_until="networkidle")
        await wait_for_document(page)
        await page.emulate_media(media="print")
        await page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
            margin={
                "top": f"{margin_mm}mm",
                "bottom": f"{margin_mm}mm",
                "left": f"{margin_mm}mm",
                "right": f"{margin_mm}mm",
            },
        )
    return output
