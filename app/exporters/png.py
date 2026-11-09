from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image

from app.exporters.browser import browser_page, wait_for_document

A4_WIDTH = 794
A4_HEIGHT = 1123
SCALE = 3


def _split(image: Image.Image, base: Path) -> list[Path]:
    page_height = A4_HEIGHT * SCALE
    pages = max(1, math.ceil(image.height / page_height))
    outputs: list[Path] = []
    for index in range(pages):
        top = index * page_height
        bottom = min(image.height, top + page_height)
        tile = image.crop((0, top, image.width, bottom))
        if pages == 1:
            target = base
        else:
            target = base.with_name(f"{base.stem}-{index + 1}{base.suffix}")
        tile.save(target, format="PNG", optimize=True)
        outputs.append(target)
    return outputs


async def export_png(url: str, output: Path) -> list[Path]:
    async with browser_page(width=A4_WIDTH, height=A4_HEIGHT, scale=SCALE) as page:
        await page.goto(url, wait_until="networkidle")
        await wait_for_document(page)
        await page.add_style_tag(content=".page::after{display:none !important}.page{box-shadow:none !important}")
        element = await page.query_selector(".page")
        if element is None:
            raise RuntimeError("预览中未找到简历页面")
        raw = await element.screenshot(type="png")
    image = Image.open(io.BytesIO(raw))
    return _split(image, output)
