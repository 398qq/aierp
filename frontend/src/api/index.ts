import client from "./client";
import type {
  AlertEvent, AlertRule, APIResponse, Attachment, Brand, BrandComparison, BrandCustomerPenetration, BrandHealth, BrandImport, BrandLifecycle, BrandPortfolio, BrandPriceTrends, BrandProductPerformance, BrandProfile, BrandRecommendation, BrandRisk, BrandSupplierMatrix,
  ChurnRisk, Contract, Customer, Customer360, CustomerAIStats, CustomerLog, CustomerProductMatch, CustomerRecognition, CustomerStats,
  DashboardStats, DashboardWidget, DeliveryNote, DeliveryNoteAI, Document, DuplicatePair,
  FollowUp, FollowUpRecognition, FollowUpReminder,
  Global360, GroupStats,
  Invoice, KpiData, LevelRule, LifecycleAnalysis, LoginData,
  MergeResult,
  NLPQueryResult, NormalizedSpec,
  InventoryItem,
  NotificationItem,
  Opportunity, OpportunityAI, OverdueFollowUp,
  PageData, PaymentRecord, POAutoSuggest, POOptimization, PORiskAssessment, PriceBenchmark, PriceRecommendation, ProcurementPlan, Product, Product360, ProductAssociation, ProductCustomerMatch, ProductProfile, PurchaseOrder,
  Quotation, QuotationAI, RFMAnalysis,
  SalesOrder, SalesOrderAI, SalesTarget, Sample, SimilarBrand, Supplier, Supplier360, SupplierAlternatives, SupplierComparison, SupplierDelayPrediction, SupplierNegotiation, SupplierPriceVariance, SupplierProductLink, SupplierScorecard,
  Tag, Ticket, TicketClassification, TicketCluster, TicketResolutionPrediction, TicketResponse, TimelineEvent,
  Visit, VisitEffectiveness, VisitReport, VisitSentiment,
  Warehouse,
} from "../types";

// Auth
export const login = (username: string, password: string) =>
  client.post<APIResponse<LoginData>>("/auth/login", { username, password });

export const getMe = () => client.get<APIResponse>("/auth/me");

export const changePassword = (current_password: string, new_password: string) =>
  client.post<APIResponse>("/auth/change-password", { current_password, new_password });

// Users
export const getUsers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Record<string, unknown>>>>("/users", { params });

export const getUser = (id: number) =>
  client.get<APIResponse<Record<string, unknown>>>(`/users/${id}`);

export const createUser = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/users", data);

export const updateUser = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/users/${id}`, data);

export const deleteUser = (id: number) =>
  client.delete<APIResponse>(`/users/${id}`);

// Customers
export const getCustomers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Customer>>>("/customers", { params });

export const getCustomer = (id: number) =>
  client.get<APIResponse<Customer>>(`/customers/${id}`);

export const createCustomer = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers", data);

export const updateCustomer = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${id}`, data);

export const deleteCustomer = (id: number) =>
  client.delete<APIResponse>(`/customers/${id}`);

export const getContacts = (customerId: number) =>
  client.get<APIResponse>(`/customers/${customerId}/contacts`);

export const createContact = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/contacts`, data);

export const getFollowUps = (customerId: number) =>
  client.get<APIResponse<FollowUp[]>>(`/customers/${customerId}/follow-ups`);

export const createFollowUp = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/follow-ups`, data);

export const updateContact = (customerId: number, contactId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${customerId}/contacts/${contactId}`, data);

export const deleteContact = (customerId: number, contactId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/contacts/${contactId}`);

export const updateFollowUp = (customerId: number, followupId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`, data);

export const deleteFollowUp = (customerId: number, followupId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`);

export const getTimeline = (customerId: number) =>
  client.get<APIResponse<TimelineEvent[]>>(`/customers/${customerId}/timeline`);

export const getCustomerStats = (customerId: number) =>
  client.get<APIResponse<CustomerStats>>(`/customers/${customerId}/stats`);

export const getDashboardStats = () =>
  client.get<APIResponse<DashboardStats>>("/customers/stats");

export const getCustomerAIStats = () =>
  client.get<APIResponse<CustomerAIStats>>("/customers/ai-stats");

export const batchScoreAI = (ids?: number[]) =>
  client.post<APIResponse<{ scored: number; errors: number; total: number }>>(
    "/customers/batch-score-ai", ids ? { ids } : {}
  );

export const getOverdueFollowUps = () =>
  client.get<APIResponse<{ total: number; items: OverdueFollowUp[] }>>("/customers/overdue-followups");

export const getFollowUpReminders = () =>
  client.get<APIResponse<{ total: number; counts: Record<string, number>; items: FollowUpReminder[] }>>("/customers/follow-up-reminders");

export const exportCustomers = (params: Record<string, unknown>) =>
  client.get("/customers/export", { params, responseType: "blob" });

export const downloadImportTemplate = () =>
  client.get("/customers/import-template", { responseType: "blob" });

export const importCustomers = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/customers/import", form, { headers: { "Content-Type": "multipart/form-data" } });
};

export const batchDeleteCustomers = (ids: number[]) =>
  client.post<APIResponse>("/customers/batch-delete", { ids });

export const batchTagCustomers = (ids: number[], tag_ids: number[]) =>
  client.post<APIResponse>("/customers/batch-tag", { ids, tag_ids });

// Tags
export const getTags = () =>
  client.get<APIResponse<Tag[]>>("/tags");

export const createTag = (data: Record<string, unknown>) =>
  client.post<APIResponse<Tag>>("/tags", data);

export const updateTag = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Tag>>(`/tags/${id}`, data);

export const deleteTag = (id: number) =>
  client.delete<APIResponse>(`/tags/${id}`);

export const getCustomerTags = (customerId: number) =>
  client.get<APIResponse<Tag[]>>(`/customers/${customerId}/tags`);

export const linkTag = (customerId: number, tagId: number) =>
  client.post<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

export const unlinkTag = (customerId: number, tagId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

// Attachments (legacy customer-specific)
export const getAttachments = (customerId: number) =>
  client.get<APIResponse<Attachment[]>>(`/customers/${customerId}/attachments`);

export const uploadAttachment = (customerId: number, file: File, category = "contract") => {
  const form = new FormData();
  form.append("file", file);
  return client.post(`/customers/${customerId}/attachments?category=${category}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const deleteAttachment = (customerId: number, attachmentId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/attachments/${attachmentId}`);

// Documents (Phase 7 — generic entity attachments)
export const getDocuments = (entityType: string, entityId: number) =>
  client.get<APIResponse<Document[]>>(`/documents?entity_type=${entityType}&entity_id=${entityId}`);

export const uploadDocument = (entityType: string, entityId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", entityType);
  form.append("entity_id", String(entityId));
  return client.post<APIResponse>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const downloadDocument = (docId: number) =>
  client.get(`/documents/${docId}/download`, { responseType: "blob" });

export const deleteDocument = (docId: number) =>
  client.delete<APIResponse>(`/documents/${docId}`);

// Dashboard widgets (Phase 7)
export const getWidgets = () =>
  client.get<APIResponse<DashboardWidget[]>>("/dashboard/widgets");

export const saveWidgets = (widgets: Partial<DashboardWidget>[]) =>
  client.put<APIResponse>("/dashboard/widgets", { widgets });

export const getKpi = () =>
  client.get<APIResponse<KpiData>>("/dashboard/kpi");

// Import/Export (Phase 7)
export const exportEntity = (entity: string, format: string = "csv") =>
  client.get(`/export/${entity}?format=${format}`, { responseType: "blob" });

export const importEntity = (entity: string, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<APIResponse>(`/import/${entity}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// Products
export const getProducts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Product>>>("/products", { params });

export const getProduct = (id: number) =>
  client.get<APIResponse<Product>>(`/products/${id}`);

export const getProductStats = () =>
  client.get<APIResponse<{
    total: number;
    in_stock_count: number;
    out_of_stock_count: number;
    low_stock_count: number;
    pending_completion_count: number;
    stale_30d_count: number;
    generated_at: string;
  }>>(`/products/stats/summary`);

export const createProduct = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/products", data);

export const updateProduct = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/products/${id}`, data);

export const deleteProduct = (id: number) =>
  client.delete<APIResponse>(`/products/${id}`);

export const batchDeleteProducts = (ids: number[]) =>
  client.post<APIResponse>(`/products/batch-delete`, { ids });

export const batchUpdateProducts = (ids: number[], fields: Record<string, unknown>) =>
  client.patch<APIResponse>(`/products/batch`, { ids, ...fields });

export const importProducts = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<APIResponse>(`/import/products`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getProductSales = (productId: number) =>
  client.get<APIResponse<{ quotations: Record<string, unknown>[]; orders: Record<string, unknown>[]; deliveries: Record<string, unknown>[] }>>(`/products/${productId}/sales`);

// Price Import
export const priceImport = (items: { sku: string; warehouse_id: number; unit_price?: number; quantity?: number }[]) =>
  client.post<APIResponse<{ success: number; failed: number; errors: string[] }>>("/products/price-import", { items });

// Brands
export const getBrands = (params?: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Brand>> | APIResponse<Brand[]>>("/brands", { params });

export const getBrand = (id: number) =>
  client.get<APIResponse<Brand>>(`/brands/${id}`);

export const createBrand = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/brands", data);

export const updateBrand = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/brands/${id}`, data);

export const deleteBrand = (id: number) =>
  client.delete<APIResponse>(`/brands/${id}`);

// Suppliers
export const getSuppliers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Supplier>>>("/suppliers", { params });

export const getSupplier = (id: number) =>
  client.get<APIResponse<Supplier>>(`/suppliers/${id}`);

export const createSupplier = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/suppliers", data);

export const updateSupplier = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Supplier>>(`/suppliers/${id}`, data);

export const getSupplierStats = () =>
  client.get<APIResponse<Record<string, unknown>>>("/suppliers/stats/summary");

// Supplier-Product Linkage
export const getSupplierProducts = (supplierId: number) =>
  client.get<APIResponse<SupplierProductLink[]>>(`/suppliers/${supplierId}/products`);

export const linkSupplierProduct = (supplierId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/suppliers/${supplierId}/products`, data);

export const updateSupplierProduct = (supplierId: number, productId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/suppliers/${supplierId}/products/${productId}`, data);

export const unlinkSupplierProduct = (supplierId: number, productId: number) =>
  client.delete<APIResponse>(`/suppliers/${supplierId}/products/${productId}`);

export const aiMatchSupplierProducts = (supplierId: number, catalogText?: string, autoLink = false) =>
  client.post<APIResponse>(`/ai/suppliers/${supplierId}/match-products?auto_link=${autoLink}${catalogText ? `&catalog_text=${encodeURIComponent(catalogText)}` : ''}`);

// Pricing AI
export const getPricingBenchmark = (productId: number) =>
  client.get<APIResponse>(`/ai/pricing/benchmark/${productId}`);

export const getPricingRecommend = (params: { product_id: number; customer_id?: number; quantity?: number; is_sample?: boolean }) =>
  client.post<APIResponse>("/ai/pricing/recommend", undefined, { params });

// Product Intelligence
export const getProductProfile = (productId: number) =>
  client.post<APIResponse<ProductProfile>>(`/ai/products/${productId}/profile`);

export const normalizeProductSpecs = (productId: number) =>
  client.post<APIResponse<{ parameters: NormalizedSpec[]; raw: string }>>(`/ai/products/${productId}/normalize-specs`);

export const getProductAssociations = (productId: number, topK = 10) =>
  client.get<APIResponse<{ associations: ProductAssociation[]; target_product_id: number }>>(`/ai/products/${productId}/associations?top_k=${topK}`);

export const getProcurementOptimize = (productId: number, quantity: number) =>
  client.post<APIResponse<ProcurementPlan>>(`/ai/products/${productId}/procurement-optimize?quantity=${quantity}`);

export const getProductLifecycle = (productId: number) =>
  client.post<APIResponse<LifecycleAnalysis>>(`/ai/products/${productId}/lifecycle`);

// Brand Intelligence
export const getBrandProfile = (brandId: number) =>
  client.post<APIResponse<BrandProfile>>(`/ai/brands/${brandId}/profile`);

export const getBrandPortfolio = (brandId: number) =>
  client.post<APIResponse<BrandPortfolio>>(`/ai/brands/${brandId}/portfolio`);

export const getSimilarBrands = (brandId: number, topK = 5) =>
  client.get<APIResponse<SimilarBrand[]>>(`/ai/brands/${brandId}/similar?top_k=${topK}`);

export const compareBrands = (brandA: number, brandB: number) =>
  client.post<APIResponse<BrandComparison>>(`/ai/brands/compare?brand_a=${brandA}&brand_b=${brandB}`);

export const importBrandFromText = (text: string, autoCreate = false) =>
  client.post<APIResponse<BrandImport>>(`/ai/brands/import?text=${encodeURIComponent(text)}&auto_create=${autoCreate}`);

// Brand Health Dashboard
export const getBrandHealth = (brandId: number) =>
  client.post<APIResponse<BrandHealth>>(`/ai/brands/${brandId}/health`);

// Brand Risk Assessment
export const getBrandRisk = (brandId: number) =>
  client.post<APIResponse<BrandRisk>>(`/ai/brands/${brandId}/risk`);

// Brand-Supplier Matrix
export const getBrandSupplierMatrix = (brandId: number) =>
  client.post<APIResponse<BrandSupplierMatrix>>(`/ai/brands/${brandId}/supplier-matrix`);

// Brand Recommendations
export const getBrandRecommendations = (brandId: number, topK = 5) =>
  client.post<APIResponse<BrandRecommendation>>(`/ai/brands/${brandId}/recommendations?top_k=${topK}`);

// Smart Matching
export const recommendProductsForCustomer = (customerId: number, topK = 5) =>
  client.post<APIResponse<CustomerProductMatch>>(`/ai/customers/${customerId}/recommend-products?top_k=${topK}`);

export const recommendCustomersForProduct = (productId: number, topK = 5) =>
  client.post<APIResponse<ProductCustomerMatch>>(`/ai/products/${productId}/recommend-customers?top_k=${topK}`);

// Brand Product Performance
export const getBrandProductPerformance = (brandId: number) =>
  client.post<APIResponse<BrandProductPerformance>>(`/ai/brands/${brandId}/product-performance`);

// Brand Customer Penetration
export const getBrandCustomerPenetration = (brandId: number) =>
  client.post<APIResponse<BrandCustomerPenetration>>(`/ai/brands/${brandId}/customer-penetration`);

// Brand Lifecycle Prediction
export const getBrandLifecycle = (brandId: number) =>
  client.post<APIResponse<BrandLifecycle>>(`/ai/brands/${brandId}/lifecycle`);

// Brand Price Trends
export const getBrandPriceTrends = (brandId: number) =>
  client.post<APIResponse<BrandPriceTrends>>(`/ai/brands/${brandId}/price-trends`);

export const autoCompleteBrand = (brandId: number) =>
  client.post<APIResponse<{filled: Record<string, string>; message: string}>>(`/ai/brands/${brandId}/auto-complete`);

export const getBrandStats = () =>
  client.get<APIResponse<Record<string, unknown>>>("/brands/stats/summary");

export const batchUpdateBrands = (ids: number[], updates: Record<string, unknown>) =>
  client.patch<APIResponse<{updated: number; fields: string[]}>>("/brands/batch", { ids, updates });

export const batchDeleteBrands = (ids: number[]) =>
  client.post<APIResponse<{deleted: number}>>("/brands/batch-delete", { ids });

export const getEolAlerts = (urgency?: string) =>
  client.get<APIResponse<{total_alerts: number; critical_count: number; warning_count: number; alerts: {brand_id: number; brand_name: string; lifecycle_stage: string; stage_label: string; severity: string; affected_products: number; sales_exposure: number; alternative_brands: string[]; recommended_action: string}[]}>>(
    `/ai/brands/eol-alerts${urgency ? `?urgency_threshold=${urgency}` : ""}`
  );

// Warehouses & Inventory
export const getWarehouses = () =>
  client.get<APIResponse<Warehouse[]>>("/warehouses");

export const createWarehouse = (data: { name: string; location?: string; description?: string }) =>
  client.post<APIResponse<{ id: number; name: string; location: string | null; description: string | null }>>("/warehouses", undefined, { params: data });

export const updateWarehouse = (id: number, data: { name: string; location?: string; description?: string }) =>
  client.put<APIResponse<{ id: number; name: string; location: string | null; description: string | null }>>(`/warehouses/${id}`, undefined, { params: data });

export const deleteWarehouse = (id: number) =>
  client.delete<APIResponse<{ id: number }>>(`/warehouses/${id}`);

export const getInventoryTransactions = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<{
    id: number; product_id: number; warehouse_id: number; type: string;
    quantity: number; before_qty: number | null; after_qty: number | null;
    reference_type: string | null; reference_id: number | null; notes: string | null;
    created_at: string; product_name: string; warehouse_name: string;
  }>>>(`/inventory-transactions`, { params });

export const getInventory = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<InventoryItem>>>("/inventory", { params });

// Inventory intelligence
export const getInventoryOverview = () =>
  client.get<APIResponse>("/inventory/overview");

export const adjustInventory = (product_id: number, warehouse_id: number, adjustment: number, reason: string) =>
  client.post<APIResponse>(`/inventory/adjust?product_id=${product_id}&warehouse_id=${warehouse_id}&adjustment=${adjustment}&reason=${encodeURIComponent(reason)}`);

export const batchAdjustInventory = (items: { product_id: number; warehouse_id: number; adjustment: number; reason: string }[]) =>
  client.post<APIResponse>("/inventory/batch-adjust", { items });

// Products Inventory CRUD (under /products/inventories)
export const getProductInventories = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<InventoryItem>>>("/products/inventories", { params });

export const createProductInventory = (data: { product_id: number; warehouse_id: number; quantity: number; safety_stock?: number; unit_price?: number }) =>
  client.post<APIResponse>("/products/inventories", data);

export const updateProductInventory = (id: number, data: { quantity?: number; safety_stock?: number; unit_price?: number }) =>
  client.put<APIResponse>(`/products/inventories/${id}`, data);

export const deleteProductInventory = (id: number) =>
  client.delete<APIResponse>(`/products/inventories/${id}`);

// Product AI
export const aiParseProduct = (text: string) =>
  client.post<APIResponse>(`/ai/products/parse?text=${encodeURIComponent(text)}`);

export const aiParseBom = (text: string) =>
  client.post<APIResponse>(`/ai/products/parse-bom?text=${encodeURIComponent(text)}`);

export const aiProductSearch = (q: string, top_k = 10) =>
  client.post<APIResponse>(`/ai/products/search?q=${encodeURIComponent(q)}&top_k=${top_k}`);

export const embedProduct = (id: number) =>
  client.post<APIResponse>(`/ai/products/${id}/embed`);

export const embedAllProducts = () =>
  client.post<APIResponse>("/ai/products/embed-all");

export const similarProducts = (id: number, top_k = 10) =>
  client.get<APIResponse>(`/ai/products/${id}/similar?top_k=${top_k}`);

export const aiSearchProducts = (q: string, top_k = 20) =>
  client.post<APIResponse>(`/ai/products/search?q=${encodeURIComponent(q)}&top_k=${top_k}`, {});

export const productSubstitutes = (id: number) =>
  client.get<APIResponse>(`/ai/products/${id}/substitutes`);

// Purchase Orders
export const getPurchaseOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PurchaseOrder>>>("/purchase-orders", { params });

export const createPurchaseOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/purchase-orders", data);

export const createPOFromRestock = (data: { supplier_id: number; items: { product_id: number; quantity: number }[]; notes?: string }) =>
  client.post<APIResponse>("/purchase-orders/from-restock", data);

export const receivePurchaseOrder = (poId: number, warehouseId: number = 1) =>
  client.post<APIResponse>(`/purchase-orders/${poId}/receive`, { warehouse_id: warehouseId });

export const getPurchaseOrder = (id: number) =>
  client.get<APIResponse<PurchaseOrder & { items: { id: number; product_id: number; product_name?: string; product_sku?: string; quantity: number; unit_price: number; amount: number }[] }>>(`/purchase-orders/${id}`);

export const updatePurchaseOrder = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/purchase-orders/${id}`, data);

export const deletePurchaseOrder = (id: number) =>
  client.delete<APIResponse>(`/purchase-orders/${id}`);

// Tickets
export const getTickets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Ticket>>>("/tickets", { params });

export const getTicket = (id: number) =>
  client.get<APIResponse<Ticket>>(`/tickets/${id}`);

export const createTicket = (data: Record<string, unknown>) =>
  client.post<APIResponse<Ticket>>("/tickets", data);

export const updateTicket = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Ticket>>(`/tickets/${id}`, data);

export const deleteTicket = (id: number) =>
  client.delete<APIResponse>(`/tickets/${id}`);

// Visits
export const getVisits = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Visit>>>("/visits", { params });

export const createVisit = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/visits", data);

// Samples
export const getSamples = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Sample>>>("/samples", { params });

export const createSample = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/samples", data);

// AI
export const getRFMAnalysis = (customerId: number) =>
  client.post<APIResponse<RFMAnalysis>>(`/ai/customer/${customerId}/rfm`);

export const getChurnRisk = (customerId: number) =>
  client.post<APIResponse<ChurnRisk>>(`/ai/customer/${customerId}/churn-risk`);

export const recognizeCustomer = (text: string) =>
  client.post<APIResponse<CustomerRecognition>>("/ai/customer/recognition", { text });

export const recognizeBusinessCard = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return client.post<APIResponse<CustomerRecognition>>("/ai/customer/card-recognition", formData, { timeout: 120000 });
};

export const getFollowUpSuggestion = (customerId: number) =>
  client.post<APIResponse>(`/ai/customer/${customerId}/followup-suggestion`);

export const recognizeFollowUp = (customerId: number, text: string) =>
  client.post<APIResponse<FollowUpRecognition>>(`/ai/customer/${customerId}/followup-recognition`, { text });

// Customer Logs
export const getCustomerLogs = (customerId: number) =>
  client.get<APIResponse<CustomerLog[]>>(`/customers/${customerId}/logs`);

export const getRecentActivity = (limit = 20) =>
  client.get<APIResponse<CustomerLog[]>>(`/customers/recent-activity?limit=${limit}`);

// Customer Merge
export const mergeCustomers = (source_id: number, target_id: number) =>
  client.post<APIResponse<MergeResult>>("/customers/merge", { source_id, target_id });

// Duplicate Detection
export const detectDuplicates = (threshold = 0.7) =>
  client.get<APIResponse<{ total: number; pairs: DuplicatePair[] }>>("/customers/duplicates", { params: { threshold } });

// Group Relationships
export const linkParent = (customerId: number, parentId: number) =>
  client.post<APIResponse>(`/customers/${customerId}/link-parent`, { parent_id: parentId });

export const unlinkParent = (customerId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/link-parent`);

export const getChildren = (customerId: number) =>
  client.get<APIResponse<Customer[]>>(`/customers/${customerId}/children`);

export const getGroupStats = (customerId: number) =>
  client.get<APIResponse<GroupStats>>(`/customers/${customerId}/group-stats`);

// Alert Center
export const getAlertRules = () =>
  client.get<APIResponse<AlertRule[]>>("/customers/alerts/rules");

export const createAlertRule = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers/alerts/rules", data);

export const updateAlertRule = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/alerts/rules/${id}`, data);

export const deleteAlertRule = (id: number) =>
  client.delete<APIResponse>(`/customers/alerts/rules/${id}`);

export const getAlertEvents = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<AlertEvent>>>("/customers/alerts", { params });

export const markAlertRead = (eventId: number) =>
  client.put<APIResponse>(`/customers/alerts/${eventId}/read`);

export const markAllAlertsRead = () =>
  client.post<APIResponse>("/customers/alerts/read-all");

export const checkAlerts = () =>
  client.post<APIResponse<{ generated: number; rules_checked: number; customers_checked: number }>>("/customers/alerts/check");

// Customer Insight
export const getCustomerInsight = (id: number) =>
  client.get<APIResponse<import("../types").CustomerInsight>>(`/customers/${id}/insight`);

export const getCustomerQuotationHistory = (customerId: number, status?: string) =>
  client.get<APIResponse<import("../types").CustomerQuotationHistory>>(
    `/customers/${customerId}/quotation-history`,
    status ? { params: { status } } : undefined
  );

// Customer Visits
export const getCustomerVisits = (customerId: number) =>
  client.get<APIResponse<Visit[]>>(`/customers/${customerId}/visits`);

export const createCustomerVisit = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/visits`, data);

export const updateCustomerVisit = (customerId: number, visitId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${customerId}/visits/${visitId}`, data);

export const deleteCustomerVisit = (customerId: number, visitId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/visits/${visitId}`);

export const getUpcomingVisits = (days = 14) =>
  client.get<APIResponse<Visit[]>>(`/customers/visits/upcoming?days=${days}`);

// Level Rules
export const getLevelRules = () =>
  client.get<APIResponse<LevelRule[]>>("/customers/level-rules");

export const createLevelRule = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers/level-rules", data);

export const updateLevelRule = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/level-rules/${id}`, data);

export const deleteLevelRule = (id: number) =>
  client.delete<APIResponse>(`/customers/level-rules/${id}`);

export const autoLevel = () =>
  client.post<APIResponse<{ updated: number }>>("/customers/auto-level");

// Notifications
export const getNotifications = (params: Record<string, unknown>) =>
  client.get<APIResponse<{ list: NotificationItem[]; total: number; page: number; page_size: number; unread_count: number }>>("/notifications", { params });

export const getUnreadCount = () =>
  client.get<APIResponse<{ count: number }>>("/notifications/unread-count");

export const markNotificationsRead = (data: { ids?: number[]; all?: boolean }) =>
  client.post<APIResponse>("/notifications/mark-read", data);

// ============================================================
// Supplier Intelligence (AI)
// ============================================================
export const getSupplierScorecard = (supplierId: number) =>
  client.post<APIResponse<SupplierScorecard>>(`/ai/suppliers/${supplierId}/scorecard`);

export const predictSupplierDelay = (supplierId: number) =>
  client.post<APIResponse<SupplierDelayPrediction>>(`/ai/suppliers/${supplierId}/delay-prediction`);

export const getSupplierAlternatives = (supplierId: number) =>
  client.post<APIResponse<SupplierAlternatives>>(`/ai/suppliers/${supplierId}/alternatives`);

export const detectSupplierPriceVariance = (supplierId: number) =>
  client.post<APIResponse<SupplierPriceVariance>>(`/ai/suppliers/${supplierId}/price-variance`);

export const getSupplier360 = (supplierId: number) =>
  client.post<APIResponse<Supplier360>>(`/ai/suppliers/${supplierId}/360`);

export const getSupplierNegotiation = (supplierId: number) =>
  client.post<APIResponse<SupplierNegotiation>>(`/ai/suppliers/${supplierId}/negotiation`);

export const compareSuppliers = (supplierIds: number[]) =>
  client.post<APIResponse<SupplierComparison>>('/ai/suppliers/compare', { supplier_ids: supplierIds });

// ============================================================
// Purchase Order Intelligence (AI)
// ============================================================
export const optimizePurchaseOrder = (orderId: number) =>
  client.post<APIResponse<POOptimization>>(`/ai/purchase-orders/${orderId}/optimize`);

export const suggestPurchaseOrders = () =>
  client.post<APIResponse<POAutoSuggest>>("/ai/purchase-orders/suggest");

export const assessPORisk = (orderId: number) =>
  client.post<APIResponse<PORiskAssessment>>(`/ai/purchase-orders/${orderId}/risk`);

// ============================================================
// Multi-Agent Orchestration (AI)
// ============================================================
export const orchestrateCustomer360 = (customerId: number) =>
  client.post<APIResponse<Customer360>>(`/ai/orchestrate/customer/${customerId}`);

export const orchestrateProduct360 = (productId: number) =>
  client.post<APIResponse<Product360>>(`/ai/orchestrate/product/${productId}`);

export const orchestrateGlobal360 = () =>
  client.post<APIResponse<Global360>>("/ai/orchestrate/global");

// ============================================================
// Watchtower & Demand Forecast (AI)
// ============================================================
export const getWatchtowerScan = (daysBack = 90) =>
  client.get<APIResponse<{
    scanned_at: string;
    total_alerts: number;
    severity: string;
    summary: string;
    top_actions: string[];
    risk_areas: string[];
    anomalies: Record<string, Record<string, unknown>[]>;
  }>>(`/ai/watchtower/scan?days_back=${daysBack}`);

export const getDailyReport = () =>
  client.get<APIResponse<{
    report_date: string;
    generated_at: string;
    metrics: {
      orders_today: number; revenue_today: number; new_customers: number;
      payments_today: number; payments_amount_today: number;
      low_stock_items: number; out_of_stock_items: number;
    };
    ai_summary: string; mood: string; top_action: string;
  }>>("/ai/daily-report");

export const getDemandForecast = (category?: string, topK = 20) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("top_k", String(topK));
  return client.get<APIResponse<{
    product_id: number; sku: string; name: string; category: string;
    monthly_forecast: number; trend: string; trend_score: number;
    seasonal_factor: number; suggested_safety_stock: number;
    current_safety_stock: number; current_quantity: number;
    lead_time_days: number; confidence: string; last_sold: string;
    monthly_history: Record<string, number>;
  }[]>>(`/ai/inventory/demand-forecast?${params.toString()}`);
};

// ============================================================
// NLP Query (AI)
// ============================================================
export const naturalLanguageQuery = (query: string) =>
  client.post<APIResponse<NLPQueryResult>>("/ai/query", { query });

// AI Chat (SSE)
export const aiChat = (query: string, history?: { role: string; content: string }[]) => {
  const token = localStorage.getItem("token");
  return fetch(`/api/v1/ai/chat?query=${encodeURIComponent(query)}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ history: history || [] }),
  });
};

// ============================================================
// Sales — Opportunities
// ============================================================

export const getOpportunities = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Opportunity> & { ai?: Record<number, OpportunityAI> }>>("/opportunities", { params });

export const getOpportunity = (id: number, includeAi = false) =>
  client.get<APIResponse<Opportunity>>(`/opportunities/${id}?include_ai=${includeAi}`);

export const createOpportunity = (data: Record<string, unknown>) =>
  client.post<APIResponse<Opportunity>>("/opportunities", data);

export const updateOpportunity = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Opportunity>>(`/opportunities/${id}`, data);

export const deleteOpportunity = (id: number) =>
  client.delete<APIResponse>(`/opportunities/${id}`);

export const batchDeleteOpportunities = (ids: number[]) =>
  client.post<APIResponse>("/opportunities/batch-delete", { ids });

export const batchUpdateOpportunities = (ids: number[], stage?: string, win_probability?: number) =>
  client.post<APIResponse>("/opportunities/batch-update", { ids, stage, win_probability });

// ============================================================
// Sales — Quotations
// ============================================================

export const getQuotations = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Quotation> & { ai?: Record<number, QuotationAI> }>>("/quotations", { params });

export const getQuotation = (id: number, includeAi = false) =>
  client.get<APIResponse<Quotation>>(`/quotations/${id}?include_ai=${includeAi}`);

export const createQuotation = (data: Record<string, unknown>) =>
  client.post<APIResponse<Quotation>>("/quotations", data);

export const updateQuotation = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Quotation>>(`/quotations/${id}`, data);

export const deleteQuotation = (id: number) =>
  client.delete<APIResponse>(`/quotations/${id}`);

export const sendQuotation = (id: number) =>
  client.put<APIResponse>(`/quotations/${id}/send`);

export const batchDeleteQuotations = (ids: number[]) =>
  client.post<APIResponse>("/quotations/batch-delete", { ids });

export const createQuotationFromInquiry = (inquiryId: number, items?: Record<string, unknown>[]) =>
  client.post<APIResponse<{ id: number; quotation_no: string }>>("/quotations/from-inquiry", {
    inquiry_id: inquiryId,
    items: items || [],
  });

export const convertQuotationToOrder = (id: number) =>
  client.post<APIResponse<{ id: number; document_no: string; msg: string }>>(`/quotations/${id}/convert-to-order`);

export const downloadQuotationPDF = async (id: number, filename?: string) => {
  const resp = await client.get(`/quotations/${id}/pdf`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename || `quotation_${id}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ============================================================
// Sales — Sales Orders
// ============================================================

export const getSalesOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesOrder> & { ai?: Record<number, SalesOrderAI> }>>("/sales-orders", { params });

export const getSalesOrder = (id: number, includeAi = false) =>
  client.get<APIResponse<SalesOrder>>(`/sales-orders/${id}?include_ai=${includeAi}`);

export const createSalesOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse<SalesOrder>>("/sales-orders", data);

export const updateSalesOrder = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<SalesOrder>>(`/sales-orders/${id}`, data);

export const deleteSalesOrder = (id: number) =>
  client.delete<APIResponse>(`/sales-orders/${id}`);

export const batchDeleteSalesOrders = (ids: number[]) =>
  client.post<APIResponse>("/sales-orders/batch-delete", { ids });

export const convertSalesOrderToDelivery = (id: number) =>
  client.post<APIResponse<{ id: number; document_no: string; msg: string }>>(`/sales-orders/${id}/convert-to-delivery`);

// ============================================================
// Sales — Delivery Notes
// ============================================================

export const getDeliveryNotes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<DeliveryNote> & { ai?: Record<number, DeliveryNoteAI> }>>("/delivery-notes", { params });

export const getDeliveryNote = (id: number, includeAi = false) =>
  client.get<APIResponse<DeliveryNote>>(`/delivery-notes/${id}?include_ai=${includeAi}`);

export const createDeliveryNote = (data: Record<string, unknown>) =>
  client.post<APIResponse<DeliveryNote>>("/delivery-notes", data);

export const updateDeliveryNote = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<DeliveryNote>>(`/delivery-notes/${id}`, data);

export const deleteDeliveryNote = (id: number) =>
  client.delete<APIResponse>(`/delivery-notes/${id}`);

export const batchDeleteDeliveryNotes = (ids: number[]) =>
  client.post<APIResponse>("/delivery-notes/batch-delete", { ids });

// ============================================================
// Finance — Invoices
// ============================================================

export const getInvoices = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Invoice>>>("/invoices", { params });

export const getInvoice = (id: number) =>
  client.get<APIResponse<Invoice>>(`/invoices/${id}`);

export const createInvoice = (data: Record<string, unknown>) =>
  client.post<APIResponse<Invoice>>("/invoices", data);

export const updateInvoice = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Invoice>>(`/invoices/${id}`, data);

export const deleteInvoice = (id: number) =>
  client.delete<APIResponse>(`/invoices/${id}`);

// ============================================================
// Finance — Payments
// ============================================================

export const getPayments = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PaymentRecord>>>("/payments", { params });

export const getPaymentStats = () =>
  client.get<APIResponse<{ total_received: number; total_pending: number; total_overdue: number; by_method: Record<string, number>; monthly: Record<string, unknown>[] }>>("/payments/stats");

export const getPayment = (id: number) =>
  client.get<APIResponse<PaymentRecord>>(`/payments/${id}`);

export const createPayment = (data: Record<string, unknown>) =>
  client.post<APIResponse<PaymentRecord>>("/payments", data);

export const updatePayment = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<PaymentRecord>>(`/payments/${id}`, data);

export const deletePayment = (id: number) =>
  client.delete<APIResponse>(`/payments/${id}`);

// ============================================================
// Finance — Contracts
// ============================================================

export const getContracts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Contract>>>("/contracts", { params });

export const getContract = (id: number) =>
  client.get<APIResponse<Contract>>(`/contracts/${id}`);

export const createContract = (data: Record<string, unknown>) =>
  client.post<APIResponse<Contract>>("/contracts", data);

export const updateContract = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Contract>>(`/contracts/${id}`, data);

export const deleteContract = (id: number) =>
  client.delete<APIResponse>(`/contracts/${id}`);

export const importContractPDF = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<APIResponse<{
    id: number;
    parsed: { title?: string; amount?: number; signed_date?: string; buyer_name?: string };
    raw_text_preview: string;
  }>>("/contracts/import-pdf", form, { headers: { "Content-Type": "multipart/form-data" } });
};

// ============================================================
// Finance — Sales Targets
// ============================================================

export const getTargets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesTarget>>>("/sales/targets", { params });

export const getTargetStats = () =>
  client.get<APIResponse<{ total_target: number; total_actual: number; achievement_pct: number; count: number; completed: number }>>("/targets/stats");

export const getTarget = (id: number) =>
  client.get<APIResponse<SalesTarget>>(`/targets/${id}`);

export const createTarget = (data: Record<string, unknown>) =>
  client.post<APIResponse<SalesTarget>>("/sales/targets", data);

export const updateTarget = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<SalesTarget>>(`/targets/${id}`, data);

export const deleteTarget = (id: number) =>
  client.delete<APIResponse>(`/targets/${id}`);

// ============================================================
// Sales Dashboard
// ============================================================

export const getSalesDashboardOverview = () =>
  client.get<APIResponse<import("../types").SalesDashboardOverview>>("/sales/dashboard/overview");

export const getSalesDashboardTrends = (months = 12) =>
  client.get<APIResponse<import("../types").SalesDashboardTrends>>(`/sales/dashboard/trends?months=${months}`);

export const getSalesDashboardAlerts = () =>
  client.get<APIResponse<import("../types").SalesDashboardAlerts>>("/sales/dashboard/alerts");

// Customer intelligence
export const getCustomer360 = (customerId: number) =>
  client.post<APIResponse<import("../types").Customer360>>(`/ai/orchestrate/customer/${customerId}`);

export const getCustomerSegments = (nClusters = 5) =>
  client.get<APIResponse<{ clusters: import("../types").SegmentCluster[]; total: number }>>(`/ai/customer/segments?n_clusters=${nClusters}`);

export const getSimilarCustomers = (customerId: number, topK = 10) =>
  client.get<APIResponse<import("../types").SimilarCustomer[]>>(`/ai/customer/${customerId}/similar?top_k=${topK}`);

export const searchSimilarCustomers = (q: string, topK = 10) =>
  client.get<APIResponse<import("../types").SimilarCustomer[]>>(`/ai/customer/similar/search?q=${encodeURIComponent(q)}&top_k=${topK}`);

// ============================================================
// Inquiry Auto-Reply
// ============================================================
export interface InquiryMatchedProduct {
  product_id: number;
  sku: string;
  name: string;
  brand: string;
  stock_status: string;
  stock_quantity?: number;
  unit_price?: number;
}

export interface InquiryAlternative {
  original_sku: string;
  alternative_sku: string;
  alternative_name: string;
  brand: string;
  reason: string;
}

export interface InquiryAutoReplyResponse {
  reply_text: string;
  confidence: number;
  matched_products: InquiryMatchedProduct[];
  alternatives: InquiryAlternative[];
}

export interface InquiryRecord {
  id: number;
  inquiry_text: string;
  reply_text: string | null;
  confidence: number | null;
  customer_id: number | null;
  customer_name: string | null;
  contact_name: string | null;
  contact_info: string | null;
  channel: string;
  status: string;
  created_at: string;
}

export const inquiryAutoReply = (data: {
  inquiry_text: string;
  customer_id?: number;
  contact_name?: string;
  contact_info?: string;
  channel?: string;
}) =>
  client.post<APIResponse<InquiryAutoReplyResponse>>("/inquiry/auto-reply", data);

export const getInquiries = (params: { limit?: number; sort_by?: string; order?: string }) =>
  client.get<APIResponse<{ list: InquiryRecord[]; total: number }>>("/inquiries", { params });
