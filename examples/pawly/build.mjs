import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {rolldown} from 'rolldown';
const require=createRequire(import.meta.url),{transform}=require('lightningcss');
const root=path.dirname(fileURLToPath(import.meta.url)),src=path.join(root,'source'),out=path.join(root,'site');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex').slice(0,10);
await fs.rm(out,{recursive:true,force:true});await fs.mkdir(path.join(out,'assets'),{recursive:true});
let html=await fs.readFile(path.join(src,'index.html'),'utf8');
const map={};for(const name of await fs.readdir(path.join(src,'assets'))){const b=await fs.readFile(path.join(src,'assets',name)),ext=path.extname(name),file=`assets/${path.basename(name,ext)}.${hash(b)}${ext}`;await fs.writeFile(path.join(out,file),b);map['assets/'+name]=file;}
const css=transform({filename:'style.css',code:await fs.readFile(path.join(src,'style.css')),minify:true}).code;map['style.css']=`assets/style.${hash(css)}.css`;await fs.writeFile(path.join(out,map['style.css']),css);
const build=await rolldown({input:path.join(src,'app.js')});const result=await build.write({dir:out,format:'es',minify:true,entryFileNames:'assets/[name].[hash].js',chunkFileNames:'assets/[name].[hash].js'});await build.close();
map['app.js']=result.output.find(x=>x.type==='chunk'&&x.isEntry).fileName;
for(const [from,to] of Object.entries(map))html=html.split(from).join(to);
await fs.writeFile(path.join(out,'index.html'),html);
await fs.writeFile(path.join(out,'_headers'),'/*\n  Cache-Control: no-cache\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n');
console.log('Built site/ from source/.');
