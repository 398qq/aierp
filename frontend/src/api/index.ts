import client from "./client";
import type {
  AlertEvent, AlertRule, APIResponse, Attachment, AttainmentPrediction, Brand, BrandComparison, BrandCustomerPenetration, BrandHealth, BrandImport, BrandLifecycle, BrandPortfolio, BrandPriceTrends, BrandProductPerformance, BrandProfile, BrandRecommendation, BrandRisk, BrandSupplierMatrix, CashFlowForecast, ChurnRisk, Contract, ContractExpiry, ContractExtraction, ContractRebate, ContractRisk, CreditRiskAssessment, Customer, Customer360, CustomerInsight, CustomerLog, CustomerProductMatch, CustomerStats,
  DashboardOverview, DashboardRealtime, DashboardStats,
  DeliveryNote, DeliveryNoteItem, DunningStrategy, DuplicatePair, FollowUp, Global360, GroupStats, Invoice, LevelRule, LifecycleAnalysis, MergeResult, NLPQueryResult,
  NotificationItem, NormalizedSpec, OverdueFollowUp,
  InventoryItem, LoginData, Opportunity, PageData, Payment, PaymentDelayPrediction, PaymentRecord, POAutoSuggest, POOptimization, PORiskAssessment, PriceBenchmark, PriceRecommendation, ProcurementPlan, Product, Product360,
  ProductAssociation, ProductCustomerMatch, ProductProfile, PurchaseOrder, Quotation, QuotationHistory, QuotationItem, QuoteAssistResult, RFMAnalysis, SalesOrder, SalesOrderItem, SalesTarget,
  PaymentSummary, Sample, SimilarBrand, Supplier, SupplierAlternatives, SupplierDelayPrediction, SupplierPriceVariance, SupplierProductLink, SupplierScorecard, Tag, TargetEarlyWarning, TargetRecommendation, TargetSummary, Ticket, TicketClassification, TicketCluster, TicketResolutionPrediction, TicketResponse, TimelineEvent, Visit, VisitEffectiveness, VisitReport, VisitSentiment, Warehouse, WatchtowerResult,
} from "../types";

// Auth
export const login = (username: string, password: string) =>
  client.post<APIResponse<LoginData>>("/auth/login", { username, password });

export const getMe = () => client.get<APIResponse>("/auth/me");

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

export const getOverdueFollowUps = () =>
  client.get<APIResponse<{ total: number; items: OverdueFollowUp[] }>>("/customers/overdue-followups");

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

// Attachments
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

// Products
export const getProducts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Product>>>("/products", { params });

export const getProduct = (id: number) =>
  client.get<APIResponse<Product>>(`/products/${id}`);

export const createProduct = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/products", data);

export const updateProduct = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/products/${id}`, data);

export const deleteProduct = (id: number) =>
  client.delete<APIResponse>(`/products/${id}`);

// Brands
export const getBrands = (params?: Record<string, unknown>) =>
  client.get<APIResponse<Brand[]>>("/brands", { params });

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

// Quote Assistant
export const getQuoteAssist = (customerId: number, items: { product_id: number; quantity: number }[]) =>
  client.post<APIResponse<QuoteAssistResult>>("/ai/quotations/assist", { customer_id: customerId, items });

// Watchtower
export const scanWatchtower = (daysBack = 90) =>
  client.get<APIResponse<WatchtowerResult>>(`/ai/watchtower/scan?days_back=${daysBack}`);

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

// Warehouses & Inventory
export const getWarehouses = () =>
  client.get<APIResponse<Warehouse[]>>("/warehouses");

export const getInventory = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<InventoryItem>>>("/inventory", { params });

// Inventory intelligence
export const getInventoryOverview = () =>
  client.get<APIResponse>("/inventory/overview");

export const adjustInventory = (product_id: number, warehouse_id: number, adjustment: number, reason: string) =>
  client.post<APIResponse>(`/inventory/adjust?product_id=${product_id}&warehouse_id=${warehouse_id}&adjustment=${adjustment}&reason=${encodeURIComponent(reason)}`);

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

export const productSubstitutes = (id: number) =>
  client.get<APIResponse>(`/ai/products/${id}/substitutes`);

// Opportunities
export const getOpportunities = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Opportunity>>>("/opportunities", { params });

export const getOpportunity = (id: number) =>
  client.get<APIResponse<Opportunity>>(`/opportunities/${id}`);

export const createOpportunity = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/opportunities", data);

export const updateOpportunity = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/opportunities/${id}`, data);

export const deleteOpportunity = (id: number) =>
  client.delete<APIResponse>(`/opportunities/${id}`);

// Quotations
export const getQuotations = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Quotation>>>("/quotations", { params });

export const getQuotation = (id: number) =>
  client.get<APIResponse<Quotation>>(`/quotations/${id}`);

export const createQuotation = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/quotations", data);

export const updateQuotation = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/quotations/${id}`, data);

export const deleteQuotation = (id: number) =>
  client.delete<APIResponse>(`/quotations/${id}`);

// Quotation Items
export const getQuotationItems = (quotationId: number) =>
  client.get<APIResponse<QuotationItem[]>>(`/quotations/${quotationId}/items`);

export const createQuotationItem = (quotationId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/quotations/${quotationId}/items`, data);

export const updateQuotationItem = (quotationId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/quotations/${quotationId}/items/${itemId}`, data);

export const deleteQuotationItem = (quotationId: number, itemId: number) =>
  client.delete<APIResponse>(`/quotations/${quotationId}/items/${itemId}`);

// Sales Orders
export const getSalesOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesOrder>>>("/sales-orders", { params });

export const getSalesOrder = (id: number) =>
  client.get<APIResponse<SalesOrder>>(`/sales-orders/${id}`);

export const createSalesOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales-orders", data);

export const updateSalesOrder = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales-orders/${id}`, data);

export const deleteSalesOrder = (id: number) =>
  client.delete<APIResponse>(`/sales-orders/${id}`);

// Sales Order Items
export const getSalesOrderItems = (orderId: number) =>
  client.get<APIResponse<SalesOrderItem[]>>(`/sales-orders/${orderId}/items`);

export const createSalesOrderItem = (orderId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/sales-orders/${orderId}/items`, data);

export const updateSalesOrderItem = (orderId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales-orders/${orderId}/items/${itemId}`, data);

export const deleteSalesOrderItem = (orderId: number, itemId: number) =>
  client.delete<APIResponse>(`/sales-orders/${orderId}/items/${itemId}`);

// Delivery Notes
export const getDeliveryNotes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<DeliveryNote>>>("/delivery-notes", { params });

export const getDeliveryNote = (id: number) =>
  client.get<APIResponse<DeliveryNote>>(`/delivery-notes/${id}`);

export const createDeliveryNote = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/delivery-notes", data);

export const updateDeliveryNote = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/delivery-notes/${id}`, data);

export const deleteDeliveryNote = (id: number) =>
  client.delete<APIResponse>(`/delivery-notes/${id}`);

// Delivery Note Items
export const getDeliveryNoteItems = (noteId: number) =>
  client.get<APIResponse<DeliveryNoteItem[]>>(`/delivery-notes/${noteId}/items`);

export const createDeliveryNoteItem = (noteId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/delivery-notes/${noteId}/items`, data);

export const updateDeliveryNoteItem = (noteId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/delivery-notes/${noteId}/items/${itemId}`, data);

export const deleteDeliveryNoteItem = (noteId: number, itemId: number) =>
  client.delete<APIResponse>(`/delivery-notes/${noteId}/items/${itemId}`);

// Purchase Orders
export const getPurchaseOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PurchaseOrder>>>("/purchase-orders", { params });

export const createPurchaseOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/purchase-orders", data);

// Payments
export const getPayments = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Payment>>>("/payments", { params });

export const createPayment = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/payments", data);

// Tickets
export const getTickets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Ticket>>>("/tickets", { params });

export const createTicket = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/tickets", data);

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

export const getFollowUpSuggestion = (customerId: number) =>
  client.post<APIResponse>(`/ai/customer/${customerId}/followup-suggestion`);

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

// Sales Funnel
import type { FunnelStage, SalesSummary, TrendPoint, StageDistribution, SalesRecommendation, WinPrediction } from "../types";

export const getSalesFunnel = (params?: Record<string, unknown>) =>
  client.get<APIResponse<FunnelStage[]>>("/opportunities/funnel", { params });

// Sales Stats
export const getSalesSummary = () =>
  client.get<APIResponse<SalesSummary>>("/sales/stats/summary");

export const getSalesTrend = (params: Record<string, unknown>) =>
  client.get<APIResponse<TrendPoint[]>>("/sales/stats/trend", { params });

export const getStageDistribution = () =>
  client.get<APIResponse<StageDistribution[]>>("/sales/stats/stage-distribution");

// Flow Conversion
export const convertQuotationToOrder = (quotationId: number) =>
  client.post<APIResponse<{ id: number; document_no: string; msg: string }>>(`/quotations/${quotationId}/convert-to-order`);

export const convertOrderToDelivery = (orderId: number) =>
  client.post<APIResponse<{ id: number; document_no: string; msg: string }>>(`/sales-orders/${orderId}/convert-to-delivery`);

// Batch Operations
export const batchDeleteOpportunities = (ids: number[]) =>
  client.post<APIResponse>("/opportunities/batch-delete", { ids });

export const batchUpdateOpportunities = (ids: number[], stage?: string, probability?: number) =>
  client.post<APIResponse>("/opportunities/batch-update", { ids, stage, probability });

export const batchDeleteQuotations = (ids: number[]) =>
  client.post<APIResponse>("/quotations/batch-delete", { ids });

export const batchDeleteSalesOrders = (ids: number[]) =>
  client.post<APIResponse>("/sales-orders/batch-delete", { ids });

export const batchDeleteDeliveryNotes = (ids: number[]) =>
  client.post<APIResponse>("/delivery-notes/batch-delete", { ids });

// Excel Import/Export
export const exportQuotations = (params?: Record<string, unknown>) =>
  client.get("/quotations/export", { params, responseType: "blob" });

export const importQuotations = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/quotations/import", form, { headers: { "Content-Type": "multipart/form-data" } });
};

export const exportSalesOrders = (params?: Record<string, unknown>) =>
  client.get("/sales-orders/export", { params, responseType: "blob" });

export const importSalesOrders = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/sales-orders/import", form, { headers: { "Content-Type": "multipart/form-data" } });
};

export const exportDeliveryNotes = (params?: Record<string, unknown>) =>
  client.get("/delivery-notes/export", { params, responseType: "blob" });

export const importDeliveryNotes = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/delivery-notes/import", form, { headers: { "Content-Type": "multipart/form-data" } });
};

// AI Sales
export const getSalesRecommendation = (customerId: number) =>
  client.post<APIResponse<SalesRecommendation>>(`/ai/sales/recommend?customer_id=${customerId}`);

export const getWinPrediction = (opportunityId: number) =>
  client.post<APIResponse<WinPrediction>>(`/ai/sales/predict?opportunity_id=${opportunityId}`);

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

// Quotation History
export const getQuotationHistory = (customerId: number) =>
  client.get<APIResponse<QuotationHistory>>(`/customers/${customerId}/quotation-history`);

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

// Payment Records
export const getPaymentRecords = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PaymentRecord>>>("/sales/payments", { params });

export const getPaymentRecord = (id: number) =>
  client.get<APIResponse<PaymentRecord>>(`/sales/payments/${id}`);

export const createPaymentRecord = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales/payments", data);

export const updatePaymentRecord = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales/payments/${id}`, data);

export const deletePaymentRecord = (id: number) =>
  client.delete<APIResponse>(`/sales/payments/${id}`);

export const getPaymentSummary = () =>
  client.get<APIResponse<PaymentSummary>>("/sales/payments/summary");

// Invoices
export const getInvoices = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Invoice>>>("/sales/invoices", { params });

export const getInvoice = (id: number) =>
  client.get<APIResponse<Invoice>>(`/sales/invoices/${id}`);

export const createInvoice = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales/invoices", data);

export const updateInvoice = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales/invoices/${id}`, data);

export const deleteInvoice = (id: number) =>
  client.delete<APIResponse>(`/sales/invoices/${id}`);

export const issueInvoice = (id: number) =>
  client.post<APIResponse>(`/sales/invoices/${id}/issue`);

export const voidInvoice = (id: number) =>
  client.post<APIResponse>(`/sales/invoices/${id}/void`);

// Sales Targets
export const getSalesTargets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesTarget>>>("/sales/targets", { params });

export const getSalesTarget = (id: number) =>
  client.get<APIResponse<SalesTarget>>(`/sales/targets/${id}`);

export const createSalesTarget = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales/targets", data);

export const updateSalesTarget = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales/targets/${id}`, data);

export const deleteSalesTarget = (id: number) =>
  client.delete<APIResponse>(`/sales/targets/${id}`);

export const getTargetSummary = () =>
  client.get<APIResponse<TargetSummary>>("/sales/targets/summary");

// Contracts
export const getContracts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Contract>>>("/sales/contracts", { params });

export const getContract = (id: number) =>
  client.get<APIResponse<Contract>>(`/sales/contracts/${id}`);

export const createContract = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales/contracts", data);

export const updateContract = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales/contracts/${id}`, data);

export const deleteContract = (id: number) =>
  client.delete<APIResponse>(`/sales/contracts/${id}`);

// Notifications
export const getNotifications = (params: Record<string, unknown>) =>
  client.get<APIResponse<{ list: NotificationItem[]; total: number; page: number; page_size: number; unread_count: number }>>("/notifications", { params });

export const getUnreadCount = () =>
  client.get<APIResponse<{ count: number }>>("/notifications/unread-count");

export const markNotificationsRead = (data: { ids?: number[]; all?: boolean }) =>
  client.post<APIResponse>("/notifications/mark-read", data);

// Dashboard
export const getDashboardOverview = () =>
  client.get<APIResponse<DashboardOverview>>("/sales/dashboard/overview");

export const getDashboardRealtime = () =>
  client.get<APIResponse<DashboardRealtime>>("/sales/dashboard/realtime");

// Customer Insight
export const getCustomerInsight = (id: number) =>
  client.get<APIResponse<CustomerInsight>>(`/customers/${id}/insight`);

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
// Payment & AR Intelligence (AI)
// ============================================================
export const predictPaymentDelays = () =>
  client.post<APIResponse<PaymentDelayPrediction>>("/ai/finance/payment-prediction");

export const forecastCashFlow = () =>
  client.post<APIResponse<CashFlowForecast>>("/ai/finance/cash-flow");

export const generateDunningStrategy = (invoiceId: number) =>
  client.post<APIResponse<DunningStrategy>>(`/ai/finance/dunning/${invoiceId}`);

export const assessCreditRisk = (customerId: number) =>
  client.post<APIResponse<CreditRiskAssessment>>(`/ai/finance/credit-risk/${customerId}`);

// ============================================================
// Sales Target Intelligence (AI)
// ============================================================
export const recommendTargets = (userId: number) =>
  client.post<APIResponse<TargetRecommendation>>(`/ai/targets/recommend/${userId}`);

export const predictAttainment = (targetId: number) =>
  client.post<APIResponse<AttainmentPrediction>>(`/ai/targets/${targetId}/attainment`);

export const scanTargetEarlyWarning = () =>
  client.post<APIResponse<TargetEarlyWarning>>("/ai/targets/early-warning");

// ============================================================
// Visit Intelligence (AI)
// ============================================================
export const generateVisitReport = (visitId: number) =>
  client.post<APIResponse<VisitReport>>(`/ai/visits/${visitId}/report`);

export const analyzeVisitSentiment = (visitId: number) =>
  client.post<APIResponse<VisitSentiment>>(`/ai/visits/${visitId}/sentiment`);

export const evaluateVisitEffectiveness = () =>
  client.post<APIResponse<VisitEffectiveness>>("/ai/visits/effectiveness");

// ============================================================
// Ticket Intelligence (AI)
// ============================================================
export const classifyTicket = (ticketId: number) =>
  client.post<APIResponse<TicketClassification>>(`/ai/tickets/${ticketId}/classify`);

export const suggestTicketResponse = (ticketId: number) =>
  client.post<APIResponse<TicketResponse>>(`/ai/tickets/${ticketId}/suggest-response`);

export const predictTicketResolution = (ticketId: number) =>
  client.post<APIResponse<TicketResolutionPrediction>>(`/ai/tickets/${ticketId}/predict-resolution`);

export const clusterTickets = () =>
  client.post<APIResponse<TicketCluster>>("/ai/tickets/cluster");

// ============================================================
// Contract Intelligence (AI)
// ============================================================
export const extractContractTerms = (contractId: number) =>
  client.post<APIResponse<ContractExtraction>>(`/ai/contracts/${contractId}/extract`);

export const assessContractRisk = (contractId: number) =>
  client.post<APIResponse<ContractRisk>>(`/ai/contracts/${contractId}/risk`);

export const scanContractExpiry = () =>
  client.post<APIResponse<ContractExpiry>>("/ai/contracts/expiry-alerts");

export const trackContractRebate = (contractId: number) =>
  client.post<APIResponse<ContractRebate>>(`/ai/contracts/${contractId}/rebate-tracking`);

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
// NLP Query (AI)
// ============================================================
export const naturalLanguageQuery = (query: string) =>
  client.post<APIResponse<NLPQueryResult>>("/ai/query", { query });
