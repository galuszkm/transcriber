/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

const API_TARGET = "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      // Inline the SW registration into index.html — no extra registerSW.js to serve
      injectRegister: "inline",
      // vite-plugin-pwa writes sw.js to outDir root (not under js/ or css/)
      // Python's ui.py must serve it at {prefix}/sw.js — handled separately
      workbox: {
        // No precaching: the app requires the backend to function anyway.
        // An empty SW is enough to satisfy Chrome's PWA installability criteria.
        globPatterns: [],
        navigateFallback: null,
        cleanupOutdatedCaches: true,
      },
      manifest: {
        name: "Transcription Service",
        short_name: "Transcriber",
        description: "AI-powered audio transcription service",
        theme_color: "#232f3e",
        background_color: "#232f3e",
        display: "standalone",
        // "./" is relative to the manifest's own URL, so it adapts to any prefix
        start_url: "./",
        scope: "./",
        icons: [
          {
            src: "static/icons/icon-192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "static/icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
          {
            src: "static/icons/icon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any",
          },
        ],
      },
      devOptions: {
        // Keep PWA disabled in dev mode to avoid SW interfering with HMR
        enabled: false,
      },
    }),
  ],
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
        target: API_TARGET,
        changeOrigin: true,
      },
      "/health": {
        target: API_TARGET,
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
