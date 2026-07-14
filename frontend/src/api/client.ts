import axios, { AxiosHeaders, type InternalAxiosRequestConfig } from "axios";

type APIErrorPayload = {
  code?: number;
  msg?: string;
  message?: string;
  request_id?: string;
  data?: unknown;
};

type APIError = Error & {
  code?: string;
  config?: InternalAxiosRequestConfig & {
    url?: string;
    _retryCount?: number;
  };
  response?: {
    status?: number;
    data?: APIErrorPayload;
    headers?: Record<string, string>;
  };
  requestId?: string;
};

const AUTH_PROBE_PATH = "/auth/me";
const LOGIN_PATH = "/login";
const RETRYABLE_METHODS = new Set(["get", "head", "options"]);
const RETRYABLE_STATUSES = new Set([408, 425, 429, 502, 503, 504]);
const MAX_RETRIES = 2;
const MAX_RETRY_DELAY_MS = 5000;

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `req_${crypto.randomUUID()}`;
  }
  return `req_${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

function retryDelayMs(error: APIError, retryCount: number): number {
  const retryAfter = error.response?.headers?.["retry-after"];
  if (retryAfter !== undefined) {
    const seconds = Number(retryAfter);
    if (Number.isFinite(seconds) && seconds >= 0) {
      return Math.min(seconds * 1000, MAX_RETRY_DELAY_MS);
    }
    const dateDelay = Date.parse(retryAfter) - Date.now();
    if (Number.isFinite(dateDelay) && dateDelay >= 0) {
      return Math.min(dateDelay, MAX_RETRY_DELAY_MS);
    }
  }
  const exponentialDelay = 250 * 2 ** retryCount;
  return Math.min(exponentialDelay + Math.random() * 100, MAX_RETRY_DELAY_MS);
}

function shouldRetry(error: APIError): boolean {
  const config = error.config;
  if (!config || !RETRYABLE_METHODS.has((config.method || "get").toLowerCase())) return false;
  if ((config._retryCount || 0) >= MAX_RETRIES || error.code === "ERR_CANCELED") return false;
  const status = error.response?.status;
  return status === undefined || RETRYABLE_STATUSES.has(status);
}

function getRequestPath(url?: string) {
  if (!url) return "";
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url;
  }
}

/** Extract a human-readable message from any axios error.

  * \`\`\`
  * import { getApiErrorMessage } from "@/api/client";
  *
  * try { await createProduct(data) }
  * catch (e) { message.error(getApiErrorMessage(e)); }
  * \`\`\`
  *
  * Priority:
  * 1. Server-provided \`\`msg\`\` / \`\`message\`\` in the response body
  * 2. Axios-level \`\`error.code\`\` / \`\`error.message\`\` (timeout, network)
  * 3. Static fallback you provide as the second argument
  */
export function getApiErrorMessage(error: unknown, fallback = "操作失败"): string {
  if (!error || typeof error !== "object") return fallback;

  const apiErr = error as APIError;

  // Server-provided message (normalized by the response interceptor below)
  if (apiErr.response?.data?.msg) return apiErr.response.data.msg;
  if (apiErr.response?.data?.message) return apiErr.response.data.message;

  // Timeout / network error
  if (apiErr.code === "ECONNABORTED" || /timeout/i.test(apiErr.message || "")) {
    return "请求超时，请稍后重试";
  }
  if (!apiErr.response?.status) return "网络连接失败，请检查网络";

  // HTTP-level fallback
  const httpStatus = apiErr.response.status;
  if (httpStatus === 403) return "无权限访问";
  if (httpStatus >= 500) return "服务器错误，请稍后重试";

  return fallback;
}

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

client.interceptors.request.use((config) => {
  config.headers = AxiosHeaders.from(config.headers);
  if (!config.headers.has("X-Request-ID")) {
    config.headers.set("X-Request-ID", createRequestId());
  }
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    if (config.headers && "Content-Type" in config.headers) {
      delete (config.headers as Record<string, unknown>)["Content-Type"];
    }
    if (config.headers && "content-type" in config.headers) {
      delete (config.headers as Record<string, unknown>)["content-type"];
    }
  }
  // httpOnly cookie is sent automatically by the browser with withCredentials.
  // This interceptor intentionally left empty — token lives in httpOnly cookie,
  // JS never needs to read it.
  return config;
});

client.interceptors.response.use(
  (resp) => resp,
  async (error: APIError) => {
    if (shouldRetry(error) && error.config) {
      const retryCount = error.config._retryCount || 0;
      error.config._retryCount = retryCount + 1;
      const delay = retryDelayMs(error, retryCount);
      if (delay > 0) await new Promise((resolve) => setTimeout(resolve, delay));
      return client.request(error.config);
    }

    const status = error.response?.status;
    const payload = (error.response?.data ?? {}) as APIErrorPayload;
    const requestId = payload.request_id || error.response?.headers?.["x-request-id"];

    const withRequestId = (msg: string) => (requestId ? `${msg} [RID: ${requestId}]` : msg);

    if (status === 401) {
      const requestPath = getRequestPath(error.config?.url);
      const isAuthProbe = requestPath.endsWith(AUTH_PROBE_PATH);
      const isLoginPage = window.location.pathname === LOGIN_PATH;

      if (!isAuthProbe && !isLoginPage) {
        window.location.assign(LOGIN_PATH);
      }
      return Promise.reject(error);
    }

    let normalizedMsg = payload.msg || payload.message || "";

    if (!normalizedMsg) {
      if (status === 403) normalizedMsg = "无权限访问";
      else if (status && status >= 500) normalizedMsg = "服务器错误";
      else if (error.code === "ECONNABORTED" || /timeout/i.test(error.message || "")) normalizedMsg = "请求超时，请稍后重试";
      else if (!status) normalizedMsg = "网络连接失败";
      else normalizedMsg = "请求失败";
    }

    const finalMsg = withRequestId(normalizedMsg);
    error.requestId = requestId;

    if (error.response?.data && typeof error.response.data === "object") {
      error.response.data.msg = finalMsg;
      if (!error.response.data.request_id && requestId) {
        error.response.data.request_id = requestId;
      }
    }
    error.message = finalMsg;

    return Promise.reject(error);
  }
);

export default client;
