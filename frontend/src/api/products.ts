import client from "./client";
import type {
  AlertEvent, AlertRule, APIResponse, Attachment, Brand, BrandComparison, BrandCustomerPenetration, BrandHealth, BrandImport, BrandLifecycle, BrandPortfolio, BrandPriceTrends, BrandProductPerformance, BrandProfile, BrandRecommendation, BrandRisk, BrandSupplierMatrix,
  ChurnRisk, Contract, Customer, Customer360, CustomerAIRecommendationSummary, CustomerAIStats, CustomerAIWorkQueuePage, CustomerLog, CustomerProductMatch, CustomerRecognition, CustomerStats,
  DashboardStats, DashboardWidget, DeliveryNote, DeliveryNoteAI, Document, DuplicatePair,
  FollowUp, FollowUpRecognition, FollowUpReminder, GlobalFollowUp,
  Global360, GroupStats,
  Invoice, KpiData, LevelRule, LifecycleAnalysis, LoginData,
  MergeResult,
  NLPQueryResult, NormalizedSpec,
  InventoryItem,
  NotificationItem,
  Opportunity, OpportunityAI, OverdueFollowUp,
  PageData, PaymentRecord, POAutoSuggest, POOptimization, PORiskAssessment, PriceBenchmark, PriceRecommendation, ProcurementPlan, Product, Product360, ProductAssociation, ProductCustomerMatch, ProductProfile, PurchaseOrder,
  Quotation, QuotationAI, QuotationStats, RFMAnalysis,
  SalesOrder, SalesOrderAI, SalesTarget, Sample, SimilarBrand, Supplier, Supplier360, SupplierAlternatives, SupplierComparison, SupplierDelayPrediction, SupplierNegotiation, SupplierPriceVariance, SupplierProductLink, SupplierScorecard,
  Tag, Ticket, TicketClassification, TicketCluster, TicketResolutionPrediction, TicketResponse, TimelineEvent,
  Visit, VisitEffectiveness, VisitReport, VisitSentiment,
  Warehouse,
} from "../types";

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


// Warehouses & Inventory
// Note: backend returns paginated {list, total, page, page_size};
// consumers should read .data.list, not .data directly.
export const getWarehouses = (params?: { page?: number; page_size?: number }) =>
  client.get<APIResponse<PageData<Warehouse>>>("/warehouses", { params });

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


// Product inventory CRUD
export const getProductInventories = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<InventoryItem>>>("/inventories/", { params });

export const createProductInventory = (data: { product_id: number; warehouse_id: number; quantity: number; safety_stock?: number; unit_price?: number }) =>
  client.post<APIResponse>("/inventories/", data);

export const updateProductInventory = (id: number, data: { quantity?: number; safety_stock?: number; unit_price?: number }) =>
  client.put<APIResponse>(`/inventories/${id}`, data);

export const deleteProductInventory = (id: number) =>
  client.delete<APIResponse>(`/inventories/${id}`);


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


