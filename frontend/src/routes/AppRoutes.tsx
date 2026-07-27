import { lazy, Suspense } from "react";
import type { ComponentType } from "react";
import { Navigate, useParams, useRoutes } from "react-router";
import type { RouteObject } from "react-router";

import AuthenticatedAppShell from "../layouts/AuthenticatedAppShell";
import Login from "../pages/auth/Login";
import FullPageLoader from "../ui/FullPageLoader";

type PageModule = { default: ComponentType };
type PageImporter = () => Promise<PageModule>;

function lazyPage(load: PageImporter) {
  const Page = lazy(load);
  return (
    <Suspense fallback={<FullPageLoader />}>
      <Page />
    </Suspense>
  );
}

function CustomerTabRedirect({ tab }: { tab: "ai" | "profile" }) {
  const { id } = useParams();
  return <Navigate to={`/customers/${id}?tab=${tab}`} replace />;
}

export const appRoutes: RouteObject[] = [
  { path: "/login", element: <Login /> },
  { path: "/inquiry", element: lazyPage(() => import("../pages/public/InquiryPortal")) },
  {
    element: <AuthenticatedAppShell />,
    children: [
      { path: "/", element: lazyPage(() => import("../pages/dashboard/index")) },
      {
        path: "/dashboard/watchtower",
        element: lazyPage(() => import("../pages/dashboard/WatchtowerDashboard")),
      },
      {
        path: "/dashboard/global360",
        element: lazyPage(() => import("../pages/dashboard/Global360")),
      },
      {
        path: "/customers",
        element: lazyPage(() => import("../pages/customers/CustomerListPage")),
      },
      {
        path: "/customers/stats",
        element: lazyPage(() => import("../pages/customers/CustomerDashboard")),
      },
      {
        path: "/customers/intelligence",
        element: lazyPage(() => import("../pages/customers/CustomerIntelligenceDashboard")),
      },
      {
        path: "/customers/workbench",
        element: lazyPage(() => import("../pages/customers/CustomerAIWorkbench")),
      },
      {
        path: "/customers/new",
        element: lazyPage(() => import("../pages/customers/CustomerNew")),
      },
      {
        path: "/customers/follow-ups",
        element: lazyPage(() => import("../pages/customers/CustomerFollowUpsPage")),
      },
      {
        path: "/customers/assignment-rules",
        element: lazyPage(() => import("../pages/customers/AssignmentRulesPage")),
      },
      {
        path: "/customers/transfer-requests",
        element: lazyPage(() => import("../pages/customers/OwnerTransferRequestsPage")),
      },
      {
        path: "/customers/release-rules",
        element: lazyPage(() => import("../pages/customers/ReleaseRulesPage")),
      },
      {
        path: "/customers/:id",
        element: lazyPage(() => import("../pages/customers/CustomerDetail")),
      },
      {
        path: "/customers/:id/insight",
        element: <CustomerTabRedirect tab="ai" />,
      },
      {
        path: "/customers/:id/360",
        element: <CustomerTabRedirect tab="profile" />,
      },
      {
        path: "/customers/:customerId/follow-ups",
        element: lazyPage(() => import("../pages/customers/FollowUpList")),
      },
      {
        path: "/customers/:customerId/follow-ups/new",
        element: lazyPage(() => import("../pages/customers/FollowUpForm")),
      },
      {
        path: "/customers/:customerId/follow-ups/:followupId/edit",
        element: lazyPage(() => import("../pages/customers/FollowUpForm")),
      },
      {
        path: "/customers/segments",
        element: lazyPage(() => import("../pages/customers/CustomerSegments")),
      },
      { path: "/products", element: lazyPage(() => import("../pages/products/index")) },
      {
        path: "/products/:id",
        element: lazyPage(() => import("../pages/products/ProductDetail")),
      },
      {
        path: "/products/:id/edit",
        element: lazyPage(() => import("../pages/products/ProductEdit")),
      },
      {
        path: "/products/:id/360",
        element: lazyPage(() => import("../pages/products/Product360")),
      },
      {
        path: "/products/price-import",
        element: lazyPage(() => import("../pages/products/PriceImport")),
      },
      {
        path: "/products/inventory",
        element: lazyPage(() => import("../pages/products/InventoryManage")),
      },
      { path: "/suppliers", element: lazyPage(() => import("../pages/suppliers/index")) },
      {
        path: "/suppliers/stats",
        element: lazyPage(() => import("../pages/suppliers/SupplierDashboard")),
      },
      {
        path: "/suppliers/:id",
        element: lazyPage(() => import("../pages/suppliers/SupplierDetail")),
      },
      {
        path: "/suppliers/:id/360",
        element: lazyPage(() => import("../pages/suppliers/Supplier360")),
      },
      {
        path: "/suppliers/compare",
        element: lazyPage(() => import("../pages/suppliers/SupplierCompare")),
      },
      { path: "/brands", element: lazyPage(() => import("../pages/brands/index")) },
      {
        path: "/brands/stats",
        element: lazyPage(() => import("../pages/brands/BrandDashboard")),
      },
      {
        path: "/brands/:id",
        element: lazyPage(() => import("../pages/brands/BrandDetail")),
      },
      {
        path: "/brands/:id/edit",
        element: lazyPage(() => import("../pages/brands/BrandEdit")),
      },
      { path: "/inventory", element: lazyPage(() => import("../pages/inventory/index")) },
      {
        path: "/inventory/expiring",
        element: lazyPage(() => import("../pages/inventory/BatchExpiring")),
      },
      {
        path: "/inventory/batches/:id/recall",
        element: lazyPage(() => import("../pages/inventory/BatchRecall")),
      },
      { path: "/warehouse", element: lazyPage(() => import("../pages/warehouse/index")) },
      {
        path: "/warehouse/warehouses",
        element: lazyPage(() => import("../pages/warehouse/WarehouseList")),
      },
      {
        path: "/warehouse/inventory-ledger",
        element: lazyPage(() => import("../pages/warehouse/InventoryLedger")),
      },
      {
        path: "/warehouse/inventory-batches",
        element: lazyPage(() => import("../pages/warehouse/InventoryBatches")),
      },
      {
        path: "/inventory/batches/:id/traceability",
        element: lazyPage(() => import("../pages/warehouse/BatchTraceability")),
      },
      { path: "/settings", element: lazyPage(() => import("../pages/settings/index")) },
      {
        path: "/system/users",
        element: lazyPage(() => import("../pages/system/users/UserList")),
      },
      {
        path: "/system/roles",
        element: lazyPage(() => import("../pages/system/Roles")),
      },
      {
        path: "/system/approvals",
        element: lazyPage(() => import("../pages/system/ApprovalList")),
      },
      {
        path: "/system/approval-rules",
        element: lazyPage(() => import("../pages/system/ApprovalRules")),
      },
      {
        path: "/system/audit-logs",
        element: lazyPage(() => import("../pages/system/AuditLogList")),
      },
      {
        path: "/system/uoms",
        element: lazyPage(() => import("../pages/system/UomsList")),
      },
      {
        path: "/procurement/dashboard",
        element: lazyPage(() => import("../pages/procurement/ProcurementDashboard")),
      },
      {
        path: "/reports/sales",
        element: lazyPage(() => import("../pages/reports/ReportSales")),
      },
      { path: "/reports/ar", element: lazyPage(() => import("../pages/reports/ReportAR")) },
      {
        path: "/reports/inventory",
        element: lazyPage(() => import("../pages/reports/ReportInventory")),
      },
      {
        path: "/reports/procurement",
        element: lazyPage(() => import("../pages/reports/ReportProcurement")),
      },
      { path: "/reports/ap", element: lazyPage(() => import("../pages/reports/ReportAP")) },
      {
        path: "/data/import-export",
        element: lazyPage(() => import("../pages/import-export/index")),
      },
      {
        path: "/finance/accounts",
        element: lazyPage(() => import("../pages/finance/AccountList")),
      },
      {
        path: "/finance/journal-entries",
        element: lazyPage(() => import("../pages/finance/JournalEntryList")),
      },
      {
        path: "/finance/journal-entries/new",
        element: lazyPage(() => import("../pages/finance/JournalEntryForm")),
      },
      {
        path: "/finance/journal-entries/:id",
        element: lazyPage(() => import("../pages/finance/JournalEntryForm")),
      },
      {
        path: "/finance/pnl",
        element: lazyPage(() => import("../pages/finance/ProfitLoss")),
      },
      {
        path: "/finance/commissions",
        element: lazyPage(() => import("../pages/finance/CommissionList")),
      },
      {
        path: "/finance/commission-schemes",
        element: lazyPage(() => import("../pages/finance/CommissionSchemeList")),
      },
      {
        path: "/system/audit",
        element: lazyPage(() => import("../pages/system/AuditLogViewer")),
      },
      { path: "/ai/chat", element: lazyPage(() => import("../pages/ai/Chat")) },
      {
        path: "/notifications",
        element: lazyPage(() => import("../pages/notifications/index")),
      },
      { path: "/sales", element: <Navigate to="/sales/dashboard" replace /> },
      {
        path: "/sales/opportunities",
        element: lazyPage(() => import("../pages/sales/OpportunityList")),
      },
      {
        path: "/sales/opportunities/new",
        element: lazyPage(() => import("../pages/sales/OpportunityForm")),
      },
      {
        path: "/sales/opportunities/:id",
        element: lazyPage(() => import("../pages/sales/OpportunityDetail")),
      },
      {
        path: "/sales/opportunities/:id/edit",
        element: lazyPage(() => import("../pages/sales/OpportunityForm")),
      },
      {
        path: "/sales/quotations",
        element: lazyPage(() => import("../pages/sales/QuotationList")),
      },
      {
        path: "/sales/quotations/new",
        element: lazyPage(() => import("../pages/sales/QuotationForm")),
      },
      {
        path: "/sales/quotations/:id",
        element: lazyPage(() => import("../pages/sales/QuotationDetail")),
      },
      {
        path: "/sales/quotations/:id/edit",
        element: lazyPage(() => import("../pages/sales/QuotationForm")),
      },
      {
        path: "/sales/orders",
        element: lazyPage(() => import("../pages/sales/SalesOrderList")),
      },
      {
        path: "/sales/orders/new",
        element: lazyPage(() => import("../pages/sales/SalesOrderForm")),
      },
      {
        path: "/sales/orders/:id",
        element: lazyPage(() => import("../pages/sales/SalesOrderDetail")),
      },
      {
        path: "/sales/orders/:id/edit",
        element: lazyPage(() => import("../pages/sales/SalesOrderForm")),
      },
      {
        path: "/sales/delivery-notes",
        element: lazyPage(() => import("../pages/sales/DeliveryNoteList")),
      },
      {
        path: "/sales/delivery-notes/new",
        element: lazyPage(() => import("../pages/sales/DeliveryNoteForm")),
      },
      {
        path: "/sales/delivery-notes/:id",
        element: lazyPage(() => import("../pages/sales/DeliveryNoteDetail")),
      },
      {
        path: "/sales/delivery-notes/:id/edit",
        element: lazyPage(() => import("../pages/sales/DeliveryNoteForm")),
      },
      {
        path: "/sales/invoices",
        element: lazyPage(() => import("../pages/sales/InvoiceList")),
      },
      {
        path: "/sales/invoices/new",
        element: lazyPage(() => import("../pages/sales/InvoiceForm")),
      },
      {
        path: "/sales/invoices/:id",
        element: lazyPage(() => import("../pages/sales/InvoiceDetail")),
      },
      {
        path: "/sales/invoices/:id/edit",
        element: lazyPage(() => import("../pages/sales/InvoiceForm")),
      },
      {
        path: "/sales/payments",
        element: lazyPage(() => import("../pages/sales/PaymentList")),
      },
      {
        path: "/sales/payments/new",
        element: lazyPage(() => import("../pages/sales/PaymentForm")),
      },
      {
        path: "/sales/payments/:id/edit",
        element: lazyPage(() => import("../pages/sales/PaymentForm")),
      },
      {
        path: "/sales/purchase-orders",
        element: lazyPage(() => import("../pages/sales/PurchaseOrderList")),
      },
      {
        path: "/sales/purchase-orders/new",
        element: lazyPage(() => import("../pages/sales/PurchaseOrderForm")),
      },
      {
        path: "/sales/purchase-orders/:id/edit",
        element: lazyPage(() => import("../pages/sales/PurchaseOrderForm")),
      },
      {
        path: "/sales/purchase-orders/:id",
        element: lazyPage(() => import("../pages/sales/PurchaseOrderDetail")),
      },
      {
        path: "/sales/contracts",
        element: lazyPage(() => import("../pages/sales/ContractList")),
      },
      {
        path: "/sales/contracts/new",
        element: lazyPage(() => import("../pages/sales/ContractForm")),
      },
      {
        path: "/sales/contracts/:id",
        element: lazyPage(() => import("../pages/sales/ContractDetail")),
      },
      {
        path: "/sales/contracts/:id/edit",
        element: lazyPage(() => import("../pages/sales/ContractForm")),
      },
      {
        path: "/sales/targets",
        element: lazyPage(() => import("../pages/sales/TargetList")),
      },
      {
        path: "/sales/targets/new",
        element: lazyPage(() => import("../pages/sales/TargetForm")),
      },
      {
        path: "/sales/targets/:id/edit",
        element: lazyPage(() => import("../pages/sales/TargetForm")),
      },
      {
        path: "/sales/inquiry",
        element: lazyPage(() => import("../pages/sales/InquiryAutoReply")),
      },
      {
        path: "/sales/dashboard",
        element: lazyPage(() => import("../pages/sales/SalesDashboard")),
      },
      { path: "/tickets", element: lazyPage(() => import("../pages/tickets/TicketList")) },
      {
        path: "/tickets/new",
        element: lazyPage(() => import("../pages/tickets/TicketForm")),
      },
      {
        path: "/tickets/:id",
        element: lazyPage(() => import("../pages/tickets/TicketDetail")),
      },
      {
        path: "/tickets/:id/edit",
        element: lazyPage(() => import("../pages/tickets/TicketForm")),
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];

export default function AppRoutes() {
  return useRoutes(appRoutes);
}
