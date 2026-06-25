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
    chunkSizeWarningLimit: 1300,
    // ERP 操作台依赖 Ant Design 组件面较宽，antd 主 chunk 约 1.1MB 未压缩。
    // 预算设为 1.3MB：避免正常构建噪音，同时保留异常膨胀预警。
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // 只处理 node_modules
          if (!id.includes("node_modules")) return;

          // 大块单独拆分
          if (id.includes("react") || id.includes("scheduler")) return "react-vendor";
          if (id.includes("react-router")) return "router";
          if (id.includes("@ant-design/icons")) return "antd-icons";
          if (id.includes("@ant-design")) return "antd-vendor";
          if (id.includes("/antd/es/table/") || id.includes("/antd/lib/table/")) {
            return "antd-table";
          }
          if (id.includes("/antd/es/date-picker/") || id.includes("/antd/lib/date-picker/")) {
            return "antd-date-picker";
          }
          if (id.includes("/antd/es/") || id.includes("/antd/lib/")) return "antd";
          if (id.includes("/rc-") || id.includes("node_modules/rc-")) return "antd-rc";
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
