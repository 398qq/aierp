import client from "./client";
import type { APIResponse, PageData } from "../types";

export interface Warehouse {
  id: number;
  name: string;
  location: string | null;
  description: string | null;
  warehouse_type: string | null;
  is_active: boolean;
  created_at?: string;
}

export const warehousesApi = {
  list: (params?: { page?: number; page_size?: number; keyword?: string }) =>
    client.get<APIResponse<PageData<Warehouse>>>("/warehouses", { params }),

  get: (id: number) => client.get<APIResponse<Warehouse>>(`/warehouses/${id}`),

  create: (data: {
    name: string;
    location?: string;
    description?: string;
    warehouse_type?: string;
    is_active?: boolean;
  }) => client.post<APIResponse<Warehouse>>("/warehouses", data),

  update: (
    id: number,
    data: {
      name?: string;
      location?: string;
      description?: string;
      warehouse_type?: string;
      is_active?: boolean;
    },
  ) => client.put<APIResponse<Warehouse>>(`/warehouses/${id}`, data),

  delete: (id: number) => client.delete<APIResponse<{ id: number }>>(`/warehouses/${id}`),
};
