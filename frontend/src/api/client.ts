import axios from "axios";

type APIErrorPayload = {
  code?: number;
  msg?: string;
  message?: string;
  request_id?: string;
  data?: unknown;
};

type APIError = Error & {
  response?: {
    status?: number;
    data?: APIErrorPayload;
    headers?: Record<string, string>;
  };
  requestId?: string;
};

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

client.interceptors.request.use((config) => {
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
      window.location.href = "/login";
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
