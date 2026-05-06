import client from "./client";
import type {
  APIResponse, Attachment, Brand, ChurnRisk, Customer, CustomerLog, CustomerStats, DashboardStats,
  DeliveryNote, DeliveryNoteItem, DuplicatePair, FollowUp, MergeResult, OverdueFollowUp,
  InventoryItem, LoginData, Opportunity, PageData, Payment, Product,
  PurchaseOrder, Quotation, QuotationItem, RFMAnalysis, SalesOrder, SalesOrderItem,
  Sample, Supplier, Tag, Ticket, TimelineEvent, Visit, Warehouse,
} from "../types";

// Auth
export const login = (username: string, password: string) =>
  client.post<APIResponse<LoginData>>("/auth/login", { username, password });

export const getMe = () => client.get<APIResponse>("/auth/me");

// Customers
export const getCustomers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Customer>>>("/customers", { params });

export const getCustomer = (id: number) =>
  client.get<APIResponse<Customer>>(`/customers/${id}`);

export const createCustomer = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/customers", data);

export const updateCustomer = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${id}`, data);

export const deleteCustomer = (id: number) =>
  client.delete<APIResponse>(`/customers/${id}`);

export const getContacts = (customerId: number) =>
  client.get<APIResponse>(`/customers/${customerId}/contacts`);

export const createContact = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/contacts`, data);

export const getFollowUps = (customerId: number) =>
  client.get<APIResponse<FollowUp[]>>(`/customers/${customerId}/follow-ups`);

export const createFollowUp = (customerId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/customers/${customerId}/follow-ups`, data);

export const updateContact = (customerId: number, contactId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${customerId}/contacts/${contactId}`, data);

export const deleteContact = (customerId: number, contactId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/contacts/${contactId}`);

export const updateFollowUp = (customerId: number, followupId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`, data);

export const deleteFollowUp = (customerId: number, followupId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/follow-ups/${followupId}`);

export const getTimeline = (customerId: number) =>
  client.get<APIResponse<TimelineEvent[]>>(`/customers/${customerId}/timeline`);

export const getCustomerStats = (customerId: number) =>
  client.get<APIResponse<CustomerStats>>(`/customers/${customerId}/stats`);

export const getDashboardStats = () =>
  client.get<APIResponse<DashboardStats>>("/customers/stats");

export const getOverdueFollowUps = () =>
  client.get<APIResponse<{ total: number; items: OverdueFollowUp[] }>>("/customers/overdue-followups");

export const exportCustomers = (params: Record<string, unknown>) =>
  client.get("/customers/export", { params, responseType: "blob" });

export const downloadImportTemplate = () =>
  client.get("/customers/import-template", { responseType: "blob" });

export const importCustomers = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post("/customers/import", form, { headers: { "Content-Type": "multipart/form-data" } });
};

export const batchDeleteCustomers = (ids: number[]) =>
  client.post<APIResponse>("/customers/batch-delete", { ids });

export const batchTagCustomers = (ids: number[], tag_ids: number[]) =>
  client.post<APIResponse>("/customers/batch-tag", { ids, tag_ids });

// Tags
export const getTags = () =>
  client.get<APIResponse<Tag[]>>("/tags");

export const createTag = (data: Record<string, unknown>) =>
  client.post<APIResponse<Tag>>("/tags", data);

export const updateTag = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse<Tag>>(`/tags/${id}`, data);

export const deleteTag = (id: number) =>
  client.delete<APIResponse>(`/tags/${id}`);

export const getCustomerTags = (customerId: number) =>
  client.get<APIResponse<Tag[]>>(`/customers/${customerId}/tags`);

export const linkTag = (customerId: number, tagId: number) =>
  client.post<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

export const unlinkTag = (customerId: number, tagId: number) =>
  client.delete<APIResponse>(`/customers/${customerId}/tags/${tagId}`);

// Attachments
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

// Products
export const getProducts = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Product>>>("/products", { params });

export const getProduct = (id: number) =>
  client.get<APIResponse<Product>>(`/products/${id}`);

export const createProduct = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/products", data);

export const updateProduct = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/products/${id}`, data);

export const deleteProduct = (id: number) =>
  client.delete<APIResponse>(`/products/${id}`);

// Brands
export const getBrands = () =>
  client.get<APIResponse<Brand[]>>("/brands");

export const createBrand = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/brands", data);

// Suppliers
export const getSuppliers = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Supplier>>>("/suppliers", { params });

export const getSupplier = (id: number) =>
  client.get<APIResponse<Supplier>>(`/suppliers/${id}`);

export const createSupplier = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/suppliers", data);

// Warehouses & Inventory
export const getWarehouses = () =>
  client.get<APIResponse<Warehouse[]>>("/warehouses");

export const getInventory = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<InventoryItem>>>("/inventory", { params });

// Opportunities
export const getOpportunities = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Opportunity>>>("/opportunities", { params });

export const getOpportunity = (id: number) =>
  client.get<APIResponse<Opportunity>>(`/opportunities/${id}`);

export const createOpportunity = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/opportunities", data);

export const updateOpportunity = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/opportunities/${id}`, data);

export const deleteOpportunity = (id: number) =>
  client.delete<APIResponse>(`/opportunities/${id}`);

// Quotations
export const getQuotations = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Quotation>>>("/quotations", { params });

export const getQuotation = (id: number) =>
  client.get<APIResponse<Quotation>>(`/quotations/${id}`);

export const createQuotation = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/quotations", data);

export const updateQuotation = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/quotations/${id}`, data);

export const deleteQuotation = (id: number) =>
  client.delete<APIResponse>(`/quotations/${id}`);

// Quotation Items
export const getQuotationItems = (quotationId: number) =>
  client.get<APIResponse<QuotationItem[]>>(`/quotations/${quotationId}/items`);

export const createQuotationItem = (quotationId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/quotations/${quotationId}/items`, data);

export const updateQuotationItem = (quotationId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/quotations/${quotationId}/items/${itemId}`, data);

export const deleteQuotationItem = (quotationId: number, itemId: number) =>
  client.delete<APIResponse>(`/quotations/${quotationId}/items/${itemId}`);

// Sales Orders
export const getSalesOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesOrder>>>("/sales-orders", { params });

export const getSalesOrder = (id: number) =>
  client.get<APIResponse<SalesOrder>>(`/sales-orders/${id}`);

export const createSalesOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales-orders", data);

export const updateSalesOrder = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales-orders/${id}`, data);

export const deleteSalesOrder = (id: number) =>
  client.delete<APIResponse>(`/sales-orders/${id}`);

// Sales Order Items
export const getSalesOrderItems = (orderId: number) =>
  client.get<APIResponse<SalesOrderItem[]>>(`/sales-orders/${orderId}/items`);

export const createSalesOrderItem = (orderId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/sales-orders/${orderId}/items`, data);

export const updateSalesOrderItem = (orderId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/sales-orders/${orderId}/items/${itemId}`, data);

export const deleteSalesOrderItem = (orderId: number, itemId: number) =>
  client.delete<APIResponse>(`/sales-orders/${orderId}/items/${itemId}`);

// Delivery Notes
export const getDeliveryNotes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<DeliveryNote>>>("/delivery-notes", { params });

export const getDeliveryNote = (id: number) =>
  client.get<APIResponse<DeliveryNote>>(`/delivery-notes/${id}`);

export const createDeliveryNote = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/delivery-notes", data);

export const updateDeliveryNote = (id: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/delivery-notes/${id}`, data);

export const deleteDeliveryNote = (id: number) =>
  client.delete<APIResponse>(`/delivery-notes/${id}`);

// Delivery Note Items
export const getDeliveryNoteItems = (noteId: number) =>
  client.get<APIResponse<DeliveryNoteItem[]>>(`/delivery-notes/${noteId}/items`);

export const createDeliveryNoteItem = (noteId: number, data: Record<string, unknown>) =>
  client.post<APIResponse>(`/delivery-notes/${noteId}/items`, data);

export const updateDeliveryNoteItem = (noteId: number, itemId: number, data: Record<string, unknown>) =>
  client.put<APIResponse>(`/delivery-notes/${noteId}/items/${itemId}`, data);

export const deleteDeliveryNoteItem = (noteId: number, itemId: number) =>
  client.delete<APIResponse>(`/delivery-notes/${noteId}/items/${itemId}`);

// Purchase Orders
export const getPurchaseOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<PurchaseOrder>>>("/purchase-orders", { params });

export const createPurchaseOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/purchase-orders", data);

// Payments
export const getPayments = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Payment>>>("/payments", { params });

export const createPayment = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/payments", data);

// Tickets
export const getTickets = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Ticket>>>("/tickets", { params });

export const createTicket = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/tickets", data);

// Visits
export const getVisits = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Visit>>>("/visits", { params });

export const createVisit = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/visits", data);

// Samples
export const getSamples = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Sample>>>("/samples", { params });

export const createSample = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/samples", data);

// AI
export const getRFMAnalysis = (customerId: number) =>
  client.post<APIResponse<RFMAnalysis>>(`/ai/customer/${customerId}/rfm`);

export const getChurnRisk = (customerId: number) =>
  client.post<APIResponse<ChurnRisk>>(`/ai/customer/${customerId}/churn-risk`);

export const getFollowUpSuggestion = (customerId: number) =>
  client.post<APIResponse>(`/ai/customer/${customerId}/followup-suggestion`);

// Customer Logs
export const getCustomerLogs = (customerId: number) =>
  client.get<APIResponse<CustomerLog[]>>(`/customers/${customerId}/logs`);

// Customer Merge
export const mergeCustomers = (source_id: number, target_id: number) =>
  client.post<APIResponse<MergeResult>>("/customers/merge", { source_id, target_id });

// Duplicate Detection
export const detectDuplicates = (threshold = 0.7) =>
  client.get<APIResponse<{ total: number; pairs: DuplicatePair[] }>>("/customers/duplicates", { params: { threshold } });
