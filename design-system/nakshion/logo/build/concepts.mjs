import fs from 'fs';import {markSvg,lockup,png,CONCEPTS,PAL} from './lib.mjs';
const ROOT='/Users/digvijay/Desktop/Astrology/design-system/nakshion/logo';
const inl=(s,cls='')=>s.replace(/ width="\d+" height="\d+"/,'').replace('<svg ',`<svg class="${cls}" focusable="false" `);
const mk=(c,v,th,px)=>inl(markSvg(c,v,th),'m').replace('class="m"',`class="m" style="width:${px}px;height:${px}px"`);
const lk=(c,k,th,h,size='full')=>inl(lockup(c,k,th,{size}),'l').replace('class="l"',`class="l" style="height:${h}px"`);
const mono=(c,v)=>inl(markSvg(c,v,'mono'),'m');
const tile=(c,px,v='small')=>{const s=0.78;return `<span class="tile" style="width:${px}px;height:${px}px;border-radius:${px*0.22}px"><span style="width:${px*s}px;height:${px*s}px;display:block">${inl(markSvg(c,v,'dark'),'m').replace('class="m"','class="m" style="width:100%;height:100%"')}</span></span>`};
const favPng=(c,px)=>{const t=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="13" fill="#0B0D1A"/><g transform="translate(9 9) scale(.86)">${markSvg(c,'small','dark').replace(/^<svg[^>]*>/,'').replace('</svg>','').replace(/<title>.*?<\/title>/,'')}</g></svg>`;return 'data:image/png;base64,'+png(t,px).toString('base64')};
const info={
 a:{rank:1,tag:'Recommended',why:'27 dots are the 27 mansions the Moon walks through; one gold dot is the nakshatra it is in tonight. The crescent opens toward the lamp. It reads as an observatory dial or orbit, not a sun-ray icon, and it holds at 16 px as crescent + lamp (the dots are an optical-size detail that appears from 48 px).',risk:'Crescent shapes are common in the category; the dotted orbit and gold lamp are what make it ownable. The gold dot is round (not a star) to avoid any crescent-and-star flag association.'},
 b:{rank:2,tag:'Strong runner-up',why:'An N drawn as a constellation: three nodes, fine lines, and a single gold star as the lamp. Very legible at 16 px, and it literally spells the name.',risk:'The "N plus sparkle" idea is the closest to the category cliché (sparkle marks are everywhere in astrology apps) and a four-point star is easily confused with generic AI-sparkle icons.'},
 c:{rank:3,tag:'Distinctly Vedic, hardest to scale',why:'The North-Indian chart: square, diamond, the Lagna house lit in gold, a small moon in the lower house. The most culturally specific idea.',risk:'Falls apart at 16 px (the diamond lines merge), and it duplicates the Kundali glyph already used for the Chart tab, so the brand mark and a UI icon would collide.'}};
const sizes=[16,24,32,64,128];
function section(c){const C=CONCEPTS[c],i=info[c];
 const row=(th)=>`<div class="panel ${th}"><div class="sizes">${sizes.map(s=>`<figure>${mk(c,s<=32?'small':'full',th,s)}<figcaption>${s}px</figcaption></figure>`).join('')}</div>
  <div class="lock">${lk(c,'horizontal',th,56)}${lk(c,'stacked',th,96)}</div></div>`;
 return `<section id="${c}"><header><h2>${i.rank}. ${C.name} <span class="chip">${i.tag}</span></h2><p class="mono-id">${C.id}/</p></header>
 <p><strong>Idea.</strong> ${i.why}</p><p><strong>Risk.</strong> ${i.risk}</p>
 <div class="two">${row('dark')}${row('light')}</div>
 <h3>In context</h3>
 <div class="two ctx">
  <div class="nav dark"><span>${lk(c,'horizontal','dark',30,'small')}</span><nav><a>Today</a><a>Chart</a><a>Ask</a></nav><span class="btn">Sign in</span></div>
  <div class="nav light"><span>${lk(c,'horizontal','light',30,'small')}</span><nav><a>Today</a><a>Chart</a><a>Ask</a></nav><span class="btn">Sign in</span></div>
  <div class="tabs"><div class="tab"><img alt="" width="16" height="16" src="${favPng(c,16)}"><span>Nakshion</span></div><div class="tab"><img alt="" width="32" height="32" src="${favPng(c,32)}"><span>32px (retina)</span></div><small>Real resvg raster, shown at 1:1 CSS pixels</small></div>
  <div class="icons">${tile(c,120,'full')}${tile(c,60,'small')}${tile(c,40,'small')}<small>App tile, full mark at 120 and small at 60/40</small></div>
 </div>
 <h3>One colour, grayscale, colour-vision</h3>
 <div class="two">
  <div class="panel dark"><div class="sizes mono1" style="color:#EEF0FA"><figure>${mono(c,'small')}<figcaption>mono 32</figcaption></figure><figure>${mono(c,'full')}<figcaption>mono 64</figcaption></figure>${lk(c,'horizontal','mono',44)}</div></div>
  <div class="panel light"><div class="sizes mono1" style="color:#1A1830"><figure>${mono(c,'small')}<figcaption>mono 32</figcaption></figure><figure>${mono(c,'full')}<figcaption>mono 64</figcaption></figure>${lk(c,'horizontal','mono',44)}</div></div>
  <div class="panel dark" style="filter:grayscale(1)"><div class="sizes">${mk(c,'small','dark',32)}${mk(c,'full','dark',64)}${lk(c,'horizontal','dark',44)}<figcaption>grayscale</figcaption></div></div>
  <div class="panel dark" style="filter:url(#deut)"><div class="sizes">${mk(c,'small','dark',32)}${mk(c,'full','dark',64)}${lk(c,'horizontal','dark',44)}<figcaption>deuteranopia</figcaption></div></div>
  <div class="panel light" style="filter:url(#prot)"><div class="sizes">${mk(c,'small','light',32)}${mk(c,'full','light',64)}${lk(c,'horizontal','light',44)}<figcaption>protanopia</figcaption></div></div>
  <div class="panel gold"><div class="sizes">${mk(c,'small','light',32)}${mk(c,'full','light',64)}${lk(c,'horizontal','mono',44)}<figcaption>on gold tint: use the one-colour version</figcaption></div></div>
 </div></section>`;}
const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nakshion logo concepts</title><link rel="icon" href="data:,">
<style>
:root{--bg:#0B0D1A;--s:#14172B;--fg:#EEF0FA;--m:#B4B9D6;--gold:#F2B544;--ai:#A99BFF;--line:#2A2E4D}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
main{max-width:1200px;margin:0 auto;padding:40px 24px 80px}h1,h2,h3{font-family:Georgia,"Fraunces","Times New Roman",serif;font-weight:600;letter-spacing:-.01em}
h1{font-size:2.4rem;margin:0 0 4px}h2{font-size:1.7rem;margin:0}h3{font-size:1.1rem;margin:28px 0 10px;color:var(--m)}
p{max-width:75ch;color:var(--m)}p strong{color:var(--fg)}.lede{font-size:1.05rem}
section{border-top:1px solid var(--line);margin-top:48px;padding-top:28px}
.chip{font:600 .72rem/1 system-ui;letter-spacing:.06em;text-transform:uppercase;background:rgba(242,181,68,.14);color:var(--gold);padding:5px 9px;border-radius:99px;vertical-align:middle;margin-left:8px}
.mono-id{font:.8rem ui-monospace,Menlo,monospace;margin:2px 0 12px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.two{grid-template-columns:1fr}}
.panel{border-radius:14px;padding:20px;border:1px solid var(--line);min-height:150px}.panel.dark{background:#0B0D1A}.panel.light{background:#FAF7F0;border-color:#E3DCCB}.panel.gold{background:#F2B544;border-color:#E0A030;color:#1A1830}
.sizes{display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap}figure{margin:0;text-align:center}figcaption{font:.7rem system-ui;color:#8F95B8;margin-top:6px}.panel.light figcaption,.panel.gold figcaption{color:#625F7C}
.lock{display:flex;align-items:center;gap:36px;margin-top:22px;flex-wrap:wrap}.l,.m{display:block}.sizes>.l{align-self:center}
.nav{display:flex;align-items:center;justify-content:space-between;height:60px;padding:0 18px;border-radius:12px;border:1px solid var(--line)}.nav.dark{background:#0B0D1A}.nav.light{background:#FAF7F0;color:#1A1830;border-color:#E3DCCB}
.nav nav{display:flex;gap:18px;font-size:.9rem;opacity:.8}.btn{font-size:.85rem;font-weight:600;background:#F2B544;color:#1A1204;padding:7px 14px;border-radius:9px}
.tabs{background:#1C1F36;border-radius:12px;padding:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.tab{display:flex;gap:8px;align-items:center;background:#2A2E4D;border-radius:9px 9px 0 0;padding:8px 12px;font:.8rem system-ui;color:#EEF0FA}small{color:#8F95B8;font-size:.72rem}
.icons{display:flex;align-items:flex-end;gap:16px;background:#2A2E4D;border-radius:12px;padding:16px;flex-wrap:wrap}.tile{background:#0B0D1A;display:grid;place-items:center;box-shadow:0 6px 18px rgba(0,0,0,.4)}
.rank{width:100%;border-collapse:collapse;margin:16px 0}.rank td,.rank th{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;font-size:.95rem;vertical-align:top}.rank th{color:var(--m);font-weight:600}
.reco{background:var(--s);border:1px solid var(--line);border-radius:14px;padding:20px 24px}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<filter id="deut"><feColorMatrix type="matrix" values="0.625 0.375 0 0 0  0.7 0.3 0 0 0  0 0.3 0.7 0 0  0 0 0 1 0"/></filter>
<filter id="prot"><feColorMatrix type="matrix" values="0.567 0.433 0 0 0  0.558 0.442 0 0 0  0 0.242 0.758 0 0  0 0 0 1 0"/></filter></defs></svg>
<main>
<h1>Nakshion logo concepts</h1>
<p class="lede">Three directions for the Soft Night Editorial identity. Palette: night #0B0D1A, cream #EEF0FA, moonlit violet #A99BFF, one gold lamp #F2B544. Wordmark: Fraunces SemiBold converted to outlines and hand-kerned (no font needed); Latin only. Every mark has a full version (48 px and up) and an optical small version (16 to 32 px).</p>
<div class="reco"><h2 style="font-size:1.3rem">Ranking and recommendation</h2>
<table class="rank"><tr><th>#</th><th>Concept</th><th>Why</th></tr>
<tr><td>1</td><td><strong>A. Lunar Dial</strong></td><td>Most ownable and most true to the name (27 mansions, one lit). Calm, scalable, not clip-art. Chosen; its asset set is built.</td></tr>
<tr><td>2</td><td>B. Constellation N</td><td>Clearest at 16 px and spells the name, but sits closest to the sparkle cliché of the category.</td></tr>
<tr><td>3</td><td>C. Kundali Emblem</td><td>Culturally precise but breaks at 16 px and collides with the in-app Kundali glyph.</td></tr></table>
<p>Distinct from checked competitors: Co-Star (black and white serif wordmark with a sparkle), The Pattern (abstract tile), Sanctuary (script-like wordmark), AstroSage (figure and wordmark) and Astro-Seek (text-led). None uses an orbit of 27 points. Web search returned no brand-asset pages, so this comparison relies on a general check of their public branding, not pixel comparison.</p></div>
${['a','b','c'].map(section).join('')}
</main></body></html>`;
fs.writeFileSync(ROOT+'/concepts.html',html);console.log(html.length);
