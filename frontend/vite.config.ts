import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const backendPort = process.env.BACKEND_PORT ?? "8080";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 3002,
    host: "0.0.0.0",
    proxy: {
      "/api": `http://localhost:${backendPort}`,
    },
    hmr: {
      clientPort: 3002,
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // 只处理 node_modules
          if (!id.includes("node_modules")) return;

          // 大块单独拆分
          if (id.includes("react") || id.includes("scheduler")) return "react-vendor";
          if (id.includes("react-router")) return "router";
          if (id.includes("antd") || id.includes("@ant-design")) return "antd";
          if (id.includes("recharts") || id.includes("d3-")) return "charts";
          if (id.includes("axios")) return "http-lib";
          if (id.includes("dayjs")) return "date-lib";

          // 剩余归入 vendor
          return "vendor";
        },
      },
    },
  },
});
