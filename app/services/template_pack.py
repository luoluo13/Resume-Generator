from __future__ import annotations

import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from app.services.sample import sample_resume
from app.services.template_guard import (
    MAX_MANIFEST_BYTES,
    MAX_MARKUP_BYTES,
    REQUIRED_FILES,
    ID_RE,
    TemplateGuardError,
    check_markup,
    check_text_size,
    validate_manifest,
)

MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_UNPACKED_BYTES = 1024 * 1024


class TemplateConflictError(TemplateGuardError):
    pass


SPEC = """# 简历工坊 · 自定义模板开发规范

## 一、目标

为「简历工坊」(Resume Studio) 设计一套中文简历模板。产物是一个 zip 模板包，导入后可在「模板中心」预览、切换，并用于 PDF / PNG / DOCX 导出。

## 二、模板包结构

zip 根目录（或单个顶层文件夹内）必须且只能包含 4 个文件：

```
<模板id>/
  manifest.json    # 元信息与能力声明
  template.html    # Jinja2 模板，完整 HTML 文档
  style.css        # 模板样式
```

不要包含图片、字体、脚本、README 或其他文件。模板必须完全自包含。

## 三、manifest.json

```json
{
  "id": "letter",
  "name": "信 · 书信体",
  "description": "左侧竖线抬头与宽松行距，适合内容克制的通用岗位。",
  "tags": ["单栏", "书信"],
  "color": "#7a5c3e",
  "order": 50,
  "serifHeading": true,
  "version": "1.0.0",
  "author": "你的名字",
  "supports": { "columns": [1], "photo": true, "divider": ["line", "none"] },
  "variants": [
    {
      "key": "header",
      "label": "抬头样式",
      "description": "控制姓名的呈现方式",
      "options": [
        { "value": "plain", "label": "素色" },
        { "value": "rule", "label": "下划线" }
      ],
      "default": "plain"
    }
  ]
}
```

字段规则：

- `id`：3~32 位小写字母、数字或连字符，以字母开头，不能与内置模板重名。
- `name`：不超过 30 个字。
- `description`：不超过 200 个字，说明适合的岗位与视觉特点。
- `tags`：最多 6 个，每个不超过 12 个字。
- `color`：`#RRGGBB`，该模板的默认强调色。
- `order`：排序，越小越靠前，建议 50 以上。
- `serifHeading`：标题是否使用衬线字体。
- `supports.columns`：支持 1 或 2，至少一项。
- `supports.photo`：是否支持照片。
- `supports.divider`：`line` / `block` / `none` 的子集。
- `variants`：可选，最多 6 组；每组 2~4 个选项；`key` 小驼峰，`value` 小写字母、数字、连字符。

## 四、可用模板变量

`template.html` 直接使用以下变量：

- `resume`：简历数据对象
  - `resume.basics`：姓名 `name`、求职意向 `jobIntention`、电话 `phone`、邮箱 `email`、城市 `city`、到岗时间 `available`、经验 `yearsOfExperience`、性别 `gender`、出生 `birth`、政治面貌 `political`、照片路径 `photo`
  - `resume.sections`：数组，每项含 `id`、`type`、`title`、`visible`、`items`
  - `section.type` 取值：`education` / `experience` / `project` / `skills` / `awards` / `certificate` / `custom`
  - `section.items[]` 常用字段：`school`、`degree`、`major`、`gpa`、`courses`、`company`、`role`、`location`、`name`、`title`、`subtitle`、`start`、`end`、`current`、`tech`（字符串数组）、`link`、`group`、`tags`（字符串数组）、`issuer`、`date`、`highlights`
  - `item.highlights`：富文本 HTML 数组，只含 `p` / `strong` / `em` / `a` / `br`，输出时必须加 `|safe`
- `theme`：`accent`、`fontFamily`、`fontSize`、`lineHeight`、`pageMargin`、`columns`、`photoPosition`、`dividerStyle`、`density`
- `variants`：已按 manifest 合并默认值后的变体字典，例如 `variants.header`
- `photo_url`：照片地址，无照片时为空字符串
- `css`：系统基础样式 + 你的 style.css，必须原样输出
- `manifest`：当前模板的 manifest 对象
- `preview`：预览模式为 true，导出为 false

## 五、HTML 硬性要求

1. 必须是完整 HTML 文档，包含 `<meta charset="utf-8">`。
2. `<head>` 中必须输出 `<style>{{ css|safe }}</style>`。
3. `<body>` 内只能有一个根容器，且必须是 `<div class="page">`，否则无法统计页数。
4. 只能遍历 `resume.sections if section.visible` 的模块。
5. 富文本必须使用 `{{ item.highlights }}` 加 `|safe`，其余文本直接输出（自动转义）。
6. 必须使用 `{{ url_for }}` 之外的方式处理照片：`{% if theme.photoPosition != 'none' and resume.basics.photo %}<img src="{{ photo_url }}" alt="">{% endif %}`。
7. 不使用 JavaScript、iframe、表单、外链字体、外链图片、`@import`。
8. 模板必须单文件自包含，不使用 `extends` / `include` / `import`。

## 六、可用 CSS 变量

基础样式已定义在 `:root`：

- `--accent` / `--accent-soft`：强调色
- `--ink` / `--ink-2` / `--muted` / `--line`：文字与线条
- `--fs` / `--lh`：字号与行距
- `--gap`：内容密度系数
- `--columns`：栏数
- `--margin`：页边距
- `--font-body` / `--font-head`：正文字体与标题字体

A4 版面：210mm × 297mm，`.page` 已设置宽度与最小高度。打印样式已处理，不要覆盖 `@page`。分页时给模块或条目加 `break-inside: avoid`。

## 七、变体使用方式

在 manifest 声明 `variants` 后，主题面板会自动生成选项。模板中通过 `variants.<key>` 读取，例如：

```html
<header class="head" data-header="{{ variants.header }}">
```

```css
.head[data-header="rule"] { border-bottom: 2px solid var(--accent); }
```

必须为每个变体提供默认值，且所有选项都有可区分的视觉差异。

## 八、导出差异

- PDF / PNG：使用你的 HTML + CSS，与预览完全一致。
- DOCX：系统统一使用通用排版回退，不执行模板中的任何 Python 代码，因此 DOCX 只能近似还原内容结构，颜色与字体跟随主题设置。

## 九、验收清单

- 姓名、求职意向、联系方式完整显示。
- 7 种模块类型都能正常渲染，空模块不报错。
- `highlights` 中的加粗、斜体、链接正常显示。
- 内容较少时不出现大面积异常空白，内容较多时可自然分页。
- 所有变体切换后布局不塌陷。
- 没有横向滚动、没有元素溢出 A4 纸张。
- 不使用任何外部资源与脚本。

## 十、输出要求

先给出 manifest.json、template.html、style.css 三个文件的完整内容，再把它们打包成一个 zip 文件，zip 内保持上述目录结构。不要省略代码，不要输出与模板无关的说明。
"""

PROMPT_INTRO = """你是资深中文简历模板设计师，熟悉 A4 排版、CSS 打印样式与 Jinja2 模板语法。
请严格按下面的规范，为「简历工坊」设计一套全新的、视觉语言独立的简历模板。

要求：
1. 先确定一个明确的视觉概念（例如书信、档案、报刊、工程蓝图等），不要模仿内置模板。
2. 完整输出 manifest.json、template.html、style.css。
3. 模板必须自包含、无脚本、无外部资源、无 Python。
4. 最后把 4 个文件按规范目录结构打包为 zip。

"""


def import_package(raw: bytes, *, builtin_ids: set[str], user_root: Path) -> dict:
    if len(raw) > MAX_PACKAGE_BYTES:
        raise TemplateGuardError("模板包超过 2MB，请精简后再试")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise TemplateGuardError("文件不是有效的 zip 模板包") from exc

    infos = [info for info in archive.infolist() if not info.is_dir()]
    if not infos:
        raise TemplateGuardError("模板包为空")

    entries: dict[str, zipfile.ZipInfo] = {}
    parts_list: list[tuple[tuple[str, ...], zipfile.ZipInfo]] = []
    for info in infos:
        parts = _safe_parts(info.filename)
        if parts[0] in ("__MACOSX",) or parts[-1] == ".DS_Store":
            continue
        parts_list.append((parts, info))
    if not parts_list:
        raise TemplateGuardError("模板包为空")
    if len(parts_list) > 6:
        raise TemplateGuardError("模板包根目录只能包含 manifest.json、template.html、style.css")
    if sum(info.file_size for _, info in parts_list) > MAX_UNPACKED_BYTES:
        raise TemplateGuardError("模板包解压后超过 1MB")

    roots = {parts[0] for parts, _ in parts_list}
    if len(roots) == 1 and all(len(parts) >= 2 for parts, _ in parts_list):
        if any(len(parts) != 2 for parts, _ in parts_list):
            raise TemplateGuardError("压缩包层级过深，请把文件放在同一个顶层文件夹内")
        entries = {parts[1]: info for parts, info in parts_list}
    else:
        if any(len(parts) != 1 for parts, _ in parts_list):
            raise TemplateGuardError("请把 manifest.json、template.html、style.css 放在压缩包根目录")
        entries = {parts[0]: info for parts, info in parts_list}

    if len(entries) != len(parts_list):
        raise TemplateGuardError("模板包包含重名文件")

    for filename in entries:
        if filename == "docx_builder.py":
            raise TemplateGuardError("自定义模板不支持 docx_builder.py，DOCX 将使用通用回退")
        if filename not in REQUIRED_FILES:
            raise TemplateGuardError(f"模板包含不支持的文件：{filename}")
    missing = [filename for filename in REQUIRED_FILES if filename not in entries]
    if missing:
        raise TemplateGuardError(f"模板缺少文件：{'、'.join(missing)}")

    manifest_info = entries["manifest.json"]
    if manifest_info.file_size > MAX_MANIFEST_BYTES:
        raise TemplateGuardError("manifest.json 超过 24KB")
    try:
        manifest_raw = archive.read(manifest_info).decode("utf-8-sig")
        manifest = validate_manifest(json.loads(manifest_raw))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TemplateGuardError("manifest.json 不是有效的 UTF-8 JSON") from exc

    template_id = manifest["id"]
    if template_id in builtin_ids:
        raise TemplateConflictError(f"模板 id「{template_id}」与内置模板冲突，请更换 id")
    target = user_root / template_id
    if target.exists():
        raise TemplateConflictError(f"已存在同 id 的自定义模板「{template_id}」，请先删除或更换 id")

    contents: dict[str, str] = {}
    for filename in ("template.html", "style.css"):
        info = entries[filename]
        if info.file_size > MAX_MARKUP_BYTES:
            raise TemplateGuardError(f"{filename} 超过 160KB")
        try:
            content = archive.read(info).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise TemplateGuardError(f"{filename} 必须使用 UTF-8 编码") from exc
        check_text_size(content, filename)
        check_markup(content, filename)
        contents[filename] = content

    _trial_render(manifest, contents["template.html"])

    staging = user_root / f".import-{uuid.uuid4().hex}"
    try:
        staging.mkdir(parents=True)
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (staging / "template.html").write_text(contents["template.html"], encoding="utf-8")
        (staging / "style.css").write_text(contents["style.css"], encoding="utf-8")
        staging.rename(target)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise TemplateGuardError(f"保存模板失败：{exc}") from exc

    return {**manifest, "source": "user"}


def delete_user_template(user_root: Path, template_id: str, builtin_ids: set[str]) -> None:
    if template_id in builtin_ids:
        raise TemplateConflictError("内置模板不能删除")
    if not ID_RE.fullmatch(template_id):
        raise TemplateGuardError("模板 id 不合法")
    target = user_root / template_id
    if not (target / "manifest.json").is_file():
        raise TemplateGuardError("自定义模板不存在")
    shutil.rmtree(target)


def build_pack(builtin_root: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("模板开发规范.md", SPEC)
        archive.writestr(
            "resume.sample.json",
            json.dumps(sample_resume(), ensure_ascii=False, indent=2),
        )
        for template_id in ("classic", "grid"):
            for filename in REQUIRED_FILES:
                archive.write(
                    builtin_root / template_id / filename,
                    f"examples/{template_id}/{filename}",
                )
    return buffer.getvalue()


def build_prompt() -> str:
    return PROMPT_INTRO + SPEC


def _safe_parts(name: str) -> tuple[str, ...]:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise TemplateGuardError(f"模板包包含非法路径：{name}")
    return path.parts


def _trial_render(manifest: dict, template_html: str) -> None:
    theme = {
        "template": manifest["id"],
        "accent": manifest["color"],
        "fontFamily": "SourceHanSansSC",
        "fontSize": 10.5,
        "lineHeight": 1.35,
        "pageMargin": 18,
        "columns": 1,
        "photoPosition": "right",
        "dividerStyle": "line",
        "density": "normal",
        "variants": {},
    }
    variants = {group["key"]: group["default"] for group in manifest["variants"]}
    env = SandboxedEnvironment(autoescape=True)
    for label, resume in _trial_datasets():
        try:
            env.from_string(template_html).render(
                resume=resume,
                theme=theme,
                variants=variants,
                css="",
                photo_url="",
                preview=True,
                manifest=manifest,
            )
        except TemplateError as exc:
            raise TemplateGuardError(f"模板试渲染失败（{label}）：{exc}") from exc


def _trial_datasets() -> list[tuple[str, dict]]:
    empty = {
        "basics": {},
        "sections": [],
        "theme": {},
    }
    sample = sample_resume()
    stress = sample_resume()
    experience = next(section for section in stress["sections"] if section["type"] == "experience")
    experience["items"] = [
        {
            "company": "某超长名称的科技股份有限公司" * 2,
            "role": "高级后端开发工程师",
            "location": "上海",
            "start": "2021.07",
            "current": True,
            "highlights": [
                "<p>负责一个非常长的项目描述，用来验证模板在极端文本长度下是否会出现横向溢出或布局塌陷。</p>"
            ],
        }
    ] * 6
    stress["basics"]["name"] = "欧阳某某某某某某某某"
    stress["basics"]["email"] = "very-long-email-address-for-layout-test@example.com"
    return [("示例数据", sample), ("空数据", empty), ("超长数据", stress)]
