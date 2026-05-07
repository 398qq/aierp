import { useState, useRef, useEffect } from "react";
import { Input, Button, Card, Typography, Space, Spin } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { aiChat } from "../../api";

const { TextArea } = Input;
const { Paragraph } = Typography;

interface Message {
  role: "user" | "assistant";
  content: string;
}

const QUICK_PROMPTS = [
  "本月销售概览",
  "高价值客户分析",
  "流失风险预警",
  "库存优化建议",
  "销售目标进度",
  "近期跟进建议",
];

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

  const sendQuery = async (query: string) => {
    if (!query.trim() || loading) return;
    const userMsg: Message = { role: "user", content: query.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await aiChat(userMsg.content);
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

  const handleSend = () => sendQuery(input);
  const handlePromptClick = (prompt: string) => sendQuery(prompt);

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", height: "calc(100vh - 200px)", display: "flex", flexDirection: "column" }}>
      <div style={{ marginBottom: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
        {QUICK_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => handlePromptClick(prompt)}
            disabled={loading}
          >
            {prompt}
          </Button>
        ))}
      </div>
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
                  maxWidth: "75%",
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
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="输入你的问题，按 Enter 发送..."
          autoSize={{ minRows: 2, maxRows: 4 }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} style={{ height: "auto" }}>
          发送
        </Button>
      </Space.Compact>
    </div>
  );
}
