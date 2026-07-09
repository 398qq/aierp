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

// Customers
export const getCustomers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Customer>>>("/customers", { params });

export const getCustomer = (id: number) => client.get<APIResponse<Customer>>(`/customers/${id}`);

export const createCustomer = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers", data);

export const updateCustomer = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${id}`, data);

export const deleteCustomer = (id: number) => client.delete<APIResponse>(`/customers/${id}`);

export const getContacts = (customerId: number) =>
  client.get<APIResponse>(`/customers/${customerId}/contacts`);

export const createContact = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/contacts`, data);

export const getFollowUps = (customerId: number) =>
  client.get<APIResponse<FollowUp[]>>(`/customers/${customerId}/follow-ups`);

export const createFollowUp = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/follow-ups`, data);

export const updateContact = (
  customerId: number,
  contactId: number,
  data: Record<string, unknown>,
) => client.put<APIResponse>(`/customers/${customerId}/contacts/${contactId}`, data);

export const deleteContact = (customerId: number, contactId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/contacts/${contactId}`);

export const updateFollowUp = (
  customerId: number,
  followupId: number,
  data: Record<string, unknown>,
) => client.put<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`, data);

export const deleteFollowUp = (customerId: number, followupId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`);

export const getTimeline = (customerId: number) =>
  client.get<APIResponse<TimelineEvent[]>>(`/customers/${customerId}/timeline`);

export const getCustomerStats = (customerId: number) =>
  client.get<APIResponse<CustomerStats>>(`/customers/${customerId}/stats`);

export const getDashboardStats = () => client.get<APIResponse<DashboardStats>>("/customers/stats");

export const getCustomerAIStats = () =>
  client.get<APIResponse<CustomerAIStats>>("/customers/ai-stats");

export const batchScoreAI = (ids?: number[]) =>
  client.post<APIResponse<{ scored: number; errors: number; total: number }>>(
    "/customers/batch-score-ai",
    ids ? { ids } : {},
  );

export const getOverdueFollowUps = () =>
  client.get<APIResponse<{ total: number; items: OverdueFollowUp[] }>>(
    "/customers/overdue-followups",
  );

export const getFollowUpReminders = () =>
  client.get<
    APIResponse<{ total: number; counts: Record<string, number>; items: FollowUpReminder[] }>
  >("/customers/follow-up-reminders");

export const getGlobalFollowUps = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<GlobalFollowUp> & { counts: Record<string, number> }>>(
    "/customers/follow-ups-global",
    { params },
  );

export const exportCustomers = (params: Record<string, unknown>) =>
  client.get("/customers/export", { params, responseType: "blob" });

export const downloadImportTemplate = () =>
  client.get("/customers/import-template", { responseType: "blob" });

export const importCustomers = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/customers/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const batchDeleteCustomers = (ids: number[]) =>
  client.post<APIResponse>("/customers/batch-delete", { ids });

export const batchTagCustomers = (ids: number[], tag_ids: number[]) =>
  client.post<APIResponse>("/customers/batch-tag", { ids, tag_ids });

export const batchSetOwner = (ids: number[], action: "claim" | "release") =>
  client.post<APIResponse>("/customers/batch-owner", { ids, action });

// Tags
export const getTags = () => client.get<APIResponse<Tag[]>>("/customers/tags");

export const createTag = (data: Record<string, unknown>) =>
  client.post<APIResponse<Tag>>("/customers/tags", data);

export const generateDefaultCustomerTags = () =>
  client.post<APIResponse<{ created: number; existing: number; tags: Tag[] }>>(
    "/customers/tags/defaults",
  );

export const updateTag = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Tag>>(`/customers/tags/${id}`, data);

export const deleteTag = (id: number) => client.delete<APIResponse>(`/customers/tags/${id}`);

export const getCustomerTags = (customerId: number) =>
  client.get<APIResponse<Tag[]>>(`/customers/${customerId}/tags`);

export const linkTag = (customerId: number, tagId: number) =>
  client.post<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

export const unlinkTag = (customerId: number, tagId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

// Attachments (legacy customer-specific)
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

// Documents (Phase 7 — generic entity attachments)
export const getDocuments = (entityType: string, entityId: number) =>
  client.get<APIResponse<Document[]>>(`/documents?entity_type=${entityType}&entity_id=${entityId}`);

export const uploadDocument = (entityType: string, entityId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  form.append("entity_type", entityType);
  form.append("entity_id", String(entityId));
  return client.post<APIResponse>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const downloadDocument = (docId: number) =>
  client.get(`/documents/${docId}/download`, { responseType: "blob" });

export const deleteDocument = (docId: number) => client.delete<APIResponse>(`/documents/${docId}`);

// Import/Export (Phase 7)
export const exportEntity = (entity: string, format: string = "csv") =>
  client.get(`/export/${entity}?format=${format}`, { responseType: "blob" });

export const importEntity = (entity: string, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post<APIResponse>(`/import/${entity}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// Customer Logs
export const getCustomerLogs = (customerId: number) =>
  client.get<APIResponse<CustomerLog[]>>(`/customers/${customerId}/logs`);

export const getRecentActivity = (limit = 20) =>
  client.get<APIResponse<CustomerLog[]>>(`/customers/recent-activity?limit=${limit}`);

// Customer Merge
export const mergeCustomers = (source_id: number, target_id: number) =>
  client.post<APIResponse<MergeResult>>("/customers/merge", { source_id, target_id });

// Duplicate Detection
export const detectDuplicates = (threshold = 0.9) =>
  client.get<APIResponse<{ total: number; pairs: DuplicatePair[] }>>("/customers/duplicates", {
    params: { threshold },
  });

// Group Relationships
export const linkParent = (customerId: number, parentId: number) =>
  client.post<APIResponse>(`/customers/${customerId}/link-parent`, { parent_id: parentId });

export const unlinkParent = (customerId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/link-parent`);

export const getChildren = (customerId: number) =>
  client.get<APIResponse<Customer[]>>(`/customers/${customerId}/children`);

export const getGroupStats = (customerId: number) =>
  client.get<APIResponse<GroupStats>>(`/customers/${customerId}/group-stats`);

// Customer Insight — uses zod schema for runtime validation
import { customerInsightSchema } from "./schemas/customer";
import { safeGet } from "./schemas";

export const getCustomerInsight = (id: number) =>
  safeGet(`/customers/${id}/insight`, customerInsightSchema);

export const getCustomerQuotationHistory = (customerId: number, status?: string) =>
  client.get<APIResponse<import("../types").CustomerQuotationHistory>>(
    `/customers/${customerId}/quotation-history`,
    status ? { params: { status } } : undefined,
  );

// Customer Visits
export const getCustomerVisits = (customerId: number) =>
  client.get<APIResponse<Visit[]>>(`/customers/${customerId}/visits`);

export const createCustomerVisit = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/visits`, data);

export const updateCustomerVisit = (
  customerId: number,
  visitId: number,
  data: Record<string, unknown>,
) => client.put<APIResponse>(`/customers/${customerId}/visits/${visitId}`, data);

export const deleteCustomerVisit = (customerId: number, visitId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/visits/${visitId}`);

export const getUpcomingVisits = (days = 14) =>
  client.get<APIResponse<{ list: Visit[]; total: number }>>(`/visits?page_size=50`);

// Level Rules
export const getLevelRules = () => client.get<APIResponse<LevelRule[]>>("/customers/level-rules");

export const createLevelRule = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers/level-rules", data);

export const updateLevelRule = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/level-rules/${id}`, data);

export const deleteLevelRule = (id: number) =>
  client.delete<APIResponse>(`/customers/level-rules/${id}`);

export const autoLevel = () =>
  client.post<APIResponse<{ updated: number }>>("/customers/auto-level");

// Customer intelligence
export const getCustomer360 = (customerId: number) =>
  client.post<APIResponse<import("../types").Customer360>>(
    `/ai/orchestrate/customer/${customerId}`,
  );

export const getCustomerSegments = (nClusters = 5) =>
  client.get<APIResponse<{ clusters: import("../types").SegmentCluster[]; total: number }>>(
    `/ai/customer/segments?n_clusters=${nClusters}`,
  );

export const getSimilarCustomers = (customerId: number, topK = 10) =>
  client.get<APIResponse<import("../types").SimilarCustomer[]>>(
    `/ai/customer/${customerId}/similar?top_k=${topK}`,
  );

export const searchSimilarCustomers = (q: string, topK = 10) =>
  client.get<APIResponse<import("../types").SimilarCustomer[]>>(
    `/ai/customer/similar/search?q=${encodeURIComponent(q)}&top_k=${topK}`,
  );

export const generateCustomerWorkQueue = (payload?: {
  customer_ids?: number[];
  replace_open?: boolean;
  dry_run?: boolean;
}) =>
  client.post<
    APIResponse<{
      generated: number;
      replaced: number;
      items: Array<{
        id?: number;
        customer_id: number;
        customer_name: string;
        action_type: string;
        title: string;
        priority_score: number;
        due_at: string | null;
        status: string;
      }>;
    }>
  >("/ai/customer/work-queue/generate", payload || {});

export const getCustomerWorkQueue = (params: Record<string, unknown>) =>
  client.get<APIResponse<CustomerAIWorkQueuePage>>("/ai/customer/work-queue", { params });

export const getCustomerAIRecommendationSummary = (customerId: number) =>
  client.get<APIResponse<CustomerAIRecommendationSummary>>(`/ai/customer/${customerId}/summary`);

export const updateCustomerRecommendationStatus = (
  recommendationId: number,
  data: { status: "open" | "in_progress" | "done" | "dismissed" | "superseded"; owner?: string },
) => client.post<APIResponse>(`/ai/customer/recommendation/${recommendationId}/status`, data);

export const submitCustomerRecommendationFeedback = (
  recommendationId: number,
  data: {
    verdict: "adopted" | "rejected" | "partial";
    usefulness?: number;
    outcome?: string;
    revenue_impact?: number;
    cost_impact?: number;
    comment?: string;
  },
) => client.post<APIResponse>(`/ai/customer/recommendation/${recommendationId}/feedback`, data);

// ============================================================
