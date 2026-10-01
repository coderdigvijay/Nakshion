import { useQuery } from "@tanstack/react-query";
import { panchangService } from "../services/panchang";

export const panchangKeys = {
  all: ["panchang"] as const,
  day: (date: string, lat: number, lon: number) => [...panchangKeys.all, date, lat.toFixed(1), lon.toFixed(1)] as const,
};

/** C9 for the birthplace-independent "today" card: uses the chart's coordinates as the user's location. */
export function usePanchang(date: string, lat: number | undefined, lon: number | undefined) {
  const enabled = lat !== undefined && lon !== undefined;
  return useQuery({
    queryKey: panchangKeys.day(date, lat ?? 0, lon ?? 0),
    queryFn: async () => (await panchangService.get(date, lat ?? 0, lon ?? 0)).data,
    enabled,
    staleTime: 6 * 60 * 60 * 1000,
    retry: false,
  });
}
