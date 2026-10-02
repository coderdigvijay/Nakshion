import fs from 'fs';import {wordPath,KERN} from './lib.mjs';
const f2=n=>+n.toFixed(2);
const h=wordPath('Nakshion',40,{kern:KERN}),s=wordPath('Nakshion',54,{kern:KERN});
const HW=Math.ceil(78+h.width),SW=Math.ceil(s.width);
const R=27.4;let dots=[];for(let k=0;k<27;k++){if(k===4)continue;const a=(-90+k*360/27)*Math.PI/180;dots.push([f2(32+R*Math.cos(a)),f2(32+R*Math.sin(a))]);}
const a4=(-90+4*360/27)*Math.PI/180,lamp=[f2(32+R*Math.cos(a4)),f2(32+R*Math.sin(a4))];
const base='/Users/digvijay/Desktop/Astrology/design-system/nakshion/logo/concept-a-lunar-dial/';
const cres=fs.readFileSync(base+'mark-dark.svg','utf8').match(/<path d="(M[^"]*A[^"]*Z)" fill="#EEF0FA"/)[1];
const cs=fs.readFileSync(base+'mark-small-dark.svg','utf8').match(/<path d="([^"]*)" fill="#EEF0FA"/)[1];
const tsx=`import { Link } from "react-router-dom";
import { cn } from "../../lib/utils";

/*
 * Nakshion logo: "Lunar Dial". A crescent Moon inside an orbit of 27 dots (the 27 nakshatras);
 * one gold dot is the lamp. The wordmark is Fraunces SemiBold converted to outlines and hand-kerned,
 * so it never depends on a font loading. Source of truth: design-system/nakshion/logo/.
 * Colours come from the theme tokens (fg / ai / accent), so dark and light work automatically.
 */

const DOTS: ReadonlyArray<readonly [number, number]> = ${JSON.stringify(dots)};
const LAMP = ${JSON.stringify(lamp)} as const;
const CRESCENT_FULL = ${JSON.stringify(cres)};
const CRESCENT_SMALL = ${JSON.stringify(cs)};
const WORD_HORIZONTAL = ${JSON.stringify(h.d)};
const WORD_STACKED = ${JSON.stringify(s.d)};
const HORIZONTAL_W = ${HW};
const STACKED_W = ${SW};
const STACKED_H = 134;

/** Mark height (px) from which the 27-dot orbit is drawn; below it the dots would turn to noise. */
const DETAIL_FROM = 44;

type Tone = "color" | "mono";
export type LogoVariant = "mark" | "horizontal" | "stacked";

function cls(tone: Tone, token: "fg" | "ai" | "accent") {
  return tone === "mono" ? "fill-current" : \`fill-\${token}\`;
}

function Mark({ detail, tone }: { detail: boolean; tone: Tone }) {
  if (!detail) {
    return (
      <>
        <path d={CRESCENT_SMALL} className={cls(tone, "fg")} />
        <circle cx="49.5" cy="14.5" r="6.8" className={cls(tone, "accent")} />
      </>
    );
  }
  return (
    <>
      <g className={cls(tone, "ai")}>
        {DOTS.map(([x, y]) => (
          <circle key={\`\${x}-\${y}\`} cx={x} cy={y} r="1.35" />
        ))}
      </g>
      <path d={CRESCENT_FULL} className={cls(tone, "fg")} />
      <circle cx={LAMP[0]} cy={LAMP[1]} r="3.9" className={cls(tone, "accent")} />
    </>
  );
}

interface LogoProps {
  variant?: LogoVariant;
  /** Mark height in px (the wordmark scales with it). Default 32. */
  size?: number;
  /** "mono" paints everything in currentColor (use on gold, photos, or one-colour print). */
  tone?: Tone;
  /** If set, the logo is a link to this route. */
  to?: string;
  className?: string;
}

/** Nakshion logo. Inline SVG, theme-aware, no animation. */
export function Logo({ variant = "horizontal", size = 32, tone = "color", to, className }: LogoProps) {
  const detail = size >= DETAIL_FROM;
  const [vw, vh] = variant === "mark" ? [64, 64] : variant === "horizontal" ? [HORIZONTAL_W, 64] : [STACKED_W, STACKED_H];
  const scale = size / 64;
  const art = (
    <svg
      viewBox={\`0 0 \${vw} \${vh}\`}
      width={Math.round(vw * scale)}
      height={Math.round(vh * scale)}
      className="shrink-0"
      aria-hidden={to ? true : undefined}
      role={to ? undefined : "img"}
      aria-label={to ? undefined : "Nakshion"}
      focusable="false"
    >
      {variant === "stacked" ? (
        <>
          <g transform={\`translate(\${(STACKED_W - 64) / 2} 0)\`}>
            <Mark detail={detail} tone={tone} />
          </g>
          <path transform="translate(0 124)" d={WORD_STACKED} className={cls(tone, "fg")} />
        </>
      ) : (
        <>
          <Mark detail={detail} tone={tone} />
          {variant === "horizontal" && <path transform="translate(78 45.5)" d={WORD_HORIZONTAL} className={cls(tone, "fg")} />}
        </>
      )}
    </svg>
  );
  if (!to) return <span className={cn("inline-flex", className)}>{art}</span>;
  return (
    <Link to={to} className={cn("focus-ring inline-flex min-h-11 items-center rounded-control", className)} aria-label="Nakshion home">
      {art}
    </Link>
  );
}

/** Custom kundali glyph for the Chart tab (MASTER §5.3). */
export function KundaliIcon({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinejoin="round">
      <rect x="3.5" y="3.5" width="17" height="17" rx="1.5" />
      <path d="M12 3.5 20.5 12 12 20.5 3.5 12Z M3.5 3.5l17 17 M20.5 3.5l-17 17" />
    </svg>
  );
}
`;
fs.mkdirSync('/Users/digvijay/Desktop/Astrology/design-system/nakshion/logo/integration',{recursive:true});
fs.writeFileSync('/Users/digvijay/Desktop/Astrology/design-system/nakshion/logo/integration/Logo.tsx',tsx);
