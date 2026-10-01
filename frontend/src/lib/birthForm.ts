// Shared birth-details model + Zod schema for onboarding and compatibility (AUDIT #3).
import { z } from "zod";
import type { BirthChart, GeocodingResult } from "../types";

export const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export type ApproxWindow = "morning" | "afternoon" | "evening" | "night" | "unknown";

/** Representative time sent for an approximate window (has_exact_time=false → engine flags `approximate`). */
export const APPROX_TIME: Record<Exclude<ApproxWindow, "unknown">, string> = {
  morning: "09:00",
  afternoon: "14:30",
  evening: "19:00",
  night: "01:30",
};

export const APPROX_LABEL: Record<ApproxWindow, string> = {
  morning: "Morning (6–12)",
  afternoon: "Afternoon (12–5)",
  evening: "Evening (5–9)",
  night: "Night (9–6)",
  unknown: "No idea",
};

export interface BirthDateValue {
  day: string;
  month: string; // "1".."12" or ""
  year: string;
}

export interface BirthTimeValue {
  hour: string; // "1".."12"
  minute: string; // "00".."59"
  period: "AM" | "PM";
  unknown: boolean;
  approx: ApproxWindow | "";
}

export const emptyDate: BirthDateValue = { day: "", month: "", year: "" };
export const emptyTime: BirthTimeValue = { hour: "", minute: "", period: "AM", unknown: false, approx: "" };

export function dateFromParts(v: BirthDateValue): Date | null {
  const d = Number(v.day);
  const m = Number(v.month);
  const y = Number(v.year);
  if (!Number.isInteger(d) || !Number.isInteger(m) || !Number.isInteger(y) || v.year.length !== 4) return null;
  const date = new Date(y, m - 1, d);
  if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) return null;
  return date;
}

export function toIsoDate(v: BirthDateValue): string {
  return `${v.year.padStart(4, "0")}-${v.month.padStart(2, "0")}-${v.day.padStart(2, "0")}`;
}

/** Returns "HH:MM" (24h) or null when the time is unknown. */
export function toTime24(v: BirthTimeValue): string | null {
  if (v.unknown) return v.approx && v.approx !== "unknown" ? APPROX_TIME[v.approx] : null;
  let h = Number(v.hour) % 12;
  if (v.period === "PM") h += 12;
  return `${String(h).padStart(2, "0")}:${v.minute.padStart(2, "0")}`;
}

export function hasExactTime(v: BirthTimeValue): boolean {
  return !v.unknown;
}

export const dateSchema = z
  .object({ day: z.string(), month: z.string(), year: z.string() })
  .superRefine((v, ctx) => {
    const d = dateFromParts(v);
    const today = new Date();
    if (!d || d.getFullYear() < 1900 || d > today) {
      ctx.addIssue({ code: "custom", message: "Enter a real date between 1900 and today." });
    }
  });

export const timeSchema = z
  .object({
    hour: z.string(),
    minute: z.string(),
    period: z.enum(["AM", "PM"]),
    unknown: z.boolean(),
    approx: z.enum(["morning", "afternoon", "evening", "night", "unknown", ""]),
  })
  .superRefine((v, ctx) => {
    if (v.unknown) {
      if (!v.approx) ctx.addIssue({ code: "custom", message: "Choose roughly when, or pick “No idea”." });
      return;
    }
    const h = Number(v.hour);
    const m = Number(v.minute);
    if (!v.hour || !v.minute || !Number.isInteger(h) || !Number.isInteger(m) || h < 1 || h > 12 || m < 0 || m > 59) {
      ctx.addIssue({ code: "custom", message: "Hour 1–12 and minute 0–59." });
    }
  });

export const placeSchema = z.custom<GeocodingResult | null>().refine((v) => !!v && Number.isFinite(v.lat) && Number.isFinite(v.lon), {
  message: "Choose a place from the list so we can find its exact coordinates.",
});

export const nameSchema = z.string().trim().min(1, "Enter a name.").max(100, "Keep the name under 100 characters.");

export const birthDetailsSchema = z.object({
  name: nameSchema,
  date: dateSchema,
  time: timeSchema,
  place: placeSchema,
});

export type BirthDetails = z.infer<typeof birthDetailsSchema>;

/** Timezone hint sent to the API. The server resolves the real zone from lat/lon (G-05). */
export function timezoneHint(place: GeocodingResult): string {
  return place.timezone || "UTC";
}

function approxWindowFor(hhmm: string): ApproxWindow {
  const h = Number(hhmm.slice(0, 2));
  if (h >= 6 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 21) return "evening";
  return "night";
}

/** Rebuild form values from a saved chart (edit dialog). */
export function chartToFormValues(chart: BirthChart): BirthDetails {
  const [y, m, d] = chart.date_of_birth.split("-");
  let time: BirthTimeValue = { ...emptyTime };
  if (chart.time_of_birth && chart.has_exact_time) {
    const h24 = Number(chart.time_of_birth.slice(0, 2));
    time = {
      hour: String(h24 % 12 === 0 ? 12 : h24 % 12),
      minute: chart.time_of_birth.slice(3, 5),
      period: h24 >= 12 ? "PM" : "AM",
      unknown: false,
      approx: "",
    };
  } else {
    time = { ...emptyTime, unknown: true, approx: chart.time_of_birth ? approxWindowFor(chart.time_of_birth) : "unknown" };
  }
  return {
    name: chart.name,
    date: { day: String(Number(d)), month: String(Number(m)), year: y },
    time,
    place: { name: chart.birth_place_name, lat: chart.latitude, lon: chart.longitude, timezone: chart.timezone },
  };
}
