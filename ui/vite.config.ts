/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir:
      process.env.VITE_OUT_DIR ||
      path.resolve(__dirname, "../src/transcriber/server/static"),
    sourcemap: false,
    emptyOutDir: true,
    minify: "esbuild",
    rollupOptions: {
      output: {
        entryFileNames: "js/[name].js",
        chunkFileNames: "js/[name].js",
        assetFileNames: ({ name }) => {
          if (/\.css$/.test(String(name))) {
            return "css/[name][extname]";
          }
          if (/\.(woff2?|eot|ttf|otf)$/.test(name ?? "")) {
            return "fonts/[name][extname]";
          }
          if (/\.(png|jpe?g|gif|svg)$/.test(name ?? "")) {
            return "img/[name][extname]";
          }
          return "js/[name][extname]";
        },
      },
    },
  },
  server: {
    proxy: {
      "/transcribe": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    css: true,
  },
});
