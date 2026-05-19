import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendPort = process.env.BACKEND_PORT ?? "8080";

export default defineConfig({
  plugins: [react()],
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
});
