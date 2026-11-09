import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ChangeEvent, DragEvent } from "react";
import { api } from "../api";
import {
  IconAlert,
  IconArrowDown,
  IconArrowUp,
  IconCheck,
  IconClose,
  IconPlus,
  IconTrash,
  IconUpload,
  IconWand
} from "../icons";
import { useResumeStore } from "../store";
import { toast, useUiStore } from "../ui";
import type { ImportBasics, ImportDraft, ImportItem, ImportSection, SectionType, Theme } from "../types";

const STEPS = ["上传文件", "识别校对", "样式选择", "确认导入"];

const TYPE_OPTIONS: { value: SectionType; label: string }[] = [
  { value: "education", label: "教育背景" },
  { value: "experience", label: "工作经历" },
  { value: "project", label: "项目经历" },
  { value: "skills", label: "专业技能" },
  { value: "awards", label: "荣誉奖项" },
  { value: "certificate", label: "证书资质" },
  { value: "custom", label: "自定义模块" }
];

const FIELD_LABELS: Record<SectionType, { headline: string; meta: string }> = {
  education: { headline: "学校", meta: "学历 / 专业" },
  experience: { headline: "公司", meta: "职位" },
  project: { headline: "项目名称", meta: "角色" },
  skills: { headline: "分组", meta: "" },
  awards: { headline: "奖项名称", meta: "颁发机构" },
  certificate: { headline: "证书名称", meta: "颁发机构" },
  custom: { headline: "标题", meta: "补充说明" }
};

const BASIC_FIELDS: { key: keyof ImportBasics; label: string; placeholder: string }[] = [
  { key: "name", label: "姓名", placeholder: "你的姓名" },
  { key: "jobIntention", label: "求职意向", placeholder: "如：后端开发工程师" },
  { key: "phone", label: "电话", placeholder: "手机或座机" },
  { key: "email", label: "邮箱", placeholder: "name@example.com" },
  { key: "city", label: "城市", placeholder: "如：上海" },
  { key: "yearsOfExperience", label: "工作经验", placeholder: "如：3年" },
  { key: "available", label: "到岗时间", placeholder: "如：一个月内" }
];

const ACCENTS = ["#bf4a2e", "#1f4e5f", "#2f6b4f", "#8a5a2b", "#5b4b8a", "#1b1a17"];

function emptyItem(): ImportItem {
  return { headline: "", meta: "", period: "", bullets: [], tags: [] };
}

function parseTags(value: string): string[] {
  return value
    .split(/[、,，;；/|]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function patchSectionList(sections: ImportSection[], index: number, patch: Partial<ImportSection>): ImportSection[] {
  return sections.map((section, current) => (current === index ? { ...section, ...patch } : section));
}

export function ImportWizard() {
  const open = useUiStore((state) => state.importOpen);
  const setOpen = useUiStore((state) => state.setImportOpen);
  const templates = useResumeStore((state) => state.templates);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<ImportDraft | null>(null);
  const [theme, setTheme] = useState<Theme | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [tagDrafts, setTagDrafts] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setStep(0);
    setDraft(null);
    setTheme(null);
    setBusy(false);
    setError("");
    setDragging(false);
    setTagDrafts({});
  }, [open]);

  if (!open) return null;

  const manifest = templates.find((item) => item.id === theme?.template) ?? templates[0];
  const sectionCount = draft?.sections.filter((section) => section.items.length > 0).length ?? 0;
  const itemCount = draft?.sections.reduce((total, section) => total + section.items.length, 0) ?? 0;
  const canNext = step === 0 ? Boolean(draft) : step === 1 ? sectionCount > 0 : true;

  const analyze = async (file: File) => {
    if (!/\.(docx?|pdf)$/i.test(file.name)) {
      setError("仅支持 DOC、DOCX、PDF 三种格式。");
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      setError("文件超过 12MB，请压缩后再试。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api.analyzeImport(file);
      setDraft(result);
      setTheme(result.style.theme);
      setTagDrafts({});
      setStep(1);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) void analyze(file);
    event.target.value = "";
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) void analyze(file);
  };

  const patchBasics = (key: keyof ImportBasics, value: string) => {
    setDraft((current) => (current ? { ...current, basics: { ...current.basics, [key]: value } } : current));
  };

  const patchSection = (index: number, patch: Partial<ImportSection>) => {
    setDraft((current) =>
      current ? { ...current, sections: patchSectionList(current.sections, index, patch) } : current
    );
  };

  const patchItem = (sectionIndex: number, itemIndex: number, patch: Partial<ImportItem>) => {
    setDraft((current) => {
      if (!current) return current;
      const sections = current.sections.map((section, currentSection) =>
        currentSection === sectionIndex
          ? {
              ...section,
              items: section.items.map((item, currentItem) =>
                currentItem === itemIndex ? { ...item, ...patch } : item
              )
            }
          : section
      );
      return { ...current, sections };
    });
  };

  const addItem = (sectionIndex: number) => {
    setDraft((current) => {
      if (!current) return current;
      const section = current.sections[sectionIndex];
      if (!section) return current;
      return {
        ...current,
        sections: patchSectionList(current.sections, sectionIndex, { items: [...section.items, emptyItem()] })
      };
    });
  };

  const removeItem = (sectionIndex: number, itemIndex: number) => {
    setTagDrafts({});
    setDraft((current) => {
      if (!current) return current;
      const section = current.sections[sectionIndex];
      if (!section) return current;
      return {
        ...current,
        sections: patchSectionList(current.sections, sectionIndex, {
          items: section.items.filter((_, currentItem) => currentItem !== itemIndex)
        })
      };
    });
  };

  const addBullet = (sectionIndex: number, itemIndex: number) => {
    const item = draft?.sections[sectionIndex]?.items[itemIndex];
    if (!item) return;
    patchItem(sectionIndex, itemIndex, { bullets: [...item.bullets, ""] });
  };

  const patchBullet = (sectionIndex: number, itemIndex: number, bulletIndex: number, value: string) => {
    const item = draft?.sections[sectionIndex]?.items[itemIndex];
    if (!item) return;
    patchItem(sectionIndex, itemIndex, {
      bullets: item.bullets.map((bullet, current) => (current === bulletIndex ? value : bullet))
    });
  };

  const removeBullet = (sectionIndex: number, itemIndex: number, bulletIndex: number) => {
    const item = draft?.sections[sectionIndex]?.items[itemIndex];
    if (!item) return;
    patchItem(sectionIndex, itemIndex, {
      bullets: item.bullets.filter((_, current) => current !== bulletIndex)
    });
  };

  const moveSection = (index: number, direction: -1 | 1) => {
    setTagDrafts({});
    setDraft((current) => {
      if (!current) return current;
      const target = index + direction;
      if (target < 0 || target >= current.sections.length) return current;
      const sections = [...current.sections];
      const [moved] = sections.splice(index, 1);
      sections.splice(target, 0, moved);
      return { ...current, sections };
    });
  };

  const removeSection = (index: number) => {
    setTagDrafts({});
    setDraft((current) => {
      if (!current) return current;
      if (current.sections.length <= 1) {
        toast("warning", "至少保留一个模块");
        return current;
      }
      return { ...current, sections: current.sections.filter((_, currentIndex) => currentIndex !== index) };
    });
  };

  const addSection = () => {
    setDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        sections: [
          ...current.sections,
          {
            id: `manual-${Date.now()}`,
            title: "其他信息",
            type: "custom",
            confidence: 1,
            items: [emptyItem()]
          }
        ]
      };
    });
  };

  const chooseTemplate = (templateId: string) => {
    const target = templates.find((item) => item.id === templateId);
    setTheme((current) => {
      if (!current) return current;
      const columns = target?.supports.columns ?? [1];
      const dividers = target?.supports.divider ?? ["line"];
      return {
        ...current,
        template: templateId,
        variants: {},
        columns: columns.includes(current.columns) ? current.columns : columns[0],
        photoPosition: target?.supports.photo ? current.photoPosition : "none",
        dividerStyle: dividers.includes(current.dividerStyle)
          ? current.dividerStyle
          : (dividers[0] as Theme["dividerStyle"])
      };
    });
  };

  const patchTheme = (patch: Partial<Theme>) => {
    setTheme((current) => (current ? { ...current, ...patch } : current));
  };

  const apply = async () => {
    if (!draft || !theme) return;
    const sections = draft.sections.filter((section) => section.items.length > 0);
    if (!sections.length) {
      toast("warning", "至少保留一个带内容的模块");
      setStep(1);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await useResumeStore.getState().saveNow();
      await api.applyImport({ basics: draft.basics, sections, theme, sourceName: draft.file.name });
      await useResumeStore.getState().load();
      useUiStore.getState().setView("editor");
      useUiStore.getState().setActiveSection("basics");
      setOpen(false);
      toast("success", "导入完成，原简历已自动备份");
    } catch (err) {
      setError((err as Error).message);
      toast("error", `导入失败：${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const footerNote =
    step === 0
      ? "文件仅在本机解析，不会上传"
      : step === 1
        ? `${sectionCount} 个模块 · ${itemCount} 条内容`
        : step === 2
          ? "换模板不会改变文字内容"
          : "导入前会自动备份当前简历";

  return (
    <div
      className="modal-backdrop iw-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && !busy && setOpen(false)}
    >
      <div className="modal iw-modal" role="dialog" aria-modal="true" aria-label="导入已有简历">
        <header className="modal-head">
          <div>
            <h3>导入已有简历</h3>
            <p>保留全部文字内容，按新模板重新排版；支持 DOC / DOCX / PDF</p>
          </div>
          <button type="button" className="icon-btn" aria-label="关闭" onClick={() => setOpen(false)} disabled={busy}>
            <IconClose size={16} />
          </button>
        </header>

        <ol className="iw-steps">
          {STEPS.map((label, index) => (
            <li
              key={label}
              className={index === step ? "is-active" : index < step ? "is-done" : ""}
              aria-current={index === step ? "step" : undefined}
            >
              <span>{index < step ? <IconCheck size={11} /> : index + 1}</span>
              {label}
            </li>
          ))}
        </ol>

        <div className="iw-body">
          {error ? (
            <div className="notice iw-error">
              <IconAlert size={14} />
              <div>{error}</div>
            </div>
          ) : null}

          {step === 0 ? (
            <>
              <div
                className={`iw-drop${dragging ? " is-drag" : ""}${busy ? " is-busy" : ""}`}
                onClick={() => !busy && fileRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") fileRef.current?.click();
                }}
              >
                <span className="iw-drop-icon">{busy ? <span className="spinner dark" /> : <IconUpload size={24} />}</span>
                <strong>{busy ? "正在解析文件…" : "拖入简历文件，或点击选择"}</strong>
                <span>{busy ? "正在识别模块、条目和基本信息" : "单个文件不超过 12MB，解析只在本机进行"}</span>
                <span className="iw-drop-types">
                  <em>DOC</em>
                  <em>DOCX</em>
                  <em>PDF</em>
                </span>
              </div>
              <p className="iw-hint">
                会尽量保留全部文字内容，并推荐一套接近原稿气质的模板。扫描件、图片型 PDF 无法识别文字，需要先转换为可复制的文本。
              </p>
            </>
          ) : null}

          {step === 1 && draft ? (
            <>
              {draft.warnings.length ? (
                <div className="notice">
                  <IconAlert size={14} />
                  <div>
                    <strong>识别提示</strong>
                    <ul className="iw-warn-list">
                      {draft.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : null}

              <section className="iw-card">
                <header className="iw-card-head">
                  <h4>基本信息</h4>
                  <span>识别结果可以直接修改</span>
                </header>
                <div className="iw-basics">
                  {BASIC_FIELDS.map((field) => (
                    <label className="iw-field" key={field.key}>
                      <span>{field.label}</span>
                      <input
                        value={draft.basics[field.key]}
                        placeholder={field.placeholder}
                        onChange={(event) => patchBasics(field.key, event.target.value)}
                      />
                    </label>
                  ))}
                </div>
              </section>

              <div className="iw-section-title">
                <h4>模块与条目</h4>
                <span>模块顺序就是简历中的显示顺序</span>
              </div>

              <div className="iw-sec-list">
                {draft.sections.map((section, sectionIndex) => {
                  const labels = FIELD_LABELS[section.type];
                  return (
                    <section className="iw-card iw-sec" key={section.id}>
                      <header className="iw-sec-head">
                        <input
                          className="iw-sec-title"
                          value={section.title}
                          maxLength={20}
                          aria-label="模块标题"
                          onChange={(event) => patchSection(sectionIndex, { title: event.target.value })}
                        />
                        <select
                          className="iw-select"
                          value={section.type}
                          aria-label="模块类型"
                          onChange={(event) =>
                            patchSection(sectionIndex, { type: event.target.value as SectionType })
                          }
                        >
                          {TYPE_OPTIONS.map((option) => (
                            <option value={option.value} key={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <span className={`iw-conf${section.confidence < 0.7 ? " is-low" : ""}`}>
                          识别度 {Math.round(section.confidence * 100)}%
                        </span>
                        <div className="iw-sec-actions">
                          <button
                            type="button"
                            className="icon-btn"
                            title="上移"
                            aria-label="上移模块"
                            disabled={sectionIndex === 0}
                            onClick={() => moveSection(sectionIndex, -1)}
                          >
                            <IconArrowUp size={13} />
                          </button>
                          <button
                            type="button"
                            className="icon-btn"
                            title="下移"
                            aria-label="下移模块"
                            disabled={sectionIndex === draft.sections.length - 1}
                            onClick={() => moveSection(sectionIndex, 1)}
                          >
                            <IconArrowDown size={13} />
                          </button>
                          <button
                            type="button"
                            className="icon-btn is-danger"
                            title="删除模块"
                            aria-label="删除模块"
                            onClick={() => removeSection(sectionIndex)}
                          >
                            <IconTrash size={13} />
                          </button>
                        </div>
                      </header>

                      <div className="iw-items">
                        {section.items.map((item, itemIndex) => (
                          <div className="iw-item" key={`${section.id}-${itemIndex}`}>
                            {section.type === "skills" ? (
                              <div className="iw-item-grid is-skills">
                                <label className="iw-field">
                                  <span>{labels.headline}</span>
                                  <input
                                    value={item.headline}
                                    placeholder="如：编程语言"
                                    onChange={(event) =>
                                      patchItem(sectionIndex, itemIndex, { headline: event.target.value })
                                    }
                                  />
                                </label>
                                <label className="iw-field">
                                  <span>技能标签（用顿号或逗号分隔）</span>
                                  <input
                                    value={
                                      tagDrafts[`${section.id}-${itemIndex}`] ?? item.tags.join("、")
                                    }
                                    placeholder="Python、Java、Go"
                                    onChange={(event) => {
                                      const value = event.target.value;
                                      setTagDrafts((current) => ({
                                        ...current,
                                        [`${section.id}-${itemIndex}`]: value
                                      }));
                                      patchItem(sectionIndex, itemIndex, { tags: parseTags(value) });
                                    }}
                                  />
                                </label>
                              </div>
                            ) : (
                              <div className="iw-item-grid">
                                <label className="iw-field">
                                  <span>{labels.headline}</span>
                                  <input
                                    value={item.headline}
                                    onChange={(event) =>
                                      patchItem(sectionIndex, itemIndex, { headline: event.target.value })
                                    }
                                  />
                                </label>
                                <label className="iw-field">
                                  <span>{labels.meta}</span>
                                  <input
                                    value={item.meta}
                                    onChange={(event) =>
                                      patchItem(sectionIndex, itemIndex, { meta: event.target.value })
                                    }
                                  />
                                </label>
                                <label className="iw-field">
                                  <span>时间</span>
                                  <input
                                    value={item.period}
                                    placeholder="2021.07 - 2023.10"
                                    onChange={(event) =>
                                      patchItem(sectionIndex, itemIndex, { period: event.target.value })
                                    }
                                  />
                                </label>
                              </div>
                            )}

                            {section.type !== "skills" ? (
                              <div className="iw-bullets">
                                <span className="iw-bullet-label">内容要点</span>
                                {item.bullets.map((bullet, bulletIndex) => (
                                  <div className="iw-bullet-row" key={`${itemIndex}-${bulletIndex}`}>
                                    <textarea
                                      value={bullet}
                                      rows={Math.min(4, Math.max(1, Math.ceil(bullet.length / 46)))}
                                      onChange={(event) =>
                                        patchBullet(sectionIndex, itemIndex, bulletIndex, event.target.value)
                                      }
                                    />
                                    <button
                                      type="button"
                                      className="icon-btn"
                                      aria-label="删除这一行"
                                      onClick={() => removeBullet(sectionIndex, itemIndex, bulletIndex)}
                                    >
                                      <IconClose size={12} />
                                    </button>
                                  </div>
                                ))}
                                <button
                                  type="button"
                                  className="iw-add-line"
                                  onClick={() => addBullet(sectionIndex, itemIndex)}
                                >
                                  <IconPlus size={12} /> 添加一行
                                </button>
                              </div>
                            ) : null}

                            <button
                              type="button"
                              className="iw-remove-item"
                              onClick={() => removeItem(sectionIndex, itemIndex)}
                            >
                              <IconTrash size={12} /> 删除条目
                            </button>
                          </div>
                        ))}

                        <button type="button" className="iw-add-item" onClick={() => addItem(sectionIndex)}>
                          <IconPlus size={13} /> 添加条目
                        </button>
                      </div>
                    </section>
                  );
                })}
              </div>

              <button type="button" className="iw-add-section" onClick={addSection}>
                <IconPlus size={14} /> 添加模块
              </button>
            </>
          ) : null}

          {step === 2 && theme ? (
            <>
              <div className="notice iw-reason">
                <IconWand size={14} />
                <div>{draft?.style.reason ?? "选择一套模板，内容会按新样式重新排版。"}</div>
              </div>

              <div className="iw-tpl-grid">
                {templates.map((template) => {
                  const selected = theme.template === template.id;
                  const recommended = draft?.style.template === template.id;
                  return (
                    <button
                      type="button"
                      key={template.id}
                      className={`iw-tpl${selected ? " is-active" : ""}`}
                      onClick={() => chooseTemplate(template.id)}
                    >
                      <span
                        className="iw-tpl-preview"
                        style={{ "--iw-tint": template.color } as CSSProperties}
                        aria-hidden="true"
                      >
                        <i className="iw-tpl-head" />
                        <i className="iw-tpl-rule" />
                        <i className="iw-tpl-line" />
                        <i className="iw-tpl-line is-short" />
                        <i className="iw-tpl-rule" />
                        <i className="iw-tpl-line" />
                        <i className="iw-tpl-line is-short" />
                      </span>
                      <span className="iw-tpl-info">
                        <span className="iw-tpl-name">
                          {template.name}
                          {recommended ? <em>推荐</em> : null}
                        </span>
                        <span className="iw-tpl-desc">{template.description}</span>
                      </span>
                      {selected ? (
                        <span className="iw-tpl-check">
                          <IconCheck size={12} />
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <div className="iw-theme-panel">
                <div className="iw-control">
                  <span>强调色</span>
                  <div className="iw-swatches">
                    {ACCENTS.map((color) => (
                      <button
                        type="button"
                        key={color}
                        className={`iw-swatch${theme.accent.toLowerCase() === color ? " is-active" : ""}`}
                        style={{ background: color }}
                        aria-label={`使用强调色 ${color}`}
                        onClick={() => patchTheme({ accent: color })}
                      />
                    ))}
                    <input
                      type="color"
                      className="iw-color"
                      value={theme.accent}
                      aria-label="自定义强调色"
                      onChange={(event) => patchTheme({ accent: event.target.value })}
                    />
                  </div>
                </div>

                <div className="iw-control">
                  <span>字体</span>
                  <div className="segmented">
                    <button
                      type="button"
                      className={theme.fontFamily === "SourceHanSansSC" ? "is-active" : ""}
                      onClick={() => patchTheme({ fontFamily: "SourceHanSansSC" })}
                    >
                      黑体
                    </button>
                    <button
                      type="button"
                      className={theme.fontFamily === "SourceHanSerifSC" ? "is-active" : ""}
                      onClick={() => patchTheme({ fontFamily: "SourceHanSerifSC" })}
                    >
                      宋体
                    </button>
                  </div>
                </div>

                <div className="iw-control">
                  <span>行距</span>
                  <div className="segmented">
                    <button
                      type="button"
                      className={theme.density === "loose" ? "is-active" : ""}
                      onClick={() => patchTheme({ density: "loose" })}
                    >
                      宽松
                    </button>
                    <button
                      type="button"
                      className={theme.density === "normal" ? "is-active" : ""}
                      onClick={() => patchTheme({ density: "normal" })}
                    >
                      标准
                    </button>
                    <button
                      type="button"
                      className={theme.density === "compact" ? "is-active" : ""}
                      onClick={() => patchTheme({ density: "compact" })}
                    >
                      紧凑
                    </button>
                  </div>
                </div>

                {manifest && manifest.supports.columns.length > 1 ? (
                  <div className="iw-control">
                    <span>版式</span>
                    <div className="segmented">
                      <button
                        type="button"
                        className={theme.columns === 1 ? "is-active" : ""}
                        onClick={() => patchTheme({ columns: 1 })}
                      >
                        单栏
                      </button>
                      <button
                        type="button"
                        className={theme.columns === 2 ? "is-active" : ""}
                        onClick={() => patchTheme({ columns: 2 })}
                      >
                        双栏
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
              <p className="iw-hint">导入后仍可在「主题」抽屉里继续微调字号、页边距、照片位置等细节。</p>
            </>
          ) : null}

          {step === 3 && draft && theme ? (
            <>
              <div className="iw-summary">
                <div>
                  <span>文件</span>
                  <strong>{draft.file.name}</strong>
                </div>
                <div>
                  <span>格式</span>
                  <strong>{draft.file.kind.toUpperCase()}</strong>
                </div>
                <div>
                  <span>模块</span>
                  <strong>
                    {sectionCount} 个 / {itemCount} 条
                  </strong>
                </div>
                <div>
                  <span>模板</span>
                  <strong>{manifest?.name ?? theme.template}</strong>
                </div>
                <div>
                  <span>保留文字</span>
                  <strong>{draft.stats.characters} 字</strong>
                </div>
                <div>
                  <span>姓名</span>
                  <strong>{draft.basics.name || "未填写"}</strong>
                </div>
              </div>

              {draft.warnings.length ? (
                <div className="notice">
                  <IconAlert size={14} />
                  <div>
                    <strong>导入前请留意</strong>
                    <ul className="iw-warn-list">
                      {draft.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : null}

              <div className="iw-confirm-note">
                <IconAlert size={14} />
                <div>
                  导入会替换当前简历内容。替换前会自动备份到 <code>data/backups</code>，需要时可以从「数据 → 导入 JSON
                  数据」恢复旧版本。
                </div>
              </div>
              <p className="iw-hint">确认后会直接进入编辑器，可以继续修改文字、调整模块顺序或更换模板。</p>
            </>
          ) : null}
        </div>

        <footer className="iw-foot">
          <span className="iw-foot-note">{footerNote}</span>
          <div className="iw-foot-actions">
            <button type="button" className="btn" onClick={() => setOpen(false)} disabled={busy}>
              取消
            </button>
            {step > 0 ? (
              <button type="button" className="btn" onClick={() => setStep((value) => Math.max(0, value - 1))} disabled={busy}>
                上一步
              </button>
            ) : null}
            {step < 3 ? (
              <button
                type="button"
                className="btn btn-primary"
                disabled={!canNext || busy}
                onClick={() => setStep((value) => Math.min(3, value + 1))}
              >
                {step === 0 ? "下一步" : "继续"}
              </button>
            ) : (
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void apply()}>
                {busy ? <span className="spinner" /> : "导入并开始编辑"}
              </button>
            )}
          </div>
        </footer>

        <input
          ref={fileRef}
          type="file"
          accept=".doc,.docx,.pdf,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          hidden
          onChange={onFileChange}
        />
      </div>
    </div>
  );
}
