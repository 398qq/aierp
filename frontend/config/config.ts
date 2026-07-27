import { defineConfig } from "@umijs/max";

const backendPort = process.env.BACKEND_PORT ?? "8080";

export default defineConfig({
  title: "AIERP",
  npmClient: "npm",
  proxy: {
    "/api": {
      target: `http://localhost:${backendPort}`,
      changeOrigin: true,
    },
  },
  routes: [
    { path: "/login", component: "@/pages/auth/Login" },
    { path: "/inquiry", component: "@/pages/public/InquiryPortal" },
    {
      path: "/",
      component: "@/layouts/ErpRouteLayout",
      routes: [{ path: "", component: "@/pages/dashboard/index" }],
    },
    { path: "*", redirect: "/" },
  ],
});
