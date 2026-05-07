import { useState, useRef, useEffect } from "react";
import { Input, Button, Card, Typography, Space, Spin } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "你好！我是 AIERP 智能助手。我可以帮你：\n\n• 分析客户 RFM 价值\n• 预测客户流失风险\n• 给出跟进建议\n• 解答销售问题\n\n请直接输入你的问题。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const token = useAuthStore.getState().token;
      const resp = await fetch(`/api/v1/ai/chat?query=${encodeURIComponent(userMsg.content)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const reader = resp.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let assistantContent = "";

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              assistantContent += parsed.content || "";
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { role: "assistant", content: assistantContent };
                return copy;
              });
            } catch {
              // partial chunk
            }
          }
        }
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "抱歉，AI 服务暂时不可用。" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", height: "calc(100vh - 200px)", display: "flex", flexDirection: "column" }}>
      <Card
        title={<><RobotOutlined /> AI 助手</>}
        style={{ flex: 1, overflow: "auto", marginBottom: 16 }}
        bodyStyle={{ padding: 12 }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <Card
                size="small"
                style={{
                  maxWidth: "80%",
                  background: msg.role === "user" ? "#1677ff" : "#f0f0f0",
                  color: msg.role === "user" ? "#fff" : "#000",
                }}
              >
                <Space align="start">
                  {msg.role === "assistant" && <RobotOutlined />}
                  <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.content}</Paragraph>
                  {msg.role === "user" && <UserOutlined />}
                </Space>
              </Card>
            </div>
          ))}
          {loading && <Spin />}
          <div ref={messagesEndRef} />
        </div>
      </Card>
      <Space.Compact style={{ width: "100%" }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder="输入你的问题，按 Enter 发送..."
          autoSize={{ minRows: 2, maxRows: 4 }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={send} loading={loading} style={{ height: "auto" }}>
          发送
        </Button>
      </Space.Compact>
    </div>
  );
}
