import { useEffect } from "react";
import { EditorView } from "./components/EditorView";
import { ExportPanel } from "./components/ExportPanel";
import { ImportWizard } from "./components/ImportWizard";
import { ThemeDrawer } from "./components/ThemeDrawer";
import { Toasts } from "./components/Toasts";
import { TopBar } from "./components/TopBar";
import { useResumeStore } from "./store";
import { useUiStore } from "./ui";
import { TemplatesView } from "./views/TemplatesView";

export function App() {
  const loading = useResumeStore((state) => state.loading);
  const error = useResumeStore((state) => state.error);
  const load = useResumeStore((state) => state.load);
  const view = useUiStore((state) => state.view);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void useResumeStore.getState().saveNow();
      }
      if (event.key === "Escape") {
        const ui = useUiStore.getState();
        ui.setThemeOpen(false);
        ui.setExportOpen(false);
        ui.setImportOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (loading) {
    return (
      <div className="boot-screen">
        <div className="boot-card">
          <div className="seal boot-seal">简</div>
          <strong>简历工坊</strong>
          <p>正在读取本地简历数据…</p>
          <span className="spinner dark" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="boot-screen">
        <div className="boot-card is-error">
          <div className="seal boot-seal">简</div>
          <strong>无法连接本地服务</strong>
          <p>{error}</p>
          <p className="boot-note">请确认 run.bat 打开的窗口仍在运行，然后重试。</p>
          <button type="button" className="btn btn-primary" onClick={() => void load()}>
            重新连接
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <TopBar />
      <main className="app-main">{view === "editor" ? <EditorView /> : <TemplatesView />}</main>
      <ThemeDrawer />
      <ExportPanel />
      <ImportWizard />
      <Toasts />
    </div>
  );
}
