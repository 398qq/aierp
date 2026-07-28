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
    // 公开入口
    { path: "/login", component: "@/pages/auth/Login", layout: false },
    { path: "/inquiry", component: "@/pages/public/InquiryPortal", layout: false },

    // 受保护入口（ErpRouteLayout 负责认证守卫 + ProLayout）
    {
      path: "/",
      component: "@/layouts/ErpRouteLayout",
      routes: [
        // Dashboard
        { path: "", component: "@/pages/dashboard/index" },
        { path: "dashboard/watchtower", component: "@/pages/dashboard/WatchtowerDashboard" },
        { path: "dashboard/global360", component: "@/pages/dashboard/Global360" },

        // Customers (13)
        { path: "customers", component: "@/pages/customers/CustomerListPage" },
        { path: "customers/stats", component: "@/pages/customers/CustomerDashboard" },
        {
          path: "customers/intelligence",
          component: "@/pages/customers/CustomerIntelligenceDashboard",
        },
        { path: "customers/workbench", component: "@/pages/customers/CustomerAIWorkbench" },
        { path: "customers/segments", component: "@/pages/customers/CustomerSegments" },
        { path: "customers/new", component: "@/pages/customers/CustomerNew" },
        { path: "customers/follow-ups", component: "@/pages/customers/CustomerFollowUpsPage" },
        { path: "customers/assignment-rules", component: "@/pages/customers/AssignmentRulesPage" },
        {
          path: "customers/transfer-requests",
          component: "@/pages/customers/OwnerTransferRequestsPage",
        },
        { path: "customers/release-rules", component: "@/pages/customers/ReleaseRulesPage" },
        { path: "customers/:id", component: "@/pages/customers/CustomerDetail" },
        { path: "customers/:customerId/follow-ups", component: "@/pages/customers/FollowUpList" },
        {
          path: "customers/:customerId/follow-ups/new",
          component: "@/pages/customers/FollowUpForm",
        },
        {
          path: "customers/:customerId/follow-ups/:followupId/edit",
          component: "@/pages/customers/FollowUpForm",
        },

        // Sales (29)
        { path: "sales/dashboard", component: "@/pages/sales/SalesDashboard" },
        { path: "sales/opportunities", component: "@/pages/sales/OpportunityList" },
        { path: "sales/opportunities/new", component: "@/pages/sales/OpportunityForm" },
        { path: "sales/opportunities/:id", component: "@/pages/sales/OpportunityDetail" },
        { path: "sales/opportunities/:id/edit", component: "@/pages/sales/OpportunityForm" },
        { path: "sales/quotations", component: "@/pages/sales/QuotationList" },
        { path: "sales/quotations/new", component: "@/pages/sales/QuotationForm" },
        { path: "sales/quotations/:id", component: "@/pages/sales/QuotationDetail" },
        { path: "sales/quotations/:id/edit", component: "@/pages/sales/QuotationForm" },
        { path: "sales/orders", component: "@/pages/sales/SalesOrderList" },
        { path: "sales/orders/new", component: "@/pages/sales/SalesOrderForm" },
        { path: "sales/orders/:id", component: "@/pages/sales/SalesOrderDetail" },
        { path: "sales/orders/:id/edit", component: "@/pages/sales/SalesOrderForm" },
        { path: "sales/delivery-notes", component: "@/pages/sales/DeliveryNoteList" },
        { path: "sales/delivery-notes/new", component: "@/pages/sales/DeliveryNoteForm" },
        { path: "sales/delivery-notes/:id", component: "@/pages/sales/DeliveryNoteDetail" },
        { path: "sales/delivery-notes/:id/edit", component: "@/pages/sales/DeliveryNoteForm" },
        { path: "sales/invoices", component: "@/pages/sales/InvoiceList" },
        { path: "sales/invoices/new", component: "@/pages/sales/InvoiceForm" },
        { path: "sales/invoices/:id", component: "@/pages/sales/InvoiceDetail" },
        { path: "sales/invoices/:id/edit", component: "@/pages/sales/InvoiceForm" },
        { path: "sales/payments", component: "@/pages/sales/PaymentList" },
        { path: "sales/payments/new", component: "@/pages/sales/PaymentForm" },
        { path: "sales/payments/:id/edit", component: "@/pages/sales/PaymentForm" },
        { path: "sales/contracts", component: "@/pages/sales/ContractList" },
        { path: "sales/contracts/new", component: "@/pages/sales/ContractForm" },
        { path: "sales/contracts/:id", component: "@/pages/sales/ContractDetail" },
        { path: "sales/contracts/:id/edit", component: "@/pages/sales/ContractForm" },
        { path: "sales/targets", component: "@/pages/sales/TargetList" },
        { path: "sales/targets/new", component: "@/pages/sales/TargetForm" },
        { path: "sales/targets/:id/edit", component: "@/pages/sales/TargetForm" },
        { path: "sales/purchase-orders", component: "@/pages/sales/PurchaseOrderList" },
        { path: "sales/purchase-orders/new", component: "@/pages/sales/PurchaseOrderForm" },
        { path: "sales/purchase-orders/:id", component: "@/pages/sales/PurchaseOrderDetail" },
        { path: "sales/purchase-orders/:id/edit", component: "@/pages/sales/PurchaseOrderForm" },
        { path: "sales/inquiry", component: "@/pages/sales/InquiryAutoReply" },

        // Products (6)
        { path: "products", component: "@/pages/products/index" },
        { path: "products/inventory", component: "@/pages/products/InventoryManage" },
        { path: "products/price-import", component: "@/pages/products/PriceImport" },
        { path: "products/new", component: "@/pages/products/ProductEdit" },
        { path: "products/:id", component: "@/pages/products/ProductDetail" },
        { path: "products/:id/edit", component: "@/pages/products/ProductEdit" },
        { path: "products/:id/360", component: "@/pages/products/Product360" },

        // Suppliers (5)
        { path: "suppliers", component: "@/pages/suppliers/index" },
        { path: "suppliers/stats", component: "@/pages/suppliers/SupplierDashboard" },
        { path: "suppliers/compare", component: "@/pages/suppliers/SupplierCompare" },
        { path: "suppliers/:id", component: "@/pages/suppliers/SupplierDetail" },
        { path: "suppliers/:id/360", component: "@/pages/suppliers/Supplier360" },

        // Brands (4)
        { path: "brands", component: "@/pages/brands/index" },
        { path: "brands/stats", component: "@/pages/brands/BrandDashboard" },
        { path: "brands/:id", component: "@/pages/brands/BrandDetail" },
        { path: "brands/:id/edit", component: "@/pages/brands/BrandEdit" },

        // Inventory (4)
        { path: "inventory", component: "@/pages/inventory/index" },
        { path: "inventory/expiring", component: "@/pages/inventory/BatchExpiring" },
        { path: "inventory/batches/:id/recall", component: "@/pages/inventory/BatchRecall" },
        {
          path: "inventory/batches/:id/traceability",
          component: "@/pages/warehouse/BatchTraceability",
        },

        // Warehouse (5)
        { path: "warehouse", component: "@/pages/warehouse/index" },
        { path: "warehouse/warehouses", component: "@/pages/warehouse/WarehouseList" },
        { path: "warehouse/inventory-batches", component: "@/pages/warehouse/InventoryBatches" },
        { path: "warehouse/inventory-ledger", component: "@/pages/warehouse/InventoryLedger" },

        // Tickets (4)
        { path: "tickets", component: "@/pages/tickets/TicketList" },
        { path: "tickets/index", component: "@/pages/tickets/index" },
        { path: "tickets/new", component: "@/pages/tickets/TicketForm" },
        { path: "tickets/:id", component: "@/pages/tickets/TicketDetail" },
        { path: "tickets/:id/edit", component: "@/pages/tickets/TicketForm" },

        // Finance (8)
        { path: "finance/accounts", component: "@/pages/finance/AccountList" },
        { path: "finance/commissions", component: "@/pages/finance/CommissionList" },
        { path: "finance/commission-schemes", component: "@/pages/finance/CommissionSchemeList" },
        { path: "finance/journal-entries", component: "@/pages/finance/JournalEntryList" },
        { path: "finance/journal-entries/new", component: "@/pages/finance/JournalEntryForm" },
        { path: "finance/journal-entries/:id", component: "@/pages/finance/JournalEntryForm" },
        { path: "finance/pnl", component: "@/pages/finance/ProfitLoss" },

        // Procurement
        { path: "procurement/dashboard", component: "@/pages/procurement/ProcurementDashboard" },

        // System (7)
        { path: "system/users", component: "@/pages/system/Users" },
        { path: "system/roles", component: "@/pages/system/Roles" },
        { path: "system/uoms", component: "@/pages/system/UomsList" },
        { path: "system/approvals", component: "@/pages/system/ApprovalList" },
        { path: "system/approval-rules", component: "@/pages/system/ApprovalRules" },
        { path: "system/audit", component: "@/pages/system/AuditLogViewer" },
        { path: "system/audit-logs", component: "@/pages/system/AuditLogList" },

        // Reports (5)
        { path: "reports/sales", component: "@/pages/reports/ReportSales" },
        { path: "reports/inventory", component: "@/pages/reports/ReportInventory" },
        { path: "reports/procurement", component: "@/pages/reports/ReportProcurement" },
        { path: "reports/ar", component: "@/pages/reports/ReportAR" },
        { path: "reports/ap", component: "@/pages/reports/ReportAP" },

        // Other top-level
        { path: "notifications", component: "@/pages/notifications/index" },
        { path: "import-export", component: "@/pages/import-export/index" },
        { path: "data/import-export", component: "@/pages/import-export/index" },
        { path: "settings", component: "@/pages/settings/index" },
        { path: "ai/chat", component: "@/pages/ai/Chat" },
      ],
    },

    // Fallback
    { path: "*", redirect: "/" },
  ],
});
