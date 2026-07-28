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

    // 根 layout
    {
      path: "/",
      component: "@/layouts/ErpRouteLayout",
      routes: [
        { path: "", component: "@/pages/dashboard/index" },

        // Sales (13)
        { path: "sales", redirect: "/sales/dashboard" },
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
        { path: "sales/deliveries", component: "@/pages/sales/DeliveryNoteList" },
        { path: "sales/deliveries/new", component: "@/pages/sales/DeliveryNoteForm" },
        { path: "sales/deliveries/:id", component: "@/pages/sales/DeliveryNoteDetail" },
        { path: "sales/invoices", component: "@/pages/sales/InvoiceList" },
        { path: "sales/invoices/new", component: "@/pages/sales/InvoiceForm" },
        { path: "sales/invoices/:id", component: "@/pages/sales/InvoiceDetail" },
        { path: "sales/payments", component: "@/pages/sales/PaymentList" },
        { path: "sales/payments/new", component: "@/pages/sales/PaymentForm" },
        { path: "sales/contracts", component: "@/pages/sales/ContractList" },
        { path: "sales/contracts/new", component: "@/pages/sales/ContractForm" },
        { path: "sales/contracts/:id", component: "@/pages/sales/ContractDetail" },
        { path: "sales/targets", component: "@/pages/sales/TargetList" },
        { path: "sales/targets/new", component: "@/pages/sales/TargetForm" },
        { path: "sales/purchase-orders", component: "@/pages/sales/PurchaseOrderList" },
        { path: "sales/purchase-orders/new", component: "@/pages/sales/PurchaseOrderForm" },
        { path: "sales/purchase-orders/:id", component: "@/pages/sales/PurchaseOrderDetail" },
        { path: "sales/inquiry-auto-reply", component: "@/pages/sales/InquiryAutoReply" },

        // Customers (8)
        { path: "customers", component: "@/pages/customers/CustomerListPage" },
        { path: "customers/new", component: "@/pages/customers/CustomerNew" },
        { path: "customers/stats", component: "@/pages/customers/CustomerDashboard" },
        {
          path: "customers/intelligence",
          component: "@/pages/customers/CustomerIntelligenceDashboard",
        },
        { path: "customers/workbench", component: "@/pages/customers/CustomerAIWorkbench" },
        { path: "customers/segments", component: "@/pages/customers/CustomerSegments" },
        { path: "customers/:id", component: "@/pages/customers/CustomerDetail" },
        { path: "customers/:id/360", component: "@/pages/customers/Customer360" },

        // Products (5)
        { path: "products", component: "@/pages/products/index" },
        { path: "products/new", component: "@/pages/products/ProductEdit" },
        { path: "products/:id", component: "@/pages/products/ProductDetail" },
        { path: "products/:id/edit", component: "@/pages/products/ProductEdit" },
        { path: "products/:id/360", component: "@/pages/products/Product360" },

        // Suppliers (4)
        { path: "suppliers", component: "@/pages/suppliers/index" },
        { path: "suppliers/dashboard", component: "@/pages/suppliers/SupplierDashboard" },
        { path: "suppliers/:id", component: "@/pages/suppliers/SupplierDetail" },
        { path: "suppliers/:id/360", component: "@/pages/suppliers/Supplier360" },

        // Brands (4)
        { path: "brands", component: "@/pages/brands/index" },
        { path: "brands/dashboard", component: "@/pages/brands/BrandDashboard" },
        { path: "brands/:id", component: "@/pages/brands/BrandDetail" },
        { path: "brands/:id/edit", component: "@/pages/brands/BrandEdit" },

        // Inventory (3)
        { path: "inventory", component: "@/pages/inventory/index" },
        { path: "inventory/expiring", component: "@/pages/inventory/BatchExpiring" },
        { path: "inventory/recall", component: "@/pages/inventory/BatchRecall" },

        // Warehouse (5)
        { path: "warehouse", component: "@/pages/warehouse/index" },
        { path: "warehouse/traceability", component: "@/pages/warehouse/BatchTraceability" },
        { path: "warehouse/warehouses", component: "@/pages/warehouse/WarehouseList" },
        { path: "warehouse/ledger", component: "@/pages/warehouse/InventoryLedger" },
        { path: "warehouse/batches", component: "@/pages/warehouse/InventoryBatches" },

        // Tickets (3)
        { path: "tickets", component: "@/pages/tickets/TicketList" },
        { path: "tickets/new", component: "@/pages/tickets/TicketForm" },
        { path: "tickets/:id", component: "@/pages/tickets/TicketDetail" },

        // Finance (5)
        { path: "finance/journal-entries", component: "@/pages/finance/JournalEntryList" },
        { path: "finance/journal-entries/new", component: "@/pages/finance/JournalEntryForm" },
        { path: "finance/commission-schemes", component: "@/pages/finance/CommissionSchemeList" },
        { path: "finance/accounts", component: "@/pages/finance/AccountList" },
        { path: "finance/profit-loss", component: "@/pages/finance/ProfitLoss" },

        // Other (10)
        { path: "notifications", component: "@/pages/notifications/index" },
        { path: "reports", component: "@/pages/reports/index" },
        { path: "import-export", component: "@/pages/import-export/index" },
        { path: "settings", component: "@/pages/settings/index" },
        { path: "procurement", component: "@/pages/procurement/index" },
        { path: "ai/chat", component: "@/pages/ai/Chat" },
        { path: "system/users", component: "@/pages/system/users/UserList" },
        { path: "dashboard/watchtower", component: "@/pages/dashboard/WatchtowerDashboard" },
        { path: "dashboard/global-360", component: "@/pages/dashboard/Global360" },
      ],
    },

    { path: "*", redirect: "/" },
  ],
});
