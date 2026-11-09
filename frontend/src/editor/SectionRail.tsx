import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  IconAward,
  IconBriefcase,
  IconChevron,
  IconGraduation,
  IconGrip,
  IconLayers,
  IconPen,
  IconPlus,
  IconStar,
  IconTrash,
  IconUser,
  IconWand
} from "../icons";
import { useResumeStore } from "../store";
import type { Section, SectionType } from "../types";
import { useUiStore } from "../ui";
import { SECTION_PRESETS } from "./schema";

function sectionIcon(type: SectionType, size = 17): ReactNode {
  switch (type) {
    case "education":
      return <IconGraduation size={size} />;
    case "experience":
      return <IconBriefcase size={size} />;
    case "project":
      return <IconLayers size={size} />;
    case "skills":
      return <IconWand size={size} />;
    case "awards":
      return <IconAward size={size} />;
    case "certificate":
      return <IconStar size={size} />;
    default:
      return <IconPen size={size} />;
  }
}

export function SectionRail() {
  const resume = useResumeStore((state) => state.resume);
  const reorderSections = useResumeStore((state) => state.reorderSections);
  const addSection = useResumeStore((state) => state.addSection);
  const toggleSection = useResumeStore((state) => state.toggleSection);
  const removeSection = useResumeStore((state) => state.removeSection);
  const activeSectionId = useUiStore((state) => state.activeSectionId);
  const setActiveSection = useUiStore((state) => state.setActiveSection);
  const [addOpen, setAddOpen] = useState(false);
  const footRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!addOpen) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent) {
        if (event.key === "Escape") setAddOpen(false);
        return;
      }
      if (!footRef.current?.contains(event.target as Node)) setAddOpen(false);
    };
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", close);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", close);
    };
  }, [addOpen]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (!resume) return null;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      reorderSections(String(active.id), String(over.id));
    }
  };

  const handleRemove = (section: Section) => {
    if (!window.confirm(`确定删除模块「${section.title}」及其全部内容吗？`)) return;
    removeSection(section.id);
  };

  return (
    <aside className="rail">
      <div className="rail-head">
        <span className="rail-title">简历模块</span>
        <span className="rail-sub">拖拽排序</span>
      </div>

      <div className="rail-list">
        <button
          type="button"
          className={`rail-item${activeSectionId === "basics" ? " is-active" : ""}`}
          onClick={() => setActiveSection("basics")}
        >
          <span className="rail-icon">
            <IconUser size={17} />
          </span>
          <span className="rail-label">基本信息</span>
          <span className="rail-count">01</span>
        </button>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={resume.sections.map((section) => section.id)} strategy={verticalListSortingStrategy}>
            {resume.sections.map((section) => (
              <SortableSection
                key={section.id}
                section={section}
                active={activeSectionId === section.id}
                onSelect={() => setActiveSection(section.id)}
                onToggle={() => toggleSection(section.id)}
                onRemove={() => handleRemove(section)}
              />
            ))}
          </SortableContext>
        </DndContext>
      </div>

      <div className="rail-foot" ref={footRef}>
        {addOpen ? (
          <div className="add-popover" role="menu">
            <p className="add-popover-title">选择要添加的模块</p>
            {SECTION_PRESETS.map((preset) => (
              <button
                type="button"
                key={preset.type}
                className="add-option"
                onClick={() => {
                  addSection(preset.type);
                  setAddOpen(false);
                }}
              >
                <span className="add-option-icon">{sectionIcon(preset.type, 15)}</span>
                <span>
                  <strong>{preset.title}</strong>
                  <em>{preset.hint}</em>
                </span>
              </button>
            ))}
          </div>
        ) : null}
        <button type="button" className="add-module" onClick={() => setAddOpen((value) => !value)}>
          <IconPlus size={14} />
          添加模块
          <IconChevron size={13} className={`add-chev${addOpen ? " is-open" : ""}`} />
        </button>
      </div>
    </aside>
  );
}

interface SortableSectionProps {
  section: Section;
  active: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onRemove: () => void;
}

function SortableSection({ section, active, onSelect, onToggle, onRemove }: SortableSectionProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: section.id
  });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`rail-item${active ? " is-active" : ""}${section.visible ? "" : " is-hidden"}${
        isDragging ? " is-dragging" : ""
      }`}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
    >
      <button
        type="button"
        ref={setActivatorNodeRef}
        className="rail-grip"
        title="拖拽调整顺序"
        onClick={(event) => event.stopPropagation()}
        {...attributes}
        {...listeners}
      >
        <IconGrip size={13} />
      </button>
      <span className="rail-icon">{sectionIcon(section.type)}</span>
      <span className="rail-label">{section.title}</span>
      <span className="rail-count">{section.items.length}</span>
      <button
        type="button"
        className="eye"
        title={section.visible ? "在简历中隐藏" : "在简历中显示"}
        onClick={(event) => {
          event.stopPropagation();
          onToggle();
        }}
      >
        {section.visible ? <IconShow size={13} /> : <IconHide size={13} />}
      </button>
      <button
        type="button"
        className="rail-del"
        title="删除模块"
        onClick={(event) => {
          event.stopPropagation();
          onRemove();
        }}
      >
        <IconTrash size={12} />
      </button>
    </div>
  );
}

function IconShow({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.7">
      <path d="M2.8 12s3.4-5.4 9.2-5.4S21.2 12 21.2 12s-3.4 5.4-9.2 5.4S2.8 12 2.8 12Z" />
      <circle cx="12" cy="12" r="2.3" />
    </svg>
  );
}

function IconHide({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
      <path d="M4 4.5 20 20" />
      <path d="M9.6 6.9A10.6 10.6 0 0 1 12 6.6c5.8 0 9.2 5.4 9.2 5.4a16 16 0 0 1-3 3.4M6.4 8.4A16.7 16.7 0 0 0 2.8 12s3.4 5.4 9.2 5.4c1 0 1.9-.2 2.8-.5" />
    </svg>
  );
}
