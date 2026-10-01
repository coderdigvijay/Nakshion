import api from "./api";
import type { GeocodingResult } from "../types";

export interface GeocodingResponse {
  results: GeocodingResult[];
  /** [v1-add] true when both providers failed (api-contract G1). */
  degraded?: boolean;
}

export const geocodingService = {
  search: async (query: string, signal?: AbortSignal): Promise<GeocodingResponse> => {
    const res = await api.get<GeocodingResponse | GeocodingResult[]>("/geocoding/search", {
      params: { q: query },
      signal,
    });
    // The contract sends { results }; tolerate a bare array as the old frontend did.
    return Array.isArray(res.data) ? { results: res.data } : { results: res.data.results ?? [], degraded: res.data.degraded };
  },
};
