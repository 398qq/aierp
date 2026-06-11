/** Audit log API (Stage 10 Day 3 backend, Stage 11 Day 3 frontend).

Used by AuditLogViewer page (system admin / owner only).
*/

import client from "./client";

export interface FieldChange {
  id: number;
  table_name: string;
  record_id: number;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  actor: string | null;
  reason: string | null;
  changed_at: string;
}

export interface FieldChangesList {
  items: FieldChange[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditSummary {
  days_back: number;
  by_table: Record<string, number>;
  by_actor: Record<string, number>;
  top_fields: Array<{ table: string; field: string; count: number }>;
}

export interface ListFieldChangesParams {
  table_name?: string;
  record_id?: number;
  field_name?: string;
  actor?: string;
  days_back?: number;
  page?: number;
  page_size?: number;
}

export const listFieldChanges = (params: ListFieldChangesParams = {}) =>
  client.get<unknown, { data: FieldChangesList }>("/audit/field-changes", { params });

export const recentFieldChanges = (limit = 20) =>
  client.get<unknown, { data: { items: FieldChange[]; count: number } }>(
    "/audit/field-changes/recent",
    { params: { limit } },
  );

export const fieldChangesSummary = (daysBack = 30) =>
  client.get<unknown, { data: AuditSummary }>("/audit/field-changes/summary", {
    params: { days_back: daysBack },
  });
