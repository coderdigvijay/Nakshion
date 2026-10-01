import api from "./api";
import type { CompatibilityReport, RelationshipType } from "../types";

export interface CalculateCompatibilityPayload {
  chart1_id: string;
  partner_name: string;
  partner_date_of_birth: string;
  partner_time_of_birth: string | null;
  partner_has_exact_time: boolean;
  partner_birth_place_name: string;
  partner_latitude: number;
  partner_longitude: number;
  /** A hint only; the server resolves the zone from lat/lon (api-contract K1, gap G-05). */
  partner_timezone: string;
  relationship_type: RelationshipType;
}

export const compatibilityService = {
  calculate: (data: CalculateCompatibilityPayload) => api.post<CompatibilityReport>("/compatibility/", data),

  list: () => api.get<CompatibilityReport[]>("/compatibility/"),

  get: (id: string) => api.get<CompatibilityReport>(`/compatibility/${id}`),

  /** K4: 204. The partner chart is kept. */
  remove: (id: string) => api.delete(`/compatibility/${id}`),
};
