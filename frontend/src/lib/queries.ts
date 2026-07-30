/**
 * 通用 React Query hooks（替代 ahooks useRequest）
 *
 * 用法：
 *   const { data, isLoading } = useApiQuery(['customers', params], '/api/v1/customers', params);
 *   const createMut = useApiMutation('post', '/api/v1/customers', { invalidateKeys: [['customers']] });
 *   createMut.mutate(newData);
 *
 * 迁移指南：
 * - useRequest('/api/x')       → useApiQuery(['x'], '/api/x')
 * - useRequest('/api/x', { manual: true }) + run(...) → useApiMutation('post', '/api/x')
 * - refresh()                    → useQueryClient().invalidateQueries({ queryKey: [...] })
 * - loading → isLoading（拼写变化）
 *
 * 分页与列表场景：
 * - useApiQuery 的 options.keepPreviousData 默认为 **false**。翻页/筛选/重排时，
 *   旧数据会被设为 undefined，列表闪空一下。
 * - 列表 + 服务端分页的页面建议开启：见下方 useApiQuery 注释。
 *   行为参考：分页/筛选触发新请求时，React Query 保留上一页 data，
 *   新请求返回前 isLoading=true 但 data 仍是上一页，避免 UI 闪烁。
 *   参考 ant-design-pro v6 #11693 设计；AIERP 首个接入：CustomerListPage。
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
} from "@tanstack/react-query";
import client from "../api/client";

export type ApiQueryOptions = {
  enabled?: boolean;
  staleTime?: number;
  refetchOnWindowFocus?: boolean;
  /**
   * 翻页/筛选时保留上一页数据，避免列表闪空。
   * 映射到 React Query v5 的 placeholderData: keepPreviousData。
   */
  keepPreviousData?: boolean;
};

export type ApiMutationOptions<TData, TVariables> = {
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: Error, variables: TVariables) => void;
  invalidateKeys?: readonly QueryKey[];
};

/**
 * 通用数据查询 hook。分页列表请把 `keepPreviousData: true`，
 * 翻页与筛选期间避免闪空 —— 默认 false（旧 useRequest 行为）。
 */
export function useApiQuery<T = unknown>(
  key: readonly unknown[],
  url: string,
  params?: Record<string, unknown>,
  options?: ApiQueryOptions,
) {
  return useQuery<T>({
    queryKey: key,
    queryFn: async () => {
      // FastAPI wraps every response in {code, msg, data}; axios hands us
      // the body as `resp.data`. Unwrap one level so callers see inner T
      // and can write `query.data.list`, not `query.data.data.list`.
      const resp = await client.get<{ code?: number; msg?: string; data: T }>(
        url,
        { params },
      );
      const body = resp.data as { code?: number; msg?: string; data: T };
      return body.data;
    },
    enabled: options?.enabled ?? true,
    staleTime: options?.staleTime,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
    placeholderData: options?.keepPreviousData ? keepPreviousData : undefined,
  });
}

export function useApiMutation<TData = unknown, TVariables = unknown>(
  method: "post" | "put" | "delete" | "patch",
  url: string | ((variables: TVariables) => string),
  options?: ApiMutationOptions<TData, TVariables>,
) {
  const queryClient = useQueryClient();
  return useMutation<TData, Error, TVariables>({
    mutationFn: async (variables: TVariables) => {
      const finalUrl = typeof url === "function" ? url(variables) : url;
      const resp = await client[method]<TData>(finalUrl, variables as never);
      return resp.data as TData;
    },
    onSuccess: (data, variables) => {
      options?.onSuccess?.(data, variables);
      options?.invalidateKeys?.forEach((k) => {
        queryClient.invalidateQueries({ queryKey: k });
      });
    },
    onError: options?.onError,
  });
}

export { useQueryClient };
