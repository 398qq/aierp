import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, Card, Popconfirm, Progress, Space, Tag, Tooltip, Typography, message } from "antd";
import { DeleteOutlined, EditOutlined, EyeOutlined, FileTextOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import AIInlineBadge from "./AIInlineBadge";
import type { Opportunity, OpportunityAI } from "../../types";
import { deleteOpportunity } from "../../api";
import { money, shortDate } from "../../pages/sales/salesUi";

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

  const winProbability = Number(opportunity.win_probability || 0);

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        style={{
          marginBottom: 10,
          cursor: "grab",
          borderLeft: `4px solid ${STAGE_TAGS[opportunity.stage || "lead"] || "#d9d9d9"}`,
          borderRadius: 6,
        }}
        bodyStyle={{ padding: 12 }}
      >
        <Space style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
          <Typography.Text
            strong
            ellipsis
            style={{ maxWidth: 180, display: "block", cursor: "pointer" }}
            onClick={() => navigate(`/sales/opportunities/${opportunity.id}`)}
          >
            {opportunity.title}
          </Typography.Text>
          {aiData && <AIInlineBadge riskLevel={aiData.risk_level} />}
        </Space>

        <Space direction="vertical" size={4} style={{ width: "100%" }}>
          <Space style={{ display: "flex", justifyContent: "space-between" }}>
            <Text type="secondary" style={{ fontSize: 12 }}>预计金额</Text>
            <Typography.Text strong>{money(opportunity.amount)}</Typography.Text>
          </Space>
          <Progress
            percent={winProbability}
            size="small"
            showInfo={false}
            strokeColor={winProbability >= 60 ? "#52c41a" : winProbability >= 30 ? "#faad14" : "#1677ff"}
          />
          <Space style={{ display: "flex", justifyContent: "space-between" }}>
            <Text type="secondary" style={{ fontSize: 12 }}>赢率 {winProbability}%</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{shortDate(opportunity.expected_close_date)}</Text>
          </Space>
        </Space>

        <Space style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }} ellipsis>{opportunity.source || "未记录来源"}</Text>
          {opportunity.assigned_to && (
            <Tooltip title="负责人">
              <Tag style={{ margin: 0 }}>{opportunity.assigned_to}</Tag>
            </Tooltip>
          )}
        </Space>

        <Space size={4} style={{ marginTop: 10 }}>
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/opportunities/${opportunity.id}`)} />
          </Tooltip>
          <Tooltip title="编辑商机">
            <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/sales/opportunities/${opportunity.id}/edit`)} />
          </Tooltip>
          <Tooltip title="新建报价">
            <Button
              size="small"
              type="primary"
              icon={<FileTextOutlined />}
              onClick={() => navigate(`/sales/quotations/new?customer_id=${opportunity.customer_id}&opportunity_id=${opportunity.id}`)}
            />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={handleDelete}>
            <Button size="small" danger type="text" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      </Card>
    </div>
  );
}
