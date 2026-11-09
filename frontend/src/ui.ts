import { create } from "zustand";

export type View = "editor" | "templates";
export type ToastKind = "success" | "warning" | "error" | "info";

export interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

interface UiState {
  view: View;
  activeSectionId: string | null;
  zoom: number;
  themeOpen: boolean;
  exportOpen: boolean;
  envOpen: boolean;
  importOpen: boolean;
  toasts: ToastItem[];
  setView: (view: View) => void;
  setActiveSection: (id: string) => void;
  setZoom: (zoom: number) => void;
  setThemeOpen: (open: boolean) => void;
  setExportOpen: (open: boolean) => void;
  setEnvOpen: (open: boolean) => void;
  setImportOpen: (open: boolean) => void;
  pushToast: (kind: ToastKind, message: string) => void;
  dismissToast: (id: number) => void;
}

let toastSeed = 0;

export const useUiStore = create<UiState>()((set, get) => ({
  view: "editor",
  activeSectionId: null,
  zoom: 0.78,
  themeOpen: false,
  exportOpen: false,
  envOpen: false,
  importOpen: false,
  toasts: [],
  setView: (view) => set({ view, themeOpen: false, exportOpen: false, envOpen: false, importOpen: false }),
  setActiveSection: (activeSectionId) => set({ activeSectionId }),
  setZoom: (zoom) => set({ zoom: Math.min(1.2, Math.max(0.5, Number(zoom.toFixed(2)))) }),
  setThemeOpen: (themeOpen) => set({ themeOpen }),
  setExportOpen: (exportOpen) => set({ exportOpen }),
  setEnvOpen: (envOpen) => set({ envOpen }),
  setImportOpen: (importOpen) => set({ importOpen }),
  pushToast: (kind, message) => {
    const id = ++toastSeed;
    set((state) => ({ toasts: [...state.toasts, { id, kind, message }] }));
    const duration = kind === "success" ? 2200 : kind === "warning" ? 4200 : kind === "error" ? 7000 : 3000;
    window.setTimeout(() => get().dismissToast(id), duration);
  },
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }))
}));

export function toast(kind: ToastKind, message: string): void {
  useUiStore.getState().pushToast(kind, message);
}
