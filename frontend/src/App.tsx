import { useEffect, Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntdApp, Spin } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useAuthStore } from "./store/auth";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/auth/Login";

// Lazy-loaded pages — code splitting for faster initial load
const Dashboard = lazy(() => import("./pages/dashboard/index"));
const CustomerList = lazy(() => import("./pages/customers/index"));
const CustomerDetail = lazy(() => import("./pages/customers/CustomerDetail"));
const CustomerNew = lazy(() => import("./pages/customers/CustomerNew"));
const CustomerDashboard = lazy(() => import("./pages/customers/CustomerDashboard"));
const CustomerInsight = lazy(() => import("./pages/customers/CustomerInsight"));
const Customer360 = lazy(() => import("./pages/customers/Customer360"));
const CustomerSegments = lazy(() => import("./pages/customers/CustomerSegments"));
const ProductList = lazy(() => import("./pages/products/index"));
const ProductDetail = lazy(() => import("./pages/products/ProductDetail"));
const SupplierList = lazy(() => import("./pages/suppliers/index"));
const SupplierDashboard = lazy(() => import("./pages/suppliers/SupplierDashboard"));
const SupplierDetail = lazy(() => import("./pages/suppliers/SupplierDetail"));
const BrandList = lazy(() => import("./pages/brands/index"));
const BrandDetail = lazy(() => import("./pages/brands/BrandDetail"));
const InventoryList = lazy(() => import("./pages/inventory/index"));
const Settings = lazy(() => import("./pages/settings/index"));
const AIChat = lazy(() => import("./pages/ai/Chat"));
const OpportunityList = lazy(() => import("./pages/sales/OpportunityList"));
const OpportunityDetail = lazy(() => import("./pages/sales/OpportunityDetail"));
const OpportunityForm = lazy(() => import("./pages/sales/OpportunityForm"));
const QuotationList = lazy(() => import("./pages/sales/QuotationList"));
const QuotationDetail = lazy(() => import("./pages/sales/QuotationDetail"));
const QuotationForm = lazy(() => import("./pages/sales/QuotationForm"));
const SalesOrderList = lazy(() => import("./pages/sales/SalesOrderList"));
const SalesOrderDetail = lazy(() => import("./pages/sales/SalesOrderDetail"));
const SalesOrderForm = lazy(() => import("./pages/sales/SalesOrderForm"));
const DeliveryNoteList = lazy(() => import("./pages/sales/DeliveryNoteList"));
const DeliveryNoteDetail = lazy(() => import("./pages/sales/DeliveryNoteDetail"));
const DeliveryNoteForm = lazy(() => import("./pages/sales/DeliveryNoteForm"));
const InvoiceList = lazy(() => import("./pages/sales/InvoiceList"));
const InvoiceDetail = lazy(() => import("./pages/sales/InvoiceDetail"));
const InvoiceForm = lazy(() => import("./pages/sales/InvoiceForm"));
const PaymentList = lazy(() => import("./pages/sales/PaymentList"));
const PaymentForm = lazy(() => import("./pages/sales/PaymentForm"));
const ContractList = lazy(() => import("./pages/sales/ContractList"));
const ContractDetail = lazy(() => import("./pages/sales/ContractDetail"));
const ContractForm = lazy(() => import("./pages/sales/ContractForm"));
const TargetList = lazy(() => import("./pages/sales/TargetList"));
const TargetForm = lazy(() => import("./pages/sales/TargetForm"));
const PurchaseOrderList = lazy(() => import("./pages/sales/PurchaseOrderList"));
const PurchaseOrderForm = lazy(() => import("./pages/sales/PurchaseOrderForm"));
const PurchaseOrderDetail = lazy(() => import("./pages/sales/PurchaseOrderDetail"));
const SalesDashboard = lazy(() => import("./pages/sales/SalesDashboard"));
const NotificationList = lazy(() => import("./pages/notifications/index"));
const Product360 = lazy(() => import("./pages/products/Product360"));
const Supplier360 = lazy(() => import("./pages/suppliers/Supplier360"));
const SupplierCompare = lazy(() => import("./pages/suppliers/SupplierCompare"));
const WatchtowerDashboard = lazy(() => import("./pages/dashboard/WatchtowerDashboard"));
const Global360 = lazy(() => import("./pages/dashboard/Global360"));

function PageLoader() {
  return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
}

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
              <Route path="/" element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
              <Route path="/dashboard/watchtower" element={<Suspense fallback={<PageLoader />}><WatchtowerDashboard /></Suspense>} />
              <Route path="/dashboard/global360" element={<Suspense fallback={<PageLoader />}><Global360 /></Suspense>} />
              <Route path="/customers" element={<Suspense fallback={<PageLoader />}><CustomerList /></Suspense>} />
              <Route path="/customers/stats" element={<Suspense fallback={<PageLoader />}><CustomerDashboard /></Suspense>} />
              <Route path="/customers/new" element={<Suspense fallback={<PageLoader />}><CustomerNew /></Suspense>} />
              <Route path="/customers/:id" element={<Suspense fallback={<PageLoader />}><CustomerDetail /></Suspense>} />
              <Route path="/customers/:id/insight" element={<Suspense fallback={<PageLoader />}><CustomerInsight /></Suspense>} />
              <Route path="/customers/:id/360" element={<Suspense fallback={<PageLoader />}><Customer360 /></Suspense>} />
              <Route path="/customers/segments" element={<Suspense fallback={<PageLoader />}><CustomerSegments /></Suspense>} />
              <Route path="/products" element={<Suspense fallback={<PageLoader />}><ProductList /></Suspense>} />
              <Route path="/products/:id" element={<Suspense fallback={<PageLoader />}><ProductDetail /></Suspense>} />
              <Route path="/products/:id/360" element={<Suspense fallback={<PageLoader />}><Product360 /></Suspense>} />
              <Route path="/suppliers" element={<Suspense fallback={<PageLoader />}><SupplierList /></Suspense>} />
              <Route path="/suppliers/stats" element={<Suspense fallback={<PageLoader />}><SupplierDashboard /></Suspense>} />
              <Route path="/suppliers/:id" element={<Suspense fallback={<PageLoader />}><SupplierDetail /></Suspense>} />
              <Route path="/suppliers/:id/360" element={<Suspense fallback={<PageLoader />}><Supplier360 /></Suspense>} />
              <Route path="/suppliers/compare" element={<Suspense fallback={<PageLoader />}><SupplierCompare /></Suspense>} />
              <Route path="/brands" element={<Suspense fallback={<PageLoader />}><BrandList /></Suspense>} />
              <Route path="/brands/:id" element={<Suspense fallback={<PageLoader />}><BrandDetail /></Suspense>} />
              <Route path="/inventory" element={<Suspense fallback={<PageLoader />}><InventoryList /></Suspense>} />
              <Route path="/settings" element={<Suspense fallback={<PageLoader />}><Settings /></Suspense>} />
              <Route path="/ai/chat" element={<Suspense fallback={<PageLoader />}><AIChat /></Suspense>} />
              <Route path="/notifications" element={<Suspense fallback={<PageLoader />}><NotificationList /></Suspense>} />
              <Route path="/sales/opportunities" element={<Suspense fallback={<PageLoader />}><OpportunityList /></Suspense>} />
              <Route path="/sales/opportunities/new" element={<Suspense fallback={<PageLoader />}><OpportunityForm /></Suspense>} />
              <Route path="/sales/opportunities/:id" element={<Suspense fallback={<PageLoader />}><OpportunityDetail /></Suspense>} />
              <Route path="/sales/opportunities/:id/edit" element={<Suspense fallback={<PageLoader />}><OpportunityForm /></Suspense>} />
              <Route path="/sales/quotations" element={<Suspense fallback={<PageLoader />}><QuotationList /></Suspense>} />
              <Route path="/sales/quotations/new" element={<Suspense fallback={<PageLoader />}><QuotationForm /></Suspense>} />
              <Route path="/sales/quotations/:id" element={<Suspense fallback={<PageLoader />}><QuotationDetail /></Suspense>} />
              <Route path="/sales/quotations/:id/edit" element={<Suspense fallback={<PageLoader />}><QuotationForm /></Suspense>} />
              <Route path="/sales/orders" element={<Suspense fallback={<PageLoader />}><SalesOrderList /></Suspense>} />
              <Route path="/sales/orders/new" element={<Suspense fallback={<PageLoader />}><SalesOrderForm /></Suspense>} />
              <Route path="/sales/orders/:id" element={<Suspense fallback={<PageLoader />}><SalesOrderDetail /></Suspense>} />
              <Route path="/sales/orders/:id/edit" element={<Suspense fallback={<PageLoader />}><SalesOrderForm /></Suspense>} />
              <Route path="/sales/delivery-notes" element={<Suspense fallback={<PageLoader />}><DeliveryNoteList /></Suspense>} />
              <Route path="/sales/delivery-notes/new" element={<Suspense fallback={<PageLoader />}><DeliveryNoteForm /></Suspense>} />
              <Route path="/sales/delivery-notes/:id" element={<Suspense fallback={<PageLoader />}><DeliveryNoteDetail /></Suspense>} />
              <Route path="/sales/delivery-notes/:id/edit" element={<Suspense fallback={<PageLoader />}><DeliveryNoteForm /></Suspense>} />
              <Route path="/sales/invoices" element={<Suspense fallback={<PageLoader />}><InvoiceList /></Suspense>} />
              <Route path="/sales/invoices/new" element={<Suspense fallback={<PageLoader />}><InvoiceForm /></Suspense>} />
              <Route path="/sales/invoices/:id" element={<Suspense fallback={<PageLoader />}><InvoiceDetail /></Suspense>} />
              <Route path="/sales/invoices/:id/edit" element={<Suspense fallback={<PageLoader />}><InvoiceForm /></Suspense>} />
              <Route path="/sales/payments" element={<Suspense fallback={<PageLoader />}><PaymentList /></Suspense>} />
              <Route path="/sales/payments/new" element={<Suspense fallback={<PageLoader />}><PaymentForm /></Suspense>} />
              <Route path="/sales/payments/:id/edit" element={<Suspense fallback={<PageLoader />}><PaymentForm /></Suspense>} />
              <Route path="/sales/purchase-orders" element={<Suspense fallback={<PageLoader />}><PurchaseOrderList /></Suspense>} />
              <Route path="/sales/purchase-orders/new" element={<Suspense fallback={<PageLoader />}><PurchaseOrderForm /></Suspense>} />
              <Route path="/sales/purchase-orders/:id/edit" element={<Suspense fallback={<PageLoader />}><PurchaseOrderForm /></Suspense>} />
              <Route path="/sales/purchase-orders/:id" element={<Suspense fallback={<PageLoader />}><PurchaseOrderDetail /></Suspense>} />
              <Route path="/sales/contracts" element={<Suspense fallback={<PageLoader />}><ContractList /></Suspense>} />
              <Route path="/sales/contracts/new" element={<Suspense fallback={<PageLoader />}><ContractForm /></Suspense>} />
              <Route path="/sales/contracts/:id" element={<Suspense fallback={<PageLoader />}><ContractDetail /></Suspense>} />
              <Route path="/sales/contracts/:id/edit" element={<Suspense fallback={<PageLoader />}><ContractForm /></Suspense>} />
              <Route path="/sales/targets" element={<Suspense fallback={<PageLoader />}><TargetList /></Suspense>} />
              <Route path="/sales/targets/new" element={<Suspense fallback={<PageLoader />}><TargetForm /></Suspense>} />
              <Route path="/sales/targets/:id/edit" element={<Suspense fallback={<PageLoader />}><TargetForm /></Suspense>} />
              <Route path="/sales/dashboard" element={<Suspense fallback={<PageLoader />}><SalesDashboard /></Suspense>} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}
