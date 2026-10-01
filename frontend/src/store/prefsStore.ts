import { create } from "zustand";
import type { ChatLanguage } from "../types";

// Per-device UI preferences. Persisted to localStorage (non-sensitive only).
export type ThemePref = "system" | "dark" | "light";
export type ChartFormat = "north" | "south";

interface PrefsState {
  theme: ThemePref;
  chartFormat: ChartFormat;
  language: ChatLanguage;
  setTheme: (t: ThemePref) => void;
  setChartFormat: (f: ChartFormat) => void;
  setLanguage: (l: ChatLanguage) => void;
}

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage unavailable: preference lasts for this session only.
  }
}

export function applyTheme(t: ThemePref) {
  const root = document.documentElement;
  if (t === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", t);
}

export const usePrefsStore = create<PrefsState>((set) => ({
  theme: read<ThemePref>("nk-theme", ["system", "dark", "light"], "dark"),
  chartFormat: read<ChartFormat>("nk-chart-format", ["north", "south"], "north"),
  language: read<ChatLanguage>("nk-language", ["english", "hindi", "hinglish"], "english"),
  setTheme: (theme) => {
    write("nk-theme", theme);
    applyTheme(theme);
    set({ theme });
  },
  setChartFormat: (chartFormat) => {
    write("nk-chart-format", chartFormat);
    set({ chartFormat });
  },
  setLanguage: (language) => {
    write("nk-language", language);
    set({ language });
  },
}));
