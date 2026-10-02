import { useEffect } from "react";

const BASE = "Nakshion";

/** Sets document.title to "<title> — Nakshion" (or the default tagline title) and restores it on unmount. */
export function useDocumentTitle(title?: string) {
  useEffect(() => {
    const prev = document.title;
    document.title = title ? `${title} — ${BASE}` : `${BASE} — your sky, read with care`;
    return () => {
      document.title = prev;
    };
  }, [title]);
}
