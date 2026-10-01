import { Fragment } from "react";

// Light, safe Markdown for AI replies (api-contract §2.3: **bold**, lists, no HTML).
// Renders React text nodes only — never dangerouslySetInnerHTML (rules §4).


function inline(text: string, keyBase: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(<strong key={`${keyBase}-${i++}`} className="font-semibold text-fg">{tok.slice(2, -2)}</strong>);
    else out.push(<code key={`${keyBase}-${i++}`} className="rounded-[4px] bg-elevated px-1 text-[0.95em]">{tok.slice(1, -1)}</code>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  // Single *emphasis* is shown as plain text (no italics: hard to read, absent in Devanagari).
  return out.map((n, idx) => (typeof n === "string" ? <Fragment key={`${keyBase}-t${idx}`}>{n.replace(/(^|\s)\*(\S[^*]*\S|\S)\*(?=\s|$|[.,;:!?])/g, "$1$2")}</Fragment> : n));
}

type Block =
  | { kind: "p"; text: string }
  | { kind: "h"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] };

function parse(src: string): Block[] {
  const blocks: Block[] = [];
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ kind: "p", text: para.join(" ") });
    para = [];
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    const h = /^#{1,6}\s+(.*)$/.exec(line);
    const ul = /^\s*[-*•]\s+(.*)$/.exec(line);
    const ol = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    const q = /^>\s?(.*)$/.exec(line);
    if (h) {
      flush();
      blocks.push({ kind: "h", text: h[1] });
    } else if (ul) {
      flush();
      const prev = blocks[blocks.length - 1];
      if (prev?.kind === "ul") prev.items.push(ul[1]);
      else blocks.push({ kind: "ul", items: [ul[1]] });
    } else if (ol) {
      flush();
      const prev = blocks[blocks.length - 1];
      if (prev?.kind === "ol") prev.items.push(ol[1]);
      else blocks.push({ kind: "ol", items: [ol[1]] });
    } else if (q) {
      flush();
      blocks.push({ kind: "quote", text: q[1] });
    } else {
      para.push(line.trim());
    }
  }
  flush();
  return blocks;
}

export function Markdown({ text }: { text: string }) {
  const blocks = parse(text);
  return (
    <div className="space-y-3 break-words [overflow-wrap:anywhere]">
      {blocks.map((b, i) => {
        const k = `b${i}`;
        switch (b.kind) {
          case "h":
            return (
              <h3 key={k} className="pt-1 text-[1.25rem] text-fg">
                {inline(b.text, k)}
              </h3>
            );
          case "quote":
            return (
              <blockquote key={k} className="border-l-[3px] border-ai pl-3 text-fg-secondary">
                {inline(b.text, k)}
              </blockquote>
            );
          case "ul":
            return (
              <ul key={k} className="list-disc space-y-2 pl-5 marker:text-fg-muted">
                {b.items.map((it, j) => (
                  <li key={j}>{inline(it, `${k}-${j}`)}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={k} className="list-decimal space-y-2 pl-5 marker:text-fg-muted">
                {b.items.map((it, j) => (
                  <li key={j}>{inline(it, `${k}-${j}`)}</li>
                ))}
              </ol>
            );
          default:
            return <p key={k}>{inline(b.text, k)}</p>;
        }
      })}
    </div>
  );
}
