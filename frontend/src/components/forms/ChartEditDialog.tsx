import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Dialog } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { Input } from "../ui/Field";
import { ErrorState } from "../ui/EmptyState";
import { BirthDateField } from "./BirthDateField";
import { BirthTimeField } from "./BirthTimeField";
import { LocationAutocomplete } from "./LocationAutocomplete";
import { useUpdateChart } from "../../hooks/useCharts";
import { toast } from "../../store/toastStore";
import { birthDetailsSchema, chartToFormValues, dateFromParts, hasExactTime, timezoneHint, toIsoDate, toTime24, type BirthDetails } from "../../lib/birthForm";
import type { BirthChart } from "../../types";

// Edit uses the same fields as onboarding (profile.md → "Edit opens Dialog/Sheet"). C4 recomputes the chart.
export function ChartEditDialog({ chart, onClose }: { chart: BirthChart | null; onClose: () => void }) {
  return (
    <Dialog open={!!chart} onClose={onClose} title={chart ? `Edit ${chart.name}'s chart` : "Edit chart"} presentation="auto" size="form">
      {chart && <EditForm key={chart.id} chart={chart} onClose={onClose} />}
    </Dialog>
  );
}

function EditForm({ chart, onClose }: { chart: BirthChart; onClose: () => void }) {
  const update = useUpdateChart();
  const form = useForm<BirthDetails>({ resolver: zodResolver(birthDetailsSchema), mode: "onTouched", defaultValues: chartToFormValues(chart) });
  const { control, register, formState, clearErrors } = form;
  const birthDate = dateFromParts(useWatch({ control, name: "date" }));

  const submit = form.handleSubmit((v) => {
    if (!v.place) return;
    update.mutate(
      {
        id: chart.id,
        payload: {
          name: v.name.trim(),
          date_of_birth: toIsoDate(v.date),
          time_of_birth: toTime24(v.time),
          has_exact_time: hasExactTime(v.time),
          birth_place_name: v.place.name,
          latitude: v.place.lat,
          longitude: v.place.lon,
          timezone: timezoneHint(v.place),
          is_primary: chart.is_primary,
        },
      },
      {
        onSuccess: () => {
          toast.success("Chart updated", "Your readings will use the new details.");
          onClose();
        },
      },
    );
  });

  return (
    <form noValidate onSubmit={submit} className="space-y-6 pb-2">
      <Input label="Name" error={formState.errors.name?.message} {...register("name")} />
      <Controller control={control} name="date" render={({ field, fieldState }) => <BirthDateField value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} />} />
      <Controller
        control={control}
        name="time"
        render={({ field, fieldState }) => (
          <BirthTimeField
            value={field.value}
            onChange={(v) => {
              if (v.unknown !== field.value.unknown) clearErrors("time");
              field.onChange(v);
            }}
            onBlur={field.onBlur}
            error={fieldState.error?.message}
          />
        )}
      />
      <Controller control={control} name="place" render={({ field, fieldState }) => <LocationAutocomplete value={field.value} onChange={field.onChange} onBlur={field.onBlur} error={fieldState.error?.message} onDate={birthDate} />} />
      {update.isError && <ErrorState compact error={update.error} what="the update" onRetry={() => void submit()} />}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={update.isPending}>
          Save changes
        </Button>
      </div>
    </form>
  );
}
