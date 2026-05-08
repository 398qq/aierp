import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm, Row, Col, Card, Statistic, Progress } from "antd";
import { PlusOutlined, AimOutlined } from "@ant-design/icons";
import { getTargets, deleteTarget, getTargetStats } from "../../api";
import type { SalesTarget } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  active: { color: "blue", label: "进行中" }, completed: { color: "green", label: "已完成" }, cancelled: { color: "default", label: "已取消" },
};
const TYPE: Record<string, string> = { monthly: "月度", quarterly: "季度", annual: "年度" };

export default function TargetList() {
  const [data, setData] = useState<SalesTarget[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [stats, setStats] = useState<{ total_target: number; total_actual: number; achievement_pct: number }>({ total_target: 0, total_actual: 0, achievement_pct: 0 });
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      const [resp, s] = await Promise.all([getTargets(params), getTargetStats()]);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setStats(s.data.data);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status]);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="总目标" value={stats.total_target} prefix="¥" /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="已完成" value={stats.total_actual} prefix="¥" valueStyle={{ color: "#52c41a" }} /></Card></Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="达成率" value={stats.achievement_pct} suffix="%" />
            <Progress percent={stats.achievement_pct} size="small" strokeColor={stats.achievement_pct >= 80 ? "#52c41a" : stats.achievement_pct >= 50 ? "#faad14" : "#ff4d4f"} />
          </Card>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/targets/new")}>新增目标</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "active", label: "进行中" }, { value: "completed", label: "已完成" },
        ]} />
      </Space>

      <Table
        rowKey="id" loading={loading} dataSource={data}
        columns={[
          { title: "ID", dataIndex: "id", width: 60 },
          { title: "类型", dataIndex: "target_type", width: 80, render: (v: string) => TYPE[v] || v },
          { title: "目标金额", dataIndex: "target_amount", width: 130, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "实际金额", dataIndex: "actual_amount", width: 130, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "达成率", width: 100, render: (_: unknown, r: SalesTarget) => <Progress percent={Math.round(r.target_amount > 0 ? r.actual_amount / r.target_amount * 100 : 0)} size="small" /> },
          { title: "期间", width: 180, render: (_: unknown, r: SalesTarget) => `${r.period_start?.slice(0, 10) || "?"} ~ ${r.period_end?.slice(0, 10) || "?"}` },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: SalesTarget) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/targets/${r.id}/edit`)}>编辑</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteTarget(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
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
