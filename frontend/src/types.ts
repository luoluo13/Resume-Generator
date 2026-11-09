export type SectionType =
  | "education"
  | "experience"
  | "project"
  | "skills"
  | "awards"
  | "certificate"
  | "custom";

export interface Basics {
  name: string;
  jobIntention: string;
  phone: string;
  email: string;
  city: string;
  available: string;
  yearsOfExperience: string;
  gender: string;
  birth: string;
  political: string;
  photo: string;
  show: Record<string, boolean>;
}

export interface Item {
  title: string;
  subtitle: string;
  name: string;
  school: string;
  degree: string;
  major: string;
  company: string;
  role: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  gpa: string;
  courses: string;
  tech: string[];
  link: string;
  group: string;
  tags: string[];
  issuer: string;
  date: string;
  highlights: string[];
}

export interface Section {
  id: string;
  type: SectionType;
  title: string;
  visible: boolean;
  items: Item[];
}

export interface Theme {
  template: string;
  accent: string;
  fontFamily: "SourceHanSansSC" | "SourceHanSerifSC" | "MicrosoftYaHei";
  fontSize: number;
  lineHeight: number;
  pageMargin: number;
  columns: number;
  photoPosition: "none" | "right" | "left";
  dividerStyle: "line" | "block" | "none";
  density: "loose" | "normal" | "compact";
  variants?: Record<string, string>;
}

export interface Resume {
  schemaVersion: number;
  id: string;
  meta: Record<string, string>;
  basics: Basics;
  sections: Section[];
  theme: Theme;
}

export interface ImportItem {
  headline: string;
  meta: string;
  period: string;
  bullets: string[];
  tags: string[];
}

export interface ImportSection {
  id: string;
  title: string;
  type: SectionType;
  confidence: number;
  items: ImportItem[];
}

export interface ImportBasics {
  name: string;
  jobIntention: string;
  phone: string;
  email: string;
  city: string;
  yearsOfExperience: string;
  available: string;
}

export interface ImportDraft {
  file: { name: string; kind: string; size: number; pages: number };
  basics: ImportBasics;
  sections: ImportSection[];
  style: { template: string; reason: string; theme: Theme };
  warnings: string[];
  stats: { blocks: number; characters: number; items: number; entries: number; maxSize: number; bodySize: number };
}

export interface ImportApplyPayload {
  basics: ImportBasics;
  sections: ImportSection[];
  theme: Theme;
  sourceName: string;
}

export interface VariantOption {
  value: string;
  label: string;
}

export interface VariantGroup {
  key: string;
  label: string;
  description?: string;
  options: VariantOption[];
  default: string;
}

export interface TemplateManifest {
  id: string;
  name: string;
  description: string;
  tags: string[];
  color: string;
  order: number;
  serifHeading?: boolean;
  source: "builtin" | "user";
  version?: string;
  supports: {
    columns: number[];
    photo: boolean;
    divider: string[];
  };
  variants?: VariantGroup[];
}

export interface SystemInfo {
  version: string;
  port: number;
  root: string;
  dataDir: string;
  exportsDir: string;
  logDir: string;
  fonts: {
    ready: boolean;
    available: Record<string, boolean>;
    labels: Record<string, string>;
    fallback: string;
  };
  chromiumReady: boolean;
  python: string;
  platform: string;
}

export interface ExportFile {
  name: string;
  path: string;
  size: number;
}

export interface ExportResult {
  dir: string;
  files: ExportFile[];
}
