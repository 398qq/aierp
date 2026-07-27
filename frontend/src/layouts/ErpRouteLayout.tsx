import { useEffect } from "react";
import { Spin } from "antd";
import { Navigate } from "@/router";
import { useAuthStore } from "../store/auth";
import MainLayout from "./MainLayout";

/** Umi route wrapper used while feature routes move out of App.tsx. */
export default function ErpRouteLayout() {
  const username = useAuthStore((state) => state.username);
  const loading = useAuthStore((state) => state.loading);
  const init = useAuthStore((state) => state.init);

  useEffect(() => {
    void init();
  }, [init]);

  if (loading) {
    return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  }
  if (!username) return <Navigate to="/login" replace />;
  return <MainLayout />;
}
