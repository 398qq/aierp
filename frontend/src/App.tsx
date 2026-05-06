import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntdApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useAuthStore } from "./store/auth";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/auth/Login";
import Dashboard from "./pages/dashboard/index";
import CustomerList from "./pages/customers/index";
import CustomerDetail from "./pages/customers/CustomerDetail";
import CustomerNew from "./pages/customers/CustomerNew";
import ProductList from "./pages/products/index";
import SalesOrderList from "./pages/sales/index";
import OpportunityList from "./pages/opportunities/index";
import InventoryList from "./pages/inventory/index";
import Settings from "./pages/settings/index";
import AIChat from "./pages/ai/Chat";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const init = useAuthStore((s) => s.init);
  const loading = useAuthStore((s) => s.loading);

  useEffect(() => { init(); }, []);

  if (loading) return null;

  return (
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: "#1677ff" } }}>
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/customers" element={<CustomerList />} />
              <Route path="/customers/new" element={<CustomerNew />} />
              <Route path="/customers/:id" element={<CustomerDetail />} />
              <Route path="/products" element={<ProductList />} />
              <Route path="/opportunities" element={<OpportunityList />} />
              <Route path="/sales" element={<SalesOrderList />} />
              <Route path="/inventory" element={<InventoryList />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/ai-chat" element={<AIChat />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}
