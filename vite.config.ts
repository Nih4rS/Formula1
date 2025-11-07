import { defineConfig } from 'vite'

// Base is set via env for GitHub Pages project sites, e.g. "/<repo>/".
// Fallback to "/" for user/org pages or local dev.
const base = process.env.VITE_BASE && process.env.VITE_BASE.trim().length > 0
  ? process.env.VITE_BASE
  : '/';

export default defineConfig({
  base,
  publicDir: 'public',
})
