// useCustomerTableColumns — builds the Antd Table columns definition for
// the customer list, sharing the parent's sort state, overdue set, and
// follow-up-by-customer map.

import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Dropdown, Space, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DeleteOutlined,
  MoreOutlined,
  ShoppingCartOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { Customer, FollowUpReminder, Tag as TagType } from "../../types";
import { FollowUpMethodTag } from "./customerUi";
import {
  formatDate,
  formatDateTime,
  getHealthColor,
  getLevelColor,
} from "./constants";

interface Args {
  sortBy: string;
  sortOrder: string;
  overdueCustomerIds: Set<number>;
  nextFollowUpByCustomer: Map<number, FollowUpReminder>;
  onOpenDetail: (id: number) => void;
  onOpenQuickFollowUp: (customer: Customer) => void;
  onConfirmDelete: (customer: Customer) => void;
  onVendAsSupplier: (customer: Customer) => void;
}

export function useCustomerTableColumns({
  sortBy,
  sortOrder,
  overdueCustomerIds,
  nextFollowUpByCustomer,
  onOpenDetail,
  onOpenQuickFollowUp,
  onConfirmDelete,
  onVendAsSupplier,
}: Args): ColumnsType<Customer> {
  const navigate = useNavigate();
  const sortIndicator = (key: string) =>
    sortBy === key ? (sortOrder === "asc" ? "ascend" : "descend") : null;

  return useMemo<ColumnsType<Customer>>(() => [
    {
      title: "客户编码",
      dataIndex: "code",
      key: "code",
      width: 120,
      sorter: true,
      sortOrder: sortIndicator("code"),
      render: (v: string | null) => (
        <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{v || "-"}</span>
      ),
    },
    {
      title: "客户",
      dataIndex: "name",
      key: "name",
      width: 280,
      sorter: true,
      sortOrder: sortIndicator("name"),
      render: (text: string, r: Customer) => (
        <Space direction="vertical" size={2}>
          <Space size={6} wrap>
            <Typography.Link strong onClick={() => navigate(`/customers/${r.id}`)}>{text}</Typography.Link>
            {r.level && <StatusTag tone={getLevelColor(r.level)} style={{ marginInlineEnd: 0 }}>{r.level}</StatusTag>}
            {overdueCustomerIds.has(r.id) && <StatusTag tone="danger" style={{ marginInlineEnd: 0 }}>逾期</StatusTag>}
          </Space>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {[r.code, r.short_name].filter(Boolean).join(" / ") || "-"}
          </Typography.Text>
          {r.contact_person && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              联系人：{r.contact_person}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "行业",
      dataIndex: "industry",
      key: "industry",
      width: 120,
      sorter: true,
      sortOrder: sortIndicator("industry"),
      render: (v: string | null) => (v ? <StatusTag>{v}</StatusTag> : "-"),
    },
    {
      title: "等级",
      dataIndex: "level",
      key: "level",
      width: 76,
      align: "center",
      sorter: true,
      sortOrder: sortIndicator("level"),
      render: (v: string | null) => <StatusTag tone={getLevelColor(v)} style={{ marginInlineEnd: 0 }}>{v || "-"}</StatusTag>,
    },
    {
      title: "区域",
      dataIndex: "region",
      key: "region",
      width: 100,
      sorter: true,
      sortOrder: sortIndicator("region"),
      render: (v: string | null) => v || "-",
    },
    {
      title: "信用",
      dataIndex: "credit_level",
      key: "credit_level",
      width: 90,
      sorter: true,
      sortOrder: sortIndicator("credit_level"),
      render: (v: string | null) => v ? <StatusTag>{v}</StatusTag> : "-",
    },
    {
      title: "健康/风险",
      key: "health",
      width: 130,
      render: (_: unknown, row: Customer) => (
        <Space size={4} wrap>
          <StatusTag tone={getHealthColor(row.health_score)}>
            {row.health_score != null ? `${row.health_score}` : "-"}
          </StatusTag>
          {overdueCustomerIds.has(row.id) && <StatusTag tone="danger">逾期</StatusTag>}
        </Space>
      ),
    },
    {
      title: "下一次跟进",
      key: "next_followup",
      width: 170,
      render: (_: unknown, row: Customer) => {
        const next = nextFollowUpByCustomer.get(row.id);
        if (!next) return "-";
        const color = next.due_bucket === "overdue" ? "red" : next.due_bucket === "today" ? "orange" : "blue";
        const label = next.due_bucket === "overdue"
          ? `逾期${next.overdue_days}天`
          : next.due_bucket === "today"
            ? "今日"
            : `${next.days_until ?? "-"}天后`;
        return (
          <Space direction="vertical" size={0}>
            <Space size={4}>
              <StatusTag tone={color}>{label}</StatusTag>
              <FollowUpMethodTag method={next.method} />
            </Space>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{formatDateTime(next.planned_at)}</Typography.Text>
          </Space>
        );
      },
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 180,
      render: (rowTags: TagType[] | undefined) => {
        const items = rowTags || [];
        if (!items.length) return "-";
        return (
          <Space size={[4, 4]} wrap>
            {items.slice(0, 2).map((t) => (
              <StatusTag key={t.id} tone={t.color || "info"}>{t.name}</StatusTag>
            ))}
            {items.length > 2 && <StatusTag>+{items.length - 2}</StatusTag>}
          </Space>
        );
      },
    },
    {
      title: "负责人",
      dataIndex: "owner",
      key: "owner",
      width: 100,
      render: (v: string | null) => v ? <Typography.Text>{v}</Typography.Text> : "-",
    },
    {
      title: "联系人",
      dataIndex: "contact_person",
      key: "contact_person",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "电话",
      dataIndex: "phone",
      key: "phone",
      width: 130,
      render: (v: string | null) => v || "-",
    },
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
      width: 180,
      render: (v: string | null) => v ? <Typography.Text copyable>{v}</Typography.Text> : "-",
    },
    {
      title: "最近联系",
      dataIndex: "last_contacted_at",
      key: "last_contacted_at",
      width: 110,
      render: (v: string | null) => formatDate(v),
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
      width: 100,
      sorter: true,
      sortOrder: sortIndicator("source"),
      render: (v: string | null) => v || "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 120,
      sorter: true,
      sortOrder: sortIndicator("created_at"),
      render: (v: string) => formatDate(v),
    },
    {
      title: "操作",
      key: "actions",
      width: 142,
      fixed: "right",
      render: (_: unknown, r: Customer) => (
        <Space size={2}>
          <Button size="small" type="link" onClick={() => onOpenDetail(r.id)}>查看</Button>
          <Button size="small" type="link" onClick={() => onOpenQuickFollowUp(r)}>跟进</Button>
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                { key: "order", icon: <ShoppingCartOutlined />, label: "创建销售订单" },
                { key: "supplier", icon: <SwapOutlined />, label: "转为供应商" },
                { type: "divider" },
                { key: "delete", icon: <DeleteOutlined />, danger: true, label: "删除客户" },
              ],
              onClick: ({ key }) => {
                if (key === "order") navigate(`/sales/orders/new?customer_id=${r.id}`);
                if (key === "supplier") onVendAsSupplier(r);
                if (key === "delete") onConfirmDelete(r);
              },
            }}
          >
            <Tooltip title="更多操作">
              <Button size="small" type="link" icon={<MoreOutlined />} aria-label="更多操作" />
            </Tooltip>
          </Dropdown>
        </Space>
      ),
    },
  ], [sortBy, sortOrder, overdueCustomerIds, nextFollowUpByCustomer, navigate,
      onOpenDetail, onOpenQuickFollowUp, onConfirmDelete, onVendAsSupplier]);
}
