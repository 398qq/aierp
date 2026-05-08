import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, Typography, Space, Tag, Tooltip, Popconfirm, Button, message } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import AIInlineBadge from "./AIInlineBadge";
import type { Opportunity, OpportunityAI } from "../../types";
import { deleteOpportunity } from "../../api";

const { Text } = Typography;

interface Props {
  opportunity: Opportunity;
  aiData?: OpportunityAI;
  onRefresh: () => void;
}

const STAGE_TAGS: Record<string, string> = {
  lead: "blue",
  qualified: "cyan",
  proposal: "orange",
  negotiation: "purple",
  closed_won: "green",
  closed_lost: "red",
};

export default function OpportunityCard({ opportunity, aiData, onRefresh }: Props) {
  const navigate = useNavigate();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: opportunity.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleDelete = async () => {
    try {
      await deleteOpportunity(opportunity.id);
      message.success("已删除");
      onRefresh();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        style={{
          marginBottom: 8,
          cursor: "grab",
          borderLeft: `3px solid ${STAGE_TAGS[opportunity.stage || "lead"] || "#ccc"}`,
        }}
        bodyStyle={{ padding: 12 }}
      >
        {/* Header: title + AI badge */}
        <Space style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
          <Typography.Text
            strong
            ellipsis
            style={{ maxWidth: 160, display: "block" }}
            onClick={() => navigate(`/sales/opportunities/${opportunity.id}`)}
          >
            {opportunity.title}
          </Typography.Text>
          {aiData && <AIInlineBadge riskLevel={aiData.risk_level} />}
        </Space>

        {/* Amount + Win prob */}
        <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            {opportunity.amount != null ? `¥${opportunity.amount.toLocaleString()}` : "—"}
          </Text>
          {opportunity.win_probability != null && (
            <Tag color={opportunity.win_probability >= 50 ? "green" : "orange"} style={{ margin: 0 }}>
              {opportunity.win_probability}%
            </Tag>
          )}
        </Space>

        {/* Expected close date + owner */}
        <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {opportunity.expected_close_date
              ? opportunity.expected_close_date.slice(0, 10)
              : "—"}
          </Text>
          {opportunity.assigned_to && (
            <Tooltip title="负责人">
              <Tag style={{ margin: 0 }}>{opportunity.assigned_to}</Tag>
            </Tooltip>
          )}
        </Space>

        {/* Actions */}
        <Space size="small" style={{ marginTop: 6 }}>
          <Button size="small" onClick={() => navigate(`/sales/opportunities/${opportunity.id}`)}>
            详情
          </Button>
          <Popconfirm title="确定删除?" onConfirm={handleDelete}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      </Card>
    </div>
  );
}
