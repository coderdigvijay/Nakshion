// Original geometric glyph set (drawn for Nakshion, no third-party outlines, so no licence
// attribution is needed). 24x24 viewBox, stroke-only: render with stroke="currentColor",
// stroke-width 1.75, round caps and joins, fill none (MASTER §7.2). No Unicode text glyphs are
// used anywhere, so iOS/Android can't swap them for colour emoji.
//
// Each entry is a list of SVG path `d` strings; circles are written as arcs.

const circle = (cx: number, cy: number, r: number) => `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;

export const SIGN_GLYPHS = {
  aries: ["M12 21V10", "M12 10C12 6 9.5 3.5 7 3.5S3 5.5 3 8", "M12 10C12 6 14.5 3.5 17 3.5S21 5.5 21 8"],
  taurus: [circle(12, 15, 5), "M4.5 3.5C4.5 8 8 10 12 10s7.5-2 7.5-6.5"],
  gemini: ["M7.5 5.5v13", "M16.5 5.5v13", "M4 4.5C9 7 15 7 20 4.5", "M4 19.5C9 17 15 17 20 19.5"],
  cancer: [circle(8.5, 10, 2.5), "M3.5 10C3.5 6.5 8 5 13 5s5.5 1 7 2.5", circle(15.5, 14, 2.5), "M20.5 14c0 3.5-4.5 5-9.5 5s-5.5-1-7-2.5"],
  leo: [circle(8, 15, 3.5), "M11.5 15C11.5 6 14 4 16.5 4S20 6 19 9c-.8 2.5-3.5 3.5-3.5 7 0 2.5 1.5 4 4 3.5"],
  virgo: ["M3.5 5v13.5", "M3.5 8.5C3.5 5.5 8.5 5.5 8.5 8.5V18.5", "M8.5 8.5C8.5 5.5 13.5 5.5 13.5 8.5V16c0 3 2.5 4.5 5.5 3", "M19 19c-1.5-3-1.5-5 0-6.5"],
  libra: ["M3.5 19.5h17", "M3.5 14.5H8.5C6.5 12.5 6 10 8 7.5S14 4.5 16 7.5s1.5 5-.5 7h5"],
  scorpio: ["M3.5 5v13.5", "M3.5 8.5C3.5 5.5 8.5 5.5 8.5 8.5V18.5", "M8.5 8.5C8.5 5.5 13.5 5.5 13.5 8.5V17c0 2.5 2 3 4 1.5", "M17.5 18.5l3-.5M17.5 18.5l.5-3.5", "M20.5 18l-3 3"],
  sagittarius: ["M4 20L20 4", "M11 4h9v9", "M6.5 13l4.5 4.5"],
  capricorn: ["M3 5.5C5 5.5 6 8 6.5 11l1.5 6c.5-5 1.5-9 3.5-9S14 12 14 14.5c0 3.5 2 5 4 5", circle(18, 15.5, 2.5)],
  aquarius: ["M3 9.5l3.5-3 3.5 3 3.5-3 3.5 3 3-2.5", "M3 17l3.5-3 3.5 3 3.5-3 3.5 3 3-2.5"],
  pisces: ["M6 3C10 7 10 17 6 21", "M18 3C14 7 14 17 18 21", "M4 12h16"],
} as const;

export const GRAHA_GLYPHS = {
  sun: [circle(12, 12, 8), circle(12, 12, 1)],
  moon: ["M15.5 3.5A8.5 8.5 0 1 0 15.5 20.5 6.5 6.5 0 0 1 15.5 3.5z"],
  mars: [circle(10, 14, 5.5), "M14 10L20 4", "M14.5 4H20v5.5"],
  mercury: [circle(12, 12.5, 4), "M8 3.5a4 4 0 0 0 8 0", "M12 16.5v5", "M9 19.5h6"],
  jupiter: ["M4.5 8.5C4.5 3.5 11 3 11 7.5c0 3.5-5 6.5-6.5 8.5H20", "M16 7.5v14"],
  venus: [circle(12, 9, 5), "M12 14v8", "M9 18h6"],
  saturn: ["M8 3v14", "M5 7h6", "M8 11c4-3 8.5 0 7.5 4-.5 2-2.5 3-2.5 6"],
  rahu: [circle(5.5, 17.5, 2.5), circle(18.5, 17.5, 2.5), "M8 17.5C8 7 16 7 16 17.5"],
  ketu: [circle(5.5, 6.5, 2.5), circle(18.5, 6.5, 2.5), "M8 6.5C8 17 16 17 16 6.5"],
} as const;

export const LAGNA_GLYPH = ["M3 19.5h18", "M6 19.5L12 5l6 14.5"] as const;

export type SignGlyphName = keyof typeof SIGN_GLYPHS;
export type GrahaGlyphName = keyof typeof GRAHA_GLYPHS;
export type GlyphName = SignGlyphName | GrahaGlyphName | "lagna";

const ALL_NAMES = new Set<string>([...Object.keys(SIGN_GLYPHS), ...Object.keys(GRAHA_GLYPHS), "lagna"]);

export function hasGlyph(name: string): name is GlyphName {
  return ALL_NAMES.has(name);
}
