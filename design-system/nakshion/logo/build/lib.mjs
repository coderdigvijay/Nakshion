import fs from 'fs'; import opentype from 'opentype.js'; import {Resvg} from '@resvg/resvg-js';
const ttf=fs.readFileSync('fraunces600.ttf');
export const font=opentype.parse(ttf.buffer.slice(ttf.byteOffset,ttf.byteOffset+ttf.byteLength));
export const PAL={
 dark:{fg:'#EEF0FA',ai:'#A99BFF',lamp:'#F2B544'},
 light:{fg:'#1A1830',ai:'#5443CF',lamp:'#E0A030'},
 mono:{fg:'currentColor',ai:'currentColor',lamp:'currentColor'}};
const f2=n=>(+n.toFixed(2)).toString();
// ---- wordmark as paths. kern = extra units between pairs (font units, 2000/em)
export function wordPath(text,fs,{track=-10,kern={}}={}){
  const s=fs/2000; let x=0,d='';
  const chars=[...text];
  chars.forEach((c,i)=>{
    const g=font.charToGlyph(c);
    const p=g.getPath(x*s,0,fs); // y flipped by opentype (baseline y=0, up negative)
    d+=p.toPathData(2);
    x+=g.advanceWidth+track+(kern[c+(chars[i+1]||'')]||0);
  });
  return {d,width:(x-track)*s};
}
export const KERN={Na:-20,ak:-6,ks:6,sh:0,hi:0,io:0,on:0};
// ---- shapes
const star=(cx,cy,R,k=0.14)=>`M${f2(cx)} ${f2(cy-R)}Q${f2(cx+R*k)} ${f2(cy-R*k)} ${f2(cx+R)} ${f2(cy)}Q${f2(cx+R*k)} ${f2(cy+R*k)} ${f2(cx)} ${f2(cy+R)}Q${f2(cx-R*k)} ${f2(cy+R*k)} ${f2(cx-R)} ${f2(cy)}Q${f2(cx-R*k)} ${f2(cy-R*k)} ${f2(cx)} ${f2(cy-R)}Z`;
function crescent(c1,r1,c2,r2){
  const dx=c2[0]-c1[0],dy=c2[1]-c1[1],d=Math.hypot(dx,dy);
  const a=(r1*r1-r2*r2+d*d)/(2*d),h=Math.sqrt(r1*r1-a*a);
  const px=c1[0]+a*dx/d,py=c1[1]+a*dy/d;
  const A=[px+h*dy/d,py-h*dx/d],B=[px-h*dy/d,py+h*dx/d];
  return `M${f2(A[0])} ${f2(A[1])}A${r1} ${r1} 0 1 0 ${f2(B[0])} ${f2(B[1])}A${r2} ${r2} 0 0 1 ${f2(A[0])} ${f2(A[1])}Z`;
}
// ---- marks (64x64 box). c = palette
export const CONCEPTS={
 a:{id:'concept-a-lunar-dial',name:'Lunar Dial',marks:{
  full:c=>{let t='';const R=27.4;for(let k=0;k<27;k++){if(k===4)continue;const a=(-90+k*360/27)*Math.PI/180;
    t+=`<circle cx="${f2(32+R*Math.cos(a))}" cy="${f2(32+R*Math.sin(a))}" r="1.35"/>`;}
   const a4=(-90+4*360/27)*Math.PI/180;
   return `<g fill="${c.ai}">${t}</g>`+
   `<path d="${crescent([30.2,34],19.2,[37.8,27],16)}" fill="${c.fg}"/>`+
   `<circle cx="${f2(32+R*Math.cos(a4))}" cy="${f2(32+R*Math.sin(a4))}" r="3.9" fill="${c.lamp}"/>`},
  small:c=>`<path d="${crescent([29,35],25,[41,23],21)}" fill="${c.fg}"/><circle cx="49.5" cy="14.5" r="6.8" fill="${c.lamp}"/>`}},
 b:{id:'concept-b-constellation-n',name:'Constellation N',marks:{
  full:c=>`<path d="M14 50L18 15L47 49L51 14" fill="none" stroke="${c.fg}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`+
   `<circle cx="14" cy="50" r="4.4" fill="${c.fg}"/><circle cx="18" cy="15" r="4.4" fill="${c.fg}"/><circle cx="47" cy="49" r="4.4" fill="${c.fg}"/>`+
   `<circle cx="31" cy="9" r="1.8" fill="${c.ai}"/><path d="${star(51,14,12,0.16)}" fill="${c.lamp}"/>`,
  small:c=>`<path d="M12 52L18 14L46 50L52 12" fill="none" stroke="${c.fg}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>`+
   `<path d="${star(52,13,13,0.2)}" fill="${c.lamp}"/>`}},
 c:{id:'concept-c-kundali-emblem',name:'Kundali Emblem',marks:{
  full:c=>`<rect x="6" y="6" width="52" height="52" rx="5" fill="none" stroke="${c.fg}" stroke-width="3.4"/>`+
   `<path d="M32 6L6 32L32 58L58 32Z" fill="none" stroke="${c.fg}" stroke-width="3.4" stroke-linejoin="round"/>`+
   `<path d="M32 9.5L20 20.5L32 31.5L44 20.5Z" fill="${c.lamp}"/>`+
   `<path d="${crescent([32,44],7,[35,41.5],5.8)}" fill="${c.ai}"/>`,
  small:c=>`<rect x="5" y="5" width="54" height="54" rx="5" fill="none" stroke="${c.fg}" stroke-width="5"/>`+
   `<path d="M32 5L5 32L32 59L59 32Z" fill="none" stroke="${c.fg}" stroke-width="4" stroke-linejoin="round"/>`+
   `<path d="M32 8L19.5 19.5L32 32L44.5 19.5Z" fill="${c.lamp}"/>`}}
};
// ---- svg builders
const head=(w,h,title)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${title}"><title>${title}</title>`;
export function markSvg(cid,size,theme){return head(64,64,'Nakshion')+CONCEPTS[cid].marks[size](PAL[theme])+'</svg>';}
export function lockup(cid,kind,theme,{kern=KERN,track=-10,size='full'}={}){
  const c=PAL[theme],m=CONCEPTS[cid].marks[size](c);
  const col=c.fg;
  if(kind==='horizontal'){const fs=40,w=wordPath('Nakshion',fs,{kern,track});
    return head(Math.ceil(78+w.width),64,'Nakshion')+m+`<path transform="translate(78 45.5)" d="${w.d}" fill="${col}"/></svg>`;}
  const fs=54,w=wordPath('Nakshion',fs,{kern,track}),W=Math.ceil(w.width);
  return head(W,134,'Nakshion')+`<g transform="translate(${f2((W-64)/2)} 0)">${m}</g><path transform="translate(0 124)" d="${w.d}" fill="${col}"/></svg>`;
}
export function png(svg,w,bg){const o={fitTo:{mode:'width',value:w}};if(bg)o.background=bg;return new Resvg(svg,o).render().asPng();}
