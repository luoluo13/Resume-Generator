import { api } from "../api";
import { IconAlert, IconCheck, IconClose, IconFolder } from "../icons";
import { useResumeStore } from "../store";
import { toast, useUiStore } from "../ui";

export function EnvPanel() {
  const open = useUiStore((state) => state.envOpen);
  const setOpen = useUiStore((state) => state.setEnvOpen);
  const info = useResumeStore((state) => state.info);

  if (!open) return null;

  const reveal = async (path: string) => {
    try {
      await api.reveal(path);
    } catch (error) {
      toast("error", (error as Error).message);
    }
  };

  return (
    <div className="modal-backdrop is-open" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
      <div className="modal env-modal" role="dialog" aria-modal="true" aria-label="运行环境">
        <div className="modal-head">
          <div>
            <h3>运行环境</h3>
            <p>所有数据与服务都在本机，不会上传到任何服务器。</p>
          </div>
          <button type="button" className="icon-btn" title="关闭" onClick={() => setOpen(false)}>
            <IconClose size={16} />
          </button>
        </div>

        <div className="modal-body">
          {info ? (
            <>
              <div className="env-card">
                <div className="env-card-head">
                  <h3>服务状态</h3>
                  <span className="right env-state">
                    <IconCheck size={13} />
                    运行正常
                  </span>
                </div>
                <div className="env-row">
                  <span className="env-name">服务地址</span>
                  <span className="env-detail">http://127.0.0.1:{info.port}</span>
                  <span className="env-state">
                    <IconCheck size={13} />
                    已连接
                  </span>
                </div>
                <div className="env-row">
                  <span className="env-name">版本</span>
                  <span className="env-detail">
                    {info.version} · {info.platform}
                  </span>
                </div>
                <div className="env-row">
                  <span className="env-name">Python</span>
                  <span className="env-detail">{info.python}</span>
                </div>
              </div>

              <div className="env-card">
                <div className="env-card-head">
                  <h3>目录</h3>
                </div>
                {[
                  { label: "数据目录", path: info.dataDir },
                  { label: "导出目录", path: info.exportsDir },
                  { label: "日志目录", path: info.logDir },
                  { label: "项目根目录", path: info.root }
                ].map((row) => (
                  <div className="env-row" key={row.label}>
                    <span className="env-name">{row.label}</span>
                    <span className="env-detail">{row.path}</span>
                    <button type="button" className="icon-btn" title="打开目录" onClick={() => void reveal(row.path)}>
                      <IconFolder size={14} />
                    </button>
                  </div>
                ))}
              </div>

              <div className="env-card">
                <div className="env-card-head">
                  <h3>导出能力</h3>
                </div>
                <div className={`env-row${info.fonts.ready ? "" : " is-pending"}`}>
                  <span className="env-name">简历字体</span>
                  <span className="env-detail">
                    {Object.entries(info.fonts.available)
                      .map(([key, value]) => `${info.fonts.labels[key] ?? key}${value ? "✓" : "×"}`)
                      .join("  ")}
                  </span>
                  <span className="env-state">
                    {info.fonts.ready ? <IconCheck size={13} /> : <IconAlert size={13} />}
                    {info.fonts.ready ? "可用" : `回退 ${info.fonts.fallback}`}
                  </span>
                </div>
                <div className={`env-row${info.chromiumReady ? "" : " is-pending"}`}>
                  <span className="env-name">Chromium 内核</span>
                  <span className="env-detail">用于渲染 PDF 与 PNG 页面</span>
                  <span className="env-state">
                    {info.chromiumReady ? <IconCheck size={13} /> : <IconAlert size={13} />}
                    {info.chromiumReady ? "已就绪" : "缺失"}
                  </span>
                </div>
                <div className="env-note">
                  首次启动时 run.bat 会自动检测并补齐依赖与 Chromium 内核。若导出内核缺失，请关闭窗口后重新运行 run.bat。
                </div>
              </div>
            </>
          ) : (
            <p className="env-loading">正在读取环境信息…</p>
          )}
        </div>
      </div>
    </div>
  );
}
