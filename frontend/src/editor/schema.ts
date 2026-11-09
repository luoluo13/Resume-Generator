import type { Item, Section, SectionType } from "../types";

export interface SectionPreset {
  type: SectionType;
  title: string;
  hint: string;
}

export const SECTION_PRESETS: SectionPreset[] = [
  { type: "education", title: "教育背景", hint: "按时间倒序填写学校、学历、专业与主修课程。" },
  { type: "experience", title: "工作经历", hint: "每条要点写清「做了什么 + 怎么做的 + 结果数据」。" },
  { type: "project", title: "项目经历", hint: "突出个人职责与技术难点，用数据说明产出。" },
  { type: "skills", title: "专业技能", hint: "按方向分组，只写自己能在面试中展开讲的内容。" },
  { type: "awards", title: "荣誉奖项", hint: "优先保留与岗位相关、含金量高的奖项。" },
  { type: "certificate", title: "证书资质", hint: "填写行业认可的证书，注明取得时间。" },
  { type: "custom", title: "自定义模块", hint: "可用来写自我评价、作品集、语言能力等。" }
];

export function presetOf(type: SectionType): SectionPreset {
  return SECTION_PRESETS.find((preset) => preset.type === type) ?? SECTION_PRESETS[SECTION_PRESETS.length - 1];
}

export function createSection(type: SectionType, title?: string): Section {
  return {
    id: `sec_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    type,
    title: title || presetOf(type).title,
    visible: true,
    items: [createItem(type)]
  };
}

export function createItem(type: SectionType): Item {
  return {
    title: "",
    subtitle: "",
    name: "",
    school: "",
    degree: "",
    major: "",
    company: "",
    role: "",
    location: "",
    start: "",
    end: "",
    current: false,
    gpa: "",
    courses: "",
    tech: [],
    link: "",
    group: "",
    tags: [],
    issuer: "",
    date: "",
    highlights: type === "skills" || type === "awards" || type === "certificate" ? [] : [""]
  };
}

export function entryTitle(type: SectionType, item: Item): string {
  switch (type) {
    case "education":
      return item.school || "新的教育经历";
    case "experience":
      return item.company || "新的工作经历";
    case "project":
      return item.name || "新的项目";
    case "skills":
      return item.group || "新的技能分组";
    case "awards":
    case "certificate":
      return item.name || "新的条目";
    default:
      return item.title || "新的条目";
  }
}

export function entrySubtitle(type: SectionType, item: Item): string {
  switch (type) {
    case "education":
      return [item.degree, item.major].filter(Boolean).join(" · ");
    case "experience":
      return item.role;
    case "project":
      return item.role;
    case "skills":
      return `${item.tags.length} 个标签`;
    case "awards":
    case "certificate":
      return item.issuer;
    default:
      return item.subtitle;
  }
}

export function entryPeriod(item: Item): string {
  if (!item.start && !item.end && !item.current) return "";
  const end = item.current ? "至今" : item.end;
  return [item.start, end].filter(Boolean).join(" – ");
}
