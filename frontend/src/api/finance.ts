import client from "./client";
import type {
  AlertEvent,
  AlertRule,
  APIResponse,
  Attachment,
  Brand,
  BrandComparison,
  BrandCustomerPenetration,
  BrandHealth,
  BrandImport,
  BrandLifecycle,
  BrandPortfolio,
  BrandPriceTrends,
  BrandProductPerformance,
  BrandProfile,
  BrandRecommendation,
  BrandRisk,
  BrandSupplierMatrix,
  ChurnRisk,
  Commission,
  Contract,
  Customer,
  Customer360,
  CustomerAIRecommendationSummary,
  CustomerAIStats,
  CustomerAIWorkQueuePage,
  CustomerLog,
  CustomerProductMatch,
  CustomerRecognition,
  CustomerStats,
  DashboardStats,
  DashboardWidget,
  DeliveryNote,
  DeliveryNoteAI,
  Document,
  DuplicatePair,
  FollowUp,
  FollowUpRecognition,
  FollowUpReminder,
  GlobalFollowUp,
  Global360,
  GroupStats,
  Invoice,
  KpiData,
  LevelRule,
  LifecycleAnalysis,
  LoginData,
  MergeResult,
  NLPQueryResult,
  NormalizedSpec,
  InventoryItem,
  NotificationItem,
  Opportunity,
  OpportunityAI,
  OverdueFollowUp,
  PageData,
  PaymentRecord,
  POAutoSuggest,
  POOptimization,
  PORiskAssessment,
  PriceBenchmark,
  PriceRecommendation,
  ProcurementPlan,
  Product,
  Product360,
  ProductAssociation,
  ProductCustomerMatch,
  ProductProfile,
  PurchaseOrder,
  Quotation,
  QuotationAI,
  QuotationStats,
  RFMAnalysis,
  SalesOrder,
  SalesOrderAI,
  SalesTarget,
  Sample,
  SimilarBrand,
  Supplier,
  Supplier360,
  SupplierAlternatives,
  SupplierComparison,
  SupplierDelayPrediction,
  SupplierNegotiation,
  SupplierPriceVariance,
  SupplierProductLink,
  SupplierScorecard,
  Tag,
  Ticket,
  TicketClassification,
  TicketCluster,
  TicketResolutionPrediction,
  TicketResponse,
  TimelineEvent,
  Visit,
  VisitEffectiveness,
  VisitReport,
  VisitSentiment,
  Warehouse,
} from "../types";

// Finance — Invoices

export const getInvoices = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Invoice>>>("/invoices", { params });

export const getInvoice = (id: number) => client.get<APIResponse<Invoice>>(`/invoices/${id}`);

export const createInvoice = (data: Record<string, unknown>) =>
  client.post<APIResponse<Invoice>>("/invoices", data);

export const updateInvoice = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Invoice>>(`/invoices/${id}`, data);

export const deleteInvoice = (id: number) => client.delete<APIResponse>(`/invoices/${id}`);

// ============================================================

// Finance — Payments

export const getPayments = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PaymentRecord>>>("/payments", { params });

export const getPaymentStats = () =>
  client.get<
    APIResponse<{
      total_received: number;
      total_pending: number;
      total_overdue: number;
      by_method: Record<string, number>;
      monthly: Record<string, unknown>[];
    }>
  >("/payments/stats");

export const markDeliveryNotePaid = (
  id: number,
  data: { amount?: number; payment_method?: string; payment_date?: string; notes?: string } = {},
) =>
  client.post<
    APIResponse<{
      created: boolean;
      payment: { id: number; amount: number; status: string; method: string; date: string };
      delivery_note: { id: number; status: string; received_date: string };
    }>
  >(`/delivery-notes/${id}/mark-paid`, data);

export const getPayment = (id: number) => client.get<APIResponse<PaymentRecord>>(`/payments/${id}`);

export const createPayment = (data: Record<string, unknown>) =>
  client.post<APIResponse<PaymentRecord>>("/payments", data);

export const updatePayment = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<PaymentRecord>>(`/payments/${id}`, data);

export const deletePayment = (id: number) => client.delete<APIResponse>(`/payments/${id}`);

// ============================================================

// Finance — Contracts

export const getContracts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Contract>>>("/contracts", { params });

export const getContract = (id: number) => client.get<APIResponse<Contract>>(`/contracts/${id}`);

export const createContract = (data: Record<string, unknown>) =>
  client.post<APIResponse<Contract>>("/contracts", data);

export const updateContract = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Contract>>(`/contracts/${id}`, data);

export const deleteContract = (id: number) => client.delete<APIResponse>(`/contracts/${id}`);

export const importContractPDF = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<
    APIResponse<{
      id: number;
      parsed: { title?: string; amount?: number; signed_date?: string; buyer_name?: string };
      raw_text_preview: string;
    }>
  >("/contracts/import-pdf", form, { headers: { "Content-Type": "multipart/form-data" } });
};

// ============================================================

// ============================================================
// Commission
// ============================================================

export const getCommissions = (params: Record<string, unknown> = {}) =>
  client.get<APIResponse<PageData<Commission>>>("/finance/commissions", { params });

export const getCommission = (id: number) =>
  client.get<APIResponse<Commission>>(`/finance/commissions/${id}`);

export const createCommission = (data: Partial<Commission>) =>
  client.post<APIResponse<Commission>>("/finance/commissions", data);

export const updateCommission = (id: number, data: Partial<Commission>) =>
  client.patch<APIResponse<Commission>>(`/finance/commissions/${id}`, data);

export const deleteCommission = (id: number) =>
  client.delete<APIResponse>(`/finance/commissions/${id}`);

export const transitionCommission = (id: number, to: Commission["status"], reason: string = "") =>
  client.post<APIResponse<Commission>>(`/finance/commissions/${id}/transition`, {
    to,
    reason,
  });

/** Batch transition multiple commissions in one call (Stage 12 Day 2). */
export const batchTransitionCommissions = (data: {
  ids: number[];
  to: Commission["status"];
  notes?: string;
  paid_amount?: number;
}) =>
  client.post<
    APIResponse<{
      ok: boolean;
      succeeded: Array<{ id: number; to: string; from?: string }>;
      failed: Array<{ id: number; error: string }>;
      summary: { total: number; succeeded: number; failed: number };
    }>
  >(`/finance/commissions/batch-transition`, data);

// ── Commission Schemes ─────────────────────────────────────────────────

export interface SchemeTier {
  id: number;
  scheme_id: number;
  tier_no: number;
  metric_type: string;
  low_amount: number;
  high_amount: number | null;
  rate: number;
  cap_amount: number;
  floor_amount: number;
  product_category: string | null;
  customer_level: string | null;
}

export interface SchemeAssignment {
  id: number;
  scheme_id: number;
  assignee_type: string;
  assignee_id: number;
}

export interface CommissionScheme {
  id: number;
  name: string;
  description: string | null;
  version_no: number;
  status: string;
  effective_from: string;
  effective_to: string | null;
  is_default: boolean;
  created_by: number | null;
  created_at: string | null;
  updated_at: string | null;
  tiers: SchemeTier[];
  assignments: SchemeAssignment[];
}

export type SchemeStatus = "draft" | "pending" | "active" | "expired" | "inactive";

export const getCommissionSchemes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<CommissionScheme>>>("/commission-schemes", { params });

export const getCommissionScheme = (id: number) =>
  client.get<APIResponse<CommissionScheme>>(`/commission-schemes/${id}`);

export const createCommissionScheme = (data: Record<string, unknown>) =>
  client.post<APIResponse<CommissionScheme>>("/commission-schemes", data);

export const updateCommissionScheme = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<CommissionScheme>>(`/commission-schemes/${id}`, data);

export const deleteCommissionScheme = (id: number) =>
  client.delete<APIResponse>(`/commission-schemes/${id}`);

export const activateCommissionScheme = (id: number) =>
  client.post<APIResponse<CommissionScheme>>(`/commission-schemes/${id}/activate`);

export const deactivateCommissionScheme = (id: number) =>
  client.post<APIResponse<CommissionScheme>>(`/commission-schemes/${id}/deactivate`);

export const getMyScheme = () =>
  client.get<APIResponse<CommissionScheme | null>>("/commission-schemes/my-scheme");
