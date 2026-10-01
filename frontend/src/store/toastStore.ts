import { create } from "zustand";

export type ToastTone = "success" | "info" | "warning" | "error";

export interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  body?: string;
}

interface ToastState {
  toasts: ToastItem[];
  push: (t: Omit<ToastItem, "id">) => number;
  dismiss: (id: number) => void;
}

let nextId = 1;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (t) => {
    const id = nextId++;
    // Max 3 visible; older ones drop off (COMPONENTS.md → Toast).
    set((s) => ({ toasts: [...s.toasts, { ...t, id }].slice(-3) }));
    return id;
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),
}));

export const toast = {
  success: (title: string, body?: string) => useToastStore.getState().push({ tone: "success", title, body }),
  info: (title: string, body?: string) => useToastStore.getState().push({ tone: "info", title, body }),
  warning: (title: string, body?: string) => useToastStore.getState().push({ tone: "warning", title, body }),
  error: (title: string, body?: string) => useToastStore.getState().push({ tone: "error", title, body }),
};
