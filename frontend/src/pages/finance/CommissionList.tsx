/** CommissionList — sales commission tracking with state machine.

Follows the ERP Operational Screens design (DESIGN.md):
- `<PageHeader>` for title
- `<SearchBar>` for filters
- `<StatusTag>` for status column
- `<MoneyCell>` (numeric style with tnum + color) for money columns
- `<ErrorBoundary>` for page-level failure containment
- `size="middle"` table with fixed action column
*/

import { useRef, useState } from "react";
import { Button, Drawer, Form, InputNumber, Space, App as AntdApp } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";

import { PageHeader } from "@/ui/PageHeader";
import { SearchBar } from "@/ui/SearchBar";
import { EmptyState } from "@/ui/EmptyState";
import { ErrorBoundary } from "@/ui/ErrorBoundary";

import {
  getCommissions,
  createCommission,
  transitionCommission,
  batchTransitionCommissions,
} from "@/api/finance";
import { getApiErrorMessage } from "@/api";
import { numericStyle } from "@/design-tokens";
import type { Commission, CommissionStatus } from "@/types";

const STATUS_LABELS: Record<CommissionStatus, string> = {
  draft: "草稿",
  pending_approval: "待审批",
  approved: "已审批",
  paid: "已发放",
  rejected: "已拒绝",
  cancelled: "已取消",
};

const STATUS_TONE: Record<CommissionStatus, Parameters<typeof StatusTag>[0]["tone"]> = {
  draft: "info",
  pending_approval: "processing",
  approved: "info",
  paid: "success",
  rejected: "danger",
  cancelled: "neutral",
};

function MoneyCell({ value }: { value: number }) {
  const isNegative = value < 0;
  return (
    <span style={{ ...numericStyle, color: isNegative ? "#ef4444" : "#10b981" }}>
      {isNegative ? "-" : ""}¥{" "}
      {Math.abs(value).toLocaleString("zh-CN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 6,
      })}
    </span>
  );
}

function CommissionList() {
  const { message } = AntdApp.useApp();
  const actionRef = useRef<ActionType>(null);
  const [statusFilter, setStatusFilter] = useState<CommissionStatus | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [form] = Form.useForm();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  const onCreate = async () => {
    try {
      const values = await form.validateFields();
      await createCommission({
        sales_order_id: values.sales_order_id,
        sales_user_id: values.sales_user_id,
        base_amount: values.base_amount ?? 0,
        rate: values.rate ?? 0,
        period: values.period,
      });
      message.success("已创建");
      setDrawerOpen(false);
      form.resetFields();
      actionRef.current?.reload();
    } catch {
      /* validation error — antd shows inline */
    }
  };

  const onTransition = async (id: number, to: CommissionStatus) => {
    try {
      await transitionCommission(id, to, "UI 触发");
      message.success(`已流转到 ${STATUS_LABELS[to]}`);
      actionRef.current?.reload();
    } catch (e) {
      message.error((e as Error).message ?? "状态流转失败");
    }
  };

  const onBatchTransition = async (to: CommissionStatus, paidAmount?: number) => {
    if (selectedRowKeys.length === 0) {
      message.warning("请先勾选要操作的记录");
      return;
    }
    setBatchLoading(true);
    try {
      const res = await batchTransitionCommissions({
        ids: selectedRowKeys.map((k) => Number(k)),
        to,
        notes: "UI 批量触发",
        ...(paidAmount !== undefined ? { paid_amount: paidAmount } : {}),
      });
      const { failed, summary } = res.data.data;
      if (summary.failed > 0) {
        message.warning(
          `批量 ${STATUS_LABELS[to]}：成功 ${summary.succeeded}，失败 ${summary.failed}（${failed.map((f) => f.id).join(", ")}）`,
        );
      } else {
        message.success(`批量 ${STATUS_LABELS[to]}：${summary.succeeded} 条全部成功`);
      }
      setSelectedRowKeys([]);
      actionRef.current?.reload();
    } catch (e) {
      message.error((e as Error).message ?? "批量操作失败");
    } finally {
      setBatchLoading(false);
    }
  };

  const columns: any = [
    { title: "佣金单号", dataIndex: "commission_no", width: 140, fixed: "left" },
    { title: "销售单", dataIndex: "sales_order_id", width: 100 },
    { title: "客户", dataIndex: "customer_id", width: 100 },
    { title: "销售人员", dataIndex: "sales_user_id", width: 100 },
    {
      title: "基数",
      dataIndex: "base_amount",
      width: 140,
      align: "right",
      render: (v: number) => <MoneyCell value={v} />,
    },
    {
      title: "比例",
      dataIndex: "rate",
      width: 80,
      align: "right",
      render: (v: number) => <span style={numericStyle}>{(v * 100).toFixed(2)}%</span>,
    },
    {
      title: "佣金金额",
      dataIndex: "commission_amount",
      width: 140,
      align: "right",
      render: (v: number) => <MoneyCell value={v} />,
    },
    {
      title: "已发放",
      dataIndex: "paid_amount",
      width: 140,
      align: "right",
      render: (v: number) => <MoneyCell value={v} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (v: CommissionStatus) => (
        <StatusTag status={v} tone={STATUS_TONE[v]} label={STATUS_LABELS[v]} />
      ),
    },
    {
      title: "操作",
      width: 220,
      fixed: "right",
      render: (_: any, row: any) => (
        <Space size="small">
          {row.status === "draft" && (
            <Button
              type="link"
              size="small"
              onClick={() => void onTransition(row.id, "pending_approval")}
            >
              提交审批
            </Button>
          )}
          {row.status === "pending_approval" && (
            <>
              <Button
                type="link"
                size="small"
                onClick={() => void onTransition(row.id, "approved")}
              >
                审批
              </Button>
              <Button
                type="link"
                size="small"
                danger
                onClick={() => void onTransition(row.id, "rejected")}
              >
                拒绝
              </Button>
            </>
          )}
          {row.status === "approved" && (
            <Button type="link" size="small" onClick={() => void onTransition(row.id, "paid")}>
              标记发放
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <ErrorBoundary>
      <PageHeader
        title="佣金管理"
        description="销售订单佣金的创建、审批、发放全流程"
        actions={
          <Button type="primary" onClick={() => setDrawerOpen(true)}>
            + 新建佣金
          </Button>
        }
      />
      <SearchBar
        placeholder="按佣金单号/销售人员搜索"
        onSearch={() => actionRef.current?.reload()}
        onReset={() => setStatusFilter(undefined)}
      />
      <ProTable<Commission>
        actionRef={actionRef}
        rowKey="id"
        size="middle"
        columns={columns}
        request={async (params) => {
          try {
            const resp = await getCommissions({
              page: params.current,
              page_size: params.pageSize,
              ...(params.status ? { status: params.status as CommissionStatus } : {}),
            });
            return {
              data: resp.data.data?.list ?? [],
              total: resp.data.data?.total ?? 0,
              success: true,
            };
          } catch {
            return { data: [], total: 0, success: false };
          }
        }}
        params={{ status: statusFilter }}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        scroll={{ x: 1200 }}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
          preserveSelectedRowKeys: true,
        }}
        toolBarRender={() =>
          selectedRowKeys.length > 0
            ? [
                <span key="count">已选 {selectedRowKeys.length} 条</span>,
                <Button
                  key="approve"
                  size="small"
                  onClick={() => void onBatchTransition("approved")}
                  loading={batchLoading}
                >
                  批量审批
                </Button>,
                <Button
                  key="reject"
                  size="small"
                  onClick={() => void onBatchTransition("rejected")}
                  loading={batchLoading}
                >
                  批量拒绝
                </Button>,
                <Button
                  key="pay"
                  size="small"
                  type="primary"
                  onClick={() => void onBatchTransition("paid")}
                  loading={batchLoading}
                >
                  批量发放
                </Button>,
                <Button key="clear" size="small" type="text" onClick={() => setSelectedRowKeys([])}>
                  清除选择
                </Button>,
              ]
            : []
        }
        locale={{
          emptyText: <EmptyState description="还没有佣金记录 — 从已完成的销售订单创建第一条" />,
        }}
      />
      <Drawer
        title="新建佣金"
        open={drawerOpen}
        width={560}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Space style={{ float: "right" }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void onCreate()}>
              创建
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item label="销售单 ID" name="sales_order_id" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} placeholder="如 1024" />
          </Form.Item>
          <Form.Item label="销售人员 ID" name="sales_user_id" rules={[{ required: true }]}>
            <InputNumber style={{ width: "100%" }} placeholder="如 7" />
          </Form.Item>
          <Form.Item label="佣金基数 (¥)" name="base_amount">
            <InputNumber style={{ width: "100%" }} min={0} step={100} />
          </Form.Item>
          <Form.Item label="比例 (0–1)" name="rate">
            <InputNumber style={{ width: "100%" }} min={0} max={1} step={0.01} />
          </Form.Item>
          <Form.Item label="结算周期" name="period">
            <InputNumber style={{ width: "100%" }} placeholder="如 2026-06" />
          </Form.Item>
        </Form>
      </Drawer>
    </ErrorBoundary>
  );
}

export default CommissionList;
