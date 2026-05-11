import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, message } from "antd";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getTicket } from "../../api";
import type { Ticket } from "../../types";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  open: { color: "blue", label: "待处理" },
  in_progress: { color: "orange", label: "处理中" },
  resolved: { color: "green", label: "已解决" },
  closed: { color: "default", label: "已关闭" },
};

const PRIORITY_MAP: Record<string, { color: string; label: string }> = {
  low: { color: "green", label: "低" },
  medium: { color: "orange", label: "中" },
  high: { color: "red", label: "高" },
};

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getTicket(Number(id))
      .then((r) => setTicket(r.data.data))
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!ticket) return <Empty description="工单不存在" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tickets")}>返回</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/tickets/${ticket.id}/edit`)}>编辑</Button>
      </Space>

      <Card title={ticket.title || `#${ticket.id}`}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="工单号">{ticket.ticket_no || `-`}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={STATUS_MAP[ticket.status]?.color}>{STATUS_MAP[ticket.status]?.label || ticket.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="优先级">
            <Tag color={PRIORITY_MAP[ticket.priority]?.color}>{PRIORITY_MAP[ticket.priority]?.label || ticket.priority}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="分类">{ticket.category || "-"}</Descriptions.Item>
          <Descriptions.Item label="处理人">{ticket.assigned_to || "-"}</Descriptions.Item>
          <Descriptions.Item label="客户ID">{ticket.customer_id || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{ticket.created_at?.slice(0, 19).replace("T", " ") || "-"}</Descriptions.Item>
          <Descriptions.Item label="解决时间">{ticket.resolved_at?.slice(0, 19).replace("T", " ") || "-"}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{ticket.description || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{ticket.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
