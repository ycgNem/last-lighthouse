import { defineConfig } from "vitest/config";

export default defineConfig({
  // Relative, so the build works from any folder (GitHub Pages serves it under /last-lighthouse/).
  base: "./",
  server: { port: 5173, open: false },
  // three.js alone is ~700 kB minified; one chunk is fine for a game.
  build: { target: "es2022", sourcemap: true, chunkSizeWarningLimit: 1200 },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
