/**
 * Types barrel — re-exports every entity / intelligence / analytics
 * interface from the per-domain modules. Consumers should keep
 * importing from "@/types"; only this file is allowed to grow.
 *
 * Per-domain split (was 1490 lines in a single file):
 *   common       — APIResponse, PageData, LoginData
 *   customer     — Customer, Contact, FollowUp, RFM, Churn, AI work queue
 *   catalog      — Product, Brand, Supplier, Warehouse, Inventory
 *   operations   — PurchaseOrder, PaymentRecord, SalesTarget, Contract,
 *                  Ticket, Visit, Sample, CustomerLog
 *   analytics    — Customer Insight, Notification, Group, Dashboard,
 *                  Product/Brand Intelligence (overview), Quote
 *                  Assistant, Sales Intelligence, Embedded AI Insights
 *   intelligence — Watchtower, Smart Matching, Brand analytics,
 *                  Supplier/Purchase Order/Payment/Sales Target/
 *                  Visit/Ticket/Contract Intelligence, Multi-Agent,
 *                  NLP, Pricing
 *   sales        — Opportunity, Quotation, SalesOrder, DeliveryNote,
 *                  Invoice, AI Insight Types, Sales Dashboard, Commission
 */

// common.ts
export type { APIResponse } from "./common";
export type { PageData } from "./common";
export type { LoginData } from "./common";

// customer.ts
export type { Customer } from "./customer";
export type { Tag } from "./customer";
export type { Attachment } from "./customer";
export type { Document } from "./customer";
export type { DashboardWidget } from "./customer";
export type { KpiData } from "./customer";
export type { OverdueFollowUp } from "./customer";
export type { FollowUpReminder } from "./customer";
export type { GlobalFollowUp } from "./customer";
export type { DashboardStats } from "./customer";
export type { CustomerStats } from "./customer";
export type { CustomerAIStats } from "./customer";
export type { CustomerRecognition } from "./customer";
export type { CustomerAIWorkQueueSnapshot } from "./customer";
export type { CustomerAIWorkQueueItem } from "./customer";
export type { CustomerAIWorkQueuePage } from "./customer";
export type { CustomerAIRecommendationSummary } from "./customer";
export type { TimelineEvent } from "./customer";
export type { Contact } from "./customer";
export type { FollowUp } from "./customer";
export type { FollowUpRecognition } from "./customer";
export type { RFMAnalysis } from "./customer";
export type { ChurnRisk } from "./customer";

// catalog.ts
export type { Product } from "./catalog";
export type { Brand } from "./catalog";
export type { Supplier } from "./catalog";
export type { Warehouse } from "./catalog";
export type { InventoryItem } from "./catalog";
export type { InventoryBatch, CogsReport } from "./catalog";

// operations.ts
export type { PurchaseOrder } from "./operations";
export type { PaymentRecord } from "./operations";
export type { SalesTarget } from "./operations";
export type { Ticket } from "./operations";
export type { Visit } from "./operations";
export type { Sample } from "./operations";
export type { CustomerLog } from "./operations";
export type { DuplicatePair } from "./operations";
export type { MergeResult } from "./operations";

// analytics.ts
export type { CustomerInsight } from "./analytics";
export type { NotificationItem } from "./analytics";
export type { GroupStats } from "./analytics";
export type { AlertRule } from "./analytics";
export type { AlertEvent } from "./analytics";
export type { LevelRule } from "./analytics";
export type { Contract } from "./analytics";
export type { ProductProfile } from "./analytics";
export type { NormalizedSpec } from "./analytics";
export type { ProductAssociation } from "./analytics";
export type { ProcurementPlan } from "./analytics";
export type { BrandProfile } from "./analytics";
export type { BrandPortfolio } from "./analytics";
export type { BrandComparison } from "./analytics";
export type { SimilarBrand } from "./analytics";
export type { BrandImport } from "./analytics";
export type { BrandHealth } from "./analytics";
export type { BrandRisk } from "./analytics";
export type { BrandSupplierMatrix } from "./analytics";
export type { BrandRecommendation } from "./analytics";

// intelligence.ts
export type { CustomerProductMatch } from "./intelligence";
export type { ProductCustomerMatch } from "./intelligence";
export type { BrandProductPerformance } from "./intelligence";
export type { BrandCustomerPenetration } from "./intelligence";
export type { BrandLifecycle } from "./intelligence";
export type { BrandPriceTrends } from "./intelligence";
export type { LifecycleAnalysis } from "./intelligence";
export type { SupplierProductLink } from "./intelligence";
export type { PriceBenchmark } from "./intelligence";
export type { PriceRecommendation } from "./intelligence";
export type { SupplierScorecard } from "./intelligence";
export type { SupplierDelayPrediction } from "./intelligence";
export type { SupplierAlternatives } from "./intelligence";
export type { SupplierPriceVariance } from "./intelligence";
export type { Supplier360 } from "./intelligence";
export type { SupplierNegotiation } from "./intelligence";
export type { SupplierComparison } from "./intelligence";
export type { POOptimization } from "./intelligence";
export type { POAutoSuggest } from "./intelligence";
export type { PORiskAssessment } from "./intelligence";
export type { VisitReport } from "./intelligence";
export type { VisitSentiment } from "./intelligence";
export type { VisitEffectiveness } from "./intelligence";
export type { TicketClassification } from "./intelligence";
export type { TicketResponse } from "./intelligence";
export type { TicketResolutionPrediction } from "./intelligence";
export type { TicketCluster } from "./intelligence";
export type { Customer360 } from "./intelligence";
export type { Product360 } from "./intelligence";
export type { DailyReport } from "./intelligence";
export type { Global360 } from "./intelligence";
export type { NLPQueryResult } from "./intelligence";

// sales.ts
export type { Opportunity } from "./sales";
export type { QuotationItem } from "./sales";
export type { Quotation } from "./sales";
export type { SalesOrder } from "./sales";
export type { DeliveryNote } from "./sales";
export type { Invoice } from "./sales";
export type { QuotationStats } from "./sales";
export type { SalesOrderItem } from "./sales";
export type { OpportunityAI } from "./sales";
export type { QuotationAI } from "./sales";
export type { SalesOrderAI } from "./sales";
export type { SalesOrderBusinessChain, OpportunityBusinessChain, OpportunityAuditItem, OpportunityAuditTrail, BusinessDocumentRef } from "./sales";
export type { DeliveryNoteAI } from "./sales";
export type { FunnelStage } from "./sales";
export type { SalesDashboardOverview } from "./sales";
export type { TrendPoint } from "./sales";
export type { SalesDashboardTrends } from "./sales";
export type { AIAlert } from "./sales";
export type { SalesDashboardAlerts } from "./sales";
export type { ConversionValidation } from "./sales";
export type { SegmentCluster } from "./sales";
export type { SimilarCustomer } from "./sales";
export type { CustomerQuotationHistory } from "./sales";
export type { CommissionStatus } from "./sales";
export type { Commission } from "./sales";
export type { CommissionCreate } from "./sales";
export type { CommissionUpdate } from "./sales";
