import { useState } from "react";
import { IconAlert, IconCheck, IconClose, IconPlus, IconTrash } from "../icons";
import { useResumeStore } from "../store";
import { toast, useUiStore } from "../ui";
import type { ResumeSummary } from "../types";

function formatTime(value: string): string {
  if (!value) return "未知时间";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (input: number) => String(input).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function ResumeLibrary() {
  const open = useUiStore((state) => state.libraryOpen);
  const setOpen = useUiStore((state) => state.setLibraryOpen);
  const resumes = useResumeStore((state) => state.resumes);
  const currentId = useResumeStore((state) => state.resume?.id ?? "");
  const switchResume = useResumeStore((state) => state.switchResume);
  const createResume = useResumeStore((state) => state.createResume);
  const renameResume = useResumeStore((state) => state.renameResume);
  const deleteResume = useResumeStore((state) => state.deleteResume);

  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState("");
  const [editName, setEditName] = useState("");
  const [working, setWorking] = useState("");
  const [error, setError] = useState("");

  if (!open) return null;

  const close = () => {
    if (working) return;
    setError("");
    setEditingId("");
    setOpen(false);
  };

  const create = async () => {
    setWorking("create");
    setError("");
    try {
      await createResume(name.trim() || undefined);
      setName("");
      toast("success", "已新建简历");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setWorking("");
    }
  };

  const openResume = async (item: ResumeSummary) => {
    if (item.id === currentId) return;
    setWorking(item.id);
    setError("");
    try {
      await switchResume(item.id);
      toast("success", `已切换到「${item.name}」`);
      setOpen(false);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setWorking("");
    }
  };

  const startRename = (item: ResumeSummary) => {
    setEditingId(item.id);
    setEditName(item.name);
    setError("");
  };

  const saveRename = async (item: ResumeSummary) => {
    const next = editName.trim();
    if (!next) {
      setError("简历名称不能为空");
      return;
    }
    if (next === item.name) {
      setEditingId("");
      return;
    }
    setWorking(item.id);
    setError("");
    try {
      await renameResume(item.id, next);
      setEditingId("");
      toast("success", "已重命名");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setWorking("");
    }
  };

  const remove = async (item: ResumeSummary) => {
    if (!window.confirm(`删除「${item.name}」？该简历的聊天记录会一并清除，且无法恢复。`)) return;
    setWorking(item.id);
    setError("");
    try {
      await deleteResume(item.id);
      toast("success", "已删除简历");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setWorking("");
    }
  };

  return (
    <div className="modal-backdrop is-open" onMouseDown={(event) => event.target === event.currentTarget && close()}>
      <div className="modal library-modal" role="dialog" aria-modal="true" aria-label="简历库">
        <div className="modal-head">
          <div>
            <h3>简历库</h3>
            <p>所有简历都保存在本机，旧版本会自动留存备份，可随时切换、重命名或删除。</p>
          </div>
          <button type="button" className="icon-btn" title="关闭" onClick={close}>
            <IconClose size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div className="lib-create">
            <input
              value={name}
              placeholder="新简历名称，留空自动命名"
              maxLength={40}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing) void create();
              }}
            />
            <button type="button" className="btn btn-primary" disabled={working === "create"} onClick={() => void create()}>
              <IconPlus size={14} />
              新建简历
            </button>
          </div>

          {error ? (
            <div className="lib-error">
              <IconAlert size={13} />
              {error}
            </div>
          ) : null}

          <div className="lib-list">
            {resumes.map((item) => {
              const active = item.id === currentId;
              const editing = editingId === item.id;
              const busy = working === item.id;
              return (
                <div key={item.id} className={`lib-row${active ? " is-active" : ""}`}>
                  <div className="lib-row-main">
                    <div className="lib-row-title">
                      <strong>{item.name}</strong>
                      {active ? <em className="badge">当前编辑</em> : null}
                    </div>
                    <p>
                      {item.personName || "未填写姓名"} · {item.sectionCount} 个模块 · 更新于{" "}
                      {formatTime(item.updatedAt)}
                    </p>
                  </div>

                  {editing ? (
                    <div className="lib-row-actions">
                      <input
                        className="lib-rename"
                        value={editName}
                        maxLength={40}
                        autoFocus
                        disabled={busy}
                        onChange={(event) => setEditName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.nativeEvent.isComposing) void saveRename(item);
                          if (event.key === "Escape") setEditingId("");
                        }}
                      />
                      <button type="button" className="icon-btn" title="保存" disabled={busy} onClick={() => void saveRename(item)}>
                        <IconCheck size={14} />
                      </button>
                      <button type="button" className="icon-btn" title="取消" disabled={busy} onClick={() => setEditingId("")}>
                        <IconClose size={14} />
                      </button>
                    </div>
                  ) : (
                    <div className="lib-row-actions">
                      <button
                        type="button"
                        className="btn btn-sm"
                        disabled={active || busy}
                        onClick={() => void openResume(item)}
                      >
                        {active ? "编辑中" : "打开"}
                      </button>
                      <button type="button" className="btn btn-sm" disabled={busy} onClick={() => startRename(item)}>
                        重命名
                      </button>
                      <button
                        type="button"
                        className="icon-btn lib-delete"
                        title="删除简历"
                        disabled={busy || resumes.length <= 1}
                        onClick={() => void remove(item)}
                      >
                        <IconTrash size={14} />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <p className="lib-hint">每次修改都会自动保存，并保留最近 20 个历史快照在 data/backups 目录。</p>
        </div>
      </div>
    </div>
  );
}
