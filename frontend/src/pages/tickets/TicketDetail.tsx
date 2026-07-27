import { useEffect, useState } from "react";
import { useParams, useNavigate } from "@/router";
import { Card, Descriptions, Button, Space, Tag, Spin, Alert, Empty, message } from "antd";
import { StatusTag, type StatusTone } from "../../ui";
import { ArrowLeftOutlined, EditOutlined } from "@ant-design/icons";
import { getTicket } from "../../api";
import type { Ticket } from "../../types";

const STATUS_MAP: Record<string, { tone: StatusTone; label: string }> = {
  open: { tone: "info", label: "待处理" },
  in_progress: { tone: "warning", label: "处理中" },
  resolved: { tone: "success", label: "已解决" },
  closed: { tone: "neutral", label: "已关闭" },
};

const PRIORITY_MAP: Record<string, { tone: StatusTone; label: string }> = {
  low: { tone: "success", label: "低" },
  medium: { tone: "warning", label: "中" },
  high: { tone: "danger", label: "高" },
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
            <StatusTag status={ticket.status} tone={STATUS_MAP[ticket.status]?.tone || "neutral"} label={STATUS_MAP[ticket.status]?.label || ticket.status} />
          </Descriptions.Item>
          <Descriptions.Item label="优先级">
            <StatusTag status={ticket.priority} tone={PRIORITY_MAP[ticket.priority]?.tone || "neutral"} label={PRIORITY_MAP[ticket.priority]?.label || ticket.priority} />
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
