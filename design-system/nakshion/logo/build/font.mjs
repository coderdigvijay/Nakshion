import fs from 'fs'; import wawoff2 from 'wawoff2'; import opentype from 'opentype.js';
const src="/Users/digvijay/.claude/skills/synced/9d62f4cf-ef68-48cd-bb86-d4dd53c17138_e43cfb00-80d1-465f-a006-da63f2d7d23a/morning/assets/fonts/fraunces-latin-600-normal.woff2";
const ttf=await wawoff2.decompress(fs.readFileSync(src));
fs.writeFileSync('fraunces600.ttf',ttf);
const f=opentype.parse(ttf.buffer.slice(ttf.byteOffset,ttf.byteOffset+ttf.byteLength));
console.log(f.unitsPerEm,f.ascender,f.descender, f.tables.os2.sCapHeight, f.tables.os2.sxHeight);
for(const c of "Nakshion"){const g=f.charToGlyph(c);console.log(c,g.advanceWidth,JSON.stringify(g.getBoundingBox()))}
