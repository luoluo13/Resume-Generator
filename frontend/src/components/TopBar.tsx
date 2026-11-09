import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import {
  IconChevron,
  IconDownload,
  IconFileJson,
  IconFolder,
  IconLayers,
  IconPalette,
  IconUpload,
  IconWand
} from "../icons";
import { useResumeStore } from "../store";
import { toast, useUiStore } from "../ui";

export function TopBar() {
  const view = useUiStore((state) => state.view);
  const setView = useUiStore((state) => state.setView);
  const setThemeOpen = useUiStore((state) => state.setThemeOpen);
  const setExportOpen = useUiStore((state) => state.setExportOpen);
  const chatOpen = useUiStore((state) => state.chatOpen);
  const setChatOpen = useUiStore((state) => state.setChatOpen);
  const setLibraryOpen = useUiStore((state) => state.setLibraryOpen);
  const resumeName = useResumeStore((state) => state.resumeName);
  const resumeCount = useResumeStore((state) => state.resumes.length);
  const saveState = useResumeStore((state) => state.saveState);
  const saveError = useResumeStore((state) => state.saveError);
  const saveNow = useResumeStore((state) => state.saveNow);
  const info = useResumeStore((state) => state.info);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [menuOpen]);

  const exportJson = () => {
    setMenuOpen(false);
    const link = document.createElement("a");
    link.href = "/api/resume/export";
    link.click();
    toast("success", "正在导出 JSON 备份");
  };

  const importJson = async (file?: File) => {
    if (!file) return;
    try {
      await api.importJson(file);
      await useResumeStore.getState().load();
      toast("success", "数据已导入，原数据已自动备份");
    } catch (error) {
      toast("error", `导入失败：${(error as Error).message}`);
    }
  };

  const revealData = async () => {
    setMenuOpen(false);
    if (!info) return;
    try {
      await api.reveal(info.dataDir);
    } catch (error) {
      toast("error", (error as Error).message);
    }
  };

  const stateLabel = saveState === "saved" ? "已保存" : saveState === "saving" ? "保存中" : "保存失败";

  return (
    <header className="topbar">
      <div className="brand">
        <div className="seal">简</div>
        <div className="brand-text">
          <strong>简历工坊</strong>
          <span>RESUME STUDIO</span>
        </div>
      </div>

      <nav className="topnav" aria-label="主导航">
        <button type="button" className={view === "editor" ? "is-active" : ""} onClick={() => setView("editor")}>
          编辑器
        </button>
        <button type="button" className={view === "templates" ? "is-active" : ""} onClick={() => setView("templates")}>
          模板中心
        </button>
      </nav>

      <div className="topbar-right">
        <button
          type="button"
          className={`save-state${saveState === "error" ? " is-error" : ""}`}
          data-state={saveState}
          title={saveState === "error" ? saveError : "所有修改自动保存在本机"}
          onClick={() => saveState === "error" && void saveNow()}
        >
          <i className="save-dot" />
          <span>{stateLabel}</span>
        </button>

        <button
          type="button"
          className="btn btn-library"
          title={`当前简历：${resumeName || "未命名"}；共 ${resumeCount} 份`}
          onClick={() => setLibraryOpen(true)}
        >
          <IconLayers size={15} />
          <span className="btn-library-name">{resumeName || "简历库"}</span>
        </button>

        <div className="menu-wrap" ref={menuRef}>
          <button type="button" className="btn" onClick={() => setMenuOpen((value) => !value)}>
            <IconFileJson size={15} />
            数据
            <IconChevron size={13} />
          </button>
          {menuOpen ? (
            <div className="menu">
              <button type="button" className="menu-item" onClick={exportJson}>
                <IconDownload size={15} />
                导出 JSON 备份
              </button>
              <button
                type="button"
                className="menu-item"
                onClick={() => {
                  setMenuOpen(false);
                  fileRef.current?.click();
                }}
              >
                <IconUpload size={15} />
                导入 JSON 数据
              </button>
              <button type="button" className="menu-item" onClick={() => void revealData()}>
                <IconFolder size={15} />
                打开数据目录
              </button>
            </div>
          ) : null}
        </div>

        <button
          type="button"
          className={`btn btn-ai${chatOpen ? " is-on" : ""}`}
          title="打开 AI 简历助手"
          onClick={() => setChatOpen(!chatOpen)}
        >
          <IconWand size={15} />
          AI 助手
        </button>
        <button type="button" className="btn" onClick={() => setThemeOpen(true)}>
          <IconPalette size={15} />
          主题
        </button>
        <button type="button" className="btn btn-primary" onClick={() => setExportOpen(true)}>
          <IconDownload size={15} />
          导出简历
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        hidden
        onChange={(event) => {
          void importJson(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </header>
  );
}
