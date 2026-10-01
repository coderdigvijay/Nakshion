import api from "./api";
import type { BirthChart, DashaResponse, TransitsResponse } from "../types";

export interface CreateChartPayload {
  name: string;
  date_of_birth: string;
  time_of_birth: string | null;
  has_exact_time: boolean;
  birth_place_name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  is_primary: boolean;
}

export const chartService = {
  create: (data: CreateChartPayload) =>
    api.post<BirthChart>("/charts/", data),

  list: () => api.get<BirthChart[]>("/charts/"),

  get: (id: string) => api.get<BirthChart>(`/charts/${id}`),

  /** C4: same body as create; all fields required; recomputes chart_data. */
  update: (id: string, data: CreateChartPayload) => api.put<BirthChart>(`/charts/${id}`, data),

  /** C7 personal transits. `from` defaults to today in the user's zone. */
  transits: (id: string, params: { from?: string; days?: number } = {}) =>
    api.get<TransitsResponse>(`/charts/${id}/transits`, { params }),

  /** C8 Vimshottari timeline. levels=3 is rejected by the server (422), so only 2 is requested. */
  dasha: (id: string) => api.get<DashaResponse>(`/charts/${id}/dasha`, { params: { levels: 2 } }),

  /** C5: 204. The server promotes another chart if the primary was deleted. */
  remove: (id: string) => api.delete(`/charts/${id}`),

  /** C6: atomic primary flip. */
  setPrimary: (id: string) => api.post<BirthChart>(`/charts/${id}/primary`),
};
