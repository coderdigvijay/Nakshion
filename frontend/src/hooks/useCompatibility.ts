import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { compatibilityService, type CalculateCompatibilityPayload } from "../services/compatibility";
import { chartKeys } from "./useCharts";

export const compatibilityKeys = {
  all: ["compatibility"] as const,
  list: () => [...compatibilityKeys.all, "list"] as const,
  detail: (id: string) => [...compatibilityKeys.all, "detail", id] as const,
};

export function useCompatibilityReports() {
  return useQuery({
    queryKey: compatibilityKeys.list(),
    queryFn: async () => (await compatibilityService.list()).data,
  });
}

export function useCompatibilityReport(id: string | null) {
  return useQuery({
    queryKey: compatibilityKeys.detail(id ?? ""),
    queryFn: async () => (await compatibilityService.get(id ?? "")).data,
    enabled: !!id,
  });
}

export function useDeleteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await compatibilityService.remove(id);
      return id;
    },
    onSuccess: (id) => {
      qc.removeQueries({ queryKey: compatibilityKeys.detail(id) });
      void qc.invalidateQueries({ queryKey: compatibilityKeys.list() });
    },
  });
}

export function useCalculateCompatibility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CalculateCompatibilityPayload) => (await compatibilityService.calculate(payload)).data,
    onSuccess: (report) => {
      qc.setQueryData(compatibilityKeys.detail(report.id), report);
      void qc.invalidateQueries({ queryKey: compatibilityKeys.list() });
      // K1 creates (or reuses) a partner chart, so the chart list changed too.
      void qc.invalidateQueries({ queryKey: chartKeys.all });
    },
  });
}
