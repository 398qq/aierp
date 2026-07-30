/**
 * useUserPreferences — per-(scope, key) JSON value store backed by
 * the /api/v1/user-preferences/* endpoints.
 *
 * Replaces ad-hoc localStorage persistence with server-side sync so
 * preferences travel across devices. The server is the source of
 * truth; the local React state is a derived view.
 *
 * Usage:
 *   const { values, upsert, remove } = useUserPreferences("products");
 *   await upsert("column_visibility", { amount: false });
 *   console.log(values["column_visibility"]);  // JSON-parsed
 *
 * Design doc: docs/frontend/products-page-design.md §4.1, §6.4
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { useApiMutation, useApiQuery, useQueryClient } from "@/lib/queries";
import { getApiErrorMessage } from "@/api";

export type PreferenceValue = unknown;

export interface PreferenceItem {
  scope: string;
  key: string;
  value: PreferenceValue;
}

interface RespList {
  items: PreferenceItem[];
}

interface ListResult {
  /** JSON-parsed value for each (scope, key) entry; missing keys → undefined. */
  values: Record<string, PreferenceValue>;
  /** Raw items keyed by key (raw string value, not parsed). */
  items: PreferenceItem[];
  /** True if the list is currently being fetched. */
  isLoading: boolean;
  /** Reload from server. */
  refresh: () => Promise<void>;
  /** Upsert one preference; idempotent on (scope, key). */
  upsert: (key: string, value: PreferenceValue) => Promise<void>;
  /** Soft-delete one preference. */
  remove: (key: string) => Promise<void>;
  /** Last upsert/remove error message (string) or null. */
  error: string | null;
}

const parse = (raw: string): PreferenceValue => {
  if (raw === "null" || raw === "undefined") return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;  // tolerate non-JSON payloads gracefully
  }
};

const stringify = (v: PreferenceValue): string => JSON.stringify(v ?? null);

export function useUserPreferences(scope: string): ListResult {
  const queryClient = useQueryClient();
  const [localValues, setLocalValues] = useState<Record<string, PreferenceValue>>({});
  const [error, setError] = useState<string | null>(null);

  const query = useApiQuery<RespList>(
    ["user-preferences", scope],
    `/user-preferences/${scope}`,
    undefined,
    { staleTime: 30 * 1000 },
  );

  // Merge server values into local state so a fresh page (e.g. cross-device
  // login) shows the synced value rather than waiting for a refetch.
  useEffect(() => {
    if (!query.data) return;
    const next: Record<string, PreferenceValue> = { ...localValues };
    for (const it of query.data.items) {
      next[it.key] = parse(it.value as string);
    }
    setLocalValues(next);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.data]);

  const upsertMut = useApiMutation<PreferenceItem, { key: string; value: string }>(
    "put",
    ({ key }) => `/user-preferences/${scope}/${key}`,
    { invalidateKeys: [["user-preferences", scope]] },
  );

  const deleteMut = useApiMutation<unknown, { key: string }>(
    "delete",
    ({ key }) => `/user-preferences/${scope}/${key}`,
    { invalidateKeys: [["user-preferences", scope]] },
  );

  const upsert = useCallback(
    async (key: string, value: PreferenceValue) => {
      setError(null);
      const raw = stringify(value);
      // Optimistic update
      setLocalValues((prev: Record<string, PreferenceValue>) => ({ ...prev, [key]: value }));
      try {
        await upsertMut.mutateAsync({ key, value: raw });
      } catch (e: unknown) {
        // Roll back optimistic
        setLocalValues((prev: Record<string, PreferenceValue>) => {
          const { [key]: _drop, ...rest } = prev;
          void _drop;
          return rest;
        });
        setError(getApiErrorMessage(e, "保存偏好失败"));
        throw e;
      }
    },
    [upsertMut],
  );

  const remove = useCallback(
    async (key: string) => {
      setError(null);
      const prevSnapshot = localValues[key];
      setLocalValues((prev: Record<string, PreferenceValue>) => {
        const { [key]: _drop, ...rest } = prev;
        void _drop;
        return rest;
      });
      try {
        await deleteMut.mutateAsync({ key });
      } catch (e: unknown) {
        // Roll back
        if (prevSnapshot !== undefined) {
          setLocalValues((prev) => ({ ...prev, [key]: prevSnapshot }));
        }
        setError(getApiErrorMessage(e, "删除偏好失败"));
        throw e;
      }
    },
    [deleteMut, localValues],
  );

  const refresh = useCallback(async () => {
    setError(null);
    try {
      await query.refetch();
    } catch (e: unknown) {
      setError(getApiErrorMessage(e, "读取偏好失败"));
    }
  }, [query]);

  // Invalidate cross-scope too: deleting scope A shouldn't affect B,
  // but in this app the only scope used today is 'products', so a single
  // key is fine. If new scopes arrive, callers should explicitly call
  // queryClient.invalidateQueries with their own scope key.
  // (No code change required; this is just a guard note.)

  return useMemo(
    () => ({
      values: localValues,
      items: (query.data?.items ?? []).map((it) => ({
        scope: it.scope,
        key: it.key,
        value: parse(it.value as string),
      })),
      isLoading: query.isLoading,
      refresh,
      upsert,
      remove,
      error,
    }),
    [localValues, query.data, query.isLoading, refresh, upsert, remove, error],
  );
}
