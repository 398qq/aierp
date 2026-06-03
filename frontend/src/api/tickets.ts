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


