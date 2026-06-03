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


// Supplier Intelligence (AI)
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

