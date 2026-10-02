import fs from 'fs';import path from 'path';
import {markSvg,lockup,png,wordPath,KERN,PAL,CONCEPTS} from './lib.mjs';
const ROOT='/Users/digvijay/Desktop/Astrology/design-system/nakshion/logo';
const w=(p,d)=>{fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,d)};
const inner=s=>s.replace(/^<svg[^>]*>/,'').replace('</svg>','').replace(/<title>.*?<\/title>/,'');
const NIGHT='#0B0D1A';
// ---------- concept files
for(const k of Object.keys(CONCEPTS)){
  const dir=`${ROOT}/${CONCEPTS[k].id}`;
  for(const th of ['dark','light','mono']){
    w(`${dir}/mark-${th}.svg`,markSvg(k,'full',th));
    w(`${dir}/mark-small-${th}.svg`,markSvg(k,'small',th));
    w(`${dir}/horizontal-${th}.svg`,lockup(k,'horizontal',th));
    w(`${dir}/horizontal-compact-${th}.svg`,lockup(k,'horizontal',th,{size:'small'}));
    w(`${dir}/stacked-${th}.svg`,lockup(k,'stacked',th));
  }
}
// ---------- recommended = a
const REC='a';
// star field
function rnd(seed){let s=seed;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;}}
function stars(W,H,n,seed,avoid=()=>false){const r=rnd(seed);let o='';for(let i=0;i<n;i++){const x=r()*W,y=r()*H,m=r();if(avoid(x,y))continue;
  const rad=m>0.93?1.9:m>0.7?1.2:0.8,op=(0.25+r()*0.55).toFixed(2);o+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${rad}" fill="${m>0.96?'#F2B544':'#EEF0FA'}" opacity="${op}"/>`;}return o;}
const bgDefs=(W,H,cx=0.5,cy=0.4)=>`<defs><radialGradient id="g" cx="${cx}" cy="${cy}" r="0.75"><stop offset="0" stop-color="#1B1D3C"/><stop offset="0.55" stop-color="#0F1124"/><stop offset="1" stop-color="${NIGHT}"/></radialGradient></defs><rect width="${W}" height="${H}" fill="url(#g)"/>`;
const svgWrap=(W,H,body)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${body}</svg>`;
const M=(size,th='dark')=>inner(markSvg(REC,size,th));
const place=(svg,x,y,s)=>`<g transform="translate(${+(+x).toFixed(2)} ${+(+y).toFixed(2)}) scale(${+(+s).toFixed(4)})">${svg}</g>`;
const word=(text,fs,x,y,fill,anchor='middle',opt={})=>{const p=wordPath(text,fs,{kern:KERN,...opt});const dx=anchor==='middle'?x-p.width/2:anchor==='end'?x-p.width:x;return `<path transform="translate(${dx.toFixed(1)} ${y})" d="${p.d}" fill="${fill}"/>`};
// kundali hint
const kundali=(cx,cy,s,op)=>`<g transform="translate(${cx-32*s} ${cy-32*s}) scale(${s})" fill="none" stroke="#A99BFF" stroke-width="${(1.2/s).toFixed(2)}" opacity="${op}"><rect x="2" y="2" width="60" height="60"/><path d="M32 2L2 32L32 62L62 32Z"/><path d="M2 2L62 62M62 2L2 62"/></g>`;
const TAG='Your sky, read with care.';
function share(W,H,{markS,markY,wordFs,wordY,tagFs,tagY,seed}){
  const cx=W/2;
  const ringHalf=32*markS;
  return svgWrap(W,H,bgDefs(W,H)+stars(W,H,Math.round(W*H/5200),seed,(x,y)=>Math.hypot(x-cx,y-(markY+ringHalf))<ringHalf+14)+
   kundali(W*0.86,H*0.78,H/70,0.10)+kundali(W*0.12,H*0.2,H/140,0.08)+
   place(M('full'),cx-ringHalf,markY,markS)+
   word('Nakshion',wordFs,cx,wordY,'#EEF0FA')+word(TAG,tagFs,cx,tagY,'#B4B9D6'));
}
const OG=share(1200,630,{markS:2.9,markY:62,wordFs:132,wordY:422,tagFs:54,tagY:508,seed:7});
w(`${ROOT}/og-image-1200x630.svg`,OG);w(`${ROOT}/og-image-1200x630.png`,png(OG,1200));
// ---------- icons
const tile=(size,{bg=NIGHT,scale,variant,rx=0,mono=false})=>{ // size px square, mark centred (bbox-centre tuned)
  const th=mono?'mono':'dark',s=scale*size/64;const off=(size-64*s)/2;
  const body=(bg?`<rect width="${size}" height="${size}" rx="${rx}" fill="${bg}"/>`:'')+place(inner(markSvg(REC,variant,th)),off,off,s);
  return svgWrap(size,size,mono?body.replace(/currentColor/g,'#000'):body);};
// favicon.svg (64 tile, small mark, rounded)
const fav=tile(64,{scale:0.80,variant:'small',rx:14});
w(`${ROOT}/favicon.svg`,fav.replace('width="64" height="64"',''));
const out={};
out['favicon-16.png']=png(tile(64,{scale:0.86,variant:'small',rx:13}),16);
out['favicon-32.png']=png(tile(64,{scale:0.82,variant:'small',rx:13}),32);
out['favicon-48.png']=png(tile(64,{scale:0.78,variant:'small',rx:13}),48);
out['apple-touch-icon-180.png']=png(tile(180,{scale:0.68,variant:'full'}),180);
out['icon-192.png']=png(tile(192,{scale:0.70,variant:'full',rx:36}),192);
out['icon-512.png']=png(tile(512,{scale:0.70,variant:'full',rx:96}),512);
out['icon-maskable-512.png']=png(tile(512,{scale:0.56,variant:'full'}),512);
out['icon-monochrome-512.png']=png(tile(512,{scale:0.62,variant:'full',bg:null,mono:true}),512);
for(const [n,b] of Object.entries(out))w(`${ROOT}/assets/${n}`,b);
// ---------- social kit
const S=`${ROOT}/social`;
w(`${S}/avatar-1024.png`,png(tile(1024,{scale:0.7,variant:'full'}),1024));
w(`${S}/linkedin-logo-400.png`,png(tile(400,{scale:0.70,variant:'full'}),400));
// banners: horizontal lockup + tagline
function banner(W,H,{cx,mark,wfs,seed,tfs,align='start',x0}){
  const mS=mark/64, wordW=wordPath('Nakshion',wfs,{kern:KERN}).width, gap=mark*0.22;
  const total=mark+gap+wordW, left=x0??cx-total/2, midY=H/2-(tfs?tfs*0.6:0);
  const my=midY-mark/2, base=midY+wfs*0.35;
  return svgWrap(W,H,bgDefs(W,H,0.6,0.5)+stars(W,H,Math.round(W*H/6000),seed,(x,y)=>x>left-20&&x<left+total+20&&y>my-10&&y<base+tfs*2)+
   kundali(W*0.93,H*0.5,H/80,0.09)+
   place(M('full'),left,my,mS)+word('Nakshion',wfs,left+mark+gap,base,'#EEF0FA','start')+
   (tfs?word(TAG,tfs,left+mark+gap,base+tfs*1.55,'#B4B9D6','start'):''));
}
const li=banner(1584,396,{cx:0,x0:560,mark:150,wfs:84,tfs:34,seed:11});
w(`${S}/linkedin-banner-1584x396.png`,png(li,1584));
const xh=banner(1500,500,{cx:0,x0:520,mark:170,wfs:96,tfs:38,seed:13});
w(`${S}/x-header-1500x500.png`,png(xh,1500));
const gh=share(1280,640,{markS:3.0,markY:56,wordFs:136,wordY:430,tagFs:56,tagY:520,seed:17});
w(`${S}/github-social-1280x640.png`,png(gh,1280));
console.log('done');
export {};
