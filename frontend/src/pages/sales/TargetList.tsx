import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Dropdown, Modal, Popconfirm, Progress, Select, Space, Table, Tag, Typography, message } from "antd";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import type { MenuProps } from "antd";
import { AimOutlined, DeleteOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { getTargets, deleteTarget, getTargetStats, getApiErrorMessage } from "../../api";
import type { SalesTarget } from "../../types";
import { ErpExportButton, MetricBand, SalesModuleShell, erpRowClass, money, statusDot, ERP_STATUS_DOT } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  active: { color: "blue", label: "进行中" }, completed: { color: "green", label: "已完成" }, cancelled: { color: "default", label: "已取消" },
};
const TYPE: Record<string, string> = { monthly: "月度", quarterly: "季度", annual: "年度" };

export default function TargetList() {
  const [data, setData] = useState<SalesTarget[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [status, setStatus] = useState<string | undefined>();
  const [stats, setStats] = useState<{ total_target: number; total_actual: number; achievement_pct: number }>({ total_target: 0, total_actual: 0, achievement_pct: 0 });
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (status) params.status = status;
      const [resp, s] = await Promise.all([getTargets(params), getTargetStats()]);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setStats(s.data.data);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载失败")); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, pageSize, status]);

  const exportData = useMemo(() =>
    data.map((r) => ({
      id: r.id,
      target_type: TYPE[r.target_type] || r.target_type,
      target_amount: r.target_amount,
      actual_amount: r.actual_amount,
      achievement: r.target_amount > 0 ? `${Math.round(r.actual_amount / r.target_amount * 100)}%` : "",
      period: `${r.period_start?.slice(0, 10) || ""} ~ ${r.period_end?.slice(0, 10) || ""}`,
      status: STATUS[r.status]?.label || r.status,
    })),
  [data]);

  return (
    <SalesModuleShell
      title="销售目标"
      subtitle="管理销售目标、实际达成和执行进度"
      activeKey="targets"
    >
      <MetricBand items={[
        { title: "总目标", value: stats.total_target, prefix: "¥", precision: 0 },
        { title: "已完成", value: stats.total_actual, prefix: "¥", precision: 0 },
        { title: "达成率", value: stats.achievement_pct, suffix: "%", precision: 1 },
      ]} />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/targets/new")}>新增目标</Button>
          <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
            { value: "active", label: "进行中" }, { value: "completed", label: "已完成" },
          ]} />
          <ErpExportButton
            data={exportData}
            columns={[
              { key: "id", title: "ID" },
              { key: "target_type", title: "类型" },
              { key: "target_amount", title: "目标金额" },
              { key: "actual_amount", title: "实际金额" },
              { key: "achievement", title: "达成率" },
              { key: "period", title: "期间" },
              { key: "status", title: "状态" },
            ]}
            filename="targets_export.csv"
          />
        </Space>
      </Card>

      <Card size="small" className="sales-erp-table-card">
        <Table
          rowKey="id" size="small" bordered loading={loading} dataSource={data}
          rowClassName={erpRowClass}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "#", width: 45, fixed: "left", render: (_: unknown, __: SalesTarget, index: number) => (page - 1) * 20 + index + 1 },
            {
              title: "类型", dataIndex: "target_type", width: 80, fixed: "left",
              render: (v: string) => (
                <div>
                  <div className="erp-cell-primary">{TYPE[v] || v}</div>
                </div>
              ),
            },
            { title: "目标金额", dataIndex: "target_amount", width: 130, align: "right", sorter: (a, b) => a.target_amount - b.target_amount, render: (v: number) => <Typography.Text strong>{money(v)}</Typography.Text> },
            { title: "实际金额", dataIndex: "actual_amount", width: 130, align: "right", sorter: (a, b) => a.actual_amount - b.actual_amount, render: (v: number) => <Typography.Text strong>{money(v)}</Typography.Text> },
            { title: "达成率", width: 100, render: (_: unknown, r: SalesTarget) => <Progress percent={Math.round(r.target_amount > 0 ? r.actual_amount / r.target_amount * 100 : 0)} size="small" /> },
            { title: "期间", width: 180, render: (_: unknown, r: SalesTarget) => `${r.period_start?.slice(0, 10) || "?"} ~ ${r.period_end?.slice(0, 10) || "?"}` },
            {
              title: "状态", dataIndex: "status", width: 90,
              sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
              render: (v: string) => (
                <>
                  {statusDot(ERP_STATUS_DOT[v] || "#d9d9d9")}
                  <StatusTag tone={STATUS[v]?.color}>{STATUS[v]?.label || v}</StatusTag>
                </>
              ),
            },
            {
              title: "操作", width: 60, fixed: "right",
              render: (_: unknown, r: SalesTarget) => {
                const items: MenuProps["items"] = [
                  { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/targets/${r.id}`) },
                  { key: "edit", icon: <EditOutlined />, label: "编辑", onClick: () => navigate(`/sales/targets/${r.id}/edit`) },
                  { type: "divider" as const },
                  { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                    Modal.confirm({ title: "确定删除?", content: `删除目标 #${r.id}？`, onOk: async () => {
                      try { await deleteTarget(r.id); message.success("已删除"); load(); } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
                    }});
                  }},
                ];
                return (
                  <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
                    <Button size="small" icon={<EllipsisOutlined />} type="text" />
                  </Dropdown>
                );
              },
            },
          ]}
          summary={(pageData: readonly SalesTarget[]) => {
            const targetAmt = pageData.reduce((s, r) => s + r.target_amount, 0);
            const actualAmt = pageData.reduce((s, r) => s + r.actual_amount, 0);
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}>合计</Table.Summary.Cell>
                <Table.Summary.Cell index={1}><Typography.Text strong>{pageData.length} 项</Typography.Text></Table.Summary.Cell>
                <Table.Summary.Cell index={2} align="right"><Typography.Text strong>{money(targetAmt)}</Typography.Text></Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right"><Typography.Text strong>{money(actualAmt)}</Typography.Text></Table.Summary.Cell>
                <Table.Summary.Cell index={4} colSpan={4} />
              </Table.Summary.Row>
            );
          }}
          pagination={erpPagination({ current: page, total, pageSize, onChange: (nextPage, nextSize) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize); } })}
        />
      </Card>
    </SalesModuleShell>
  );
}
