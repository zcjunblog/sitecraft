import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(root, 'site');
await fs.rm(out, { recursive: true, force: true });
await fs.cp(path.join(root, 'source'), out, { recursive: true });
console.log('Copied editable source to site/ without transforming HTML, CSS or JavaScript.');
