import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'marked';

const repoRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../../../');

export function loadLegalMarkdown(relativePath) {
  const fullPath = path.join(repoRoot, relativePath);
  const markdown = fs.readFileSync(fullPath, 'utf8');
  return marked.parse(markdown);
}
