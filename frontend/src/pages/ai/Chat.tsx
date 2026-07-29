import { useMemo, useState } from "react";
import { Avatar } from "antd";
import { Bubble, Prompts, Sender, type BubbleListProps } from "@ant-design/x";
import { RobotOutlined, ThunderboltOutlined, UserOutlined } from "@ant-design/icons";
import { useXChat } from "@ant-design/x-sdk";
import {
  ABORTED_MESSAGE,
  FALLBACK_MESSAGE,
  WELCOME_MESSAGE,
  createAIERPChatProvider,
  type ChatMessage,
  type ChatRequestParams,
} from "./chat-provider";

const QUICK_PROMPTS = [
  "本月销售概览",
  "高价值客户分析",
  "流失风险预警",
  "库存优化建议",
  "销售目标进度",
  "近期跟进建议",
];

const BUBBLE_ROLES: BubbleListProps["role"] = {
  assistant: {
    placement: "start",
    avatar: <Avatar icon={<RobotOutlined />} />,
  },
  user: {
    placement: "end",
    avatar: <Avatar icon={<UserOutlined />} />,
  },
};

export default function AIChat() {
  const [input, setInput] = useState("");
  const provider = useMemo(() => createAIERPChatProvider(), []);

  const { onRequest, messages, isRequesting, abort } = useXChat<
    ChatMessage,
    ChatMessage,
    ChatRequestParams
  >({
    provider,
    defaultMessages: [
      { message: { role: "assistant", content: WELCOME_MESSAGE, isWelcome: true } },
    ],
    requestPlaceholder: { role: "assistant", content: "" },
    requestFallback: (_params, { error, messageInfo }) => {
      if (error.name === "AbortError") {
        const partial = (messageInfo?.message as ChatMessage | undefined)?.content;
        return { role: "assistant", content: partial || ABORTED_MESSAGE };
      }
      return { role: "assistant", content: FALLBACK_MESSAGE };
    },
  });

  const sendQuery = (query: string) => {
    const text = query.trim();
    if (!text || isRequesting) return;
    onRequest({ message: text });
    setInput("");
  };

  return (
    <div
      style={{
        maxWidth: 800,
        margin: "0 auto",
        height: "calc(100vh - 200px)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Prompts
        items={QUICK_PROMPTS.map((prompt) => ({
          key: prompt,
          label: prompt,
          icon: <ThunderboltOutlined />,
          disabled: isRequesting,
        }))}
        onItemClick={({ data }) => sendQuery(String(data.label))}
        styles={{ list: { marginBottom: 12 } }}
      />
      <div style={{ flex: 1, overflowY: "auto", marginBottom: 16 }}>
        <Bubble.List
          role={BUBBLE_ROLES}
          items={messages.map(({ id, message, status }) => ({
            key: id,
            role: message.role,
            content: message.content,
            loading: status === "loading",
          }))}
        />
      </div>
      <Sender
        value={input}
        onChange={setInput}
        onSubmit={sendQuery}
        onCancel={abort}
        loading={isRequesting}
        placeholder="输入你的问题，按 Enter 发送..."
        autoSize={{ minRows: 2, maxRows: 4 }}
      />
    </div>
  );
}
