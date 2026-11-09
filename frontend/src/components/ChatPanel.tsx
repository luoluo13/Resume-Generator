import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { IconAlert, IconArrowUp, IconCheck, IconClose, IconPlus, IconTrash, IconWand } from "../icons";
import { useResumeStore } from "../store";
import type {
  AiProvider,
  AiSettings,
  ChatAction,
  ChatEntry,
  ChatPending,
  ChatSession,
  ChatSessionSummary
} from "../types";
import { useUiStore } from "../ui";

const PROVIDER_LABELS: Record<AiProvider, string> = {
  deepseek: "DeepSeek 官方",
  custom: "自定义供应商"
};

const QUICK_PROMPTS = [
  "帮我检查简历里有没有明显缺失的信息",
  "优化工作经历的要点描述",
  "新增一个项目经历模块",
  "把简历切换成双栏模板",
  "导出一份 PDF"
];

function toEntries(session: ChatSession): ChatEntry[] {
  return session.messages.map((message) => ({
    id: message.id,
    role: message.role,
    content: message.content,
    actions: message.actions
  }));
}

function toSummary(session: ChatSession): ChatSessionSummary {
  return {
    id: session.id,
    title: session.title,
    resumeId: session.resumeId,
    createdAt: session.createdAt,
    updatedAt: session.updatedAt,
    messageCount: session.messages.length,
    preview: ""
  };
}

export function ChatPanel() {
  const open = useUiStore((state) => state.chatOpen);
  const setOpen = useUiStore((state) => state.setChatOpen);
  const replaceResume = useResumeStore((state) => state.replaceResume);
  const resumes = useResumeStore((state) => state.resumes);
  const resumeId = useResumeStore((state) => state.resume?.id ?? "");
  const resumeName = useResumeStore((state) => state.resumeName);
  const switchResume = useResumeStore((state) => state.switchResume);
  const loadResumes = useResumeStore((state) => state.loadResumes);

  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [provider, setProvider] = useState<AiProvider>("deepseek");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com/v1");
  const [model, setModel] = useState("deepseek-chat");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [pending, setPending] = useState<ChatPending[]>([]);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [resolving, setResolving] = useState("");
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || settings) return;
    void (async () => {
      try {
        const data = await api.getAiSettings();
        setSettings(data);
        applyForm(data);
        if (!data.hasKey) setConfigOpen(true);
      } catch (error) {
        setFeedback((error as Error).message);
        setConfigOpen(true);
      }
    })();
  }, [open, settings]);

  useEffect(() => {
    if (!open) return;
    void loadResumes().catch(() => undefined);
  }, [open, loadResumes]);

  useEffect(() => {
    if (!open || !resumeId) return;
    let cancelled = false;
    void (async () => {
      setLoadingSession(true);
      try {
        const list = await api.getChatSessions(resumeId);
        if (cancelled) return;
        if (list.items.length) {
          setSessions(list.items);
          const target = await api.getChatSession(list.items[0].id);
          if (cancelled) return;
          applySession(target);
          return;
        }
        const created = await api.createChatSession(resumeId);
        if (cancelled) return;
        setSessions([toSummary(created)]);
        applySession(created);
      } catch (error) {
        if (!cancelled) setFeedback((error as Error).message);
      } finally {
        if (!cancelled) setLoadingSession(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, resumeId]);

  useEffect(() => {
    const body = bodyRef.current;
    if (body) body.scrollTop = body.scrollHeight;
  }, [entries, pending, busy]);

  function applyForm(data: AiSettings) {
    setProvider(data.provider);
    setBaseUrl(data.baseUrl);
    setModel(data.model);
    setApiKey("");
  }

  function applySession(session: ChatSession) {
    setSessionId(session.id);
    setEntries(toEntries(session));
    setPending([]);
  }

  function reportError(message: string) {
    setEntries((items) => [...items, { id: `local-${Date.now()}`, role: "assistant", content: message }]);
  }

  async function refreshSessions(targetResume = resumeId) {
    if (!targetResume) return;
    try {
      const list = await api.getChatSessions(targetResume);
      setSessions(list.items);
    } catch {
      /* 会话列表刷新失败不影响当前对话 */
    }
  }

  async function openSession(id: string) {
    if (!id || id === sessionId || busy) return;
    setLoadingSession(true);
    try {
      const session = await api.getChatSession(id);
      applySession(session);
    } catch (error) {
      setFeedback((error as Error).message);
    } finally {
      setLoadingSession(false);
    }
  }

  async function createSession() {
    if (!resumeId || busy) return;
    try {
      const created = await api.createChatSession(resumeId);
      setSessions((items) => [toSummary(created), ...items]);
      applySession(created);
    } catch (error) {
      setFeedback((error as Error).message);
    }
  }

  async function removeSession() {
    if (!sessionId || !resumeId || busy) return;
    if (!window.confirm("删除当前会话？该会话的聊天记录将无法恢复。")) return;
    try {
      await api.deleteChatSession(sessionId);
      const list = await api.getChatSessions(resumeId);
      if (list.items.length) {
        setSessions(list.items);
        const target = await api.getChatSession(list.items[0].id);
        applySession(target);
      } else {
        const created = await api.createChatSession(resumeId);
        setSessions([toSummary(created)]);
        applySession(created);
      }
    } catch (error) {
      setFeedback((error as Error).message);
    }
  }

  async function changeResume(id: string) {
    if (!id || id === resumeId || switching) return;
    setSwitching(true);
    setFeedback("");
    try {
      await switchResume(id);
    } catch (error) {
      setFeedback((error as Error).message);
    } finally {
      setSwitching(false);
    }
  }

  if (!open) return null;

  const configured = Boolean(settings?.hasKey);

  const payload = () => ({
    provider,
    baseUrl: provider === "custom" ? baseUrl.trim() : undefined,
    model: model.trim() || undefined,
    apiKey: apiKey.trim() || undefined
  });

  const persist = async () => {
    setSaving(true);
    setFeedback("");
    try {
      const next = await api.updateAiSettings(payload());
      setSettings(next);
      applyForm(next);
      setConfigOpen(false);
      setFeedback("");
    } catch (error) {
      setFeedback((error as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    setFeedback("");
    try {
      const result = await api.testAi(payload());
      setFeedback(result.message);
    } catch (error) {
      setFeedback((error as Error).message);
    } finally {
      setTesting(false);
    }
  };

  const send = async (value?: string) => {
    const content = (value ?? input).trim();
    if (!content || busy) return;
    if (!configured) {
      setConfigOpen(true);
      setFeedback("请先填写并保存 API Key");
      return;
    }
    if (!sessionId) {
      setFeedback("会话尚未就绪，请稍后重试");
      return;
    }
    const activeSession = sessionId;
    setInput("");
    setEntries((items) => [...items, { id: `local-${Date.now()}`, role: "user", content }]);
    setBusy(true);
    try {
      const result = await api.chat(activeSession, content);
      if (result.session) {
        setEntries(toEntries(result.session));
        setPending(result.pending);
      } else {
        reportError(result.reply);
      }
      if (result.resume && result.resumeId === useResumeStore.getState().resume?.id) {
        replaceResume(result.resume);
      }
      void refreshSessions();
      void loadResumes().catch(() => undefined);
    } catch (error) {
      reportError(`请求失败：${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const resolve = async (item: ChatPending, approve: boolean) => {
    setResolving(item.id);
    try {
      const result = await api.confirmChat(item.id, approve, sessionId || undefined);
      if (result.session) setEntries(toEntries(result.session));
      else reportError(result.message);
      if (result.resume && result.resumeId === useResumeStore.getState().resume?.id) {
        replaceResume(result.resume);
      }
      setPending((items) => items.filter((entry) => entry.id !== item.id));
    } catch (error) {
      reportError(`操作失败：${(error as Error).message}`);
    } finally {
      setResolving("");
    }
  };

  const changeProvider = (next: AiProvider) => {
    setProvider(next);
    setFeedback("");
    if (next === "deepseek") {
      if (!(settings?.models ?? ["deepseek-chat"]).includes(model)) setModel("deepseek-chat");
      setBaseUrl("https://api.deepseek.com/v1");
    } else if (baseUrl === "https://api.deepseek.com/v1") {
      setBaseUrl("");
      setModel("");
    }
  };

  const modelLabel = settings ? `${PROVIDER_LABELS[settings.provider]} · ${settings.model}` : "未配置";
  const scopeLocked = switching || busy || loadingSession;

  return (
    <aside className="chat-panel">
      <header className="chat-head">
        <span className="chat-seal">
          <IconWand size={16} />
        </span>
        <div className="chat-head-text">
          <h3>AI 简历助手</h3>
          <p>{modelLabel}</p>
        </div>
        <button
          type="button"
          className="chat-config-toggle"
          onClick={() => {
            setConfigOpen((value) => !value);
            setFeedback("");
          }}
        >
          设置
        </button>
        <button type="button" className="icon-btn" title="收起" onClick={() => setOpen(false)}>
          <IconClose size={15} />
        </button>
      </header>

      <div className="chat-scope">
        <label className="chat-scope-item">
          <span>操作简历</span>
          <select value={resumeId} disabled={scopeLocked} onChange={(event) => void changeResume(event.target.value)}>
            {resumes.length === 0 ? <option value={resumeId}>{resumeName || "加载中…"}</option> : null}
            {resumes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <div className="chat-scope-row">
          <label className="chat-scope-item is-grow">
            <span>会话</span>
            <select value={sessionId} disabled={scopeLocked} onChange={(event) => void openSession(event.target.value)}>
              {sessions.length === 0 ? <option value="">暂无会话</option> : null}
              {sessions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}（{item.messageCount}）
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="icon-btn" title="新建会话" disabled={scopeLocked} onClick={() => void createSession()}>
            <IconPlus size={14} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="删除当前会话"
            disabled={scopeLocked || !sessionId}
            onClick={() => void removeSession()}
          >
            <IconTrash size={14} />
          </button>
        </div>
        <p className="chat-scope-hint">
          所有修改只会写入「{resumeName || "当前简历"}」，其他简历仅可只读参考。
        </p>
      </div>

      {configOpen ? (
        <section className="chat-config">
          <div className="chat-field">
            <span>供应商</span>
            <div className="segmented">
              {(Object.keys(PROVIDER_LABELS) as AiProvider[]).map((item) => (
                <button
                  type="button"
                  key={item}
                  className={provider === item ? "is-active" : ""}
                  onClick={() => changeProvider(item)}
                >
                  {PROVIDER_LABELS[item]}
                </button>
              ))}
            </div>
          </div>

          {provider === "deepseek" ? (
            <div className="chat-field">
              <span>模型</span>
              <div className="segmented">
                {(settings?.models ?? ["deepseek-chat", "deepseek-reasoner"]).map((item) => (
                  <button
                    type="button"
                    key={item}
                    className={model === item ? "is-active" : ""}
                    onClick={() => setModel(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <label className="chat-field">
                <span>接口地址</span>
                <input
                  value={baseUrl}
                  placeholder="https://api.example.com/v1"
                  onChange={(event) => setBaseUrl(event.target.value)}
                />
              </label>
              <label className="chat-field">
                <span>模型名称</span>
                <input value={model} placeholder="模型 ID" onChange={(event) => setModel(event.target.value)} />
              </label>
            </>
          )}

          <label className="chat-field">
            <span>API Key</span>
            <input
              type="password"
              value={apiKey}
              placeholder={settings?.hasKey ? `已保存 ${settings.keyHint}，留空表示不修改` : "sk-..."}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </label>

          <div className="chat-config-actions">
            <button type="button" className="btn btn-sm" disabled={testing} onClick={() => void test()}>
              {testing ? "测试中…" : "测试连接"}
            </button>
            <button type="button" className="btn btn-sm btn-primary" disabled={saving} onClick={() => void persist()}>
              {saving ? "保存中…" : "保存设置"}
            </button>
          </div>
          {feedback ? <p className="chat-feedback">{feedback}</p> : null}
          <p className="chat-hint">API Key 只保存在本机 data/settings.json，不会上传到其他服务。</p>
        </section>
      ) : null}

      <div className="chat-body" ref={bodyRef}>
        {loadingSession ? <p className="chat-loading">正在加载会话…</p> : null}

        {!loadingSession && entries.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-seal">AI</div>
            <strong>直接对话，就能改简历</strong>
            <p>当前操作「{resumeName || "当前简历"}」，增删改模块与条目、调整模板排版、导出文件，都可以在对话里完成。</p>
            <div className="chat-prompts">
              {QUICK_PROMPTS.map((prompt) => (
                <button type="button" key={prompt} onClick={() => void send(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {entries.map((entry) => (
          <div key={entry.id} className={`chat-msg is-${entry.role}`}>
            <div className="chat-bubble">{entry.content}</div>
            {entry.actions?.length ? <ActionChips actions={entry.actions} /> : null}
          </div>
        ))}

        {busy ? (
          <div className="chat-msg is-assistant">
            <div className="chat-bubble is-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        ) : null}

        {pending.map((item) => (
          <div className="chat-confirm" key={item.id}>
            <div className="chat-confirm-head">
              <IconAlert size={13} />
              <strong>{item.title}</strong>
            </div>
            <p>{item.summary}</p>
            <div className="chat-confirm-actions">
              <button
                type="button"
                className="btn btn-sm"
                disabled={resolving === item.id}
                onClick={() => void resolve(item, false)}
              >
                取消
              </button>
              <button
                type="button"
                className="btn btn-sm btn-danger"
                disabled={resolving === item.id}
                onClick={() => void resolve(item, true)}
              >
                确认执行
              </button>
            </div>
          </div>
        ))}
      </div>

      <footer className="chat-foot">
        <textarea
          value={input}
          rows={2}
          placeholder={configured ? "描述你想怎么改简历，Enter 发送" : "请先在上方配置 API Key"}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              void send();
            }
          }}
        />
        <button
          type="button"
          className="chat-send"
          title="发送"
          disabled={busy || !input.trim() || !sessionId}
          onClick={() => void send()}
        >
          <IconArrowUp size={16} />
        </button>
      </footer>
    </aside>
  );
}

function ActionChips({ actions }: { actions: ChatAction[] }) {
  return (
    <div className="chat-actions">
      {actions.map((action, index) => (
        <span className="chat-action" key={`${action.tool}-${index}`}>
          <IconCheck size={11} />
          {action.label}
          {action.detail ? <em>· {action.detail}</em> : null}
        </span>
      ))}
    </div>
  );
}
