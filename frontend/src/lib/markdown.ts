// Streaming helpers for AI replies.

/** Fact markers the model may emit, e.g. [VN.MOON.NAK.ASHLESHA]. */
const FACT_MARKER = /\s?\[[A-Z0-9_.]{3,}\]/g;

export function extractFactMarkers(text: string): string[] {
  const out = new Set<string>();
  for (const m of text.matchAll(/\[([A-Z0-9_.]{3,})\]/g)) out.add(m[1]);
  return [...out];
}

/** "VN.MOON.NAK.ASHLESHA" -> "Moon · Nak · Ashlesha" (drops the leading namespace). */
export function humaniseFactId(id: string): string {
  const parts = id.split(".").slice(1);
  return (parts.length ? parts : id.split(".")).map((p) => p.charAt(0) + p.slice(1).toLowerCase()).join(" · ");
}

/** Removes complete markers, and hides a marker that is still arriving ("[VN.MO"). */
export function stripFactMarkers(text: string): string {
  return text.replace(FACT_MARKER, "").replace(/\s?\[[A-Z0-9_.]*$/, "");
}

/** Hides an unfinished trailing token while text is still arriving (buffered partial markdown). */
export function bufferPartial(text: string): string {
  let t = stripFactMarkers(text);
  const boldCount = (t.match(/\*\*/g) ?? []).length;
  if (boldCount % 2 === 1) t = t.slice(0, t.lastIndexOf("**")) + t.slice(t.lastIndexOf("**") + 2);
  // A lone trailing "#", "-" or "*" on a new line is probably the start of a block.
  return t.replace(/\n[#*\-\s]*$/, "\n");
}
