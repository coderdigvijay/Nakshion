import api from "./api";
import type { DailyHoroscope, PersonalReading } from "../types";

export const horoscopeService = {
  getDaily: (sign: string) => api.get<DailyHoroscope>("/horoscopes/daily", { params: { sign } }),

  /** R3: personal reading from the primary chart (auth required, verified email). */
  getPersonalToday: () => api.get<PersonalReading>("/horoscopes/personal/today"),
};
