import { useEffect, useRef, useState } from "react";
import { api, TEMPLATE_PACK_URL } from "../api";
import { IconDownload, IconTemplate, IconTrash, IconUpload, IconWand } from "../icons";
import { useResumeStore } from "../store";
import { toast } from "../ui";
import type { TemplateManifest } from "../types";

type Filter = "all" | "single" | "double" | "serif" | "custom";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "single", label: "单栏" },
  { value: "double", label: "双栏" },
  { value: "serif", label: "衬线标题" },
  { value: "custom", label: "自定义" }
];

export function TemplatesView() {
  const templates = useResumeStore((state) => state.templates);
  const resume = useResumeStore((state) => state.resume);
  const setTemplate = useResumeStore((state) => state.setTemplate);
  const refreshTemplates = useResumeStore((state) => state.refreshTemplates);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  if (!resume) return null;

  const customCount = templates.filter((item) => item.source === "user").length;

  const visible = templates.filter((item) => {
    if (filter === "single") return item.supports.columns.includes(1);
    if (filter === "double") return item.supports.columns.includes(2);
    if (filter === "serif") return Boolean(item.serifHeading);
    if (filter === "custom") return item.source === "user";
    return true;
  });

  const choose = (id: string, name: string) => {
    if (resume.theme.template === id) return;
    setTemplate(id);
    toast("success", `已切换到「${name}」`);
  };

  const importPackage = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".zip")) {
      toast("error", "请选择 zip 格式的模板包");
      return;
    }
    setBusy(true);
    try {
      const manifest = await api.importTemplate(file);
      await refreshTemplates();
      toast("success", `模板「${manifest.name}」已导入，可在下方切换`);
    } catch (error) {
      toast("error", (error as Error).message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const copyPrompt = async () => {
    try {
      const prompt = await api.getTemplatePrompt();
      await navigator.clipboard.writeText(prompt);
      toast("success", "AI 提示词已复制，可粘贴给任意 AI");
    } catch {
      toast("error", "复制失败，请检查浏览器剪贴板权限");
    }
  };

  const removeTemplate = async (item: TemplateManifest) => {
    if (!window.confirm(`确定删除自定义模板「${item.name}」？此操作不会影响简历内容。`)) return;
    try {
      await api.deleteTemplate(item.id);
      await refreshTemplates();
      const state = useResumeStore.getState();
      if (state.resume?.theme.template === item.id) {
        const next = state.templates.find((entry) => entry.source === "builtin");
        if (next) state.setTemplate(next.id);
      }
      toast("success", `已删除「${item.name}」`);
    } catch (error) {
      toast("error", (error as Error).message);
    }
  };

  return (
    <div className="screen-templates">
      <div className="tpl-wrap">
        <header className="page-head">
          <div>
            <p className="pane-eyebrow">TEMPLATES</p>
            <h1>模板中心</h1>
            <p>
              {templates.length} 套模板，其中 {customCount} 套为自定义；切换只改变排版与配色，不会修改任何内容。
            </p>
          </div>
          <div className="filters">
            {FILTERS.map((item) => (
              <button
                type="button"
                key={item.value}
                className={`filter${filter === item.value ? " is-active" : ""}`}
                onClick={() => setFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </header>

        <div className="tpl-actions">
          <input
            ref={fileRef}
            type="file"
            accept=".zip,application/zip"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importPackage(file);
            }}
          />
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => fileRef.current?.click()}>
            <IconUpload size={15} />
            {busy ? "正在校验..." : "导入模板包"}
          </button>
          <a className="btn" href={TEMPLATE_PACK_URL} download>
            <IconDownload size={15} />
            下载模板开发包
          </a>
          <button type="button" className="btn" onClick={() => void copyPrompt()}>
            <IconWand size={15} />
            复制 AI 提示词
          </button>
          <p className="tpl-actions-note">
            把提示词交给任意 AI，让它产出 zip 模板包，再导入这里即可。模板只允许 HTML/CSS，不执行任何脚本。
          </p>
        </div>

        <div className="tpl-grid">
          {visible.map((item) => (
            <article
              key={item.id}
              className={`tpl-card${resume.theme.template === item.id ? " is-active" : ""}`}
              role="button"
              tabIndex={0}
              onClick={() => choose(item.id, item.name)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  choose(item.id, item.name);
                }
              }}
            >
              <ThumbFrame id={item.id} />
              {item.source === "user" ? (
                <button
                  type="button"
                  className="icon-btn tpl-del"
                  title="删除模板"
                  onClick={(event) => {
                    event.stopPropagation();
                    void removeTemplate(item);
                  }}
                >
                  <IconTrash size={14} />
                </button>
              ) : null}
              <div className="tpl-meta">
                <div className="tpl-info">
                  <p className="tpl-name">{item.name}</p>
                  <p className="tpl-desc">{item.description}</p>
                  <div className="tpl-tags">
                    {item.tags.map((tag) => (
                      <span className="tpl-tag" key={tag}>
                        {tag}
                      </span>
                    ))}
                    {item.source === "user" ? <span className="tpl-tag is-user">自定义</span> : null}
                  </div>
                </div>
                <span className={`tpl-state${resume.theme.template === item.id ? "" : " muted"}`}>
                  {resume.theme.template === item.id ? "使用中" : "可切换"}
                </span>
              </div>
            </article>
          ))}
        </div>

        {!visible.length ? <p className="tpl-empty">当前筛选下没有模板。</p> : null}

        <p className="tpl-note">
          <IconTemplate size={14} />
          内置模板同时提供 HTML 与 DOCX 渲染；自定义模板的 DOCX 使用通用回退，PDF / PNG 与预览完全一致。
        </p>
      </div>
    </div>
  );
}

function ThumbFrame({ id }: { id: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.4);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const update = () => setScale(node.clientWidth / 794);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="tpl-thumb" ref={ref}>
      <iframe
        src={`/api/preview?template=${encodeURIComponent(id)}&preview=0`}
        title={`${id} 模板缩略预览`}
        style={{ width: 794, height: 1123, transform: `scale(${scale})` }}
        loading="lazy"
        tabIndex={-1}
      />
    </div>
  );
}
