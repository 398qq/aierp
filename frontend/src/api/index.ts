import client from "./client";
import type {
  APIResponse, Brand, ChurnRisk, Customer, DeliveryNote, FollowUp,
  InventoryItem, LoginData, Opportunity, PageData, Payment, Product,
  PurchaseOrder, Quotation, RFMAnalysis, SalesOrder, Sample, Supplier,
  Tag, Ticket, TimelineEvent, Visit, Warehouse,
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

export const exportCustomers = (params: Record<string, unknown>) =>
  client.get("/customers/export", { params, responseType: "blob" });

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

export const createOpportunity = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/opportunities", data);

// Quotations
export const getQuotations = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<Quotation>>>("/quotations", { params });

export const createQuotation = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/quotations", data);

// Sales Orders
export const getSalesOrders = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<SalesOrder>>>("/sales-orders", { params });

export const createSalesOrder = (data: Record<string, unknown>) =>
  client.post<APIResponse>("/sales-orders", data);

// Delivery Notes
export const getDeliveryNotes = (params: Record<string, unknown>) =>
  client.get<APIResponse<PageData<DeliveryNote>>>("/delivery-notes", { params });

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
