import { copyFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const output = resolve(root, "dist");
const extension = resolve(root, "extension");

await mkdir(output, { recursive: true });

for (const file of ["manifest.json", "background.js"]) {
  await copyFile(resolve(extension, file), resolve(output, file));
}

console.log("VIDQUERY: Extension files copied into dist/");
console.log("VIDQUERY: No Chromium-reserved generated paths");
