# 简历工坊（Resume Studio）产品需求文档

| 项目 | 内容 |
|---|---|
| 文档版本 | v1.0 |
| 日期 | 2026-11-09 |
| 产品形态 | Windows 本地 Web 应用，双击 `run.bat` 启动 |
| 技术栈 | Python 3.12 + FastAPI + React 18 + TypeScript + Vite |
| 目标读者 | 负责实现的开发 AI / 开发者 |
| 视觉基准 | 同目录 `prototype.html`（UI 样式与交互的唯一视觉参照） |

---

## 0. 给开发 AI 的执行说明

1. 本文档同时包含**产品行为**与**技术实现约束**，两者都是硬性要求。
2. 技术栈不得替换：后端 FastAPI，前端 React + TS + Vite，导出使用 Playwright + python-docx。
3. `prototype.html` 是视觉基准：布局比例、间距、字号层级、配色、交互反馈需对齐；允许在实现时做工程化调整，但不得改变整体设计语言。
4. P0 范围必须完整交付，不要自行增加 P1 功能。
5. 所有路径必须能处理空格与中文；禁止把运行期依赖写入 C 盘用户目录。
6. 每完成一个里程碑，按第 10 节验收标准自测后再继续。

---

## 1. 产品概述

### 1.1 一句话定义

面向非开发用户的本地简历工作台：左侧结构化编辑，右侧 A4 实时预览，一键导出 PDF / PNG / DOCX，全部数据与运行环境保存在本地。

### 1.2 要解决的问题

- 在线简历工具要求注册、联网、上传隐私信息，且导出常带水印或付费墙。
- Word 排版简历门槛高，改一处格式全篇错位。
- 现有开源工具多面向开发者，需要命令行和环境配置。

### 1.3 产品决策

- **本地优先**：服务只监听 `127.0.0.1`，不上传任何数据。
- **零环境门槛**：用户只需双击 `run.bat`，其余依赖自动补齐。
- **结构化而非画布**：简历是线性文档，用数据驱动模板，保证三种导出格式一致。
- **单页优先**：中文求职场景以单页为佳，产品主动提示超页。

### 1.4 目标用户

| 用户 | 特征 | 核心诉求 |
|---|---|---|
| 主要用户：中文求职者 | 校招/社招，非技术背景 | 不会排版也能做出专业单页简历 |
| 次要用户：需要多版本投递者 | 同时投多个岗位 | 快速改内容、换模板、换强调色后导出 |

### 1.5 核心用户旅程

```
双击 run.bat
  → 环境自检与补齐（首次较慢，有进度提示）
  → 浏览器自动打开应用
  → 编辑基本信息与各模块内容
  → 右侧实时预览，超页时出现提示
  → 选择模板与主题
  → 导出 PDF / PNG / DOCX
  → 文件落在项目 exports 目录，可一键打开所在文件夹
```

完成标志：用户在未安装 Python 的 Windows 电脑上，双击 `run.bat` 后 10 分钟内拿到一份可投递的 PDF。

---

## 2. 范围

### 2.1 P0（必须交付）

| 编号 | 能力 |
|---|---|
| FR-01 | `run.bat` 启动、依赖自举、环境路径隔离 |
| FR-02 | 单份简历的创建、示例数据、自动保存 |
| FR-03 | 结构化内容编辑（基本信息、教育、工作、项目、技能、奖项、自定义） |
| FR-04 | 要点（bullet）富文本编辑：加粗、斜体、链接 |
| FR-05 | 模块管理：排序、显隐、重命名、增删 |
| FR-06 | A4 实时预览、缩放、页数显示 |
| FR-07 | 1 套内置模板 + 模板选择界面 |
| FR-08 | 主题参数：主色、字体、字号、行距、页边距、栏数、照片位置、分隔样式 |
| FR-09 | 一页检测与超页提示 |
| FR-10 | PDF / PNG / DOCX 三格式导出，输出到 `exports/` |
| FR-11 | 数据备份：导出/导入 JSON |
| FR-12 | 系统状态与错误提示（字体、Chromium、端口、导出失败） |

### 2.2 P1（本期不做，但需预留）

- 多份简历管理与按岗位切换
- 2~4 套额外模板
- 自定义 CSS 模板
- JD 关键词匹配与要点改写建议
- 旧简历 PDF/DOCX 解析导入
- 离线依赖包（`vendor/wheels`）与自动更新
- 打印直连、系统托盘常驻

### 2.3 非目标

- 不做在线账号、云同步、多人协作。
- 不做自由拖拽画布式设计器。
- 不做移动端适配（仅保证 1280px 及以上桌面浏览器）。

---

## 3. 信息架构与页面

### 3.1 页面清单

| 页面 | 入口 | 说明 |
|---|---|---|
| 启动加载页 | 服务启动后自动展示 | 显示环境检查结果，失败时给出可操作提示 |
| 编辑器（默认） | 启动后 | 三栏：模块导航 / 表单编辑 / A4 预览 |
| 模板中心 | 顶栏“模板” | 模板卡片网格，当前模板有“使用中”标记 |
| 主题设置 | 顶栏“主题” | 右侧抽屉或独立视图，改动实时反映到预览 |
| 导出面板 | 顶栏“导出” | 三格式卡片、文件名、导出选项、最近导出记录 |
| 关于/环境 | 底部状态栏 | 版本、端口、数据目录、日志目录、字体与 Chromium 状态 |

### 3.2 编辑器布局规格

| 区域 | 宽度 | 行为 |
|---|---|---|
| 顶栏 | 高 60px，固定 | 品牌、页面切换、保存状态、导出主按钮 |
| 左栏模块导航 | 260px，独立滚动 | 模块列表、拖拽手柄、显隐开关、添加模块 |
| 中栏表单 | 弹性，最小 520px，独立滚动 | 当前模块的条目卡片与字段 |
| 右栏预览 | 弹性，最小 560px | 深色工作台背景、A4 纸张居中、缩放控件 |
| 底部状态栏 | 高 32px | 本地服务状态、数据目录、页数、字体状态 |

A4 纸张基准：210×297mm，96dpi 下 `794×1123px`；预览默认缩放 0.78，可 50%~120% 调整。

### 3.3 视觉方向

- 气质：纸张质感 + 编辑部工具感，克制、密度适中，不用通用 SaaS 蓝紫渐变。
- 底色 `#f6f4ef`，卡片 `#fffdfa`，墨色 `#1b1a17`，强调色朱砂 `#bf4a2e`。
- 标题与品牌用衬线字体（宋体族），正文与控件用无衬线（微软雅黑/思源黑体）。
- 细边框 `#e2ded4`，弱阴影，圆角 8~12px；不使用大面积高饱和色块。
- 所有图标使用内联 SVG，不依赖图标字体或 CDN。

---

## 4. 功能需求

### FR-01 启动与环境自举（`run.bat`）

**目的**：非开发用户双击即用，不手动安装任何东西。

**触发**：用户双击项目根目录 `run.bat`。

**处理流程**

1. 切换工作目录到脚本所在目录（`pushd "%~dp0"`），启用 UTF-8（`chcp 65001`）。
2. 创建运行目录 `.runtime\`，并重定向以下环境变量，确保不写入 C 盘用户目录：
   - `TEMP` / `TMP` → `.runtime\temp`
   - `PIP_CACHE_DIR` → `.runtime\pip-cache`
   - `PLAYWRIGHT_BROWSERS_PATH` → `.runtime\ms-playwright`
   - `PYTHONNOUSERSITE=1`、`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`
3. **Python 检测顺序**：
   1. 已存在 `.venv\Scripts\python.exe` 且版本 ≥ 3.10；
   2. `py -3.12` / `py -3.11` / `py -3.10`；
   3. PATH 中的 `python`；
   4. 均无 → 下载官方安装包，静默安装到 `.runtime\python`（不使用默认的 `%LOCALAPPDATA%\Programs`）。
4. 若 `.venv` 不存在，用选中的解释器创建 `.venv`（虚拟环境位于项目盘）。
5. 计算 `requirements.txt` 的 SHA-256，与 `.runtime\deps.sha256` 比对；不一致则执行 `pip install -r requirements.txt`。
   - 默认使用清华镜像源，失败自动回退官方源并重试一次。
6. 检查 `.runtime\playwright.ok`；缺失则执行 `python -m playwright install chromium`。
7. 检查 `frontend\dist\index.html` 是否存在；不存在则提示“发布包不完整”，不尝试现场构建（终端用户无 Node）。
8. 从 8765 开始探测可用端口，被占用则递增。
9. 启动 `uvicorn app.main:app --host 127.0.0.1 --port <PORT>`，轮询 `/api/health` 最多 30 秒。
10. 健康检查通过后自动打开默认浏览器；失败则输出日志路径并 `pause`。

**结果与状态**

- 成功：浏览器打开应用，控制台窗口标题为“简历工坊 - 请勿关闭此窗口”。
- 首次启动：显示 5 个阶段的进度文本，安装依赖与 Chromium 时提示“首次启动需要几分钟”。
- 失败：输出明确原因（网络、磁盘空间、被杀毒拦截、端口占用）与日志路径 `.runtime\logs\bootstrap.log`，窗口停留等待用户阅读。

**约束**

- 所有路径加引号，兼容空格与中文目录。
- `run.bat` 使用 UTF-8（无 BOM）+ CRLF 保存；首行之后立即 `chcp 65001`。
- 不修改系统 PATH，不写注册表自启动项；Python 安装器产生的卸载登记项不可避免，需在日志中说明。
- 重复运行必须幂等：已安装的依赖不重复安装，已存在的 Chromium 不重复下载。
- 端口、数据目录、日志目录写入 `.runtime\runtime.json` 供后端读取。

**参考实现**：见附录 A。

---

### FR-02 简历创建与自动保存

**目的**：用户打开即可开始，不面对空白配置。

**规则**

- P0 只有一份当前简历，数据存于 `data/resume.json`，媒体资源存于 `data/assets/`。
- 首次启动若无数据文件，加载内置示例数据（虚构人物，内容完整，便于用户对照修改）。
- 任意字段修改后 500ms 防抖保存；顶栏显示“保存中 / 已保存 / 保存失败”。
- 每次保存前写临时文件再原子替换，避免断电导致文件损坏。
- 应用启动时若 JSON 解析失败，使用最近一次 `.bak` 备份并提示用户。

**字段级规则**

| 字段 | 必填 | 规则 |
|---|---|---|
| 姓名 | 是 | 1~30 字符，超长在预览中自动缩小字号但不截断 |
| 求职意向 | 否 | ≤ 30 字符 |
| 电话 | 否 | 6~20 位，允许数字、`+`、`-`、空格、括号 |
| 邮箱 | 否 | 基础邮箱格式校验 |
| 现居城市 | 否 | ≤ 20 字符 |
| 照片 | 否 | jpg/png，≤ 5MB；导入后统一转为 JPEG，长边 ≤ 600px |
| 时间 | 否 | 格式 `YYYY.MM`；结束时间必须 ≥ 开始时间；支持“至今” |
| 要点 | 否 | 每条 ≤ 200 字，建议 2~4 条；超过 6 条在 UI 中提示精简 |

**异常**

- 保存失败：顶栏变红，点击可重试，并显示错误原因。
- 图片格式不支持：拒绝导入并提示支持的格式与大小上限。

---

### FR-03 结构化内容编辑

**目的**：用户不需要理解排版，只填写内容。

**布局**：左栏选择模块 → 中栏渲染该模块的条目卡片 → 右栏实时变化。

**模块类型**

| 类型 | 字段 |
|---|---|
| 基本信息 | 姓名、求职意向、电话、邮箱、城市、到岗时间、照片、可选隐私字段显隐 |
| 教育背景 | 学校、学历、专业、起止时间、GPA/排名（可选）、主修课程（逗号分隔） |
| 工作/实习经历 | 公司、部门/职位、地点、起止时间、要点列表 |
| 项目经历 | 项目名、角色、起止时间、技术栈（标签）、要点列表、链接（可选） |
| 专业技能 | 分组名 + 标签列表 |
| 荣誉奖项 | 名称、颁发方、时间 |
| 自定义模块 | 标题 + 条目（标题、副标题、时间、要点） |

**交互规则**

- 条目卡片支持折叠/展开；新增条目后自动展开并聚焦首个输入框。
- 卡片头部显示“公司 · 职位”摘要，折叠后仍可辨认。
- 删除条目需二次确认；删除后可撤销（3 秒内）。
- 字段输入即时写入本地状态，不点“保存”按钮。
- 中栏顶部显示模块名、条目数、简短填写建议。

**空状态**

- 某模块无条目时显示插画式空状态与“添加第一条”按钮。
- 预览中该模块整体隐藏，不显示空标题。

---

### FR-04 要点富文本

**目的**：支持少量强调，不引入 Word 级别的排版复杂度。

**允许的格式**：加粗、斜体、超链接。**禁止**：字号、颜色、表格、图片、标题层级。

**交互**

- 点击要点进入编辑态，浮出 4 个按钮：加粗、斜体、链接、删除。
- 快捷键支持 `Ctrl+B`、`Ctrl+I`。
- 链接插入需要填写显示文字与 URL；URL 必须以 `http://` 或 `https://` 开头。
- 粘贴时剥离外部样式，只保留纯文本与换行。

**存储**：存 HTML 片段（`<strong>`、`<em>`、`<a>`）；导出 DOCX 时映射为 run 级格式，遇到不支持的标签降级为纯文本。

---

### FR-05 模块管理

- 左栏模块支持拖拽排序，顺序即预览顺序。
- 每个模块有显隐开关；关闭后预览不渲染，但数据保留。
- 模块标题可重命名（仅自定义模块允许修改默认标题时需二次确认）。
- “添加模块”提供 7 种预设与 1 个空白自定义模块。
- 最后一个可见模块不允许删除。

---

### FR-06 实时预览

- 使用同源 iframe 渲染，与导出共用同一模板与 CSS，禁止另写一套预览样式。
- 预览随表单输入在 100ms 内更新。
- 缩放：50% / 75% / 100% / 适应宽度；显示当前页与总页数。
- 超出 A4 一页时，纸张底部出现红色虚线裁切提示，并在底部状态栏显示“超出 1 页”。
- 预览区不显示编辑控件，保持所见即所得。

---

### FR-07 模板中心

- P0 内置 1 套模板“笺 · 单栏经典”，卡片显示名称、风格标签、缩略图。
- 模板卡片状态：使用中 / 可切换。
- 切换模板不修改内容数据，只修改 `theme.template`。
- 缩略图使用真实模板缩小渲染，不使用静态图片，保证与实际效果一致。
- 模板协议见 5.3，新增模板不得修改业务代码。

---

### FR-08 主题与排版

**可调项**

| 项 | 取值 | 默认 |
|---|---|---|
| 主色 | 6 个预设 + 自定义色值 | 朱砂 `#bf4a2e` |
| 正文字体 | 思源黑体 / 思源宋体 / 微软雅黑 | 思源黑体 |
| 正文字号 | 9~12pt，步进 0.5 | 10.5pt |
| 行距 | 1.0~1.6，步进 0.05 | 1.35 |
| 页边距 | 12~25mm，步进 1 | 18mm |
| 栏数 | 单栏 / 双栏 | 单栏 |
| 照片位置 | 无 / 右上 / 左上 | 右上 |
| 分隔样式 | 细线 / 色块 / 无 | 细线 |
| 密度 | 宽松 / 标准 / 紧凑 | 标准 |

**规则**

- 主题配置写入 `resume.theme`，与内容一起保存与导出。
- 所有尺寸由同一份 `theme` 驱动 HTML 与 DOCX 两条渲染管线，禁止在任一管线硬编码。
- 切换主题时预览 200ms 内完成更新，不闪烁。

---

### FR-09 一页检测

- 渲染完成后测量内容高度，与 A4 可用高度比较。
- 超出时：预览纸张底部显示裁切虚线，状态栏显示超页比例，导出面板顶部显示提醒。
- 提醒文案示例：“内容约 1.18 页，建议删减 2~3 条要点，或切换‘紧凑’密度。”
- 提供“一键紧凑”按钮：将密度切换为紧凑并适当缩小行距，用户可撤销。
- 不强制阻止导出多页。

---

### FR-10 三格式导出

**入口**：顶栏“导出”按钮 → 导出面板。

**通用规则**

- 默认输出目录 `exports/`（项目根目录下），文件名 `姓名_求职意向_YYYYMMDD-HHmm.<ext>`，非法字符替换为 `-`。
- 导出前重新渲染一次，确保与预览一致。
- 同一时刻只允许一个导出任务，按钮进入 loading 并显示阶段文案。
- 成功后展示文件路径、文件大小，以及“打开所在文件夹”按钮。
- 失败时展示原因与日志路径，允许重试。

**PDF**

- 使用 Playwright Chromium `page.pdf()`，A4、`printBackground: true`、边距为 0（由 CSS `@page` 控制）。
- 文字必须可选中、可搜索；禁止将整页转为图片。
- 条目使用 `break-inside: avoid`，避免跨页截断。

**PNG**

- 视口 `794×1123`，`deviceScaleFactor: 3`，输出约 `2382×3369`。
- 通过元素截图截取 `.page`，保证只有纸张内容、无阴影与背景。
- 多页时逐页导出为 `姓名_1.png`、`姓名_2.png`。

**DOCX**

- 使用 python-docx 直接构建，禁止 HTML→DOCX 转换库。
- 每套模板提供对应的 `docx_builder.py`，与 HTML 模板共享同一份 `theme` 与数据模型。
- 中文字体必须同时设置 `ascii`、`hAnsi`、`eastAsia` 三个字体槽位。
- 行距使用固定值（pt），段间距使用 `space_before/space_after`，禁止用空段落凑间距。
- 双栏用无边框表格实现；要点使用“•”字符 + 悬挂缩进；小标题设置 `keep_with_next`。
- 照片按厘米尺寸插入，尺寸与 HTML 端同源配置。

**格式一致性验收**

同一份 JSON 导出三种格式后，按顺序抽取纯文本，正文内容与顺序必须完全一致（允许空白差异）。

---

### FR-11 数据备份

- 编辑器“数据”菜单提供：导出 JSON、导入 JSON、打开数据目录。
- 导入前校验 `schemaVersion` 与必填字段；不兼容时提示并拒绝。
- 导入成功后先备份当前数据到 `data/backups/`，再替换。
- 备份文件保留最近 20 份，超出自动清理。

---

### FR-12 系统状态与错误提示

底部状态栏常驻展示：

- 本地服务：已连接 / 断开
- 数据目录（可点击打开）
- 页数：`1 / 1`
- 字体：已就绪 / 缺失（缺失时提示将回退为微软雅黑）
- 环境状态：正常 / 异常（点击进入环境页）

错误提示统一使用右下角 Toast，成功 2 秒、警告 4 秒、错误常驻并提供“详情”。

---

## 5. 技术方案

### 5.1 总体架构

```
浏览器（React SPA）
   │  HTTP /api
   ▼
FastAPI（127.0.0.1:8765）
   ├─ ResumeService      读写 data/resume.json，原子保存与备份
   ├─ TemplateRegistry   扫描 templates/*/manifest.json
   ├─ PreviewRenderer    Jinja2 渲染 HTML（预览与导出共用）
   ├─ Exporter
   │    ├─ Playwright → PDF / PNG
   │    └─ python-docx → DOCX
   └─ StaticFiles        托管 frontend/dist
```

- 单进程运行；Playwright 使用异步 API，导出加互斥锁，避免并发启动 Chromium。
- 后端不直接生成预览 HTML 给前端，前端通过 iframe 请求 `/api/preview` 获取同源 HTML，保证预览与导出同源。
- 所有接口只绑定 `127.0.0.1`，校验 `Origin`，拒绝外部来源请求。

### 5.2 技术栈与版本

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | FastAPI + Uvicorn + Pydantic v2 | 数据校验即 API 契约 |
| 模板 | Jinja2 | 预览与 PDF/PNG 共用 |
| PDF/PNG | Playwright（Chromium） | 矢量 PDF、高清 PNG |
| DOCX | python-docx | 原生构建 |
| 图片 | Pillow | 照片旋转、缩放、转码 |
| 前端 | React 18 + TypeScript + Vite | SPA |
| 样式 | 原生 CSS + CSS 变量 | 不引入重型 UI 框架，便于还原设计 |
| 状态 | Zustand | 轻量全局状态 |
| 表单 | react-hook-form + zod | 校验与错误提示 |
| 富文本 | TipTap | 仅启用 bold/italic/link |
| 拖拽 | dnd-kit | 模块与条目排序 |

依赖固定版本，写入 `requirements.txt` 与 `package-lock.json`。

### 5.3 目录结构

```
Resume-Generator/
├─ run.bat                    # 唯一用户入口
├─ requirements.txt
├─ PRD.md
├─ prototype.html             # UI 视觉基准
├─ app/
│  ├─ main.py                 # FastAPI 入口、静态托管、启动参数
│  ├─ config.py               # 路径、端口、runtime.json 读取
│  ├─ models.py               # Pydantic 数据模型
│  ├─ routers/
│  │  ├─ resume.py            # 读写、备份、导入导出
│  │  ├─ export.py            # 三格式导出
│  │  ├─ templates.py         # 模板列表与预览
│  │  └─ system.py            # 健康检查、字体、打开目录
│  ├─ services/
│  │  ├─ store.py             # 原子写入、备份轮转
│  │  ├─ preview.py           # Jinja2 渲染
│  │  └─ fonts.py             # 字体探测
│  └─ exporters/
│     ├─ pdf.py
│     ├─ png.py
│     └─ docx.py              # 调度 templates/*/docx_builder.py
├─ templates/
│  └─ classic/
│     ├─ manifest.json
│     ├─ template.html
│     ├─ style.css
│     └─ docx_builder.py
├─ frontend/
│  ├─ src/
│  │  ├─ App.tsx
│  │  ├─ views/ (Editor, Templates, Theme, Export)
│  │  ├─ components/
│  │  ├─ store/
│  │  └─ styles/
│  ├─ public/fonts/           # 自托管 woff2
│  └─ dist/                   # 预构建产物，随发布包提供
├─ data/
│  ├─ resume.json
│  ├─ assets/
│  └─ backups/
├─ exports/
└─ .runtime/                  # 运行环境，全部在项目盘
   ├─ python/  (按需)
   ├─ temp/
   ├─ pip-cache/
   ├─ ms-playwright/
   ├─ logs/
   └─ runtime.json
```

### 5.4 数据模型

```json
{
  "schemaVersion": 1,
  "id": "default",
  "meta": { "createdAt": "", "updatedAt": "" },
  "basics": {
    "name": "陈亦然",
    "jobIntention": "高级后端开发工程师",
    "phone": "138-0000-0000",
    "email": "chenyiran@example.com",
    "city": "上海",
    "available": "一个月内",
    "yearsOfExperience": "5 年",
    "photo": "assets/photo.jpg",
    "show": { "photo": true, "gender": false, "birth": false, "political": false }
  },
  "sections": [
    {
      "id": "sec_edu", "type": "education", "title": "教育背景", "visible": true,
      "items": [{
        "school": "华东师范大学", "degree": "本科", "major": "计算机科学与技术",
        "start": "2015.09", "end": "2019.06", "gpa": "3.8/4.0",
        "courses": "数据结构、操作系统、计算机网络"
      }]
    },
    {
      "id": "sec_exp", "type": "experience", "title": "工作经历", "visible": true,
      "items": [{
        "company": "字节跳动", "role": "后端开发工程师", "location": "上海",
        "start": "2021.07", "end": "", "current": true,
        "highlights": [
          "<p>主导简历解析服务重构，通过异步任务与缓存优化，P95 延迟从 <strong>820ms</strong> 降至 <strong>210ms</strong>。</p>"
        ]
      }]
    },
    {
      "id": "sec_proj", "type": "project", "title": "项目经历", "visible": true,
      "items": [{
        "name": "简历智能生成平台", "role": "技术负责人",
        "start": "2023.03", "end": "2023.10",
        "tech": ["Python", "FastAPI", "Playwright", "PostgreSQL"],
        "link": "",
        "highlights": ["<p>设计模板协议与导出管线，支持 PDF/PNG/DOCX 三格式一致输出。</p>"]
      }]
    },
    {
      "id": "sec_skill", "type": "skills", "title": "专业技能", "visible": true,
      "items": [{ "group": "后端", "tags": ["Python", "FastAPI", "MySQL", "Redis"] }]
    },
    {
      "id": "sec_award", "type": "awards", "title": "荣誉奖项", "visible": true,
      "items": [{ "name": "优秀员工", "issuer": "字节跳动", "date": "2023.12" }]
    },
    {
      "id": "sec_summary", "type": "custom", "title": "自我评价", "visible": true,
      "items": [{ "title": "", "subtitle": "", "start": "", "end": "", "highlights": ["<p>5 年后端经验，擅长高并发系统设计与工程效率优化。</p>"] }]
    }
  ],
  "theme": {
    "template": "classic",
    "accent": "#bf4a2e",
    "fontFamily": "SourceHanSansSC",
    "fontSize": 10.5,
    "lineHeight": 1.35,
    "pageMargin": 18,
    "columns": 1,
    "photoPosition": "right",
    "dividerStyle": "line",
    "density": "normal"
  }
}
```

**规则**

- `sections` 是有序数组，顺序即渲染顺序。
- `highlights` 存 HTML 片段，仅允许 `strong`、`em`、`a`、`p`。
- `theme` 是唯一排版配置源，HTML 与 DOCX 渲染器都必须读取它。

### 5.5 模板协议

`templates/<id>/manifest.json`：

```json
{
  "id": "classic",
  "name": "笺 · 单栏经典",
  "description": "单栏、信息密度适中，适合大多数中文岗位",
  "tags": ["单栏", "经典"],
  "supports": { "columns": [1], "photo": true, "divider": ["line", "block", "none"] },
  "thumbnail": "thumbnail.html"
}
```

- `template.html` 接收 `{ resume, theme, fonts }` 上下文。
- 模板内不写业务逻辑，只做展示与条件判断。
- 新增模板 = 新建目录 + 三件套 + 在 manifest 注册，不修改后端代码。

### 5.6 API 设计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | `{ status, version, chromiumReady, fontsReady, dataDir }` |
| GET | `/api/resume` | 读取当前简历 |
| PUT | `/api/resume` | 全量保存，返回 `{ savedAt }` |
| POST | `/api/resume/import` | 导入 JSON，先备份 |
| GET | `/api/resume/export` | 导出 JSON 文件 |
| GET | `/api/templates` | 模板列表与 manifest |
| GET | `/api/preview?template=classic` | 返回渲染后的完整 HTML |
| POST | `/api/assets/photo` | 上传照片，返回相对路径 |
| POST | `/api/export` | `{ format: "pdf"\|"png"\|"docx", fileName?: string }`，返回 `{ files: [], dir }` |
| POST | `/api/system/reveal` | `{ path }`，在资源管理器中定位 |
| GET | `/api/system/info` | 版本、端口、日志路径、字体清单 |

**约定**

- 错误统一返回 `{ code, message, detail? }`，HTTP 状态码语义化。
- 所有写操作做 Pydantic 校验；非法数据返回字段级错误。
- 导出接口设置 120 秒超时，超时终止 Chromium 进程。

### 5.7 导出实现要点

**PDF / PNG**

```python
browser = await playwright.chromium.launch(headless=True)
page = await browser.new_page(viewport={"width": 794, "height": 1123})
await page.goto(preview_url, wait_until="networkidle")
await page.emulate_media(media="print")
await page.pdf(path=out, format="A4", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
```

- 必须等待 `document.fonts.ready` 后再导出。
- 图片需等待 `img` 的 `complete` 状态。
- 页面 CSS 使用 `@page { size: A4; margin: 0 }`，页边距由内层容器控制。

**DOCX 中文排版**

```python
from docx.oxml.ns import qn

def set_cn_font(run, name: str, size_pt: float, bold=False):
    run.font.name = name
    run.font.size = Pt(size_pt)
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts if rpr.rFonts is not None else rpr._add_rFonts()
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)
```

- 页面尺寸 `Cm(21) × Cm(29.7)`，页边距由 `theme.pageMargin` 换算。
- 段落行距 `paragraph_format.line_spacing = Pt(fontSize * lineHeight * 1.2)`。
- 小标题 `paragraph_format.keep_with_next = True`。
- 双栏使用 1 行 2 列表格，去掉边框，固定列宽。

### 5.8 环境自举实现约束

- 所有安装动作必须幂等，失败可重试，且不留下半安装状态（安装前写 `.installing` 标记，成功后删除）。
- 下载使用 PowerShell `Invoke-WebRequest`，带 `-UseBasicParsing`，失败重试 3 次。
- 官方 Python 安装包固定版本与 SHA-256，下载后校验。
- 端口探测与写回 `runtime.json` 由 `run.bat` 完成，后端只读取。
- 若项目所在磁盘剩余空间 < 2GB，直接提示并退出。

---

## 6. 全局规则与异常

| 场景 | 行为 |
|---|---|
| 端口全部被占用 | 提示手动关闭占用程序，并给出 `netstat` 命令 |
| Python 安装被拦截 | 提示关闭杀毒软件或手动安装，给出官网链接 |
| 依赖安装失败 | 自动切换官方源重试一次；仍失败则输出最后 20 行日志 |
| Chromium 下载失败 | 提示网络问题，提供“重试”与“仅导出 DOCX”的降级入口 |
| 字体缺失 | 回退微软雅黑，状态栏提示，不阻断导出 |
| 数据文件损坏 | 使用 `.bak` 恢复；无备份则加载示例数据并保留损坏文件副本 |
| 导出超时 | 终止任务，提示“内容较多，请稍后重试”，记录日志 |
| 浏览器未自动打开 | 控制台输出可点击的 URL |

---

## 7. 数据与隐私

- 所有数据仅存本地 `data/`，不上传、不埋点、不联网（首次安装依赖除外）。
- 服务只监听 `127.0.0.1`，校验 `Origin` 为同源。
- 照片与导出的简历属于用户敏感数据，删除简历时需二次确认。
- `exports/` 与 `data/` 不随应用更新被覆盖。

---

## 8. 验收标准

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| AC-01 | 全新环境启动 | 未安装 Python 的 Windows 10/11 机器，双击 `run.bat` 后自动完成安装并打开应用 |
| AC-02 | 路径约束 | 除 Python 安装器登记的卸载信息外，所有运行文件位于项目盘，可用“按大小排序”确认 |
| AC-03 | 幂等启动 | 第二次启动不重复安装，30 秒内打开应用 |
| AC-04 | 编辑闭环 | 修改姓名/条目后 1 秒内预览更新，刷新页面后内容仍在 |
| AC-05 | 一页检测 | 增加内容超过 A4 后，2 秒内出现超页提示与裁切线 |
| AC-06 | PDF | 文字可选中、可搜索，A4 尺寸正确，条目无跨页截断 |
| AC-07 | PNG | 输出宽度 ≥ 2382px，无界面元素、无阴影、无黑边 |
| AC-08 | DOCX | Word 与 WPS 打开均无字体替换提示，中文不变成宋体，照片尺寸正确 |
| AC-09 | 三格式一致 | 抽取纯文本后内容与顺序完全一致 |
| AC-10 | 异常恢复 | 手动删除 Chromium 目录后重启，自动补齐并可导出 |
| AC-11 | 数据安全 | 导入非法 JSON 被拒绝，原数据不丢失 |
| AC-12 | 视觉还原 | 与 `prototype.html` 对照，布局比例、配色、字号层级一致 |

---

## 9. 里程碑（实现顺序）

| 阶段 | 交付 |
|---|---|
| M1 | 项目骨架、`run.bat` 与依赖自举、健康检查、静态托管 |
| M2 | 数据模型、存储服务、模板渲染、预览 iframe |
| M3 | 编辑器三栏、模块管理、富文本、主题面板、自动保存 |
| M4 | 导出管线：PDF → PNG → DOCX，输出目录与打开文件夹 |
| M5 | 一页检测、异常处理、字体与 Chromium 自检、验收自测 |

> 每个阶段结束必须能独立启动并演示，不允许最后一次性联调。

---

## 10. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| DOCX 与 HTML 版式漂移 | 高 | 共享 `theme`，模板与 `docx_builder` 成对开发，三格式文本比对纳入自测 |
| 首次安装耗时长 | 中 | 分阶段进度提示，明确“首次需要几分钟”，失败可续装 |
| 用户机器无网络 | 中 | P1 提供离线 wheels 包；P0 明确提示需联网 |
| 中文批处理乱码 | 中 | 统一 UTF-8 无 BOM + `chcp 65001`，所有输出走 `echo` 而非复杂转义 |
| 杀毒软件拦截安装 | 中 | 检测失败原因并给出可操作提示，不静默失败 |
| 路径含空格/中文 | 中 | 全路径加引号，Python 侧使用 `pathlib`，禁止字符串拼接 |
| 浏览器缩放导致预览尺寸误判 | 低 | 预览容器固定像素宽度，使用 CSS transform 缩放，不影响测量 |

---

## 附录 A：`run.bat` 参考实现

> 保存为 UTF-8（无 BOM）、CRLF 换行。实际实现需补充下载校验与更细的错误分支。

```bat
@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title 简历工坊 - 环境检查
pushd "%~dp0"

set "ROOT=%CD%"
set "RUNTIME=%ROOT%\.runtime"
set "VENV=%ROOT%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "LOG=%RUNTIME%\logs\bootstrap.log"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PORT=8765"

if not exist "%RUNTIME%" mkdir "%RUNTIME%"
if not exist "%RUNTIME%\logs" mkdir "%RUNTIME%\logs"
if not exist "%RUNTIME%\temp" mkdir "%RUNTIME%\temp"
if not exist "%RUNTIME%\pip-cache" mkdir "%RUNTIME%\pip-cache"
if not exist "%RUNTIME%\ms-playwright" mkdir "%RUNTIME%\ms-playwright"

set "TEMP=%RUNTIME%\temp"
set "TMP=%RUNTIME%\temp"
set "PIP_CACHE_DIR=%RUNTIME%\pip-cache"
set "PLAYWRIGHT_BROWSERS_PATH=%RUNTIME%\ms-playwright"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONNOUSERSITE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

echo ============================================
echo   简历工坊 Resume Studio
echo   首次启动需要安装依赖，请保持网络连接
echo ============================================
echo.

echo [1/5] 检查 Python 运行环境...
call :ensure_python
if errorlevel 1 goto :fail

echo [2/5] 检查 Python 依赖...
call :ensure_deps
if errorlevel 1 goto :fail

echo [3/5] 检查浏览器内核...
call :ensure_chromium
if errorlevel 1 goto :fail

echo [4/5] 检查前端资源...
if not exist "%ROOT%\frontend\dist\index.html" (
  echo    [错误] 缺少前端构建产物 frontend\dist\index.html
  echo    请使用完整发布包，或由开发者执行 build_frontend.bat
  goto :fail
)

echo [5/5] 启动本地服务...
call :pick_port
start "简历工坊 - 请勿关闭此窗口" cmd /k ""%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%"

echo    等待服务就绪...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$u='http://127.0.0.1:%PORT%/api/health'; for($i=0;$i -lt 60;$i++){ try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 (
  echo    [错误] 服务启动超时，请查看控制台窗口与日志：
  echo    %LOG%
  goto :fail
)

start "" "http://127.0.0.1:%PORT%"
echo.
echo 启动成功，浏览器已打开。本窗口可以关闭。
timeout /t 3 >nul
popd
exit /b 0

:ensure_python
if exist "%PY%" (
  "%PY%" -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
  if not errorlevel 1 exit /b 0
)
set "SYSPY="
for %%V in (3.12 3.11 3.10) do (
  if not defined SYSPY (
    py -%%V -c "import sys" >nul 2>&1
    if not errorlevel 1 set "SYSPY=py -%%V"
  )
)
if not defined SYSPY (
  python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
  if not errorlevel 1 set "SYSPY=python"
)
if not defined SYSPY (
  echo    未检测到 Python，正在下载并安装到本目录 .runtime\python ...
  set "INSTALLER=%RUNTIME%\python-installer.exe"
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%INSTALLER%' -UseBasicParsing"
  if not exist "%INSTALLER%" (
    echo    [错误] Python 安装包下载失败，请检查网络。
    exit /b 1
  )
  "%INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%RUNTIME%\python" Include_pip=1 Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0
  if not exist "%RUNTIME%\python\python.exe" (
    echo    [错误] Python 静默安装失败，可能被杀毒软件拦截。
    exit /b 1
  )
  set "SYSPY=%RUNTIME%\python\python.exe"
)
if not exist "%PY%" (
  echo    正在创建虚拟环境 .venv ...
  %SYSPY% -m venv "%VENV%"
  if errorlevel 1 exit /b 1
)
"%PY%" -m ensurepip --upgrade >nul 2>&1
exit /b 0

:ensure_deps
set "REQ_HASH="
for /f "delims=" %%H in ('"%PY%" -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "REQ_HASH=%%H"
set "OLD_HASH="
if exist "%RUNTIME%\deps.sha256" set /p OLD_HASH=<"%RUNTIME%\deps.sha256"
if "%REQ_HASH%"=="%OLD_HASH%" exit /b 0
echo    正在安装依赖，首次可能需要几分钟...
"%PY%" -m pip install -r requirements.txt -i %MIRROR% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo    镜像源失败，切换官方源重试...
  "%PY%" -m pip install -r requirements.txt >>"%LOG%" 2>&1
  if errorlevel 1 exit /b 1
)
>"%RUNTIME%\deps.sha256" echo %REQ_HASH%
exit /b 0

:ensure_chromium
if exist "%RUNTIME%\playwright.ok" exit /b 0
echo    正在下载浏览器内核，首次可能需要几分钟...
"%PY%" -m playwright install chromium >>"%LOG%" 2>&1
if errorlevel 1 exit /b 1
>"%RUNTIME%\playwright.ok" echo ok
exit /b 0

:pick_port
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
  set /a PORT+=1
  goto :pick_port
)
exit /b 0

:fail
echo.
echo 启动失败。请查看日志：%LOG%
echo 可将本窗口截图发送给开发者。
pause
popd
exit /b 1
```

## 附录 B：`requirements.txt`

```text
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.4
jinja2==3.1.5
python-docx==1.1.2
playwright==1.49.1
python-multipart==0.0.20
pillow==11.0.0
```

## 附录 C：前端构建（仅开发者）

- `build_frontend.bat`：`npm ci && npm run build`，产物输出到 `frontend/dist`。
- 发布包必须包含 `frontend/dist`，终端用户无需安装 Node。
- 开发模式：`npm run dev`（5173 端口），Vite 代理 `/api` 到 `127.0.0.1:8765`。
