import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Button, Card, Dropdown, Progress, Select, Space, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import type { MenuProps } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  EllipsisOutlined,
  EyeOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { getApiErrorMessage } from "../../api";
import type { PageData, SalesTarget } from "../../types";
import { useApiMutation, useApiQuery } from "../../lib/queries";
import {
  ErpExportButton,
  MetricBand,
  SalesModuleShell,
  erpRowClass,
  money,
  statusDot,
  ERP_STATUS_DOT,
} from "./salesUi";

interface TargetStats {
  total_target: number;
  total_actual: number;
  achievement_pct: number;
  count?: number;
  completed?: number;
}

const STATUS: Record<string, { color: string; label: string }> = {
  active: { color: "blue", label: "进行中" },
  completed: { color: "green", label: "已完成" },
  cancelled: { color: "default", label: "已取消" },
};
const TYPE: Record<string, string> = {
  monthly: "月度",
  quarterly: "季度",
  annual: "年度",
};

const EMPTY_ROWS: SalesTarget[] = [];
const EMPTY_STATS: TargetStats = {
  total_target: 0,
  total_actual: 0,
  achievement_pct: 0,
};

interface TargetStats {
  total_target: number;
  total_actual: number;
  achievement_pct: number;
  count?: number;
  completed?: number;
}

export default function TargetList() {
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>(null);

  const [status, setStatus] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const listQuery = useApiQuery<PageData<SalesTarget>>(
    ["sales", "targets", { status, page, pageSize }],
    "/api/v1/sales/targets",
    { status, page, page_size: pageSize },
    { keepPreviousData: true, staleTime: 30 * 1000 },
  );

  const statsQuery = useApiQuery<TargetStats>(
    ["sales", "targets", "stats"],
    "/api/v1/sales/targets/stats",
    undefined,
    { staleTime: 60 * 1000 },
  );

  const deleteMut = useApiMutation<unknown, number>(
    "delete",
    (id) => `/api/v1/sales/targets/${id}`,
    {
      invalidateKeys: [
        ["sales", "targets"],
        ["sales", "targets", "stats"],
      ],
      onSuccess: () => message.success("已删除"),
      onError: (err) => message.error(getApiErrorMessage(err, "删除失败")),
    },
  );

  const dataSource = useMemo(
    () => listQuery.data?.list ?? EMPTY_ROWS,
    [listQuery.data],
  );
  const stats: TargetStats = statsQuery.data ?? EMPTY_STATS;

  const exportData = useMemo(
    () =>
      dataSource.map((r) => ({
        id: r.id,
        target_type: TYPE[r.target_type] || r.target_type,
        target_amount: r.target_amount,
        actual_amount: r.actual_amount,
        achievement:
          r.target_amount > 0
            ? `${Math.round((r.actual_amount / r.target_amount) * 100)}%`
            : "",
        period: `${r.period_start?.slice(0, 10) || ""} ~ ${r.period_end?.slice(0, 10) || ""}`,
        status: STATUS[r.status]?.label || r.status,
      })),
    [dataSource],
  );

  return (
    <SalesModuleShell
      title="销售目标"
      subtitle="管理销售目标、实际达成和执行进度"
      activeKey="targets"
    >
      <MetricBand
        items={[
          { title: "总目标", value: stats.total_target, prefix: "¥", precision: 0 },
          { title: "已完成", value: stats.total_actual, prefix: "¥", precision: 0 },
          { title: "达成率", value: stats.achievement_pct, suffix: "%", precision: 1 },
        ]}
      />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/sales/targets/new")}
          >
            新增目标
          </Button>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: "active", label: "进行中" },
              { value: "completed", label: "已完成" },
            ]}
          />
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
        <ProTable<SalesTarget>
          actionRef={actionRef}
          rowKey="id"
          size="small"
          bordered
          search={false}
          options={{ reload: () => listQuery.refetch(), density: true, setting: true }}
          rowClassName={erpRowClass}
          scroll={{ x: "max-content" }}
          dataSource={dataSource}
          loading={listQuery.isLoading || listQuery.isFetching}
          columns={[
            {
              title: "#",
              width: 45,
              fixed: "left",
              render: (_: unknown, __: SalesTarget, index: number) =>
                (page - 1) * pageSize + index + 1,
            },
            {
              title: "类型",
              dataIndex: "target_type",
              width: 80,
              fixed: "left",
              render: (_dom, r: SalesTarget) => (
                <div>
                  <div className="erp-cell-primary">{TYPE[r.target_type] || r.target_type}</div>
                </div>
              ),
            },
            {
              title: "目标金额",
              dataIndex: "target_amount",
              width: 130,
              align: "right",
              sorter: (a, b) => a.target_amount - b.target_amount,
              render: (_dom, r: SalesTarget) => (
                <Typography.Text strong>{money(r.target_amount)}</Typography.Text>
              ),
            },
            {
              title: "实际金额",
              dataIndex: "actual_amount",
              width: 130,
              align: "right",
              sorter: (a, b) => a.actual_amount - b.actual_amount,
              render: (_dom, r: SalesTarget) => (
                <Typography.Text strong>{money(r.actual_amount)}</Typography.Text>
              ),
            },
            {
              title: "达成率",
              width: 100,
              render: (_: unknown, r: SalesTarget) => (
                <Progress
                  percent={Math.round(
                    r.target_amount > 0 ? (r.actual_amount / r.target_amount) * 100 : 0,
                  )}
                  size="small"
                />
              ),
            },
            {
              title: "期间",
              width: 180,
              render: (_: unknown, r: SalesTarget) =>
                `${r.period_start?.slice(0, 10) || "?"} ~ ${r.period_end?.slice(0, 10) || "?"}`,
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 90,
              sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
              render: (_dom, r: SalesTarget) => (
                <>
                  {statusDot(ERP_STATUS_DOT[r.status] || "#d9d9d9")}
                  <StatusTag tone={STATUS[r.status]?.color}>
                    {STATUS[r.status]?.label || r.status}
                  </StatusTag>
                </>
              ),
            },
            {
              title: "操作",
              width: 60,
              fixed: "right",
              render: (_: unknown, r: SalesTarget) => {
                const items: MenuProps["items"] = [
                  {
                    key: "view",
                    icon: <EyeOutlined />,
                    label: "查看详情",
                    onClick: () => navigate(`/sales/targets/${r.id}`),
                  },
                  {
                    key: "edit",
                    icon: <EditOutlined />,
                    label: "编辑",
                    onClick: () => navigate(`/sales/targets/${r.id}/edit`),
                  },
                  { type: "divider" as const },
                  {
                    key: "delete",
                    icon: <DeleteOutlined />,
                    label: "删除",
                    danger: true,
                    onClick: () => {
                      modal.confirm({
                        title: "确定删除?",
                        content: `删除目标 #${r.id}？`,
                        okButtonProps: { danger: true },
                        onOk: async () => {
                          try {
                            await deleteMut.mutateAsync(r.id);
                          } catch {
                            // useApiMutation onError already surfaces a message
                          }
                        },
                      });
                    },
                  },
                ];
                return (
                  <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
                    <Button size="small" icon={<EllipsisOutlined />} type="text" />
                  </Dropdown>
                );
              },
            },
          ]}
          summary={() => {
            const targetAmt = dataSource.reduce((s, r) => s + r.target_amount, 0);
            const actualAmt = dataSource.reduce((s, r) => s + r.actual_amount, 0);
            return (
              <ProTable.Summary.Row>
                <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={1}>
                  <Typography.Text strong>{dataSource.length} 项</Typography.Text>
                </ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={2} align="right">
                  <Typography.Text strong>{money(targetAmt)}</Typography.Text>
                </ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={3} align="right">
                  <Typography.Text strong>{money(actualAmt)}</Typography.Text>
                </ProTable.Summary.Cell>
                <ProTable.Summary.Cell index={4} colSpan={4} />
              </ProTable.Summary.Row>
            );
          }}
          pagination={{
            current: page,
            pageSize,
            total: listQuery.data?.total ?? 0,
            showSizeChanger: true,
            pageSizeOptions: [20, 50, 100],
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 条 / 共 ${t} 条`,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage);
              setPageSize(nextSize);
            },
          }}
        />
      </Card>
    </SalesModuleShell>
  );
}
