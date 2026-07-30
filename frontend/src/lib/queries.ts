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
 */

import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import client from "../api/client";

export type ApiQueryOptions = {
  enabled?: boolean;
  staleTime?: number;
  refetchOnWindowFocus?: boolean;
};

export type ApiMutationOptions<TData, TVariables> = {
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: Error, variables: TVariables) => void;
  invalidateKeys?: readonly QueryKey[];
};

export function useApiQuery<T = unknown>(
  key: readonly unknown[],
  url: string,
  params?: Record<string, unknown>,
  options?: ApiQueryOptions
) {
  return useQuery<T>({
    queryKey: key,
    queryFn: async () => {
      const resp = await client.get<T>(url, { params });
      return resp.data as T;
    },
    enabled: options?.enabled ?? true,
    staleTime: options?.staleTime,
    refetchOnWindowFocus: options?.refetchOnWindowFocus,
  });
}

export function useApiMutation<TData = unknown, TVariables = unknown>(
  method: "post" | "put" | "delete" | "patch",
  url: string | ((variables: TVariables) => string),
  options?: ApiMutationOptions<TData, TVariables>
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