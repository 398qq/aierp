import { useEffect } from "react";
import { Spin } from "antd";
import type { ReactElement } from "react";
// @ts-expect-error - Outlet/Navigate/useLocation are re-exported from react-router
// by @umijs/max at runtime, but @umijs/max type definitions do not include them.
import { Outlet, Navigate, useLocation } from "@umijs/max";
import { ProLayout, type MenuDataItem } from "@ant-design/pro-components";
import { QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { menuItems } from "./menuConfig";
import { queryClient } from "@/lib/queryClient";
import { OfflineBanner } from "@/ui";

export default function ErpRouteLayout(): ReactElement {
  const username = useAuthStore((s) => s.username);
  const loading = useAuthStore((s) => s.loading);
  const init = useAuthStore((s) => s.init);
  const location = useLocation();

  useEffect(() => {
    void init();
  }, [init]);

  if (loading) {
    return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  }
  if (!username) {
    return <Navigate to="/login" replace />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <OfflineBanner />
      <ProLayout
        layout="mix"
        title="AIERP"
        logo="/icon-192.png"
        location={location}
        menuDataRender={() => menuItems as unknown as MenuDataItem[]}
        contentWidth="Fluid"
        siderWidth={224}
        fixedHeader
      >
        <Outlet />
      </ProLayout>
    </QueryClientProvider>
  );
}
