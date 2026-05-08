import { useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Col, Row, Typography, Space, Statistic, message } from "antd";
import { batchUpdateOpportunities } from "../../api";
import OpportunityCard from "./OpportunityCard";
import type { Opportunity, OpportunityAI } from "../../types";

export const STAGES = [
  { key: "lead", label: "初步接触", color: "#1677ff" },
  { key: "qualified", label: "已确认", color: "#13c2c2" },
  { key: "proposal", label: "报价中", color: "#fa8c16" },
  { key: "negotiation", label: "谈判", color: "#722ed1" },
  { key: "closed_won", label: "赢单", color: "#52c41a" },
  { key: "closed_lost", label: "丢单", color: "#f5222d" },
] as const;

export type StageKey = typeof STAGES[number]["key"];

interface ColumnProps {
  stageKey: string;
  label: string;
  color: string;
  opportunities: Opportunity[];
  aiMap: Record<number, OpportunityAI>;
  onRefresh: () => void;
}

function PipelineColumn({ stageKey, label, color, opportunities, aiMap, onRefresh }: ColumnProps) {
  const totalAmount = opportunities.reduce((sum, o) => sum + (o.amount || 0), 0);

  return (
    <div
      style={{
        background: "#f5f5f5",
        borderRadius: 8,
        padding: "8px 8px 0",
        minHeight: 200,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Column header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
          padding: "4px 4px",
        }}
      >
        <Space>
          <span
            style={{
              display: "inline-block",
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: color,
            }}
          />
          <Typography.Text strong>{label}</Typography.Text>
          <span
            style={{
              background: "#e6e6e6",
              borderRadius: 10,
              padding: "0 6px",
              fontSize: 12,
              color: "#666",
            }}
          >
            {opportunities.length}
          </span>
        </Space>
      </div>

      {/* Column stats */}
      <div style={{ marginBottom: 8, padding: "0 4px" }}>
        <Statistic
          title={null}
          value={totalAmount}
          prefix="¥"
          valueStyle={{ fontSize: 14 }}
          formatter={(v) => (Number(v) === 0 ? "—" : Number(v).toLocaleString())}
        />
      </div>

      {/* Cards */}
      <SortableContext items={opportunities.map((o) => o.id)} strategy={verticalListSortingStrategy}>
        {opportunities.map((opp) => (
          <OpportunityCard
            key={opp.id}
            opportunity={opp}
            aiData={aiMap[opp.id]}
            onRefresh={onRefresh}
          />
        ))}
      </SortableContext>

      {opportunities.length === 0 && (
        <div style={{ textAlign: "center", color: "#bbb", padding: "20px 0", fontSize: 13 }}>
          暂无商机
        </div>
      )}
    </div>
  );
}

interface Props {
  opportunities: Opportunity[];
  aiMap: Record<number, OpportunityAI>;
  loading: boolean;
  onRefresh: () => void;
}

export default function PipelineBoard({ opportunities, aiMap, loading, onRefresh }: Props) {
  const [activeId, setActiveId] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const opportunitiesByStage = STAGES.reduce<Record<string, Opportunity[]>>((acc, s) => {
    acc[s.key] = opportunities.filter((o) => o.stage === s.key);
    return acc;
  }, {});

  const activeOpportunity = activeId != null ? opportunities.find((o) => o.id === activeId) : null;

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);

      if (!over) return;

      const draggedOpp = opportunities.find((o) => o.id === active.id);
      if (!draggedOpp) return;

      // Determine target stage: over.id could be another card id or a column id
      let targetStage: string | null = null;

      // Check if over.id is a known opportunity id in a different stage
      const overOpp = opportunities.find((o) => o.id === over.id);
      if (overOpp) {
        targetStage = overOpp.stage;
      } else {
        // over.id might be a stage key (column drop zone)
        targetStage = over.id as string;
      }

      if (!targetStage || targetStage === draggedOpp.stage) return;

      try {
        await batchUpdateOpportunities([draggedOpp.id], targetStage);
        message.success(`已移动至 ${STAGES.find((s) => s.key === targetStage)?.label}`);
        onRefresh();
      } catch {
        message.error("移动失败");
      }
    },
    [opportunities, onRefresh]
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <Row gutter={[12, 12]} style={{ overflowX: "auto", paddingBottom: 16 }}>
        {STAGES.map(({ key, label, color }) => (
          <Col key={key} xs={24} sm={12} md={8} lg={6} xl={4}>
            <PipelineColumn
              stageKey={key}
              label={label}
              color={color}
              opportunities={opportunitiesByStage[key] || []}
              aiMap={aiMap}
              onRefresh={onRefresh}
            />
          </Col>
        ))}
      </Row>

      <DragOverlay>
        {activeOpportunity && (
          <div style={{ opacity: 0.8 }}>
            <OpportunityCard
              opportunity={activeOpportunity}
              aiData={aiMap[activeOpportunity.id]}
              onRefresh={onRefresh}
            />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
