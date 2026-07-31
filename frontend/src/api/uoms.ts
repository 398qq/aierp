import client from "./client";
import type { APIResponse } from "../types";

export interface UomItem {
  code: string;
  name: string;
  uom_type: "count" | "package";
  category: string | null;
  description: string | null;
  sort_order: number;
}

export const uomsApi = {
  list: () => client.get<APIResponse<UomItem[]>>("/uoms"),

  create: (data: Partial<UomItem>) => client.post<APIResponse>("/uoms", data),

  update: (code: string, data: Partial<UomItem>) => client.put<APIResponse>(`/uoms/${code}`, data),

  delete: (code: string) => client.delete<APIResponse>(`/uoms/${code}`),
};
