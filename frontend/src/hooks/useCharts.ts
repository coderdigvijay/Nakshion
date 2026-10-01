import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chartService, type CreateChartPayload } from "../services/charts";
import type { BirthChart } from "../types";

export const chartKeys = {
  all: ["charts"] as const,
  list: () => [...chartKeys.all, "list"] as const,
  detail: (id: string) => [...chartKeys.all, "detail", id] as const,
};

export function useCharts() {
  return useQuery({
    queryKey: chartKeys.list(),
    queryFn: async () => (await chartService.list()).data,
  });
}

/**
 * The user's own primary chart, or null. Never falls back to charts[0]: saved people can't be primary
 * (422 PRIMARY_MUST_BE_SELF), and a user who deleted their own chart may have only saved people left.
 */
export function pickPrimaryChart(charts: BirthChart[] | undefined): BirthChart | null {
  return charts?.find((c) => c.is_primary) ?? null;
}

const PERSON_LABELS = new Set(["partner", "friend", "family", "coworker"]);

/** True for charts saved as other people (compatibility partners, friends, family, coworkers). */
export function isSavedPerson(c: BirthChart): boolean {
  return !c.is_primary && PERSON_LABELS.has(c.relationship_label);
}

/** The user's own charts: primary, "self", and extra charts they added themselves ("other"). */
export function ownCharts(charts: BirthChart[] | undefined): BirthChart[] {
  return (charts ?? []).filter((c) => !isSavedPerson(c));
}

/** People saved through compatibility. Never primary, never used for "your" readings. */
export function savedPeople(charts: BirthChart[] | undefined): BirthChart[] {
  return (charts ?? []).filter(isSavedPerson);
}

export function useTransits(chartId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: [...chartKeys.all, "transits", chartId ?? ""] as const,
    queryFn: async () => (await chartService.transits(chartId ?? "")).data,
    enabled: !!chartId && enabled,
    staleTime: 60 * 60 * 1000,
  });
}

export function useDasha(chartId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: [...chartKeys.all, "dasha", chartId ?? ""] as const,
    queryFn: async () => (await chartService.dasha(chartId ?? "")).data,
    enabled: !!chartId && enabled,
    staleTime: 60 * 60 * 1000,
  });
}

export function useCreateChart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateChartPayload) => (await chartService.create(payload)).data,
    onSuccess: (chart) => {
      qc.setQueryData(chartKeys.detail(chart.id), chart);
      void qc.invalidateQueries({ queryKey: chartKeys.all });
      // Daily reading is keyed by sign and depends on the primary chart.
      void qc.invalidateQueries({ queryKey: ["horoscope"] });
    },
  });
}

function invalidateChartDerived(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: chartKeys.all });
  void qc.invalidateQueries({ queryKey: ["horoscope"] });
}

export function useUpdateChart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; payload: CreateChartPayload }) => (await chartService.update(v.id, v.payload)).data,
    onSuccess: (chart) => {
      qc.setQueryData(chartKeys.detail(chart.id), chart);
      invalidateChartDerived(qc);
      // Compatibility reports and chats that used this chart are now out of date.
      void qc.invalidateQueries({ queryKey: ["compatibility"] });
    },
  });
}

export function useDeleteChart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await chartService.remove(id);
      return id;
    },
    onSuccess: (id) => {
      qc.removeQueries({ queryKey: chartKeys.detail(id) });
      invalidateChartDerived(qc);
      // Reports cascade; conversations keep their messages but lose the chart link.
      void qc.invalidateQueries({ queryKey: ["compatibility"] });
      void qc.invalidateQueries({ queryKey: ["chat"] });
    },
  });
}

export function useSetPrimaryChart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await chartService.setPrimary(id)).data,
    onSuccess: () => invalidateChartDerived(qc),
  });
}
