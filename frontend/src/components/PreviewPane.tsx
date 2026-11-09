import { useEffect, useRef, useState } from "react";
import { IconAlert, IconZoomIn, IconZoomOut } from "../icons";
import { useResumeStore } from "../store";
import { useUiStore } from "../ui";

const PAGE_W = 794;
const PAGE_H = 1123;

interface MetricsMessage {
  type: string;
  pages: number;
  ratio: number;
  height: number;
}

export function PreviewPane() {
  const resume = useResumeStore((state) => state.resume);
  const templates = useResumeStore((state) => state.templates);
  const previewKey = useResumeStore((state) => state.previewKey);
  const pages = useResumeStore((state) => state.pages);
  const pageRatio = useResumeStore((state) => state.pageRatio);
  const setMetrics = useResumeStore((state) => state.setMetrics);
  const zoom = useUiStore((state) => state.zoom);
  const setZoom = useUiStore((state) => state.setZoom);
  const [height, setHeight] = useState(PAGE_H);
  const [loading, setLoading] = useState(true);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const target = fitZoom(stage);
    if (target && PAGE_W * useUiStore.getState().zoom > stage.clientWidth - 64) {
      useUiStore.getState().setZoom(target);
    }
  }, []);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.source !== frameRef.current?.contentWindow) return;
      const data = event.data as MetricsMessage | null;
      if (!data || data.type !== "resume-metrics") return;
      setHeight(Math.max(PAGE_H, Math.ceil(data.height)));
      setMetrics(Math.max(1, data.pages), data.ratio);
      setLoading(false);
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [setMetrics]);

  if (!resume) return null;

  const template = templates.find((item) => item.id === resume.theme.template);
  const src = `/api/preview?template=${encodeURIComponent(resume.theme.template)}&preview=1&v=${previewKey}`;
  const overflow = pages > 1;

  const fitWidth = () => {
    const target = fitZoom(stageRef.current);
    if (target) setZoom(target);
  };

  return (
    <section className="preview-pane">
      <div className="preview-toolbar">
        <span className="pt-label">A4 实时预览</span>
        <span className="pt-template">{template ? template.name : resume.theme.template}</span>
        {overflow ? (
          <span className="overpage-badge">
            <IconAlert size={12} />
            超出 {Math.round((pageRatio - 1) * 100)}%
          </span>
        ) : null}
        <span className="pt-spacer" />
        <span className="pt-page">共 {pages} 页</span>
        <div className="zoom-group">
          <button type="button" title="缩小" onClick={() => setZoom(zoom - 0.05)}>
            <IconZoomOut size={13} />
          </button>
          <span className="zoom-value">{Math.round(zoom * 100)}%</span>
          <button type="button" title="放大" onClick={() => setZoom(zoom + 0.05)}>
            <IconZoomIn size={13} />
          </button>
        </div>
        <button type="button" className="zoom-fit" onClick={fitWidth}>
          适应宽度
        </button>
      </div>

      <div className="paper-stage" ref={stageRef}>
        <div className="paper-wrap" style={{ width: PAGE_W * zoom, height: height * zoom }}>
          <iframe
            ref={frameRef}
            src={src}
            title="简历预览"
            className="paper-frame"
            style={{ width: PAGE_W, height, transform: `scale(${zoom})` }}
            onLoad={() => setLoading(false)}
          />
        </div>
        {loading ? (
          <div className="preview-loading">
            <span className="spinner dark" />
            正在渲染简历…
          </div>
        ) : null}
      </div>
    </section>
  );
}

function fitZoom(stage: HTMLDivElement | null): number | null {
  if (!stage) return null;
  const available = stage.clientWidth - 64;
  if (available <= 0) return null;
  return Math.min(1.2, Math.max(0.5, Number((available / PAGE_W).toFixed(2))));
}
