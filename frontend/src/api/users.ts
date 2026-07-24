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

export const getActiveUsers = () =>
  client.get<APIResponse<Array<{ username: string; role: string }>>>("/users/active");


