import { useState } from "react";
import { Check, Download, Share2 } from "lucide-react";
import { Dialog } from "../ui/Dialog";
import { Button } from "../ui/Button";
import { chartToPngBlob, downloadBlob } from "../../lib/exportChart";
import { toast } from "../../store/toastStore";

// Download as PNG / share. Birth details are never included unless the user ticks the box.
export interface ChartShareDialogProps {
  open: boolean;
  onClose: () => void;
  /** Returns the wheel's <svg> at the moment of export. */
  getSvg: () => SVGSVGElement | null;
  title: string;
  /** "14 Mar 1995 · 6:42 AM · Varanasi, India" — only used if the user opts in. */
  birthLine: string;
  /** Placement summary, no birth data. */
  summary: string;
}

export function ChartShareDialog({ open, onClose, getSvg, title, birthLine, summary }: ChartShareDialogProps) {
  const [includeBirth, setIncludeBirth] = useState(false);
  const [busy, setBusy] = useState<"download" | "share" | null>(null);

  const subtitle = includeBirth ? birthLine : "Vedic · sidereal (Lahiri)";
  const make = async () => {
    const svg = getSvg();
    if (!svg) throw new Error("The chart isn't ready yet.");
    return chartToPngBlob(svg, { title, subtitle });
  };
  const filename = `${title.replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "").toLowerCase() || "chart"}.png`;

  const download = async () => {
    setBusy("download");
    try {
      downloadBlob(await make(), filename);
      toast.success("Chart image saved");
    } catch (e) {
      toast.error("Couldn't save the image", e instanceof Error ? e.message : undefined);
    } finally {
      setBusy(null);
    }
  };

  const share = async () => {
    setBusy("share");
    const text = `${title} on Nakshion (Vedic, sidereal). ${summary}${includeBirth ? ` ${birthLine}` : ""}`;
    try {
      if (navigator.share) {
        const blob = await make().catch(() => null);
        const file = blob ? new File([blob], filename, { type: "image/png" }) : null;
        if (file && navigator.canShare?.({ files: [file] })) await navigator.share({ title: "My Nakshion chart", text, files: [file] });
        else await navigator.share({ title: "My Nakshion chart", text });
      } else {
        await navigator.clipboard.writeText(text);
        toast.success("Summary copied");
      }
    } catch (e) {
      // The user closing the share sheet is not an error.
      if (!(e instanceof DOMException && e.name === "AbortError")) toast.error("Couldn't share", "Try downloading the image instead.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Share or download your chart"
      description="Saves the chart picture as a PNG, or shares a short summary of the placements."
      presentation="auto"
      footer={
        <>
          <Button variant="secondary" leadingIcon={<Share2 aria-hidden="true" className="size-4" />} onClick={() => void share()} loading={busy === "share"}>
            Share
          </Button>
          <Button variant="primary" leadingIcon={<Download aria-hidden="true" className="size-4" />} onClick={() => void download()} loading={busy === "download"}>
            Download PNG
          </Button>
        </>
      }
    >
      <label className="flex min-h-11 cursor-pointer items-start gap-3">
        <span className="relative mt-0.5 inline-flex size-5 shrink-0">
          <input
            type="checkbox"
            checked={includeBirth}
            onChange={(e) => setIncludeBirth(e.target.checked)}
            className="peer focus-ring size-5 cursor-pointer appearance-none rounded-[6px] border border-border-strong bg-field checked:border-ai checked:bg-ai-fill"
          />
          <Check aria-hidden="true" className="pointer-events-none absolute inset-0.5 size-4 text-on-ai opacity-0 peer-checked:opacity-100" />
        </span>
        <span>
          <span className="block text-body text-fg">Include my birth date, time and place</span>
          <span className="block text-caption text-fg-muted">Off by default. Anyone who sees the image will see them.</span>
        </span>
      </label>
    </Dialog>
  );
}
