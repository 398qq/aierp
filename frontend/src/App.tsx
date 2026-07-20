import { Component, useEffect, Suspense, lazy } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Button, ConfigProvider, App as AntdApp, Result, Spin } from "antd";
import zhCN from "antd/locale/zh_CN";

import { useAuthStore } from "./store/auth";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/auth/Login";
import { antdTheme, fontSize, fontWeight, lineHeight } from "./design-tokens";
import AntdOverlayGuard from "./ui/AntdOverlayGuard";

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面加载异常"
          subTitle={this.state.error?.message || "未知错误"}
          extra={
            <Button
              type="primary"
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
            >
              刷新页面
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}

// Lazy-loaded pages — code splitting for faster initial load
const Dashboard = lazy(() => import("./pages/dashboard/index"));
const CustomerList = lazy(() => import("./pages/customers/CustomerListPage"));
const CustomerDetail = lazy(() => import("./pages/customers/CustomerDetail"));
const CustomerNew = lazy(() => import("./pages/customers/CustomerNew"));
const CustomerDashboard = lazy(() => import("./pages/customers/CustomerDashboard"));
const CustomerIntelligenceDashboard = lazy(
  () => import("./pages/customers/CustomerIntelligenceDashboard"),
);
const CustomerAIWorkbench = lazy(() => import("./pages/customers/CustomerAIWorkbench"));
const CustomerSegments = lazy(() => import("./pages/customers/CustomerSegments"));
const CustomerFollowUpsPage = lazy(() => import("./pages/customers/CustomerFollowUpsPage"));
const FollowUpList = lazy(() => import("./pages/customers/FollowUpList"));
const ProductList = lazy(() => import("./pages/products/index"));
const ProductDetail = lazy(() => import("./pages/products/ProductDetail"));
const ProductEdit = lazy(() => import("./pages/products/ProductEdit"));
const SupplierList = lazy(() => import("./pages/suppliers/index"));
const SupplierDashboard = lazy(() => import("./pages/suppliers/SupplierDashboard"));
const SupplierDetail = lazy(() => import("./pages/suppliers/SupplierDetail"));
const BrandList = lazy(() => import("./pages/brands/index"));
const BrandDashboard = lazy(() => import("./pages/brands/BrandDashboard"));
const BrandDetail = lazy(() => import("./pages/brands/BrandDetail"));
const BrandEdit = lazy(() => import("./pages/brands/BrandEdit"));
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
const InquiryAutoReply = lazy(() => import("./pages/sales/InquiryAutoReply"));
const NotificationList = lazy(() => import("./pages/notifications/index"));
const Product360 = lazy(() => import("./pages/products/Product360"));
const PriceImport = lazy(() => import("./pages/products/PriceImport"));
const InventoryManage = lazy(() => import("./pages/products/InventoryManage"));
const Supplier360 = lazy(() => import("./pages/suppliers/Supplier360"));
const SupplierCompare = lazy(() => import("./pages/suppliers/SupplierCompare"));
const WatchtowerDashboard = lazy(() => import("./pages/dashboard/WatchtowerDashboard"));
const Global360 = lazy(() => import("./pages/dashboard/Global360"));
const InquiryPortal = lazy(() => import("./pages/public/InquiryPortal"));
const UserList = lazy(() => import("./pages/system/users/UserList"));
const WarehouseList = lazy(() => import("./pages/warehouse/WarehouseList"));
const InventoryLedger = lazy(() => import("./pages/warehouse/InventoryLedger"));
const InventoryBatches = lazy(() => import("./pages/warehouse/InventoryBatches"));
const WarehouseIndex = lazy(() => import("./pages/warehouse/index"));
const TicketList = lazy(() => import("./pages/tickets/TicketList"));
const TicketForm = lazy(() => import("./pages/tickets/TicketForm"));
const TicketDetail = lazy(() => import("./pages/tickets/TicketDetail"));
const FollowUpForm = lazy(() => import("./pages/customers/FollowUpForm"));
const ApprovalList = lazy(() => import("./pages/system/ApprovalList"));
const ApprovalRules = lazy(() => import("./pages/system/ApprovalRules"));
const RolesPage = lazy(() => import("./pages/system/Roles"));
const AuditLogList = lazy(() => import("./pages/system/AuditLogList"));
const ProcurementDashboard = lazy(() => import("./pages/procurement/ProcurementDashboard"));
const ReportSales = lazy(() => import("./pages/reports/ReportSales"));
const ReportAR = lazy(() => import("./pages/reports/ReportAR"));
const ReportInventory = lazy(() => import("./pages/reports/ReportInventory"));
const ReportProcurement = lazy(() => import("./pages/reports/ReportProcurement"));
const AccountList = lazy(() => import("./pages/finance/AccountList"));
const JournalEntryList = lazy(() => import("./pages/finance/JournalEntryList"));
const JournalEntryForm = lazy(() => import("./pages/finance/JournalEntryForm"));
const ProfitLoss = lazy(() => import("./pages/finance/ProfitLoss"));
const CommissionList = lazy(() => import("./pages/finance/CommissionList"));
const CommissionSchemeList = lazy(() => import("./pages/finance/CommissionSchemeList"));
const AuditLogViewer = lazy(() => import("./pages/system/AuditLogViewer"));
const ReportAP = lazy(() => import("./pages/reports/ReportAP"));
const ImportExport = lazy(() => import("./pages/import-export/index"));

function PageLoader() {
  return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const username = useAuthStore((s) => s.username);
  if (!username) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const init = useAuthStore((s) => s.init);
  const loading = useAuthStore((s) => s.loading);

  useEffect(() => {
    init();
  }, []);

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;

  return (
    <ErrorBoundary>
      <ConfigProvider
        locale={zhCN}
        theme={antdTheme}
        pagination={{
          showSizeChanger: true,
          totalBoundaryShowSizeChanger: 0,
        }}
      >
        <style>{`
        :root {
          --color-primary: ${antdTheme.token.colorPrimary};
          --color-success: ${antdTheme.token.colorSuccess};
          --color-warning: ${antdTheme.token.colorWarning};
          --color-error: ${antdTheme.token.colorError};
          --color-info: ${antdTheme.token.colorInfo};
          --color-text: ${antdTheme.token.colorText};
          --color-text-secondary: ${antdTheme.token.colorTextSecondary};
          --color-text-tertiary: ${antdTheme.token.colorTextTertiary};
          --color-border: ${antdTheme.token.colorBorder};
          --color-canvas: ${antdTheme.token.colorBgContainer};
          --color-bg-layout: ${antdTheme.token.colorBgLayout};
          --color-primary-bg: #edf3fa;
          --radius-card: ${antdTheme.token.borderRadius}px;
          --radius-input: ${antdTheme.token.borderRadiusSM}px;
          --radius-tag: ${antdTheme.token.borderRadiusXS}px;
          --font-size-page-title: ${fontSize.headingMd}px;
          --font-size-section-title: ${fontSize.section}px;
          --font-size-card-title: ${fontSize.cardTitle}px;
          --font-size-body: ${fontSize.body}px;
          --font-size-body-sm: ${fontSize.bodySm}px;
          --font-size-caption: ${fontSize.caption}px;
          --font-size-table: ${fontSize.table}px;
          --font-size-table-header: ${fontSize.tableHeader}px;
          --font-size-metric: ${fontSize.metric}px;
          --font-weight-medium: ${fontWeight.medium};
          --font-weight-semibold: ${fontWeight.semibold};
          --font-weight-bold: ${fontWeight.bold};
          --line-height-heading: ${lineHeight.heading};
          --line-height-body: ${lineHeight.body};
          --line-height-compact: ${lineHeight.compact};
          --line-height-caption: ${lineHeight.caption};
        }
      `}</style>
        <AntdApp>
          <AntdOverlayGuard />
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/inquiry"
                element={
                  <Suspense fallback={<PageLoader />}>
                    <InquiryPortal />
                  </Suspense>
                }
              />
              <Route
                element={
                  <ProtectedRoute>
                    <MainLayout />
                  </ProtectedRoute>
                }
              >
                <Route
                  path="/"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Dashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/dashboard/watchtower"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <WatchtowerDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/dashboard/global360"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Global360 />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerList />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/stats"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/intelligence"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerIntelligenceDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/workbench"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerAIWorkbench />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerNew />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/follow-ups"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerFollowUpsPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/:id/insight"
                  element={<Navigate to="../?tab=ai" relative="path" replace />}
                />
                <Route
                  path="/customers/:id/360"
                  element={<Navigate to="../?tab=profile" relative="path" replace />}
                />
                <Route
                  path="/customers/:customerId/follow-ups"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <FollowUpList />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/:customerId/follow-ups/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <FollowUpForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/:customerId/follow-ups/:followupId/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <FollowUpForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/customers/segments"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CustomerSegments />
                    </Suspense>
                  }
                />
                <Route
                  path="/products"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ProductList />
                    </Suspense>
                  }
                />
                <Route
                  path="/products/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ProductDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/products/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ProductEdit />
                    </Suspense>
                  }
                />
                <Route
                  path="/products/:id/360"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Product360 />
                    </Suspense>
                  }
                />
                <Route
                  path="/products/price-import"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PriceImport />
                    </Suspense>
                  }
                />
                <Route
                  path="/products/inventory"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InventoryManage />
                    </Suspense>
                  }
                />
                <Route
                  path="/suppliers"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SupplierList />
                    </Suspense>
                  }
                />
                <Route
                  path="/suppliers/stats"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SupplierDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/suppliers/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SupplierDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/suppliers/:id/360"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Supplier360 />
                    </Suspense>
                  }
                />
                <Route
                  path="/suppliers/compare"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SupplierCompare />
                    </Suspense>
                  }
                />
                <Route
                  path="/brands"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <BrandList />
                    </Suspense>
                  }
                />
                <Route
                  path="/brands/stats"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <BrandDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/brands/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <BrandDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/brands/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <BrandEdit />
                    </Suspense>
                  }
                />
                <Route
                  path="/inventory"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InventoryList />
                    </Suspense>
                  }
                />
                <Route
                  path="/warehouse"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <WarehouseIndex />
                    </Suspense>
                  }
                />
                <Route
                  path="/warehouse/warehouses"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <WarehouseList />
                    </Suspense>
                  }
                />
                <Route
                  path="/warehouse/inventory-ledger"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InventoryLedger />
                    </Suspense>
                  }
                />
                <Route
                  path="/warehouse/inventory-batches"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InventoryBatches />
                    </Suspense>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Settings />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/users"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <UserList />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/roles"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <RolesPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/approvals"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ApprovalList />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/approval-rules"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ApprovalRules />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/audit-logs"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AuditLogList />
                    </Suspense>
                  }
                />
                <Route
                  path="/procurement/dashboard"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ProcurementDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/reports/sales"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ReportSales />
                    </Suspense>
                  }
                />
                <Route
                  path="/reports/ar"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ReportAR />
                    </Suspense>
                  }
                />
                <Route
                  path="/reports/inventory"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ReportInventory />
                    </Suspense>
                  }
                />
                <Route
                  path="/reports/procurement"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ReportProcurement />
                    </Suspense>
                  }
                />
                <Route
                  path="/reports/ap"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ReportAP />
                    </Suspense>
                  }
                />
                <Route
                  path="/data/import-export"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ImportExport />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/accounts"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AccountList />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/journal-entries"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <JournalEntryList />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/journal-entries/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <JournalEntryForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/journal-entries/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <JournalEntryForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/pnl"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ProfitLoss />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/commissions"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CommissionList />
                    </Suspense>
                  }
                />
                <Route
                  path="/finance/commission-schemes"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CommissionSchemeList />
                    </Suspense>
                  }
                />
                <Route
                  path="/system/audit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AuditLogViewer />
                    </Suspense>
                  }
                />
                <Route
                  path="/ai/chat"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AIChat />
                    </Suspense>
                  }
                />
                <Route
                  path="/notifications"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <NotificationList />
                    </Suspense>
                  }
                />
                <Route path="/sales" element={<Navigate to="/sales/dashboard" replace />} />
                <Route
                  path="/sales/opportunities"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <OpportunityList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/opportunities/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <OpportunityForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/opportunities/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <OpportunityDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/opportunities/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <OpportunityForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/quotations"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <QuotationList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/quotations/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <QuotationForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/quotations/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <QuotationDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/quotations/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <QuotationForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/orders"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SalesOrderList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/orders/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SalesOrderForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/orders/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SalesOrderDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/orders/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SalesOrderForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/delivery-notes"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <DeliveryNoteList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/delivery-notes/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <DeliveryNoteForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/delivery-notes/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <DeliveryNoteDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/delivery-notes/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <DeliveryNoteForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/invoices"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InvoiceList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/invoices/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InvoiceForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/invoices/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InvoiceDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/invoices/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InvoiceForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/payments"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PaymentList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/payments/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PaymentForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/payments/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PaymentForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/purchase-orders"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PurchaseOrderList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/purchase-orders/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PurchaseOrderForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/purchase-orders/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PurchaseOrderForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/purchase-orders/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PurchaseOrderDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/contracts"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ContractList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/contracts/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ContractForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/contracts/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ContractDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/contracts/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <ContractForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/targets"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TargetList />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/targets/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TargetForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/targets/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TargetForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/inquiry"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <InquiryAutoReply />
                    </Suspense>
                  }
                />
                <Route
                  path="/sales/dashboard"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SalesDashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/tickets"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TicketList />
                    </Suspense>
                  }
                />
                <Route
                  path="/tickets/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TicketForm />
                    </Suspense>
                  }
                />
                <Route
                  path="/tickets/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TicketDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/tickets/:id/edit"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <TicketForm />
                    </Suspense>
                  }
                />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </ErrorBoundary>
  );
}
