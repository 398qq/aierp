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
  return client.post<APIResponse<CustomerRecognition>>("/ai/customer/card-recognition", formData, {
    timeout: 120000,
  });
};

export const getFollowUpSuggestion = (customerId: number) =>
  client.post<APIResponse>(`/ai/customer/${customerId}/followup-suggestion`);

export const recognizeFollowUp = (customerId: number, text: string) =>
  client.post<APIResponse<FollowUpRecognition>>(`/ai/customer/${customerId}/followup-recognition`, {
    text,
  });

// Alert Center
export const getAlertRules = () => client.get<APIResponse<AlertRule[]>>("/customers/alerts/rules");

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

export const markAllAlertsRead = () => client.post<APIResponse>("/customers/alerts/read-all");

export const checkAlerts = () =>
  client.post<APIResponse<{ generated: number; rules_checked: number; customers_checked: number }>>(
    "/customers/alerts/check",
  );

// Multi-Agent Orchestration (AI)
export const orchestrateCustomer360 = (customerId: number) =>
  client.post<APIResponse<Customer360>>(`/ai/orchestrate/customer/${customerId}`);

export const orchestrateProduct360 = (productId: number) =>
  client.post<APIResponse<Product360>>(`/ai/orchestrate/product/${productId}`);

export function normalizeGlobal360(payload: Global360): Global360 {
  if (!payload.insights) return payload;
  return {
    ...payload,
    ...payload.insights,
    insights: payload.insights,
  };
}

export const orchestrateGlobal360 = () =>
  client
    .post<APIResponse<Global360>>("/ai/orchestrate/global", undefined, { timeout: 25000 })
    .then((response) => {
      if (response.data.data) {
        response.data.data = normalizeGlobal360(response.data.data);
      }
      return response;
    });

// ============================================================

// Watchtower & Demand Forecast (AI)
export const getWatchtowerScan = (daysBack = 90) =>
  client.get<
    APIResponse<{
      scanned_at: string;
      total_alerts: number;
      severity: string;
      summary: string;
      top_actions: string[];
      risk_areas: string[];
      anomalies: Record<string, Record<string, unknown>[]>;
    }>
  >(`/ai/watchtower/scan?days_back=${daysBack}`);

export const getDailyReport = () =>
  client.get<
    APIResponse<{
      report_date: string;
      generated_at: string;
      metrics: {
        orders_today: number;
        revenue_today: number;
        new_customers: number;
        payments_today: number;
        payments_amount_today: number;
        low_stock_items: number;
        out_of_stock_items: number;
      };
      ai_summary: string;
      mood: string;
      top_action: string;
    }>
  >("/ai/daily-report");

export const getDemandForecast = (category?: string, topK = 20) => {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  params.set("top_k", String(topK));
  return client.get<
    APIResponse<
      {
        product_id: number;
        sku: string;
        name: string;
        category: string;
        monthly_forecast: number;
        trend: string;
        trend_score: number;
        seasonal_factor: number;
        suggested_safety_stock: number;
        current_safety_stock: number;
        current_quantity: number;
        lead_time_days: number;
        confidence: string;
        last_sold: string;
        monthly_history: Record<string, number>;
      }[]
    >
  >(`/ai/inventory/demand-forecast?${params.toString()}`);
};

// ============================================================

// NLP Query (AI)
export const naturalLanguageQuery = (query: string) =>
  client.post<APIResponse<NLPQueryResult>>("/ai/query", { query });

// ============================================================
