import react from "@vitejs/plugin-react";
import path from "path";
import { visualizer } from "rollup-plugin-visualizer";
import { defineConfig, type PluginOption } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    VitePWA({
      // Enable SW in development for testing PWA features
      devOptions: {
        enabled: true,
        type: "module",
      },
      registerType: "autoUpdate",
      injectRegister: "auto",
      includeAssets: ["favicon.svg", "apple-touch-icon.png", "icons/*.png"],
      manifest: false, // Use the existing public/manifest.json
      workbox: {
        // Import custom push notification handler
        importScripts: ["/custom-sw.js"],
        // Cache JS/CSS/HTML with StaleWhileRevalidate (offline-first shell)
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        // Serve offline.html when navigation requests fail
        navigateFallback: "/offline.html",
        navigateFallbackDenylist: [
          /^\/api/, // Never fallback API requests
          /^\/admin/, // Admin requires live connection
        ],
        // Update SW immediately
        skipWaiting: true,
        clientsClaim: true,
        runtimeCaching: [
          {
            // API calls - network-first so we get fresh data when online,
            // but fall back to cache when offline
            urlPattern: /\/api\/v1\/.*/i,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 60 * 60 * 24, // 24 hours
              },
              networkTimeoutSeconds: 5,
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // OpenStreetMap tiles - cache-first for offline maps
            urlPattern: /^https:\/\/[abc]\.tile\.openstreetmap\.org\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "osm-tiles",
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Static assets from CDN or same-origin - cache-first
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico|woff2?)$/i,
            handler: "CacheFirst",
            options: {
              cacheName: "asset-cache",
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
        ],
      },
    }),
    // Bundle analysis visualizer (run with VITE_ANALYZE=true)
    mode === "analyze" &&
      (visualizer({
        filename: "dist/bundle-report.html",
        open: true,
        gzipSize: true,
        brotliSize: true,
        template: "treemap",
      }) as PluginOption),
  ].filter(Boolean) as PluginOption[],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Build ES module workers for comlink integration
  worker: {
    format: "es",
  },
  // Pre-bundle heavy dependencies for faster dev cold start
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "@tanstack/react-query",
      "axios",
      "zustand",
      "framer-motion",
      "lucide-react",
      "sonner",
      "date-fns",
      "react-hook-form",
      "zod",
      "urql",
      "@deck.gl/core",
      "@turf/helpers",
    ],
  },
  build: {
    target: "es2022", // Align with tsconfig.app.json for smaller output
    cssMinify: true,
    cssCodeSplit: true,
    // Assume no side effects in tree-shakeable libs (date-fns, lucide-react)
    modulePreload: { polyfill: false },
    commonjsOptions: { transformMixedEsModules: true },
    chunkSizeWarningLimit: 400, // Flag chunks > 400 KB
    rollupOptions: {
      treeshake: {
        moduleSideEffects: false,
        propertyReadSideEffects: false,
      },
      output: {
        // Content-hash in asset names for cache busting
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        manualChunks: {
          // React core
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          // Charting library (recharts is ~300 kB)
          "vendor-charts": ["recharts"],
          // Map library (leaflet + react-leaflet ~200 kB)
          "vendor-maps": ["leaflet", "react-leaflet"],
          // Form libraries
          "vendor-forms": ["react-hook-form", "@hookform/resolvers", "zod"],
          // Data fetching & state
          "vendor-data": ["@tanstack/react-query", "axios", "zustand"],
          // Utility libraries
          "vendor-utils": ["date-fns"],
          // Animation library
          "vendor-motion": ["framer-motion"],
          // WebGL visualization (deck.gl + luma.gl) — lazy-loaded
          "vendor-webgl": [
            "@deck.gl/core",
            "@deck.gl/react",
            "@deck.gl/layers",
            "@deck.gl/aggregation-layers",
            "@luma.gl/core",
            "@luma.gl/webgl",
          ],
          // Geospatial utilities (Turf.js)
          "vendor-geo": ["@turf/helpers", "@turf/boolean-point-in-polygon"],
          // GraphQL client
          "vendor-graphql": ["urql", "graphql"],
          // UI primitives (Radix)
          "vendor-ui": [
            "@radix-ui/react-alert-dialog",
            "@radix-ui/react-avatar",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-label",
            "@radix-ui/react-select",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
            "@radix-ui/react-switch",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toast",
          ],
        },
      },
    },
  },
  server: {
    port: 3000,
    host: true, // Bind to 0.0.0.0 for cross-device testing
    // Pre-transform frequently accessed modules for faster page load
    warmup: {
      clientFiles: [
        "./src/App.tsx",
        "./src/state/stores/authStore.ts",
        "./src/lib/api-client.ts",
        "./src/components/feedback/index.ts",
        "./src/features/map/components/FloodMap.tsx",
        "./src/features/alerts/components/AlertList.tsx",
      ],
    },
    proxy: {
      "/api/v1/sse": {
        target: "http://localhost:5000",
        changeOrigin: true,
        timeout: 0,
      },
      "/api/v1/chat/stream": {
        target: "http://localhost:5000",
        changeOrigin: true,
        timeout: 0,
      },
      "/api/v1/evacuation/capacity-stream": {
        target: "http://localhost:5000",
        changeOrigin: true,
        timeout: 0,
      },
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
      "/static": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
}));
