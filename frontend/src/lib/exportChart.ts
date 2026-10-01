// Client-side "chart as PNG": serialise the wheel SVG, rasterise it on a canvas, frame it with a
// title, an optional birth-data line and a small Nakshion mark. No dependencies. Styling that
// comes from CSS classes/variables is inlined from computed styles because a standalone SVG image
// cannot see the page's stylesheet; web fonts are not available inside an SVG image, so text uses
// the system sans fallback.

const INLINE_PROPS = [
  "fill", "stroke", "stroke-width", "stroke-opacity", "fill-opacity", "opacity",
  "font-size", "font-weight", "text-anchor", "dominant-baseline", "stroke-linecap", "stroke-linejoin",
] as const;

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function inlineStyles(source: Element, target: Element) {
  const cs = getComputedStyle(source);
  const decl: string[] = [];
  for (const p of INLINE_PROPS) decl.push(`${p}:${cs.getPropertyValue(p)}`);
  decl.push("font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif");
  target.setAttribute("style", decl.join(";"));
  target.removeAttribute("class");
}

function serialiseSvg(svg: SVGSVGElement, px: number): string {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const src = [svg, ...svg.querySelectorAll("*")];
  const dst = [clone, ...clone.querySelectorAll("*")];
  src.forEach((el, i) => dst[i] && inlineStyles(el, dst[i]));
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(px));
  clone.setAttribute("height", String(px));
  clone.removeAttribute("style");
  clone.removeAttribute("role");
  return new XMLSerializer().serializeToString(clone);
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("The chart image couldn't be prepared."));
    img.src = url;
  });
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (ctx.measureText(next).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

export interface ChartImageOptions {
  title: string;
  /** Shown under the title. Pass birth details here only if the user opted in. */
  subtitle: string;
}

export async function chartToPngBlob(svg: SVGSVGElement, { title, subtitle }: ChartImageOptions): Promise<Blob> {
  const W = 1080;
  const pad = 80;
  const wheel = W - pad * 2;
  const bg = cssVar("--nk-bg", "#0B0D1A");
  const surface = cssVar("--nk-bg-sunken", "#070812");
  const fg = cssVar("--nk-fg", "#EEF0FA");
  const muted = cssVar("--nk-fg-muted", "#8F95B8");
  const accent = cssVar("--nk-accent", "#F2B544");

  const svgText = serialiseSvg(svg, wheel);
  const img = await loadImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText)}`);

  const canvas = document.createElement("canvas");
  const probe = canvas.getContext("2d");
  if (!probe) throw new Error("Your browser can't create images here.");
  probe.font = "26px Inter, system-ui, sans-serif";
  const subLines = wrapText(probe, subtitle, W - pad * 2);
  const headerH = 190 + (subLines.length - 1) * 36;
  const H = headerH + wheel + 170;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Your browser can't create images here.");

  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = fg;
  ctx.font = "500 56px Fraunces, Georgia, serif";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(title, pad, 110);
  ctx.fillStyle = muted;
  ctx.font = "26px Inter, system-ui, sans-serif";
  subLines.forEach((l, i) => ctx.fillText(l, pad, 160 + i * 36));

  ctx.fillStyle = surface;
  ctx.fillRect(pad - 12, headerH - 12, wheel + 24, wheel + 24);
  ctx.drawImage(img, pad, headerH, wheel, wheel);

  // Nakshion mark + wordmark
  const y = headerH + wheel + 90;
  ctx.strokeStyle = accent;
  ctx.lineWidth = 3;
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.arc(pad + 22, y - 10, 22, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  const cx = pad + 22;
  const cy = y - 10;
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? 14 : 6;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    ctx[i === 0 ? "moveTo" : "lineTo"](cx + Math.cos(a) * r, cy + Math.sin(a) * r);
  }
  ctx.closePath();
  ctx.stroke();
  ctx.fillStyle = fg;
  ctx.font = "500 38px Fraunces, Georgia, serif";
  ctx.fillText("Nakshion", pad + 60, y);
  ctx.fillStyle = muted;
  ctx.font = "22px Inter, system-ui, sans-serif";
  ctx.fillText("Vedic · sidereal (Lahiri) · guidance, not certainty", pad, y + 48);

  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Couldn't create the image."))), "image/png"));
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
