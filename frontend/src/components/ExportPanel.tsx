import { useState } from "react";
import { api } from "../api";
import { IconAlert, IconCheck, IconClose, IconFolder, IconRefresh } from "../icons";
import { useResumeStore } from "../store";
import type { ExportResult, Theme } from "../types";
import { toast, useUiStore } from "../ui";

type Format = "pdf" | "png" | "docx";

const FORMATS: { value: Format; icon: string; title: string; desc: string; badge: string }[] = [
  { value: "pdf", icon: "PDF", title: "PDF 文档", desc: "文字可选中、可搜索，适合网申、邮件投递与打印。", badge: "推荐" },
  { value: "png", icon: "PNG", title: "高清图片", desc: "3 倍分辨率，适合微信、即时通讯工具直接发送。", badge: "高清" },
  { value: "docx", icon: "DOC", title: "Word 文档", desc: "可直接编辑的 DOCX，方便在 Word 中继续调整。", badge: "可编辑" }
];

interface Recent {
  name: string;
  format: Format;
  time: string;
}

export function ExportPanel() {
  const open = useUiStore((state) => state.exportOpen);
  const setOpen = useUiStore((state) => state.setExportOpen);
  const resume = useResumeStore((state) => state.resume);
  const info = useResumeStore((state) => state.info);
  const pageRatio = useResumeStore((state) => state.pageRatio);
  const setTheme = useResumeStore((state) => state.setTheme);
  const [format, setFormat] = useState<Format>("pdf");
  const [fileName, setFileName] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<Recent[]>([]);
  const [previousTheme, setPreviousTheme] = useState<Theme | null>(null);

  if (!open || !resume) return null;

  const now = new Date();
  const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  const suggested = `${resume.basics.name || "我的简历"}_${resume.basics.jobIntention || "简历"}_${stamp}`;
  const selected = FORMATS.find((item) => item.value === format) ?? FORMATS[0];

  const close = () => {
    if (running) return;
    setOpen(false);
    setError("");
    setResult(null);
  };

  const applyCompact = () => {
    setPreviousTheme({ ...resume.theme });
    setTheme({ density: "compact", lineHeight: Math.min(resume.theme.lineHeight, 1.25) });
    toast("info", "已切换为紧凑密度，预览即将刷新");
  };

  const undoCompact = () => {
    if (!previousTheme) return;
    setTheme(previousTheme);
    setPreviousTheme(null);
    toast("info", "已恢复原来的排版设置");
  };

  const reveal = async (path: string) => {
    try {
      await api.reveal(path);
    } catch (reason) {
      toast("error", (reason as Error).message);
    }
  };

  const run = async () => {
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const exported = await api.exportResume(format, fileName.trim());
      setResult(exported);
      setRecent((items) =>
        [
          {
            name: exported.files[0]?.name ?? selected.title,
            format,
            time: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
          },
          ...items
        ].slice(0, 6)
      );
      toast("success", `${selected.title} 已导出`);
    } catch (reason) {
      setError((reason as Error).message);
      toast("error", `导出失败：${(reason as Error).message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="modal-backdrop is-open" onMouseDown={(event) => event.target === event.currentTarget && close()}>
      <div className="modal export-modal" role="dialog" aria-modal="true" aria-label="导出简历">
        <div className="modal-head">
          <div>
            <h3>导出简历</h3>
            <p>导出前会重新渲染一次，确保与右侧预览完全一致。</p>
          </div>
          <button type="button" className="icon-btn" title="关闭" onClick={close}>
            <IconClose size={16} />
          </button>
        </div>

        <div className="modal-body">
          {pageRatio > 1 ? (
            <div className="notice">
              <IconAlert size={14} />
              <div>
                当前内容约 <strong>{pageRatio.toFixed(2)}</strong> 页，超出单页范围。导出不会被阻止，但建议精简条目或切换紧凑密度。
                <div className="notice-actions">
                  {previousTheme ? (
                    <button type="button" className="btn btn-sm" onClick={undoCompact}>
                      撤销紧凑
                    </button>
                  ) : (
                    <button type="button" className="btn btn-sm" onClick={applyCompact}>
                      一键紧凑
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : null}

          <div className="fmt-list">
            {FORMATS.map((item) => (
              <button
                type="button"
                key={item.value}
                className={`fmt-card${format === item.value ? " is-selected" : ""}`}
                onClick={() => setFormat(item.value)}
              >
                <span className="fmt-icon">{item.icon}</span>
                <span>
                  <span className="fmt-title">
                    {item.title}
                    <em className="badge">{item.badge}</em>
                  </span>
                  <span className="fmt-desc">{item.desc}</span>
                </span>
                <span className="fmt-radio" />
              </button>
            ))}
          </div>

          <div className="export-field">
            <span>文件名（可留空自动命名）</span>
            <input value={fileName} placeholder={suggested} onChange={(event) => setFileName(event.target.value)} />
          </div>
          <div className="export-field">
            <span>输出目录</span>
            <div className="path-display">
              <span>{info?.exportsDir ?? "exports"}</span>
              <button type="button" className="icon-btn" title="打开目录" onClick={() => info && void reveal(info.exportsDir)}>
                <IconFolder size={14} />
              </button>
            </div>
          </div>

          <div className="export-actions">
            <button type="button" className="btn btn-primary" disabled={running} onClick={() => void run()}>
              {running ? <span className="spinner" /> : <IconRefresh size={15} />}
              {running ? "正在导出…" : `导出 ${selected.icon}`}
            </button>
            <span className="hint">同一时刻只处理一个导出任务</span>
          </div>

          {running ? (
            <div className="export-progress is-on">
              <div className="progress-step">
                <span>正在渲染模板并生成文件</span>
                <span>请稍候</span>
              </div>
              <div className="progress-track">
                <div className="progress-bar is-running" />
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="export-error">
              <IconAlert size={14} />
              <div>
                <strong>导出失败</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : null}

          {result ? (
            <div className="export-success">
              <IconCheck size={16} />
              <div>
                <strong>导出成功</strong>
                {result.files.map((file) => (
                  <code key={file.path}>
                    {file.name} · {formatSize(file.size)}
                  </code>
                ))}
                <button type="button" className="btn btn-sm" onClick={() => void reveal(result.dir)}>
                  <IconFolder size={13} />
                  打开所在文件夹
                </button>
              </div>
            </div>
          ) : null}

          {recent.length ? (
            <div className="recent-list">
              <p className="recent-title">本次会话最近导出</p>
              {recent.map((item, index) => (
                <div className="recent-item" key={`${item.name}-${index}`}>
                  <span className="ext">{item.format.toUpperCase()}</span>
                  <span className="recent-name">{item.name}</span>
                  <span className="time">{item.time}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function formatSize(size: number): string {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}
