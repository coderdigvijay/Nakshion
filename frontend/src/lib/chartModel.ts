// Adapters from the API's chart_data to what the UI renders. Pure, display-only.
import type { BirthChart, ChartData, DivisionalChart, VedicData, VedicPlanet } from "../types";
import { findGraha, findSign, GRAHAS, ordinal, planetAbbr, signIndex, SIGNS, type GrahaKey } from "./astro";

export type Dignity = "exalted" | "own" | "mooltrikona" | "debilitated" | "friendly" | "enemy" | "neutral";

export function normaliseDignity(raw: string | null | undefined): Dignity {
  const d = (raw ?? "").toLowerCase();
  if (d.includes("exalt") || d.includes("uchcha")) return "exalted";
  if (d.includes("debilit") || d.includes("neecha")) return "debilitated";
  if (d.includes("moolatrikona") || d.includes("mooltrikona")) return "mooltrikona";
  if (d.includes("own") || d.includes("swakshetra")) return "own";
  if (d.includes("friend") || d.includes("mitra")) return "friendly";
  if (d.includes("enemy") || d.includes("shatru")) return "enemy";
  return "neutral";
}

export interface WheelPlanet {
  english: string;
  sanskrit: string;
  abbr: string;
  key: GrahaKey | undefined;
  signIdx: number;
  house: number;
  degree: number;
  retrograde: boolean;
  combust: boolean;
  dignity: Dignity;
  nakshatra?: string;
  pada?: number;
}

export interface WheelData {
  lagnaIdx: number;
  lagnaDegree?: number;
  planets: WheelPlanet[];
  /** Birth time unknown: Lagna and houses are approximate. */
  approximate: boolean;
}

const OUTER = new Set(["uranus", "neptune", "pluto"]);

function toWheelPlanet(p: VedicPlanet, lagnaIdx: number): WheelPlanet | null {
  const signIdx = signIndex(p.rashi_english) >= 0 ? signIndex(p.rashi_english) : signIndex(p.rashi);
  if (signIdx < 0) return null;
  const g = findGraha(p.english) ?? findGraha(p.name);
  // Whole-sign house counted from the lagna sign (matches the engine for D1 and vargas).
  // house 0 = unknown (no birth time): the planet is shown by sign only.
  const house = lagnaIdx >= 0 ? ((signIdx - lagnaIdx + 12) % 12) + 1 : (p.house ?? 0);
  return {
    english: g?.english ?? p.english ?? p.name,
    sanskrit: g?.sanskrit ?? p.name,
    abbr: g?.abbr ?? planetAbbr(p.english ?? p.name),
    key: g?.key,
    signIdx,
    house,
    degree: p.degree,
    retrograde: !!p.retrograde,
    combust: !!p.combust,
    dignity: normaliseDignity(p.dignity),
    nakshatra: p.nakshatra || undefined,
    pada: p.pada || undefined,
  };
}

function sortByGraha(a: WheelPlanet, b: WheelPlanet) {
  const ia = GRAHAS.findIndex((g) => g.key === a.key);
  const ib = GRAHAS.findIndex((g) => g.key === b.key);
  return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
}

export function vedicWheel(vedic: VedicData, approximate: boolean): WheelData {
  const lg = vedic.lagna;
  const lagnaIdx = !lg ? -1 : signIndex(lg.rashi_english) >= 0 ? signIndex(lg.rashi_english) : signIndex(lg.rashi);
  const planets = vedic.planets
    .filter((p) => !OUTER.has((p.english ?? "").toLowerCase()))
    .map((p) => toWheelPlanet(p, lagnaIdx))
    .filter((p): p is WheelPlanet => p !== null)
    .sort(sortByGraha);
  return { lagnaIdx, lagnaDegree: vedic.lagna?.degree, planets, approximate };
}

export function divisionalWheel(div: DivisionalChart, approximate: boolean): WheelData {
  const lagnaIdx = signIndex(div.lagna.rashi);
  const planets = (div.planets ?? [])
    .filter((p) => !OUTER.has((p.english ?? "").toLowerCase()))
    .map((p) => toWheelPlanet(p, lagnaIdx))
    .filter((p): p is WheelPlanet => p !== null)
    .sort(sortByGraha);
  return { lagnaIdx, planets, approximate };
}

/** Western fallback for charts without a vedic block (G-20 says this shouldn't happen). */
export function westernWheel(data: ChartData): WheelData {
  const lagnaIdx = signIndex(data.rising_sign?.sign);
  const planets: WheelPlanet[] = data.planets
    .filter((p) => !OUTER.has(p.name.toLowerCase()) && p.name !== "South Node")
    .map((p) => {
      const g = findGraha(p.name);
      const signIdx = signIndex(p.sign);
      return {
        english: g?.english ?? p.name,
        sanskrit: g?.sanskrit ?? p.name,
        abbr: g?.abbr ?? planetAbbr(p.name),
        key: g?.key,
        signIdx,
        house: p.house ?? 0,
        degree: p.degree,
        retrograde: p.retrograde,
        combust: false,
        dignity: "neutral" as Dignity,
      };
    })
    .filter((p) => p.signIdx >= 0)
    .sort(sortByGraha);
  return { lagnaIdx, planets, approximate: !!data.metadata?.approximate_time };
}

/**
 * False when the engine could not compute houses/ascendant (birth time unknown). Reads every
 * plausible flag and falls back to "lagna missing" so it works before the shape is final.
 */
export function housesAvailable(chart: BirthChart): boolean {
  const cd = chart.chart_data;
  const flags = [cd.metadata?.houses_available, cd.vedic?.houses_available, cd.houses_available];
  if (flags.some((f) => f === false)) return false;
  if (cd.vedic && !cd.vedic.lagna) return false;
  return true;
}

export function isApproximate(chart: BirthChart): boolean {
  return !chart.has_exact_time || !!chart.chart_data.metadata?.approximate_time;
}

export function chartWheelData(chart: BirthChart): WheelData {
  const approx = isApproximate(chart);
  return chart.chart_data.vedic ? vedicWheel(chart.chart_data.vedic, approx) : westernWheel(chart.chart_data);
}

/** One-sentence aria summary: "Lagna Simha (Leo). Sun and Mercury in the 10th house. Saturn retrograde in the 7th." */
export function wheelSummary(w: WheelData): string {
  const lagna = w.lagnaIdx >= 0 ? SIGNS[w.lagnaIdx] : undefined;
  const parts: string[] = [];
  if (lagna) parts.push(`Lagna ${lagna.rashi} (${lagna.english})${w.approximate ? ", approximate" : ""}.`);
  const byHouse = new Map<number, WheelPlanet[]>();
  for (const p of w.planets.filter((x) => x.house > 0)) byHouse.set(p.house, [...(byHouse.get(p.house) ?? []), p]);
  for (const [house, ps] of [...byHouse.entries()].sort((a, b) => a[0] - b[0])) {
    const names = ps.map((p) => `${p.english}${p.retrograde ? " retrograde" : ""}`);
    const list = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];
    parts.push(`${list} in the ${ordinal(house)} house.`);
  }
  return parts.join(" ");
}

/** Big Three, Vedic-first: sidereal Sun rashi, Moon rashi (+ nakshatra), Lagna. */
export interface BigThreeItem {
  role: "Sun" | "Moon" | "Lagna";
  sign: string | undefined;
  system: "sidereal" | "tropical";
  extra?: string;
}

/** `system` follows the user's astrology_system: western = tropical signs, vedic = sidereal (when the chart has it). */
export function bigThree(chart: BirthChart, system: "vedic" | "western" = "vedic"): BigThreeItem[] {
  const v = system === "vedic" ? chart.chart_data.vedic : undefined;
  if (v) {
    const sun = v.planets.find((p) => findGraha(p.english)?.key === "sun");
    const moon = v.planets.find((p) => findGraha(p.english)?.key === "moon");
    return [
      { role: "Sun", sign: findSign(sun?.rashi_english ?? sun?.rashi)?.english, system: "sidereal" },
      { role: "Moon", sign: findSign(moon?.rashi_english ?? moon?.rashi)?.english, system: "sidereal", extra: v.moon_nakshatra?.name || undefined },
      { role: "Lagna", sign: findSign(v.lagna?.rashi_english ?? v.lagna?.rashi)?.english, system: "sidereal", extra: v.lagna ? undefined : "Needs birth time" },
    ];
  }
  const d = chart.chart_data;
  return [
    { role: "Sun", sign: findSign(d.sun_sign?.sign)?.english, system: "tropical" },
    { role: "Moon", sign: findSign(d.moon_sign?.sign)?.english, system: "tropical" },
    { role: "Lagna", sign: findSign(d.rising_sign?.sign)?.english, system: "tropical" },
  ];
}
