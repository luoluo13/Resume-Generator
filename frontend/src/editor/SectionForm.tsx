import { useState } from "react";
import { IconArrowDown, IconArrowUp, IconChevron, IconPlus, IconTrash } from "../icons";
import { useResumeStore } from "../store";
import type { Item, Section } from "../types";
import { toast } from "../ui";
import { BulletEditor } from "./BulletEditor";
import { AddButton, Field, TagInput, TextInput, Toggle } from "./fields";
import { createItem, entryPeriod, entrySubtitle, entryTitle, presetOf } from "./schema";

interface SectionFormProps {
  section: Section;
  index: number;
}

const ADD_LABEL: Record<Section["type"], string> = {
  education: "添加教育经历",
  experience: "添加工作经历",
  project: "添加项目经历",
  skills: "添加技能分组",
  awards: "添加荣誉奖项",
  certificate: "添加证书资质",
  custom: "添加条目"
};

export function SectionForm({ section, index }: SectionFormProps) {
  const update = useResumeStore((state) => state.update);
  const removeSection = useResumeStore((state) => state.removeSection);
  const [focusIndex, setFocusIndex] = useState<number | null>(null);

  const patchSection = (mutate: (target: Section) => void) => {
    update((resume) => {
      const target = resume.sections.find((item) => item.id === section.id);
      if (target) mutate(target);
    });
  };

  const patchItem = (itemIndex: number, patch: Partial<Item>) => {
    patchSection((target) => {
      const item = target.items[itemIndex];
      if (item) Object.assign(item, patch);
    });
  };

  const addItem = () => {
    const nextIndex = section.items.length;
    patchSection((target) => {
      target.items.push(createItem(section.type));
    });
    setFocusIndex(nextIndex);
  };

  const removeItem = (itemIndex: number) => {
    if (!window.confirm("删除后无法恢复，确定删除这条内容吗？")) return;
    patchSection((target) => {
      target.items.splice(itemIndex, 1);
    });
  };

  const moveItem = (itemIndex: number, delta: number) => {
    patchSection((target) => {
      const to = itemIndex + delta;
      if (to < 0 || to >= target.items.length) return;
      const [moved] = target.items.splice(itemIndex, 1);
      target.items.splice(to, 0, moved);
    });
  };

  const removeSelf = () => {
    if (!window.confirm(`确定删除模块「${section.title}」及其全部内容吗？`)) return;
    removeSection(section.id);
    toast("info", "模块已删除");
  };

  return (
    <>
      <div className="pane-head">
        <div className="pane-head-main">
          <p className="pane-eyebrow">SECTION {String(index + 1).padStart(2, "0")}</p>
          <input
            className="pane-title-input"
            value={section.title}
            maxLength={16}
            aria-label="模块标题"
            onChange={(event) => patchSection((target) => (target.title = event.target.value))}
          />
          <p className="pane-hint">{presetOf(section.type).hint}</p>
        </div>
        <div className="pane-actions">
          <span className="pane-count">{section.items.length} 条</span>
          <button type="button" className="icon-btn" title="删除模块" onClick={removeSelf}>
            <IconTrash size={15} />
          </button>
        </div>
      </div>

      <div className="panel is-active">
        {section.items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-mark">{String(index + 1).padStart(2, "0")}</div>
            <strong>这个模块还是空的</strong>
            <p>添加第一条内容后，右侧简历会立即出现对应模块。</p>
            <AddButton label={ADD_LABEL[section.type]} onClick={addItem} />
          </div>
        ) : (
          section.items.map((item, itemIndex) => (
            <EntryCard
              key={`${section.id}-${itemIndex}`}
              section={section}
              item={item}
              itemIndex={itemIndex}
              total={section.items.length}
              autoFocus={focusIndex === itemIndex}
              onPatch={patchItem}
              onRemove={removeItem}
              onMove={moveItem}
            />
          ))
        )}

        {section.items.length > 0 ? <AddButton label={ADD_LABEL[section.type]} onClick={addItem} /> : null}
      </div>
    </>
  );
}

interface EntryCardProps {
  section: Section;
  item: Item;
  itemIndex: number;
  total: number;
  autoFocus: boolean;
  onPatch: (index: number, patch: Partial<Item>) => void;
  onRemove: (index: number) => void;
  onMove: (index: number, delta: number) => void;
}

function EntryCard({ section, item, itemIndex, total, autoFocus, onPatch, onRemove, onMove }: EntryCardProps) {
  const [open, setOpen] = useState(itemIndex === 0 || autoFocus);
  const title = entryTitle(section.type, item);
  const subtitle = entrySubtitle(section.type, item);
  const period = entryPeriod(item);

  const patch = (value: Partial<Item>) => onPatch(itemIndex, value);
  const setHighlight = (highlightIndex: number, html: string) => {
    const next = [...item.highlights];
    next[highlightIndex] = html;
    patch({ highlights: next });
  };

  return (
    <article className={`entry-card${open ? " is-open" : ""}`}>
      <header className="entry-head" onClick={() => setOpen((value) => !value)}>
        <div className="entry-title">
          <span className="entry-co">{title}</span>
          {subtitle ? <span className="entry-role">{subtitle}</span> : null}
        </div>
        {period ? <span className="entry-period">{period}</span> : null}
        <span className="entry-toggle">
          <IconChevron size={14} />
        </span>
      </header>

      {open ? (
        <div className="entry-body">
          <ItemFields
            type={section.type}
            item={item}
            autoFocus={autoFocus}
            patch={patch}
            setHighlight={setHighlight}
          />

          <div className="entry-footer">
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              disabled={itemIndex === 0}
              onClick={() => onMove(itemIndex, -1)}
            >
              <IconArrowUp size={13} />
              上移
            </button>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              disabled={itemIndex === total - 1}
              onClick={() => onMove(itemIndex, 1)}
            >
              <IconArrowDown size={13} />
              下移
            </button>
            <button type="button" className="btn btn-sm btn-ghost entry-remove" onClick={() => onRemove(itemIndex)}>
              <IconTrash size={13} />
              删除条目
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}

interface ItemFieldsProps {
  type: Section["type"];
  item: Item;
  autoFocus: boolean;
  patch: (value: Partial<Item>) => void;
  setHighlight: (index: number, html: string) => void;
}

function ItemFields({ type, item, autoFocus, patch, setHighlight }: ItemFieldsProps) {
  if (type === "education") {
    return (
      <div className="field-grid">
        <TextInput label="学校" value={item.school} full placeholder="如：华东师范大学" autoFocus={autoFocus} onChange={(value) => patch({ school: value })} />
        <TextInput label="学历" value={item.degree} placeholder="本科 / 硕士" onChange={(value) => patch({ degree: value })} />
        <TextInput label="专业" value={item.major} placeholder="计算机科学与技术" onChange={(value) => patch({ major: value })} />
        <TextInput label="GPA / 排名" value={item.gpa} placeholder="3.8 / 4.0，专业前 10%" onChange={(value) => patch({ gpa: value })} />
        <TextInput label="主修课程" value={item.courses} placeholder="逗号分隔" onChange={(value) => patch({ courses: value })} />
        <TimeFields item={item} patch={patch} />
      </div>
    );
  }

  if (type === "experience") {
    return (
      <>
        <div className="field-grid">
          <TextInput label="公司" value={item.company} full placeholder="如：字节跳动" autoFocus={autoFocus} onChange={(value) => patch({ company: value })} />
          <TextInput label="职位" value={item.role} placeholder="后端开发工程师" onChange={(value) => patch({ role: value })} />
          <TextInput label="地点" value={item.location} placeholder="上海" onChange={(value) => patch({ location: value })} />
          <TimeFields item={item} patch={patch} />
        </div>
        <Bullets item={item} patch={patch} setHighlight={setHighlight} />
      </>
    );
  }

  if (type === "project") {
    return (
      <>
        <div className="field-grid">
          <TextInput label="项目名称" value={item.name} full placeholder="如：简历智能生成平台" autoFocus={autoFocus} onChange={(value) => patch({ name: value })} />
          <TextInput label="担任角色" value={item.role} placeholder="技术负责人" onChange={(value) => patch({ role: value })} />
          <TextInput label="项目链接" value={item.link} placeholder="https://（选填）" onChange={(value) => patch({ link: value })} />
          <TimeFields item={item} patch={patch} />
        </div>
        <div className="form-divider">技术栈</div>
        <TagInput label="使用到的技术" value={item.tech} placeholder="回车添加，如 Python" onChange={(value) => patch({ tech: value })} />
        <Bullets item={item} patch={patch} setHighlight={setHighlight} />
      </>
    );
  }

  if (type === "skills") {
    return (
      <div className="field-grid">
        <TextInput label="分组名称" value={item.group} full placeholder="如：后端 / 工程 / 语言" autoFocus={autoFocus} onChange={(value) => patch({ group: value })} />
        <TagInput label="技能标签" value={item.tags} full placeholder="回车添加，如 Python" onChange={(value) => patch({ tags: value })} />
      </div>
    );
  }

  if (type === "awards" || type === "certificate") {
    return (
      <div className="field-grid">
        <TextInput label="名称" value={item.name} full autoFocus={autoFocus} placeholder="如：年度优秀员工" onChange={(value) => patch({ name: value })} />
        <TextInput label="颁发方" value={item.issuer} placeholder="颁发机构" onChange={(value) => patch({ issuer: value })} />
        <TextInput label="获得时间" value={item.date} placeholder="2023.12" onChange={(value) => patch({ date: value })} />
      </div>
    );
  }

  return (
    <>
      <div className="field-grid">
        <TextInput label="标题" value={item.title} full autoFocus={autoFocus} placeholder="如：自我评价" onChange={(value) => patch({ title: value })} />
        <TextInput label="副标题" value={item.subtitle} full placeholder="选填" onChange={(value) => patch({ subtitle: value })} />
        <TimeFields item={item} patch={patch} />
      </div>
      <Bullets item={item} patch={patch} setHighlight={setHighlight} />
    </>
  );
}

interface TimeFieldsProps {
  item: Item;
  patch: (value: Partial<Item>) => void;
}

function TimeFields({ item, patch }: TimeFieldsProps) {
  return (
    <>
      <TextInput label="开始时间" value={item.start} placeholder="2021.07" onChange={(value) => patch({ start: value })} />
      <Field label="结束时间">
        <input
          value={item.current ? "至今" : item.end}
          placeholder="2023.10"
          disabled={item.current}
          onChange={(event) => patch({ end: event.target.value })}
        />
      </Field>
      <div className="field full">
        <Toggle label="至今（在职 / 在读）" checked={item.current} onChange={(value) => patch({ current: value })} />
      </div>
    </>
  );
}

interface BulletsProps {
  item: Item;
  patch: (value: Partial<Item>) => void;
  setHighlight: (index: number, html: string) => void;
}

function Bullets({ item, patch, setHighlight }: BulletsProps) {
  const add = () => patch({ highlights: [...item.highlights, ""] });
  const remove = (index: number) => patch({ highlights: item.highlights.filter((_, current) => current !== index) });

  return (
    <div className="bullets">
      <div className="bullets-head">
        <span>要点描述</span>
        <span className="bullets-count">{item.highlights.length} 条</span>
      </div>
      {item.highlights.map((highlight, index) => (
        <BulletEditor
          key={index}
          value={highlight}
          onChange={(html) => setHighlight(index, html)}
          onRemove={() => remove(index)}
        />
      ))}
      {item.highlights.length >= 6 ? (
        <p className="inline-note">
          <IconPlus size={13} />
          要点超过 6 条时建议精简，保留最有说服力的 2~4 条。
        </p>
      ) : null}
      <button type="button" className="add-bullet" onClick={add}>
        <IconPlus size={12} />
        添加一条要点
      </button>
    </div>
  );
}
