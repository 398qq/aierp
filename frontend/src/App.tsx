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
import CustomerDashboard from "./pages/customers/CustomerDashboard";
import ProductList from "./pages/products/index";
import SalesOrderList from "./pages/sales/SalesOrderList";
import SalesOrderDetail from "./pages/sales/SalesOrderDetail";
import SalesOrderForm from "./pages/sales/SalesOrderForm";
import OpportunityList from "./pages/sales/OpportunityList";
import OpportunityDetail from "./pages/sales/OpportunityDetail";
import OpportunityForm from "./pages/sales/OpportunityForm";
import QuotationList from "./pages/sales/QuotationList";
import QuotationDetail from "./pages/sales/QuotationDetail";
import QuotationForm from "./pages/sales/QuotationForm";
import DeliveryNoteList from "./pages/sales/DeliveryNoteList";
import DeliveryNoteDetail from "./pages/sales/DeliveryNoteDetail";
import DeliveryNoteForm from "./pages/sales/DeliveryNoteForm";
import SalesFunnel from "./pages/sales/SalesFunnel";
import SalesStats from "./pages/sales/SalesStats";
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
              <Route path="/customers/stats" element={<CustomerDashboard />} />
              <Route path="/customers/new" element={<CustomerNew />} />
              <Route path="/customers/:id" element={<CustomerDetail />} />
              <Route path="/products" element={<ProductList />} />
              <Route path="/sales/opportunities" element={<OpportunityList />} />
              <Route path="/sales/opportunities/new" element={<OpportunityForm />} />
              <Route path="/sales/opportunities/:id" element={<OpportunityDetail />} />
              <Route path="/sales/opportunities/:id/edit" element={<OpportunityForm />} />
              <Route path="/sales/quotations" element={<QuotationList />} />
              <Route path="/sales/quotations/new" element={<QuotationForm />} />
              <Route path="/sales/quotations/:id" element={<QuotationDetail />} />
              <Route path="/sales/quotations/:id/edit" element={<QuotationForm />} />
              <Route path="/sales/orders" element={<SalesOrderList />} />
              <Route path="/sales/orders/new" element={<SalesOrderForm />} />
              <Route path="/sales/orders/:id" element={<SalesOrderDetail />} />
              <Route path="/sales/orders/:id/edit" element={<SalesOrderForm />} />
              <Route path="/sales/delivery-notes" element={<DeliveryNoteList />} />
              <Route path="/sales/delivery-notes/new" element={<DeliveryNoteForm />} />
              <Route path="/sales/delivery-notes/:id" element={<DeliveryNoteDetail />} />
              <Route path="/sales/delivery-notes/:id/edit" element={<DeliveryNoteForm />} />
              <Route path="/sales/funnel" element={<SalesFunnel />} />
              <Route path="/sales/stats" element={<SalesStats />} />
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
