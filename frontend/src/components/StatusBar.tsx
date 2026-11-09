import { api } from "../api";
import { useResumeStore } from "../store";
import { toast, useUiStore } from "../ui";

export function StatusBar() {
  const info = useResumeStore((state) => state.info);
  const pages = useResumeStore((state) => state.pages);
  const pageRatio = useResumeStore((state) => state.pageRatio);
  const setEnvOpen = useUiStore((state) => state.setEnvOpen);

  const reveal = async (path: string) => {
    try {
      await api.reveal(path);
    } catch (error) {
      toast("error", (error as Error).message);
    }
  };

  return (
    <footer className="statusbar">
      <span className="sb-item">
        <i className={`dot-${info ? "ok" : "warn"}`} />
        {info ? `本地服务 127.0.0.1:${info.port}` : "本地服务未连接"}
      </span>
      {info ? (
        <button type="button" className="sb-item sb-link" title={info.dataDir} onClick={() => void reveal(info.dataDir)}>
          数据目录
        </button>
      ) : null}
      <span className="sb-item">
        页数 {pages} 页{pageRatio > 1 ? ` · 约 ${pageRatio.toFixed(2)} 页` : ""}
      </span>
      <span className="sb-item">
        <i className={`dot-${info?.fonts.ready ? "ok" : "warn"}`} />
        字体{info?.fonts.ready ? "已就绪" : "回退微软雅黑"}
      </span>
      <span className="sb-item">
        <i className={`dot-${info?.chromiumReady ? "ok" : "warn"}`} />
        {info?.chromiumReady ? "导出内核就绪" : "导出内核缺失"}
      </span>
      <span className="sb-right">
        <span className="sb-item">版本 {info?.version ?? "1.0.0"}</span>
        <button type="button" className="sb-item sb-link" onClick={() => setEnvOpen(true)}>
          运行环境
        </button>
      </span>
    </footer>
  );
}
