from __future__ import annotations

import json
from pathlib import Path
from string import Template

from jinja2 import ChoiceLoader, FileSystemLoader, TemplateError, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

from app.models import Resume
from app.services.fonts import css_stack
from app.services.template_guard import TemplateGuardError, ensure_safe

BASE_CSS = Template(
    """
*{box-sizing:border-box}
:root{
  --accent:$accent;
  --accent-soft:color-mix(in srgb, $accent 12%, #fff);
  --ink:#23211c;
  --ink-2:#4d4940;
  --muted:#7f786c;
  --line:#e0dace;
  --fs:$fs;
  --lh:$lh;
  --gap:$gap;
  --columns:$columns;
  --margin:$margin_mm mm;
  --font-body:$font_body;
  --font-head:$font_head;
}
html{background:#fff}
body{margin:0;padding:0;background:#fff;color:var(--ink);
  font-family:var(--font-body);font-size:var(--fs);line-height:var(--lh);
  -webkit-font-smoothing:antialiased;-webkit-print-color-adjust:exact;print-color-adjust:exact}
img{max-width:100%;display:block}
a{color:var(--accent);text-decoration:none}
ul,ol{margin:0;padding:0;list-style:none}
p{margin:0}
.page{
  position:relative;width:210mm;min-height:297mm;margin:0 auto;padding:$margin_mm mm;
  background:#fff;overflow:visible;
}
.page::after{
  content:"";position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(to bottom,
    transparent 0 calc(297mm - 1px),
    rgba(190,74,46,.55) calc(297mm - 1px) 297mm);
}
.sec,.entry,.entry-list li{break-inside:avoid}
@media print{
  html,body{background:#fff}
  .page{width:auto;min-height:0;padding:0;margin:0}
  .page::after{display:none}
  .page-break{break-after:page}
}
@page{size:A4;margin:0}
"""
)

METRICS_SCRIPT = """
<script>
(function(){
  function send(){
    var page = document.querySelector('.page');
    if(!page) return;
    var PAGE_H = 1123;
    var height = page.scrollHeight;
    parent.postMessage({type:'resume-metrics', pages: Math.max(1, Math.ceil(height / PAGE_H - 0.002)),
      ratio: +(height / PAGE_H).toFixed(3), height: height}, '*');
  }
  function afterImages(){
    var imgs = Array.prototype.slice.call(document.images).filter(function(img){ return !img.complete; });
    return Promise.all(imgs.map(function(img){
      return new Promise(function(resolve){ img.onload = img.onerror = resolve; });
    }));
  }
  var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
  ready.then(afterImages).then(function(){ requestAnimationFrame(send); });
  window.addEventListener('load', send);
})();
</script>
"""


class TemplateError(Exception):
    pass


class TemplateRegistry:
    def __init__(self, roots: list[Path]) -> None:
        self.roots = roots
        self.env = SandboxedEnvironment(
            loader=ChoiceLoader([FileSystemLoader(str(root)) for root in roots]),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def list(self) -> list[dict]:
        manifests: list[dict] = []
        seen: set[str] = set()
        for root in self.roots:
            source = "builtin" if root == self.roots[0] else "user"
            for manifest_file in sorted(root.glob("*/manifest.json")):
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not data.get("id") or not data.get("name") or data["id"] in seen:
                    continue
                seen.add(data["id"])
                manifests.append({**data, "source": source})
        manifests.sort(key=lambda item: (item.get("order", 99), item["name"]))
        return manifests

    def get(self, template_id: str) -> dict:
        for manifest in self.list():
            if manifest["id"] == template_id:
                return manifest
        raise TemplateError(f"模板不存在：{template_id}")

    def directory(self, template_id: str) -> tuple[Path, str]:
        for index, root in enumerate(self.roots):
            folder = root / template_id
            if (folder / "manifest.json").is_file():
                return folder, ("builtin" if index == 0 else "user")
        raise TemplateError(f"模板不存在：{template_id}")

    def default_id(self) -> str:
        manifests = self.list()
        if not manifests:
            raise TemplateError("未找到任何模板")
        return manifests[0]["id"]

    def render(self, resume: dict, template_id: str | None, *, for_preview: bool) -> str:
        model = Resume.model_validate(resume)
        theme = model.theme.model_dump()
        resolved_id = template_id or theme["template"]
        manifest = self.get(resolved_id)
        theme["template"] = resolved_id
        folder, source = self.directory(resolved_id)

        template_file = folder / "template.html"
        style_file = folder / "style.css"
        if not template_file.exists() or not style_file.exists():
            raise TemplateError(f"模板文件不完整：{resolved_id}")
        if source == "user":
            try:
                ensure_safe(folder)
            except TemplateGuardError as exc:
                raise TemplateError(f"自定义模板校验失败：{exc}") from exc

        variants = resolve_variants(manifest, theme.get("variants", {}))
        gap = {"compact": 0.62, "normal": 1.0, "loose": 1.32}[theme["density"]]
        font_body = css_stack(theme["fontFamily"])
        font_head = '"Source Han Serif SC","Noto Serif SC","Songti SC",SimSun,serif' \
            if manifest.get("serifHeading") else font_body
        base_css = BASE_CSS.substitute(
            accent=theme["accent"],
            fs=f'{theme["fontSize"] * 4 / 3:.2f}px',
            lh=theme["lineHeight"],
            gap=gap,
            columns=theme["columns"],
            margin_mm=theme["pageMargin"],
            font_body=font_body,
            font_head=font_head,
        )
        css = base_css + "\n" + style_file.read_text(encoding="utf-8")
        photo = model.basics.photo
        html = self.env.get_template(f"{resolved_id}/template.html").render(
            resume=model.model_dump(mode="json"),
            theme=theme,
            css=css,
            photo_url=f"/media/{photo}" if photo else "",
            preview=for_preview,
            manifest=manifest,
            variants=variants,
        )
        if for_preview:
            html = html.replace("</body>", METRICS_SCRIPT + "</body>")
        return html


def resolve_variants(manifest: dict, selected: dict) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for group in manifest.get("variants", []):
        values = {option["value"] for option in group.get("options", [])}
        fallback = group.get("default") or next(iter(values), "")
        chosen = selected.get(group["key"]) if isinstance(selected, dict) else None
        resolved[group["key"]] = chosen if chosen in values else fallback
    return resolved
