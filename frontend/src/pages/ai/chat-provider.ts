import {
  AbstractChatProvider,
  XRequest,
  type SSEOutput,
  type TransformMessage,
} from "@ant-design/x-sdk";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  isWelcome?: boolean;
}

export interface ChatRequestParams {
  message: string;
  history?: Array<{ role: string; content: string }>;
}

export const WELCOME_MESSAGE =
  "你好！我是 AIERP 智能助手。我可以帮你：\n\n• 分析客户 RFM 价值\n• 预测客户流失风险\n• 给出跟进建议\n• 解答销售问题\n\n请直接输入你的问题。";

export const FALLBACK_MESSAGE = "抱歉，AI 服务暂时不可用。";

export const ABORTED_MESSAGE = "已停止生成。";

const MAX_HISTORY_MESSAGES = 20;

class AIERPChatProvider extends AbstractChatProvider<ChatMessage, ChatRequestParams, SSEOutput> {
  transformParams(requestParams: Partial<ChatRequestParams>): ChatRequestParams {
    // getMessages() already includes the local user message that triggered
    // this request (appended synchronously before run()), so drop the tail.
    const history = this.getMessages()
      .slice(0, -1)
      .filter((msg) => !msg.isWelcome && msg.content)
      .slice(-MAX_HISTORY_MESSAGES)
      .map(({ role, content }) => ({ role, content }));
    return { message: requestParams.message ?? "", history };
  }

  transformLocalMessage(requestParams: Partial<ChatRequestParams>): ChatMessage {
    return { role: "user", content: requestParams.message ?? "" };
  }

  transformMessage(info: TransformMessage<ChatMessage, SSEOutput>): ChatMessage {
    const { originMessage, chunk } = info;
    const accumulated: ChatMessage = originMessage ?? { role: "assistant", content: "" };
    const data = typeof chunk?.data === "string" ? chunk.data.trim() : "";
    if (!data || data === "[DONE]") {
      return accumulated;
    }
    try {
      const parsed = JSON.parse(data) as { content?: string };
      return { ...accumulated, content: accumulated.content + (parsed.content ?? "") };
    } catch {
      // partial JSON chunk — keep accumulated content
      return accumulated;
    }
  }
}

export function createAIERPChatProvider(): AIERPChatProvider {
  return new AIERPChatProvider({
    request: XRequest<ChatRequestParams, SSEOutput>("/api/v1/ai/chat", {
      manual: true,
      fetch: (baseURL, options) => {
        const params = options.params ?? {};
        const token = localStorage.getItem("token");
        const url = `${baseURL}?query=${encodeURIComponent(params.message ?? "")}`;
        return globalThis.fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ history: params.history ?? [] }),
          signal: options.signal,
        });
      },
    }),
  });
}
