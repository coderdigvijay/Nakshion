import { useId, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, MapPin, Search } from "lucide-react";
import { cn } from "../../lib/utils";
import { FieldLabel } from "../ui/Field";
import { controlStyles } from "../ui/styles";
import { Button } from "../ui/Button";
import { useLocationSearch } from "../../hooks/useLocationSearch";
import { formatCoords, formatUtcOffset } from "../../lib/astro";
import type { GeocodingResult } from "../../types";

// COMPONENTS.md → LocationAutocomplete. ARIA 1.2 combobox; must-select rule; resolved
// timezone + coordinates read-back (P2, gap G-05).

export interface LocationAutocompleteProps {
  label?: string;
  value: GeocodingResult | null;
  onChange: (v: GeocodingResult | null) => void;
  onBlur?: () => void;
  error?: string;
  /** Civil birth date, so the UTC offset shown is the one in force on that day. */
  onDate?: Date | null;
  placeholder?: string;
}

function highlight(name: string, q: string) {
  const i = name.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return name;
  return (
    <>
      {name.slice(0, i)}
      <span className="font-semibold">{name.slice(i, i + q.length)}</span>
      {name.slice(i + q.length)}
    </>
  );
}

export function LocationAutocomplete({ label = "Place of birth", value, onChange, onBlur, error, onDate, placeholder = "Start typing a city" }: LocationAutocompleteProps) {
  const id = useId();
  const listId = `${id}-list`;
  const [typed, setText] = useState(value?.name ?? "");
  // A selected place always shows its full name (also when a parent restores the value).
  const text = value ? value.name : typed;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const search = useLocationSearch(text, open && !value);
  const results = (search.data?.results ?? []).slice(0, 6);
  const [touchedEmpty, setTouchedEmpty] = useState(false);

  const select = (r: GeocodingResult) => {
    onChange(r);
    setText(r.name);
    setOpen(false);
    setActive(-1);
  };

  const showList = open && !value && search.active;
  const status = search.isSearching ? (
    <Loader2 aria-hidden="true" className="size-5 animate-spin motion-reduce:animate-none" />
  ) : value ? (
    <CheckCircle2 aria-hidden="true" className="size-5 text-success" />
  ) : search.isError || error ? (
    <AlertCircle aria-hidden="true" className="size-5 text-danger" />
  ) : (
    <Search aria-hidden="true" className="size-5" />
  );

  const liveText = !showList
    ? ""
    : search.isSearching
      ? "Searching places"
      : search.isError
        ? "Place search is unavailable right now."
        : `${results.length} ${results.length === 1 ? "place" : "places"} found`;

  const msg = error ?? (touchedEmpty && !value && text.trim().length > 0 ? "Choose a place from the list so we can find its exact coordinates." : undefined);

  return (
    <div className="relative">
      <FieldLabel htmlFor={`${id}-input`}>{label}</FieldLabel>
      <div className="relative">
        <MapPin aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-fg-muted" />
        <input
          id={`${id}-input`}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && active >= 0 ? `${id}-opt-${active}` : undefined}
          aria-invalid={msg ? true : undefined}
          aria-describedby={`${id}-msg`}
          autoComplete="off"
          placeholder={placeholder}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (value) onChange(null);
            setOpen(true);
            setActive(-1);
            setTouchedEmpty(false);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            // Delay so a click on an option registers first.
            setTimeout(() => {
              setOpen(false);
              setTouchedEmpty(true);
              onBlur?.();
            }, 120);
          }}
          onKeyDown={(e) => {
            if (!showList || results.length === 0) {
              if (e.key === "Escape") setOpen(false);
              return;
            }
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => (a + 1) % results.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => (a <= 0 ? results.length - 1 : a - 1));
            } else if (e.key === "Enter" && active >= 0) {
              e.preventDefault();
              select(results[active]);
            } else if (e.key === "Tab" && active >= 0) {
              select(results[active]);
            } else if (e.key === "Escape") {
              e.preventDefault();
              setOpen(false);
            }
          }}
          className={cn(controlStyles, "h-12 pl-11 pr-12", msg ? "border-danger" : "border-border-strong")}
        />
        <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-fg-muted">{status}</span>
      </div>

      <span role="status" aria-live="polite" className="sr-only">
        {liveText}
      </span>

      {showList && (
        <div className="absolute inset-x-0 top-full z-40 mt-2 max-h-80 overflow-y-auto rounded-card border border-border bg-overlay p-1 shadow-e2">
          {search.isError ? (
            <div className="p-3">
              <p className="text-body-sm text-fg">Place search is unavailable right now.</p>
              <Button variant="ghost" size="sm" className="mt-2" onMouseDown={(e) => e.preventDefault()} onClick={() => void search.refetch()}>
                Retry
              </Button>
            </div>
          ) : search.isSearching && results.length === 0 ? (
            <p className="p-3 text-body-sm text-fg-muted">Searching…</p>
          ) : results.length === 0 ? (
            <p className="p-3 text-body-sm text-fg-secondary">
              {search.data?.degraded
                ? "Location search is having trouble. Try again in a minute."
                : `No places match “${search.debouncedQuery}”. Check the spelling or try the nearest larger city.`}
            </p>
          ) : null}
          <ul id={listId} role="listbox" aria-label="Matching places" className={cn(results.length === 0 && "hidden")}>
            {results.map((r, i) => {
              const [city, ...rest] = r.name.split(", ");
              return (
                <li
                  key={`${r.lat},${r.lon},${r.name}`}
                  id={`${id}-opt-${i}`}
                  role="option"
                  aria-selected={active === i}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => select(r)}
                  onMouseEnter={() => setActive(i)}
                  className={cn("flex min-h-14 cursor-pointer items-center gap-3 rounded-control px-3 py-2", active === i ? "bg-ai-subtle" : "hover:bg-elevated")}
                >
                  <MapPin aria-hidden="true" className="size-4 shrink-0 text-fg-muted" />
                  <span className="min-w-0">
                    <span className="block truncate text-[0.9375rem] text-fg">{highlight(city, search.debouncedQuery)}</span>
                    {rest.length > 0 && <span className="block truncate text-caption text-fg-muted">{rest.join(", ")}</span>}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div id={`${id}-msg`} className="mt-1.5 space-y-1">
        {value && (
          <p className="text-caption tabular text-fg-secondary">
            {value.timezone ? `${value.timezone} · ${formatUtcOffset(value.timezone, onDate ?? new Date())} · ` : "Time zone set from coordinates · "}
            {formatCoords(value.lat, value.lon)}
          </p>
        )}
        {msg && (
          <p className="flex items-start gap-1.5 text-caption text-danger">
            <AlertCircle aria-hidden="true" className="mt-px size-4 shrink-0" />
            {msg}
          </p>
        )}
        <p className="text-caption text-fg-muted">
          <a href="https://locationiq.com" target="_blank" rel="noopener noreferrer" className="focus-ring inline-flex min-h-6 items-center rounded-[4px] underline-offset-4 hover:underline">
            Search by LocationIQ.com
          </a>
        </p>
      </div>
    </div>
  );
}
