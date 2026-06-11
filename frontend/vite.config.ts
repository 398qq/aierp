import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { visualizer } from "rollup-plugin-visualizer";

const backendPort = process.env.BACKEND_PORT ?? "8080";

export default defineConfig({
  plugins: [
    react(),
    // Stage 13 Day 2: 生成 dist/stats.html 体积可视化 (本地看, CI 存档)
    visualizer({
      template: "treemap",
      filename: "dist/stats.html",
      gzipSize: true,
      brotliSize: true,
      title: "AIERP Frontend Bundle Analysis",
    }),
  ],
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
    // Stage 13 Day 2: 体积预算 — 警告阈值 (KB, 未压缩)
    // antd ~700KB 是合理范围; vendor 2MB 是上限; 单文件 600KB warning
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
