import { useEffect, useState, useRef, DragEvent } from "react";
import { Card, Tag, Typography, message, Spin, Dropdown, Button, Tooltip } from "antd";
import { PlusOutlined, MoreOutlined, UserOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getOpportunities, updateOpportunity, scoreOpportunity } from "../../api";
import type { Opportunity, OpportunityScoreResult } from "../../types";

interface OppWithCustomer extends Opportunity {
  customer_name?: string;
}
import dayjs from "dayjs";

const { Text, Title } = Typography;

const STAGES = [
  { key: "lead", label: "线索", color: "#8c8c8c" },
  { key: "qualified", label: "初步接触", color: "#1677ff" },
  { key: "proposal", label: "需求确认", color: "#fa8c16" },
  { key: "negotiation", label: "方案报价", color: "#722ed1" },
  { key: "won", label: "成交", color: "#52c41a" },
  { key: "lost", label: "失败", color: "#ff4d4f" },
];

interface DragState {
  oppId: number;
  fromStage: string;
}

export default function SalesPipeline() {
  const [opportunities, setOpportunities] = useState<OppWithCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [drag, setDrag] = useState<DragState | null>(null);
  const dragOverCol = useRef<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [scores, setScores] = useState<Record<number, OpportunityScoreResult>>({});
  const [scoringId, setScoringId] = useState<number | null>(null);

  const fetchOpps = async () => {
    try {
      const res = await getOpportunities({ page_size: 500 });
      type OppPage = { list: Opportunity[]; total: number; page: number; page_size: number };
      const list = ((res.data as { data?: OppPage })?.data?.list ?? []) as OppWithCustomer[];
      setOpportunities(list);
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOpps(); }, []);

  const byStage = (stage: string) =>
    opportunities.filter((o) => o.stage === stage);

  const handleDragStart = (e: DragEvent, opp: Opportunity) => {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(opp.id));
    setDrag({ oppId: opp.id, fromStage: opp.stage });
    dragOverCol.current = null;
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>, stage: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    dragOverCol.current = stage;
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>, toStage: string) => {
    e.preventDefault();
    if (!drag || drag.fromStage === toStage) { setDrag(null); return; }

    const { oppId, fromStage } = drag;
    setSaving(true);
    try {
      await updateOpportunity(oppId, { stage: toStage });
      setOpportunities((prev) =>
        prev.map((o) => (o.id === oppId ? { ...o, stage: toStage } : o))
      );
      message.success(`移动到「${STAGES.find((s) => s.key === toStage)?.label}」`);
    } catch {
      message.error("移动失败");
    } finally {
      setSaving(false);
      setDrag(null);
    }
  };

  const handleDragEnd = () => setDrag(null);

  const handleScore = async (oppId: number) => {
    setScoringId(oppId);
    try {
      const res = await scoreOpportunity(oppId);
      const data = (res as { data?: { data?: OpportunityScoreResult } })?.data?.data;
      if (data) setScores((prev) => ({ ...prev, [oppId]: data }));
      message.success("AI 评分完成");
    } catch { message.error("AI 评分失败"); }
    finally { setScoringId(null); }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: "16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>销售 Pipeline 看板</Title>
        <Tag color="blue">{opportunities.length} 个机会</Tag>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${STAGES.length}, minmax(220px, 1fr))`,
        gap: 12,
        overflowX: "auto",
        minHeight: "calc(100vh - 160px)",
      }}>
        {STAGES.map(({ key, label, color }) => (
          <div
            key={key}
            onDragOver={(e) => handleDragOver(e, key)}
            onDragLeave={() => { dragOverCol.current = null; }}
            onDrop={(e) => handleDrop(e, key)}
            style={{
              background: dragOverCol.current === key ? `${color}15` : "#f5f5f5",
              borderRadius: 8,
              padding: "8px",
              minHeight: 400,
              transition: "background 0.15s",
              border: dragOverCol.current === key ? `2px solid ${color}` : "2px solid transparent",
            }}
          >
            {/* Column header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, padding: "4px 4px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
                <Text strong style={{ fontSize: 13 }}>{label}</Text>
                <Tag style={{ marginLeft: 4, fontSize: 11 }}>{byStage(key).length}</Tag>
              </div>
              <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => {/* 新建 */}} />
            </div>

            {/* Cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {byStage(key).map((opp) => (
                <OppCard
                  key={opp.id}
                  opp={opp}
                  isDragging={drag?.oppId === opp.id}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                  score={scores[opp.id]}
                  scoring={scoringId === opp.id}
                  onScore={handleScore}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {saving && (
        <div style={{
          position: "fixed", top: 80, right: 24, zIndex: 1000,
          background: "#fff", borderRadius: 8, padding: "8px 16px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)", display: "flex", alignItems: "center", gap: 8,
        }}>
          <Spin size="small" /> 保存中...
        </div>
      )}
    </div>
  );
}

function OppCard({
  opp, isDragging, onDragStart, onDragEnd, score, scoring, onScore,
}: {
  opp: OppWithCustomer;
  isDragging: boolean;
  onDragStart: (e: DragEvent, o: OppWithCustomer) => void;
  onDragEnd: () => void;
  score?: OpportunityScoreResult;
  scoring: boolean;
  onScore: (oppId: number) => void;
}) {
  const probColor = opp.probability
    ? opp.probability >= 80 ? "#52c41a"
    : opp.probability >= 50 ? "#fa8c16"
    : "#8c8c8c"
    : "#8c8c8c";

  const stageColor: Record<string, string> = {
    lead: "#8c8c8c", qualified: "#1677ff", proposal: "#fa8c16",
    negotiation: "#722ed1", won: "#52c41a", lost: "#ff4d4f",
  };

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, opp)}
      onDragEnd={onDragEnd}
      style={{
        background: "#fff",
        borderRadius: 6,
        padding: "10px 12px",
        cursor: "grab",
        boxShadow: isDragging ? "0 8px 20px rgba(0,0,0,0.2)" : "0 1px 3px rgba(0,0,0,0.08)",
        opacity: isDragging ? 0.5 : 1,
        transform: isDragging ? "rotate(2deg)" : "none",
        borderLeft: `3px solid ${stageColor[opp.stage] ?? "#8c8c8c"}`,
        userSelect: "none",
      }}
    >
      {/* Title row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <Text strong style={{ fontSize: 13, lineHeight: 1.3, flex: 1 }}>{opp.name}</Text>
        <Dropdown menu={{
          items: [
            { key: "view", label: "查看详情", onClick: () => window.location.href = `/sales/opportunities/${opp.id}` },
            { key: "edit", label: "编辑", onClick: () => window.location.href = `/sales/opportunities/${opp.id}/edit` },
          ],
        }}>
          <Button type="text" size="small" icon={<MoreOutlined />} style={{ flexShrink: 0 }} onClick={(e) => e.stopPropagation()} />
        </Dropdown>
      </div>

      {/* Customer */}
      {opp.customer_name && (
        <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 4 }}>
          <UserOutlined style={{ fontSize: 11, color: "#8c8c8c" }} />
          <Text type="secondary" style={{ fontSize: 12 }}>{opp.customer_name}</Text>
        </div>
      )}

      {/* Amount */}
      {opp.amount != null && opp.amount > 0 && (
        <Text style={{ fontSize: 13, fontWeight: 600, color: "#fa8c16" }}>
          ¥{opp.amount.toLocaleString()}
        </Text>
      )}

      {/* Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
        {opp.probability != null ? (
          <Tooltip title={`赢单概率 ${opp.probability}%`}>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 40, height: 4, background: "#f0f0f0", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ width: `${opp.probability}%`, height: "100%", background: probColor, borderRadius: 2 }} />
              </div>
              <Text style={{ fontSize: 11, color: probColor }}>{opp.probability}%</Text>
            </div>
          </Tooltip>
        ) : <span />}

        {opp.expected_close_date && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {dayjs(opp.expected_close_date).format("MM/DD")}
          </Text>
        )}

        <Tooltip title="AI 评分">
          <Button type="text" size="small" icon={<ThunderboltOutlined />}
            loading={scoring}
            onClick={(e) => { e.stopPropagation(); onScore(opp.id); }}
            style={{ color: score ? "#722ed1" : "#8c8c8c" }}
          />
        </Tooltip>
      </div>

      {/* AI Score */}
      {score && (
        <div style={{ marginTop: 4, padding: "4px 6px", background: "#f9f0ff", borderRadius: 4 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Tag color={score.risk_level === "高" ? "red" : score.risk_level === "中" ? "orange" : "green"}
              style={{ fontSize: 10, lineHeight: "16px" }}>
              {score.risk_level}风险
            </Tag>
            <Text strong style={{ fontSize: 12, color: "#722ed1" }}>AI {score.score}分</Text>
          </div>
          {score.next_best_action && (
            <Text style={{ fontSize: 11, color: "#666" }}>{score.next_best_action}</Text>
          )}
        </div>
      )}
    </div>
  );
}
