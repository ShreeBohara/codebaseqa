import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const cssDir = path.join(repoRoot, "apps/web/.next/static/css");

const requiredSelectors = [".bg-white{", ".text-black{", ".max-w-6xl{", ".px-6{"];

if (!fs.existsSync(cssDir)) {
  console.error(`Missing build CSS directory: ${cssDir}`);
  console.error("Run `pnpm web:build` before `pnpm web:verify-css`.");
  process.exit(1);
}

const cssFiles = fs
  .readdirSync(cssDir)
  .filter((file) => file.endsWith(".css"))
  .map((file) => path.join(cssDir, file));

if (cssFiles.length === 0) {
  console.error(`No CSS files found in ${cssDir}`);
  console.error("Run `pnpm web:build` before `pnpm web:verify-css`.");
  process.exit(1);
}

const css = cssFiles.map((file) => fs.readFileSync(file, "utf8")).join("\n");
const missing = requiredSelectors.filter((selector) => !css.includes(selector));

if (missing.length > 0) {
  console.error("Missing expected Tailwind selectors in compiled CSS:");
  missing.forEach((selector) => console.error(`- ${selector}`));
  process.exit(1);
}

console.log("Web CSS verification passed.");
console.log(`Checked ${cssFiles.length} file(s) in ${cssDir}.`);
