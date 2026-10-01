// Display-only astrology reference tables and formatters.
// Nothing here computes chart facts; the engine does (docs/astrology-engine.md).

export type Element = "fire" | "earth" | "air" | "water";
export type GrahaKey =
  | "sun" | "moon" | "mars" | "mercury" | "jupiter" | "venus" | "saturn" | "rahu" | "ketu";

export interface SignInfo {
  english: string;
  rashi: string;
  devanagari: string;
  element: Element;
  abbr: string;
}

/** Zodiac order, Aries first. Rashi spellings follow astrology-engine.md §2 (`Vrishchika`). */
export const SIGNS: SignInfo[] = [
  { english: "Aries", rashi: "Mesha", devanagari: "मेष", element: "fire", abbr: "Ar" },
  { english: "Taurus", rashi: "Vrishabha", devanagari: "वृषभ", element: "earth", abbr: "Ta" },
  { english: "Gemini", rashi: "Mithuna", devanagari: "मिथुन", element: "air", abbr: "Ge" },
  { english: "Cancer", rashi: "Karka", devanagari: "कर्क", element: "water", abbr: "Cn" },
  { english: "Leo", rashi: "Simha", devanagari: "सिंह", element: "fire", abbr: "Le" },
  { english: "Virgo", rashi: "Kanya", devanagari: "कन्या", element: "earth", abbr: "Vi" },
  { english: "Libra", rashi: "Tula", devanagari: "तुला", element: "air", abbr: "Li" },
  { english: "Scorpio", rashi: "Vrishchika", devanagari: "वृश्चिक", element: "water", abbr: "Sc" },
  { english: "Sagittarius", rashi: "Dhanu", devanagari: "धनु", element: "fire", abbr: "Sg" },
  { english: "Capricorn", rashi: "Makara", devanagari: "मकर", element: "earth", abbr: "Cp" },
  { english: "Aquarius", rashi: "Kumbha", devanagari: "कुम्भ", element: "air", abbr: "Aq" },
  { english: "Pisces", rashi: "Meena", devanagari: "मीन", element: "water", abbr: "Pi" },
];

/** Accepts an English sign name or a rashi name (any case) and returns its sign info. */
export function findSign(name: string | null | undefined): SignInfo | undefined {
  if (!name) return undefined;
  const n = name.trim().toLowerCase();
  return SIGNS.find(
    (s) => s.english.toLowerCase() === n || s.rashi.toLowerCase() === n || (n === "vrischika" && s.rashi === "Vrishchika"),
  );
}

export function signIndex(name: string | null | undefined): number {
  const s = findSign(name);
  return s ? SIGNS.indexOf(s) : -1;
}

export interface GrahaInfo {
  key: GrahaKey;
  english: string;
  sanskrit: string;
  abbr: string;
}

export const GRAHAS: GrahaInfo[] = [
  { key: "sun", english: "Sun", sanskrit: "Surya", abbr: "Su" },
  { key: "moon", english: "Moon", sanskrit: "Chandra", abbr: "Mo" },
  { key: "mars", english: "Mars", sanskrit: "Mangala", abbr: "Ma" },
  { key: "mercury", english: "Mercury", sanskrit: "Budha", abbr: "Me" },
  { key: "jupiter", english: "Jupiter", sanskrit: "Guru", abbr: "Ju" },
  { key: "venus", english: "Venus", sanskrit: "Shukra", abbr: "Ve" },
  { key: "saturn", english: "Saturn", sanskrit: "Shani", abbr: "Sa" },
  { key: "rahu", english: "Rahu", sanskrit: "Rahu", abbr: "Ra" },
  { key: "ketu", english: "Ketu", sanskrit: "Ketu", abbr: "Ke" },
];

const GRAHA_ALIASES: Record<string, GrahaKey> = {
  sun: "sun", surya: "sun",
  moon: "moon", chandra: "moon",
  mars: "mars", mangal: "mars", mangala: "mars",
  mercury: "mercury", budha: "mercury",
  jupiter: "jupiter", guru: "jupiter",
  venus: "venus", shukra: "venus",
  saturn: "saturn", shani: "saturn",
  rahu: "rahu", "north node": "rahu",
  ketu: "ketu", "south node": "ketu",
};

export function findGraha(name: string | null | undefined): GrahaInfo | undefined {
  if (!name) return undefined;
  const key = GRAHA_ALIASES[name.trim().toLowerCase()];
  return key ? GRAHAS.find((g) => g.key === key) : undefined;
}

/** Abbreviation for any body; outer planets fall back to two letters. */
export function planetAbbr(name: string): string {
  return findGraha(name)?.abbr ?? name.slice(0, 2);
}

/** Tailwind text-colour class per graha (token utilities from tokens.css). */
export const GRAHA_TEXT: Record<GrahaKey, string> = {
  sun: "text-sun", moon: "text-moon", mars: "text-mars", mercury: "text-mercury",
  jupiter: "text-jupiter", venus: "text-venus", saturn: "text-saturn", rahu: "text-rahu", ketu: "text-ketu",
};

/** SVG fill classes per graha. */
export const GRAHA_FILL: Record<GrahaKey, string> = {
  sun: "fill-sun", moon: "fill-moon", mars: "fill-mars", mercury: "fill-mercury",
  jupiter: "fill-jupiter", venus: "fill-venus", saturn: "fill-saturn", rahu: "fill-rahu", ketu: "fill-ketu",
};

export const GRAHA_BG: Record<GrahaKey, string> = {
  sun: "bg-sun", moon: "bg-moon", mars: "bg-mars", mercury: "bg-mercury",
  jupiter: "bg-jupiter", venus: "bg-venus", saturn: "bg-saturn", rahu: "bg-rahu", ketu: "bg-ketu",
};

export const ELEMENT_TEXT: Record<Element, string> = {
  fire: "text-fire", earth: "text-earth", air: "text-air", water: "text-water",
};

export const ELEMENT_LABEL: Record<Element, string> = {
  fire: "Fire", earth: "Earth", air: "Air", water: "Water",
};

export const HOUSE_THEMES: Record<number, string> = {
  1: "self, body, temperament",
  2: "wealth, speech, family",
  3: "courage, siblings, communication",
  4: "home, mother, inner security",
  5: "children, creativity, learning",
  6: "health, service, obstacles",
  7: "marriage, partnerships",
  8: "transformation, shared resources",
  9: "dharma, fortune, teachers",
  10: "career, public life",
  11: "gains, friends, aspirations",
  12: "release, retreat, foreign lands",
};

/** 14.37 → 14°22′ (MASTER §4.2: prime U+2032, never decimals). */
export function formatDeg(decimal: number): string {
  if (!Number.isFinite(decimal)) return "—";
  let deg = Math.floor(decimal);
  let min = Math.round((decimal - deg) * 60);
  if (min === 60) {
    deg += 1;
    min = 0;
  }
  return `${deg}°${String(min).padStart(2, "0")}′`;
}

export function degAriaLabel(decimal: number): string {
  const deg = Math.floor(decimal);
  const min = Math.round((decimal - deg) * 60);
  return `${deg} degrees ${min} minutes`;
}

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
}

/** Legacy IANA aliases some browsers still report, mapped to the canonical zone the server stores. */
const TZ_ALIASES: Record<string, string> = {
  "Asia/Calcutta": "Asia/Kolkata",
  "Asia/Katmandu": "Asia/Kathmandu",
  "Asia/Saigon": "Asia/Ho_Chi_Minh",
  "Asia/Rangoon": "Asia/Yangon",
  "Asia/Dacca": "Asia/Dhaka",
  "Asia/Thimbu": "Asia/Thimphu",
  "Asia/Ulan_Bator": "Asia/Ulaanbaatar",
  "Europe/Kiev": "Europe/Kyiv",
  "Atlantic/Faeroe": "Atlantic/Faroe",
  "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
  "Pacific/Truk": "Pacific/Chuuk",
  "UTC": "UTC",
  "Etc/UTC": "UTC",
  "Etc/GMT": "UTC",
};

export function canonicalTimeZone(zone: string): string {
  return TZ_ALIASES[zone] ?? zone;
}

/** Lat/lon read-back: "25.32° N, 82.97° E". */
export function formatCoords(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}° ${ns}, ${Math.abs(lon).toFixed(2)}° ${ew}`;
}

/**
 * UTC offset of an IANA zone on a given civil date, e.g. "UTC+05:30".
 * Uses Intl only; returns the zone name if the browser can't resolve it.
 */
export function formatUtcOffset(timeZone: string, date: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: "longOffset" }).formatToParts(date);
    const tz = parts.find((p) => p.type === "timeZoneName")?.value ?? "";
    if (tz === "GMT") return "UTC+00:00";
    return tz.replace("GMT", "UTC");
  } catch {
    return timeZone;
  }
}

export type ZodiacSystem = "sidereal" | "tropical";
export const SYSTEM_LABEL: Record<ZodiacSystem, string> = { sidereal: "Vedic, sidereal", tropical: "Western, tropical" };
