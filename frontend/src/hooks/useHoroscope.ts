import { useQuery } from "@tanstack/react-query";
import { horoscopeService } from "../services/horoscope";

export const horoscopeKeys = {
  all: ["horoscope"] as const,
  daily: (sign: string) => [...horoscopeKeys.all, "daily", sign] as const,
  personal: () => [...horoscopeKeys.all, "personal"] as const,
};

/** R3 personal reading. Not retried: 403/409 are states, not blips (the dashboard falls back to R1). */
export function usePersonalReading(enabled: boolean) {
  return useQuery({
    queryKey: horoscopeKeys.personal(),
    queryFn: async () => (await horoscopeService.getPersonalToday()).data,
    enabled,
    staleTime: 60 * 60 * 1000,
    retry: false,
    // A quick template reading is upgraded to the AI one in the background: poll quietly (initial
    // fetch + 3 retries). Background tabs are skipped (refetchIntervalInBackground defaults to false).
    refetchInterval: (query) => (query.state.data?.generated_by === "template" && query.state.dataUpdateCount < 4 ? 12_000 : false),
  });
}

/**
 * R1 daily horoscope by tropical sun sign (MVP). Gap G-08: the personal reading (R3) is v1-add
 * and not wired yet, so the UI labels this as a general, sun-sign reading.
 */
export function useDailyHoroscope(sign: string | undefined) {
  const s = sign?.toLowerCase() ?? "";
  return useQuery({
    queryKey: horoscopeKeys.daily(s),
    queryFn: async () => (await horoscopeService.getDaily(s)).data,
    enabled: s.length > 0,
    staleTime: 60 * 60 * 1000,
  });
}
