import { create } from "zustand";
import { api } from "./api";
import { createSection } from "./editor/schema";
import type { Resume, ResumeSummary, Section, SectionType, SystemInfo, TemplateManifest, Theme } from "./types";
import { toast, useUiStore } from "./ui";

type SaveState = "saved" | "saving" | "error";

interface ResumeState {
  resume: Resume | null;
  resumes: ResumeSummary[];
  resumeName: string;
  templates: TemplateManifest[];
  info: SystemInfo | null;
  loading: boolean;
  error: string | null;
  saveState: SaveState;
  saveError: string;
  previewKey: number;
  pages: number;
  pageRatio: number;
  load: () => Promise<void>;
  loadResumes: () => Promise<void>;
  switchResume: (id: string) => Promise<void>;
  createResume: (name?: string) => Promise<void>;
  renameResume: (id: string, name: string) => Promise<void>;
  deleteResume: (id: string) => Promise<void>;
  refreshTemplates: () => Promise<void>;
  update: (mutate: (resume: Resume) => void) => void;
  replaceResume: (resume: Resume) => void;
  saveNow: () => Promise<void>;
  setTemplate: (id: string) => void;
  setTheme: (patch: Partial<Theme>) => void;
  reorderSections: (activeId: string, overId: string) => void;
  addSection: (type: SectionType) => void;
  removeSection: (id: string) => void;
  toggleSection: (id: string) => void;
  setMetrics: (pages: number, ratio: number) => void;
}

let timer: ReturnType<typeof setTimeout> | undefined;
let inFlight = false;
let queued = false;

function scheduleSave(get: () => ResumeState): void {
  if (timer) window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    timer = undefined;
    void get().saveNow();
  }, 120);
}

export const useResumeStore = create<ResumeState>()((set, get) => ({
  resume: null,
  resumes: [],
  resumeName: "",
  templates: [],
  info: null,
  loading: true,
  error: null,
  saveState: "saved",
  saveError: "",
  previewKey: 0,
  pages: 1,
  pageRatio: 1,

  load: async () => {
    set({ loading: true, error: null });
    try {
      const [resume, templates, info, library] = await Promise.all([
        api.getResume(),
        api.getTemplates(),
        api.getInfo(),
        api.getResumes()
      ]);
      set({
        resume,
        resumes: library.items,
        resumeName: library.activeName,
        templates,
        info,
        loading: false,
        previewKey: 1
      });
      if (!useUiStore.getState().activeSectionId) {
        useUiStore.getState().setActiveSection("basics");
      }
    } catch (error) {
      set({ loading: false, error: (error as Error).message });
    }
  },

  loadResumes: async () => {
    const data = await api.getResumes();
    set({ resumes: data.items, resumeName: data.activeName });
  },

  switchResume: async (id) => {
    if (get().resume?.id === id) return;
    await get().saveNow();
    await api.activateResume(id);
    const [resume, library] = await Promise.all([api.getResume(), api.getResumes()]);
    set((state) => ({
      resume,
      resumes: library.items,
      resumeName: library.activeName,
      previewKey: state.previewKey + 1,
      saveState: "saved",
      saveError: ""
    }));
    useUiStore.getState().setActiveSection("basics");
  },

  createResume: async (name) => {
    await get().saveNow();
    const result = await api.createResume(name);
    set((state) => ({
      resume: result.resume,
      resumes: result.items,
      resumeName: result.activeName,
      previewKey: state.previewKey + 1,
      saveState: "saved",
      saveError: ""
    }));
    useUiStore.getState().setActiveSection("basics");
  },

  renameResume: async (id, name) => {
    const result = await api.renameResume(id, name);
    set((state) => ({
      resumes: result.items,
      resumeName: state.resume?.id === id ? result.item.name : state.resumeName
    }));
  },

  deleteResume: async (id) => {
    const result = await api.deleteResume(id);
    if (get().resume?.id !== id) {
      set({ resumes: result.items, resumeName: result.activeName });
      return;
    }
    const resume = await api.getResume();
    set((state) => ({
      resume,
      resumes: result.items,
      resumeName: result.activeName,
      previewKey: state.previewKey + 1,
      saveState: "saved",
      saveError: ""
    }));
    useUiStore.getState().setActiveSection("basics");
  },

  refreshTemplates: async () => {
    const templates = await api.getTemplates();
    set({ templates });
  },

  update: (mutate) => {
    const current = get().resume;
    if (!current) return;
    const next = structuredClone(current);
    mutate(next);
    set({ resume: next, saveState: "saving" });
    scheduleSave(get);
  },

  replaceResume: (resume) => {
    set((state) => ({ resume, previewKey: state.previewKey + 1, saveState: "saved", saveError: "" }));
    const ui = useUiStore.getState();
    const active = ui.activeSectionId;
    if (active && active !== "basics" && !resume.sections.some((section) => section.id === active)) {
      ui.setActiveSection(resume.sections[0]?.id ?? "basics");
    }
  },

  saveNow: async () => {
    if (timer) {
      window.clearTimeout(timer);
      timer = undefined;
    }
    const resume = get().resume;
    if (!resume) return;
    if (inFlight) {
      queued = true;
      return;
    }
    inFlight = true;
    set({ saveState: "saving" });
    try {
      await api.saveResume(resume);
      set((state) => ({ saveState: "saved", saveError: "", previewKey: state.previewKey + 1 }));
    } catch (error) {
      set({ saveState: "error", saveError: (error as Error).message });
    } finally {
      inFlight = false;
      if (queued) {
        queued = false;
        void get().saveNow();
      }
    }
  },

  setTemplate: (id) => {
    const manifest = get().templates.find((item) => item.id === id);
    get().update((resume) => {
      resume.theme.template = id;
      resume.theme.variants = {};
      if (!manifest) return;
      if (!manifest.supports.columns.includes(resume.theme.columns)) {
        resume.theme.columns = manifest.supports.columns[0];
      }
      if (!manifest.supports.photo && resume.theme.photoPosition !== "none") {
        resume.theme.photoPosition = "none";
      }
      if (!manifest.supports.divider.includes(resume.theme.dividerStyle)) {
        resume.theme.dividerStyle = manifest.supports.divider[0] as Theme["dividerStyle"];
      }
    });
  },

  setTheme: (patch) => {
    get().update((resume) => {
      Object.assign(resume.theme, patch);
    });
  },

  reorderSections: (activeId, overId) => {
    if (activeId === overId) return;
    get().update((resume) => {
      const from = resume.sections.findIndex((section) => section.id === activeId);
      const to = resume.sections.findIndex((section) => section.id === overId);
      if (from < 0 || to < 0) return;
      const [moved] = resume.sections.splice(from, 1);
      resume.sections.splice(to, 0, moved);
    });
  },

  addSection: (type) => {
    const section: Section = createSection(type);
    get().update((resume) => {
      resume.sections.push(section);
    });
    useUiStore.getState().setActiveSection(section.id);
    toast("success", `已添加「${section.title}」`);
  },

  removeSection: (id) => {
    const resume = get().resume;
    if (!resume) return;
    if (resume.sections.length <= 1) {
      toast("warning", "至少需要保留一个模块");
      return;
    }
    get().update((state) => {
      state.sections = state.sections.filter((section) => section.id !== id);
    });
    if (useUiStore.getState().activeSectionId === id) {
      const next = get().resume?.sections[0];
      if (next) useUiStore.getState().setActiveSection(next.id);
    }
  },

  toggleSection: (id) => {
    const resume = get().resume;
    if (!resume) return;
    const target = resume.sections.find((section) => section.id === id);
    if (!target) return;
    const visibleCount = resume.sections.filter((section) => section.visible).length;
    if (target.visible && visibleCount <= 1) {
      toast("warning", "至少需要保留一个可见模块");
      return;
    }
    get().update((state) => {
      const section = state.sections.find((item) => item.id === id);
      if (section) section.visible = !section.visible;
    });
  },

  setMetrics: (pages, ratio) => set({ pages, pageRatio: ratio })
}));
