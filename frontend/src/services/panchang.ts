import api from "./api";
import type { Panchang } from "../types";

export const panchangService = {
  /** C9 (public). Server rounds lat/lon to 0.1 degrees for caching. */
  get: (date: string, lat: number, lon: number) => api.get<Panchang>("/panchang", { params: { date, lat, lon } }),
};
