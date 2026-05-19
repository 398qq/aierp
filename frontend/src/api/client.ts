import axios from "axios";

type APIErrorPayload = {
  code?: number;
  msg?: string;
  message?: string;
  request_id?: string;
  data?: unknown;
};

type APIError = Error & {
  config?: {
    url?: string;
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

function getRequestPath(url?: string) {
  if (!url) return "";
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url;
  }
}

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

client.interceptors.request.use((config) => {
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
  (error: APIError) => {
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
