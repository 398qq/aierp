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


