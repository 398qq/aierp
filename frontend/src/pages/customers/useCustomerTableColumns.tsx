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

const MONO: React.CSSProperties = {
  fontFamily: "ui-monospace, SFMono-Regular, Consolas, Menlo, monospace",
  fontSize: 13,
};
const TITLE_STYLE: React.CSSProperties = { fontSize: 13, fontWeight: 600 };

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
  const sortDir = (key: string) =>
    sortBy === key ? (sortOrder === "asc" ? "ascend" as const : "descend" as const) : null;

  return useMemo<ColumnsType<Customer>>(() => [
    {
      title: "编码",
      dataIndex: "code",
      key: "code",
      width: 110,
      sorter: true,
      sortOrder: sortDir("code"),
      render: (v: string | null) => (
        <Typography.Text style={MONO}>{v || "-"}</Typography.Text>
      ),
    },
    {
      title: "客户名称",
      dataIndex: "name",
      key: "name",
      width: 240,
      sorter: true,
      sortOrder: sortDir("name"),
      fixed: "left",
      render: (text: string, r: Customer) => (
        <div>
          <Space size={4}>
            <Typography.Link
              onClick={() => navigate(`/customers/${r.id}`)}
              style={TITLE_STYLE}
            >
              {text}
            </Typography.Link>
            {r.level && (
              <StatusTag tone={getLevelColor(r.level)}>{r.level}</StatusTag>
            )}
            {overdueCustomerIds.has(r.id) && (
              <StatusTag tone="danger">逾期</StatusTag>
            )}
          </Space>
          <div style={{ color: "#8c8c8c", fontSize: 12, marginTop: 1 }}>
            {r.short_name || r.code ? `${r.short_name || r.code}${r.tax_id ? ` · ${r.tax_id}` : ""}` : "-"}
          </div>
        </div>
      ),
    },
    {
      title: "简称",
      dataIndex: "short_name",
      key: "short_name",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "行业",
      dataIndex: "industry",
      key: "industry",
      width: 90,
      sorter: true,
      sortOrder: sortDir("industry"),
      render: (v: string | null) => (v ? <StatusTag>{v}</StatusTag> : "-"),
    },
    {
      title: "等级",
      dataIndex: "level",
      key: "level",
      width: 64,
      align: "center",
      sorter: true,
      sortOrder: sortDir("level"),
      render: (v: string | null) => (
        <StatusTag tone={getLevelColor(v)}>{v || "-"}</StatusTag>
      ),
    },
    {
      title: "区域",
      dataIndex: "region",
      key: "region",
      width: 90,
      sorter: true,
      sortOrder: sortDir("region"),
      render: (v: string | null) => v || "-",
    },
    {
      title: "信用",
      key: "credit_level",
      width: 130,
      sorter: true,
      sortOrder: sortDir("credit_level"),
      render: (_: unknown, r: Customer) => (
        <Space size={4}>
          {r.credit_level ? (
            <StatusTag>{r.credit_level}</StatusTag>
          ) : (
            "-"
          )}
          {r.credit_limit != null && r.credit_limit > 0 && (
            <Typography.Text style={{ fontSize: 12, color: "#595959" }}>
              ¥{r.credit_limit.toLocaleString()}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "付款条件",
      dataIndex: "payment_terms",
      key: "payment_terms",
      width: 110,
      render: (v: string | null) =>
        v ? <StatusTag tone="info">{v}</StatusTag> : "-",
    },
    {
      title: "币种",
      dataIndex: "currency",
      key: "currency",
      width: 64,
      align: "center",
      render: (v: string) => (
        <Typography.Text style={MONO}>{v || "CNY"}</Typography.Text>
      ),
    },
    {
      title: "税号",
      dataIndex: "tax_id",
      key: "tax_id",
      width: 150,
      render: (v: string | null) =>
        v ? <Typography.Text copyable style={MONO}>{v}</Typography.Text> : "-",
    },
    {
      title: "收货地址",
      dataIndex: "delivery_address",
      key: "delivery_address",
      width: 160,
      ellipsis: true,
      render: (v: string | null) => v || "-",
    },
    {
      title: "健康度",
      key: "health",
      width: 80,
      align: "center",
      render: (_: unknown, r: Customer) => (
        <StatusTag tone={getHealthColor(r.health_score)}>
          {r.health_score != null ? r.health_score : "-"}
        </StatusTag>
      ),
    },
    {
      title: "下次跟进",
      key: "next_followup",
      width: 150,
      render: (_: unknown, r: Customer) => {
        const next = nextFollowUpByCustomer.get(r.id);
        if (!next) return <Typography.Text type="secondary">-</Typography.Text>;
        const tone =
          next.due_bucket === "overdue"
            ? "danger"
            : next.due_bucket === "today"
              ? "warning"
              : "info";
        const label =
          next.due_bucket === "overdue"
            ? `逾期${next.overdue_days}天`
            : next.due_bucket === "today"
              ? "今日"
              : `${next.days_until ?? "-"}天后`;
        return (
          <Space size={4}>
            <StatusTag tone={tone as any}>{label}</StatusTag>
            <FollowUpMethodTag method={next.method} />
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              {formatDateTime(next.planned_at)}
            </Typography.Text>
          </Space>
        );
      },
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 140,
      render: (rowTags: TagType[] | undefined) => {
        const items = rowTags || [];
        if (!items.length) return "-";
        return (
          <Space size={[3, 3]} wrap>
            {items.slice(0, 2).map((t) => (
              <StatusTag key={t.id} tone={(t.color as any) || "info"}>
                {t.name}
              </StatusTag>
            ))}
            {items.length > 2 && (
              <StatusTag>+{items.length - 2}</StatusTag>
            )}
          </Space>
        );
      },
    },
    {
      title: "负责人",
      dataIndex: "owner",
      key: "owner",
      width: 80,
      render: (v: string | null) => (v || "-"),
    },
    {
      title: "联系人",
      dataIndex: "contact_person",
      key: "contact_person",
      width: 90,
      render: (v: string | null) => v || "-",
    },
    {
      title: "电话",
      dataIndex: "phone",
      key: "phone",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
      width: 170,
      render: (v: string | null) =>
        v ? <Typography.Text copyable style={{ fontSize: 12 }}>{v}</Typography.Text> : "-",
    },
    {
      title: "最近联系",
      dataIndex: "last_contacted_at",
      key: "last_contacted_at",
      width: 100,
      sorter: true,
      sortOrder: sortDir("last_contacted_at"),
      render: (v: string | null) => formatDate(v),
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
      width: 80,
      sorter: true,
      sortOrder: sortDir("source"),
      render: (v: string | null) => v || "-",
    },
    {
      title: "类型",
      dataIndex: "customer_type",
      key: "customer_type",
      width: 90,
      render: (v: string | null) => v || "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 100,
      sorter: true,
      sortOrder: sortDir("created_at"),
      render: (v: string) => (
        <Typography.Text style={{ fontSize: 12 }}>{formatDate(v)}</Typography.Text>
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 130,
      fixed: "right",
      render: (_: unknown, r: Customer) => (
        <Space size={0}>
          <Button size="small" type="link" onClick={() => onOpenDetail(r.id)}>
            查看
          </Button>
          <Button size="small" type="link" onClick={() => onOpenQuickFollowUp(r)}>
            跟进
          </Button>
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                {
                  key: "order",
                  icon: <ShoppingCartOutlined />,
                  label: "创建销售订单",
                },
                {
                  key: "supplier",
                  icon: <SwapOutlined />,
                  label: "转为供应商",
                },
                { type: "divider" },
                {
                  key: "delete",
                  icon: <DeleteOutlined />,
                  danger: true,
                  label: "删除客户",
                },
              ],
              onClick: ({ key }) => {
                if (key === "order")
                  navigate(`/sales/orders/new?customer_id=${r.id}`);
                if (key === "supplier") onVendAsSupplier(r);
                if (key === "delete") onConfirmDelete(r);
              },
            }}
          >
            <Tooltip title="更多">
              <Button
                size="small"
                type="text"
                icon={<MoreOutlined />}
                aria-label="更多操作"
              />
            </Tooltip>
          </Dropdown>
        </Space>
      ),
    },
  ], [
    sortBy, sortOrder, overdueCustomerIds, nextFollowUpByCustomer,
    navigate, onOpenDetail, onOpenQuickFollowUp, onConfirmDelete, onVendAsSupplier,
  ]);
}
