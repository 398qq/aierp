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
  client.get<APIResponse<PurchaseOrder & { items: import("../types/operations").PurchaseOrderItem[] }>>(`/purchase-orders/${id}`);

export const updatePurchaseOrder = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/purchase-orders/${id}`, data);

export const deletePurchaseOrder = (id: number) =>
  client.delete<APIResponse>(`/purchase-orders/${id}`);

export const batchDeletePurchaseOrders = (ids: number[]) =>
  client.post<APIResponse>("/purchase-orders/batch-delete", { ids });

export const transitionPurchaseOrder = (id: number, targetStatus: string) =>
  client.post<APIResponse>(`/purchase-orders/${id}/transition`, { target_status: targetStatus });

export const confirmLargePurchaseOrder = (id: number) =>
  client.post<APIResponse>(`/purchase-orders/${id}/confirm-large-order`);

export const confirmPurchaseOrderSupplier = (id: number, data: { method: string; confirmed_delivery_date: string; allow_partial_delivery: boolean }) =>
  client.post<APIResponse>(`/purchase-orders/${id}/supplier-confirmation`, data);


// Purchase Order Intelligence (AI)
export const optimizePurchaseOrder = (orderId: number) =>
  client.post<APIResponse<POOptimization>>(`/ai/purchase-orders/${orderId}/optimize`);

export const suggestPurchaseOrders = () =>
  client.post<APIResponse<POAutoSuggest>>("/ai/purchase-orders/suggest");

export const assessPORisk = (orderId: number) =>
  client.post<APIResponse<PORiskAssessment>>(`/ai/purchase-orders/${orderId}/risk`);

// ============================================================
