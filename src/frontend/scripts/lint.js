import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(__dirname, "..", "src");

function collectJsFiles(dir, files = []) {
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (fs.statSync(full).isDirectory()) {
      collectJsFiles(full, files);
    } else if (full.endsWith(".js")) {
      files.push(full);
    }
  }
  return files;
}

const jsFiles = collectJsFiles(srcDir);
for (const file of jsFiles) {
  execFileSync(process.execPath, ["--check", file], { stdio: "inherit" });
  const content = fs.readFileSync(file, "utf8");
  if (content.includes("console.log(")) {
    throw new Error(`Lint Error: Found leftover console.log in ${file}`);
  }
}

console.log(`Lint & syntax check passed for ${jsFiles.length} frontend modules.`);
