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

export type AiProvider = "deepseek" | "custom";

export interface AiSettings {
  provider: AiProvider;
  baseUrl: string;
  model: string;
  hasKey: boolean;
  keyHint: string;
  models: string[];
}

export interface ChatAction {
  tool: string;
  label: string;
  detail: string;
}

export interface ChatPending {
  id: string;
  tool: string;
  title: string;
  summary: string;
}

export interface ChatResponse {
  reply: string;
  actions: ChatAction[];
  pending: ChatPending[];
  resume: Resume | null;
  changed: boolean;
  resumeId: string;
  session?: ChatSession;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatEntry extends ChatMessage {
  id: string;
  actions?: ChatAction[];
}

export interface ResumeSummary {
  id: string;
  name: string;
  personName: string;
  createdAt: string;
  updatedAt: string;
  sectionCount: number;
  active: boolean;
}

export interface ChatSessionMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions: ChatAction[];
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  resumeId: string;
  messages: ChatSessionMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  resumeId: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  preview: string;
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
