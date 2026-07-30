import { useRef, useState } from "react";
import { Button, Space, Switch, Popconfirm, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType, ProColumns } from "@ant-design/pro-components";
import { ThunderboltOutlined } from "@ant-design/icons";
import { StatusTag, type StatusTone } from "../../ui";
import {
  getLevelRules,
  deleteLevelRule,
  updateLevelRule,
  autoLevel,
  getApiErrorMessage,
} from "../../api";
import type { LevelRule } from "../../types";

const CONDITION_LABELS: Record<string, string> = {
  revenue: "累计营收",
  order_count: "订单数",
  no_order_days: "未下单天数",
};
const OPERATOR_LABELS: Record<string, string> = { ">": ">", "<": "<", ">=": ">=", "<=": "<=" };
const LEVEL_TONES: Record<string, StatusTone> = {
  A: "danger",
  B: "warning",
  C: "info",
  D: "neutral",
};

export default function LevelRulesTable() {
  const actionRef = useRef<ActionType>(null);
  const [autoLevelLoading, setAutoLevelLoading] = useState(false);

  const handleDelete = async (id: number) => {
    try {
      await deleteLevelRule(id);
      message.success("已删除");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleToggleEnabled = async (rule: LevelRule) => {
    try {
      await updateLevelRule(rule.id, { enabled: !rule.enabled });
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const handleAutoLevel = async () => {
    setAutoLevelLoading(true);
    try {
      const resp = await autoLevel();
      message.success(`自动分级完成，更新 ${resp.data.data.updated} 个客户`);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "自动分级失败"));
    } finally {
      setAutoLevelLoading(false);
    }
  };

  const columns: ProColumns<LevelRule>[] = [
    { title: "名称", dataIndex: "name", width: 160 },
    {
      title: "目标等级",
      dataIndex: "target_level",
      width: 80,
      render: (_, r) => (
        <StatusTag status={r.target_level} tone={LEVEL_TONES[r.target_level] || "neutral"} />
      ),
    },
    {
      title: "条件",
      dataIndex: "condition_type",
      width: 100,
      render: (_, r) => CONDITION_LABELS[r.condition_type] || r.condition_type,
    },
    {
      title: "运算符",
      dataIndex: "operator",
      width: 60,
      render: (_, r) => OPERATOR_LABELS[r.operator] || r.operator,
    },
    { title: "阈值", dataIndex: "threshold_value", width: 80 },
    { title: "周期(天)", dataIndex: "period_days", width: 80 },
    { title: "优先级", dataIndex: "priority", width: 60 },
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
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ThunderboltOutlined />} loading={autoLevelLoading} onClick={handleAutoLevel}>
          执行自动分级
        </Button>
      </Space>
      <ProTable<LevelRule>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        options={{ reload: true, density: true, setting: true }}
        size="small"
        pagination={false}
        request={async () => {
          const r = await getLevelRules();
          const list = r.data.data || [];
          return { data: list, success: true, total: list.length };
        }}
      />
    </div>
  );
}