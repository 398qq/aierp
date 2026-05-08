import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Input, Select, message, Popconfirm, Modal, Switch } from "antd";
import { PlusOutlined, DeleteOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { getOpportunities, batchDeleteOpportunities, batchUpdateOpportunities, deleteOpportunity } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { Opportunity } from "../../types";

const STAGE_TAGS: Record<string, string> = {
  lead: "blue", qualified: "cyan", proposal: "orange", negotiation: "purple", closed_won: "green", closed_lost: "red",
};

export default function OpportunityList() {
  const [data, setData] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [stage, setStage] = useState<string | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { risk_level: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (stage) params.stage = stage;
      if (includeAi) params.include_ai = true;
      const resp = await getOpportunities(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      if (includeAi) setAiMap((resp.data.data as unknown as Record<string, unknown>).ai as Record<string, { risk_level: string; flag?: string }> || {});
      else setAiMap({});
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, stage, includeAi]);

  const handleBatchDelete = async () => {
    try { await batchDeleteOpportunities(selected); message.success("已批量删除"); setSelected([]); load(); } catch { message.error("删除失败"); }
  };

  const handleBatchUpdate = async (s: string) => {
    try { await batchUpdateOpportunities(selected, s); message.success(`已批量更新为 ${s}`); setSelected([]); load(); } catch { message.error("更新失败"); }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/opportunities/new")}>新增商机</Button>
        {selected.length > 0 && (
          <>
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}><Button danger icon={<DeleteOutlined />}>删除({selected.length})</Button></Popconfirm>
            <Select placeholder="批量更新阶段" style={{ width: 140 }} onChange={(v) => handleBatchUpdate(v)} options={[
              { value: "lead", label: "初步接触" }, { value: "qualified", label: "已确认" },
              { value: "proposal", label: "报价中" }, { value: "negotiation", label: "谈判" },
              { value: "closed_won", label: "赢单" }, { value: "closed_lost", label: "丢单" },
            ]} />
          </>
        )}
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "active", label: "活跃" }, { value: "won", label: "已赢单" }, { value: "lost", label: "已丢单" },
        ]} />
        <Select placeholder="阶段筛选" allowClear style={{ width: 120 }} value={stage} onChange={setStage} options={[
          { value: "lead", label: "初步接触" }, { value: "qualified", label: "已确认" },
          { value: "proposal", label: "报价中" }, { value: "negotiation", label: "谈判" },
        ]} />
        <Space>
          <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
          <span style={{ fontSize: 13 }}>AI</span>
        </Space>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        columns={[
          { title: "标题", dataIndex: "title", ellipsis: true, render: (v: string, r: Opportunity) => <a onClick={() => navigate(`/sales/opportunities/${r.id}`)}>{v}</a> },
          { title: "金额", dataIndex: "amount", width: 120, render: (v: number | null) => v ? `¥${v.toLocaleString()}` : "-" },
          { title: "阶段", dataIndex: "stage", width: 100, render: (v: string) => <Tag color={STAGE_TAGS[v] || "default"}>{v || "-"}</Tag> },
          { title: "赢单率", dataIndex: "win_probability", width: 80, render: (v: number | null) => v !== null ? `${v}%` : "-" },
          { title: "预计成交", dataIndex: "expected_close_date", width: 110, render: (v: string | null) => v?.slice(0, 10) || "-" },
          { title: "负责人", dataIndex: "assigned_to", width: 90 },
          {
            title: "AI", width: 90,
            render: (_: unknown, r: Opportunity) => <AIInlineBadge riskLevel={aiMap[r.id]?.risk_level} flag={aiMap[r.id]?.flag} />,
          },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: Opportunity) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/opportunities/${r.id}`)}>详情</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteOpportunity(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  );
}
