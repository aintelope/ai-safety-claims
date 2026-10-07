import { defineConfig } from "astro/config";

// Served from GitHub Pages under the repository path. Pages are generated from src/data/registry.json,
// which `python -m validator export` writes; the site computes nothing itself.
export default defineConfig({
  site: "https://aintelope.github.io",
  base: "/ai-safety-claims",
  trailingSlash: "always",
});
