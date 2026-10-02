import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// Documentation tools live outside the checkout; no application install is needed.
const modules = path.resolve(process.argv[2]);
const { JSDOM } = await import(pathToFileURL(path.join(modules, 'jsdom/lib/api.js')));
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
const { default: mermaid } = await import(pathToFileURL(path.join(modules, 'mermaid/dist/mermaid.esm.mjs')));
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
function markdownFiles(root) {
  return fs.readdirSync(root, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(root, entry.name);
    return entry.isDirectory() ? markdownFiles(file) : entry.isFile() && entry.name.endsWith('.md') ? [file] : [];
  });
}
const files = ['README.md', ...markdownFiles('docs/architecture')];
let count = 0;
for (const file of files) {
  for (const match of fs.readFileSync(file, 'utf8').matchAll(/\x60\x60\x60mermaid\s*\n([\s\S]*?)\x60\x60\x60/g)) {
    await mermaid.parse(match[1]);
    count++;
  }
}
process.stdout.write(count + ' Mermaid diagrams parsed\n');
