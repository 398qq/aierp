/**
 * React Query client 配置
 *
 * 提供全站共享的 QueryClient 实例。挂在 ErpRouteLayout 根，
 * 让所有 ProLayout 子页面都能用 useQuery/useMutation 共享缓存。
 *
 * 配置策略：
 * - staleTime 5 分钟：减少重复请求，ERP 数据更新频率不高
 * - gcTime 10 分钟：内存中保留最近 10 分钟数据
 * - retry 1 次：网络抖动时自动重试
 * - refetchOnWindowFocus false：避免切回标签页突然刷新
 * - refetchOnReconnect true：网络恢复后自动重取
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,
    },
  },
});