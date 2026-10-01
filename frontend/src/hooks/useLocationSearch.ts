import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { geocodingService } from "../services/geocoding";

export const geocodingKeys = {
  search: (q: string) => ["geocoding", "search", q] as const,
};

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

/**
 * Place search for LocationAutocomplete. Debounced 300 ms; stale requests are cancelled via the
 * query's AbortSignal. The contract requires >= 3 characters (api-contract G1).
 */
export function useLocationSearch(query: string, enabled: boolean) {
  const q = useDebouncedValue(query.trim(), 300);
  const active = enabled && q.length >= 3;
  const result = useQuery({
    queryKey: geocodingKeys.search(q.toLowerCase()),
    queryFn: ({ signal }) => geocodingService.search(q, signal),
    enabled: active,
    staleTime: 24 * 60 * 60 * 1000,
    retry: false,
  });
  return {
    ...result,
    /** True while the user is still typing (debounce pending) or a request is in flight. */
    isSearching: active && (result.isFetching || q !== query.trim()),
    debouncedQuery: q,
    active,
  };
}
