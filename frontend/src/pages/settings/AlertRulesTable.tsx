import { useRef } from "react";
import { Button, Switch, Popconfirm, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType, ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { SEVERITY_TONES } from "./constants";
import {
  getAlertRules,
  deleteAlertRule,
  updateAlertRule,
  getApiErrorMessage,
} from "../../api";
import type { AlertRule } from "../../types";

const RULE_TYPE_LABELS: Record<string, string> = {
  no_order: "长期未下单",
  credit_over: "信用额度使用率",
  order_drop: "订单下降",
  ar_overdue: "应收逾期",
};

export default function AlertRulesTable() {
  const actionRef = useRef<ActionType>(null);

  const handleDelete = async (id: number) => {
    try {
      await deleteAlertRule(id);
      message.success("已删除");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleToggleEnabled = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const columns: ProColumns<AlertRule>[] = [
    { title: "名称", dataIndex: "name", width: 160 },
    {
      title: "规则类型",
      dataIndex: "rule_type",
      width: 120,
      render: (_, r) => RULE_TYPE_LABELS[r.rule_type] || r.rule_type,
    },
    { title: "阈值天数", dataIndex: "threshold_days", width: 90 },
    { title: "阈值%", dataIndex: "threshold_pct", width: 80 },
    { title: "阈值金额", dataIndex: "threshold_amount", width: 90 },
    {
      title: "严重级别",
      dataIndex: "severity",
      width: 90,
      render: (_, r) => (
        <StatusTag status={r.severity} tone={SEVERITY_TONES[r.severity] || "neutral"} />
      ),
    },
    {
      title: "启用",
      dataIndex: "enabled",
      width: 60,
      render: (_, r) => (
        <Switch size="small" checked={r.enabled} onChange={() => handleToggleEnabled(r)} />
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 90,
      render: (_, r) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
          <Button size="small" danger>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <ProTable<AlertRule>
      actionRef={actionRef}
      rowKey="id"
      columns={columns}
      search={false}
      options={{ reload: true, density: true, setting: true }}
      size="small"
      pagination={false}
      request={async () => {
        const r = await getAlertRules();
        const list = r.data.data || [];
        return { data: list, success: true, total: list.length };
      }}
    />
  );
}