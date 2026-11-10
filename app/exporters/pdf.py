from __future__ import annotations

from pathlib import Path

from app.exporters.browser import browser_page, wait_for_document


async def export_pdf(url: str, output: Path) -> Path:
    async with browser_page(width=794, height=1123) as page:
        response = await page.goto(url, wait_until="networkidle")
        if response is None or response.status >= 400:
            raise RuntimeError(f"预览页加载失败（HTTP {response.status if response else '无响应'}）")
        await wait_for_document(page)
        await page.emulate_media(media="print")
        # 页边距由模板 CSS 的 @page 控制，确保多页内容每页都保留一致留白
        await page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
        )
    return output
