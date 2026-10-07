import { defineConfig } from "astro/config";

// Served from GitHub Pages on the custom domain, at the root (the old aintelope.github.io/ai-safety-claims/
// addresses redirect here). Pages are generated from src/data/registry.json, which
// `python -m validator export` writes; the site computes nothing itself.
export default defineConfig({
  site: "https://ai-safety-claims.com",
  base: "/",
  trailingSlash: "always",
});
