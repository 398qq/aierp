import { useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { Empty, Typography, Space, Statistic, message } from "antd";
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
  const { setNodeRef, isOver } = useDroppable({ id: stageKey });
  const totalAmount = opportunities.reduce((sum, o) => sum + (o.amount || 0), 0);
  const weightedAmount = opportunities.reduce((sum, o) => sum + Number(o.amount || 0) * Number(o.win_probability || 0) / 100, 0);

  return (
    <div
      ref={setNodeRef}
      style={{
        background: isOver ? "#f0f7ff" : "#f7f8fa",
        border: `1px solid ${isOver ? "#91caff" : "#edf0f3"}`,
        borderRadius: 8,
        padding: 10,
        minHeight: 520,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 10,
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
              background: "#fff",
              border: "1px solid #e8ebef",
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
        <Statistic
          title="金额"
          value={totalAmount}
          prefix="¥"
          valueStyle={{ fontSize: 14, lineHeight: 1.2 }}
          formatter={(v) => (Number(v) === 0 ? "0" : Number(v).toLocaleString())}
        />
        <Statistic
          title="加权"
          value={weightedAmount}
          prefix="¥"
          valueStyle={{ fontSize: 14, lineHeight: 1.2 }}
          formatter={(v) => (Number(v) === 0 ? "0" : Number(v).toLocaleString())}
        />
      </div>

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
        <div style={{ flex: 1, display: "grid", placeItems: "center", minHeight: 160 }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无商机" />
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
      <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 16 }}>
        {STAGES.map(({ key, label, color }) => (
          <div key={key} style={{ flex: "0 0 260px", minWidth: 260 }}>
            <PipelineColumn
              stageKey={key}
              label={label}
              color={color}
              opportunities={opportunitiesByStage[key] || []}
              aiMap={aiMap}
              onRefresh={onRefresh}
            />
          </div>
        ))}
      </div>

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
