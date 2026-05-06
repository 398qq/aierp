import { Card, Descriptions, Typography } from "antd";
import { useAuthStore } from "../../store/auth";

const { Title } = Typography;

export default function Settings() {
  const username = useAuthStore((s) => s.username);

  return (
    <div>
      <Title level={4}>系统设置</Title>
      <Card style={{ maxWidth: 600 }}>
        <Descriptions title="账户信息" column={1}>
          <Descriptions.Item label="用户名">{username}</Descriptions.Item>
          <Descriptions.Item label="角色">管理员</Descriptions.Item>
          <Descriptions.Item label="AI 分析模型">
            Qwen/Qwen2.5-7B-Instruct (RFM/流失/建议)
          </Descriptions.Item>
          <Descriptions.Item label="AI 助手模型">
            Qwen/Qwen2.5-7B-Instruct (Chat)
          </Descriptions.Item>
          <Descriptions.Item label="嵌入模型">
            BAAI/bge-large-zh-v1.5
          </Descriptions.Item>
          <Descriptions.Item label="数据库">PostgreSQL 16 + pgvector</Descriptions.Item>
          <Descriptions.Item label="后端框架">FastAPI + SQLAlchemy 2.0</Descriptions.Item>
          <Descriptions.Item label="前端框架">React 19 + TypeScript + Ant Design</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
