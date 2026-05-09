import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Space, Select, Switch, message, Spin } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getOpportunities, batchUpdateOpportunities } from "../../api";
import PipelineBoard from "../../components/sales/PipelineBoard";
import type { Opportunity, OpportunityAI } from "../../types";

export default function OpportunityList() {
  const [data, setData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, OpportunityAI>>({});
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page_size: 100 };
      if (status) params.status = status;
      if (stage) params.stage = stage;
      if (includeAi) params.include_ai = true;
      const resp = await getOpportunities(params);
      const list = resp.data.data.list || [];
      setData(list);
      if (includeAi) {
        setAiMap(
          (resp.data.data as unknown as Record<string, unknown>).ai as Record<number, OpportunityAI> || {}
        );
      } else {
        setAiMap({});
      }
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status, stage, includeAi]);

  return (
    <div>
      {/* Toolbar */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/opportunities/new")}>
          新增商机
        </Button>

        <Select
          placeholder="状态筛选"
          allowClear
          style={{ width: 120 }}
          value={status}
          onChange={(v) => {
            setStatus(v);
          }}
          options={[
            { value: "active", label: "活跃" },
            { value: "won", label: "已赢单" },
            { value: "lost", label: "已丢单" },
          ]}
        />

        <Select
          placeholder="阶段筛选"
          allowClear
          style={{ width: 120 }}
          value={stage}
          onChange={(v) => {
            setStage(v);
          }}
          options={[
            { value: "lead", label: "初步接触" },
            { value: "qualified", label: "已确认" },
            { value: "proposal", label: "报价中" },
            { value: "negotiation", label: "谈判" },
          ]}
        />

        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      {/* Kanban Board */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : (
        <PipelineBoard
          opportunities={data}
          aiMap={aiMap}
          loading={loading}
          onRefresh={load}
        />
      )}
    </div>
  );
}
