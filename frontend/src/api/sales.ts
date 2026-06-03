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

// Sales — Opportunities

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

export const getQuotations = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Quotation> & { ai?: Record<number, QuotationAI> }>>("/quotations", { params });

export const getQuotationStats = () =>
  client.get<APIResponse<QuotationStats>>("/quotations/stats");

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

export const updateQuotationStatus = (id: number, status: string) =>
  client.put<APIResponse<Quotation>>(`/quotations/${id}/status`, { status });

export const duplicateQuotation = (id: number) =>
  client.post<APIResponse<Quotation>>(`/quotations/${id}/duplicate`);

export const batchDeleteQuotations = (ids: number[]) =>
  client.post<APIResponse>("/quotations/batch-delete", { ids });

export const createQuotationFromInquiry = (inquiryId: number, items?: Record<string, unknown>[]) =>
  client.post<APIResponse<{ id: number; quotation_no: string }>>("/quotations/from-inquiry", {
    inquiry_id: inquiryId,
    items: items || [],
  });

export const convertQuotationToOrder = (id: number) =>
  client.post<APIResponse<{ id: number; document_no: string; msg: string }>>(`/quotations/${id}/convert-to-order`);

export type QuotationPDFOptions = {
  template?: "smart" | "standard" | "compact";
  company_name?: string;
  document_title?: string;
  show_smart_summary?: boolean;
  show_line_hints?: boolean;
  show_terms?: boolean;
  show_notes?: boolean;
  show_internal_metrics?: boolean;
  show_signature?: boolean;
  prepared_by?: string;
  contact_phone?: string;
  terms?: string;
};

export const downloadQuotationPDF = async (id: number, filename?: string, options?: QuotationPDFOptions) => {
  const resp = await client.get(`/quotations/${id}/pdf`, { params: options, responseType: "blob" });
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

export type SalesOrderPDFImportResult = {
  id: number;
  order_no: string | null;
  customer_id: number;
  parsed: {
    order_no?: string | null;
    customer_name?: string | null;
    item_count: number;
    total_amount: number;
    order_date?: string | null;
    delivery_date?: string | null;
  };
  matched: {
    customer_name: string;
    products: Array<{ source?: string | null; product_id: number | null; product_name: string | null }>;
  };
  raw_text_preview: string;
};

export const importSalesOrderPDF = (file: File, customerId?: number) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<APIResponse<SalesOrderPDFImportResult>>("/sales-orders/import-pdf", form, {
    params: customerId ? { customer_id: customerId } : undefined,
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export type SalesOrderPDFOptions = {
  template?: "smart" | "standard" | "compact";
  company_name?: string;
  document_title?: string;
  show_smart_summary?: boolean;
  show_line_hints?: boolean;
  show_terms?: boolean;
  show_notes?: boolean;
  show_signature?: boolean;
  prepared_by?: string;
  contact_phone?: string;
  terms?: string;
};

export const downloadSalesOrderPDF = async (id: number, filename?: string, options?: SalesOrderPDFOptions) => {
  const resp = await client.get(`/sales-orders/${id}/pdf`, { params: options, responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename || `sales_order_${id}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ============================================================

// Sales — Delivery Notes

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

// Finance — Sales Targets

export const getTargets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesTarget>>>("/sales/targets", { params });

export const getTargetStats = () =>
  client.get<APIResponse<{ total_target: number; total_actual: number; achievement_pct: number; count: number; completed: number }>>("/sales/targets/stats");

export const getTarget = (id: number) =>
  client.get<APIResponse<SalesTarget>>(`/sales/targets/${id}`);

export const createTarget = (data: Record<string, unknown>) =>
  client.post<APIResponse<SalesTarget>>("/sales/targets", data);

export const updateTarget = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<SalesTarget>>(`/sales/targets/${id}`, data);

export const deleteTarget = (id: number) =>
  client.delete<APIResponse>(`/sales/targets/${id}`);

// ============================================================

// Sales Dashboard

export const getSalesDashboardOverview = () =>
  client.get<APIResponse<import("../types").SalesDashboardOverview>>("/sales/dashboard/overview");

export const getSalesDashboardTrends = (months = 12) =>
  client.get<APIResponse<import("../types").SalesDashboardTrends>>(`/sales/dashboard/trends?months=${months}`);

export const getSalesDashboardAlerts = () =>
  client.get<APIResponse<import("../types").SalesDashboardAlerts>>("/sales/dashboard/alerts");


// Inquiry Auto-Reply
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

