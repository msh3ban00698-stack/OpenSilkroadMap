import { defineConfig } from "vite";
import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

const NAVLINK_URL =
  "https://github.com/Silkroad-Developer-Community/Silkroad-NavLink/releases/latest/download/navigation_linkage.json.gz";

let resolvedOutDir = "dist";

export default defineConfig({
  css: {
    postcss: {
      plugins: [tailwindcss(), autoprefixer()],
    },
  },
  plugins: [
    {
      name: "navlink-dev-proxy",
      configureServer(server) {
        server.middlewares.use("/navlink-proxy", async (_req, res) => {
          try {
            const response = await fetch(NAVLINK_URL);
            res.statusCode = response.status;
            const contentLength = response.headers.get("content-length");
            if (contentLength) {
              res.setHeader("content-length", contentLength);
            }
            res.setHeader("content-type", "application/gzip");
            const buffer = await response.arrayBuffer();
            res.end(new Uint8Array(buffer));
          } catch (e) {
            res.statusCode = 500;
            res.end(String(e));
          }
        });
      },
    },
    {
      name: "navlink-build-download",
      apply: "build",
      configResolved(config) {
        resolvedOutDir = config.build.outDir;
      },
      async closeBundle() {
        const fs = await import("node:fs");
        const path = await import("node:path");
        const dest = path.join(path.resolve(resolvedOutDir), "assets", "navigation_linkage.json.gz");
        if (fs.existsSync(dest)) return;
        try {
          const response = await fetch(NAVLINK_URL);
          if (!response.ok) return;
          const buffer = await response.arrayBuffer();
          fs.mkdirSync(path.dirname(dest), { recursive: true });
          fs.writeFileSync(dest, new Uint8Array(buffer));
          console.log(`Downloaded navlink to ${dest}`);
        } catch (e) {
          console.warn("Could not pre-download navlink file for build:", e);
        }
      },
    },
  ],
  server: {
    port: 3000,
    host: true,
    allowedHosts: [".monkeycode-ai.live"],
    watch: {
      ignored: ["**/public/assets/**"],
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
