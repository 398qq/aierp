/**
 * useCustomersList — Stage 3 Day 2.
 *
 * Encapsulates the customers list fetch loop:
 * - 4 states (data / total / loading / error)
 * - 1 debounced effect that refetches when any filter / sort changes
 * - 1 manual `refetch()` for explicit re-load (after create/update/delete)
 *
 * Shared list-fetch behaviour for customer workbench/search surfaces.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { getCustomers } from "../api/customers";
import type { Customer, PageData } from "../types";

import { useCustomersFilter } from "./useCustomersFilter";

export interface UseCustomersListResult {
  data: Customer[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  /** Page state managed internally (filter changes reset to 1). */
  page: number;
  pageSize: number;
  setPage: (n: number) => void;
  setPageSize: (n: number) => void;
}

const DEBOUNCE_MS = 350;

export function useCustomersList(
  filter: ReturnType<typeof useCustomersFilter>,
  sceneFilterResolver: (scene: ReturnType<typeof useCustomersFilter>["scene"]) => {
    level?: string; region?: string; source?: string; creditLevel?: string;
  }
): UseCustomersListResult {
  const { q, scene, industry, level, region, source, creditLevel, sortBy, sortOrder } = filter;

  const [data, setData] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [reloadNonce, setReloadNonce] = useState(0);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refetch = useCallback(() => setReloadNonce((n) => n + 1), []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      // Reset to page 1 whenever filter changes, not when page itself changes.
      setPage(1);

      setLoading(true);
      setError(null);
      try {
        const sceneFilter = sceneFilterResolver(scene);
        const params: Record<string, unknown> = {
          page: 1,  // always start at page 1 after filter change
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder,
        };
        if (q.trim()) {
          params.keyword = q.trim();
          params.q = q.trim();
        }
        if (industry) params.industry = industry;
        if (level ?? sceneFilter.level) params.level = level ?? sceneFilter.level;
        if (region ?? sceneFilter.region) params.region = region ?? sceneFilter.region;
        if (source ?? sceneFilter.source) params.source = source ?? sceneFilter.source;
        if (creditLevel ?? sceneFilter.creditLevel) params.credit_level = creditLevel ?? sceneFilter.creditLevel;

        const resp = await getCustomers(params);
        const pageData: PageData<Customer> = resp.data.data;
        setData(pageData.list || []);
        setTotal(pageData.total || 0);
      } catch (e) {
        setError(e instanceof Error ? e.message : "加载客户失败");
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, scene, industry, level, region, source, creditLevel, sortBy, sortOrder, pageSize, reloadNonce]);

  // Page change refetch (no debounce)
  useEffect(() => {
    if (page === 1) return;  // already loaded by filter effect
    let cancelled = false;
    setLoading(true);
    const fetchPage = async () => {
      try {
        const sceneFilter = sceneFilterResolver(scene);
        const params: Record<string, unknown> = {
          page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder,
        };
        if (q.trim()) {
          params.keyword = q.trim();
          params.q = q.trim();
        }
        if (industry) params.industry = industry;
        if (level ?? sceneFilter.level) params.level = level ?? sceneFilter.level;
        if (region ?? sceneFilter.region) params.region = region ?? sceneFilter.region;
        if (source ?? sceneFilter.source) params.source = source ?? sceneFilter.source;
        if (creditLevel ?? sceneFilter.creditLevel) params.credit_level = creditLevel ?? sceneFilter.creditLevel;

        const resp = await getCustomers(params);
        if (cancelled) return;
        setData(resp.data.data.list || []);
        setTotal(resp.data.data.total || 0);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchPage();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  return { data, total, loading, error, refetch, page, pageSize, setPage, setPageSize };
}
