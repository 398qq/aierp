// useProductTableColumns — Antd Table columns definition for the
// product workbench. Returns a memoized ColumnsType<Product>.

import { useMemo } from "react";
import { Button, Dropdown, Modal, Progress, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DeleteOutlined,
  DollarOutlined,
  EditOutlined,
  EllipsisOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { Product } from "../../types";
import { formatDateTime, getAvailableQty, getStockState } from "./constants";

interface Args {
  onOpenDetail: (product: Product) => void;
  onOpenEdit: (product: Product) => void;
  onOpenQuickPrice: (product: Product) => void;
  onOpenQuickSafety: (product: Product) => void;
  onDelete: (id: number) => void;
}

export function useProductTableColumns({
  onOpenDetail,
  onOpenEdit,
  onOpenQuickPrice,
  onOpenQuickSafety,
  onDelete,
}: Args): ColumnsType<Product> {
  return useMemo<ColumnsType<Product>>(
    () => [
      {
        title: "SKU",
        dataIndex: "sku",
        key: "sku",
        width: 140,
        fixed: "left",
        render: (v: string | null) => <span className="product-sku">{v || "-"}</span>,
      },
      {
        title: "产品名称",
        dataIndex: "name",
        key: "name",
        width: 160,
        fixed: "left",
        sorter: true,
        render: (text: string, r: Product) => (
          <button type="button" className="product-name-link" onClick={() => onOpenDetail(r)}>
            {text}
          </button>
        ),
      },
      {
        title: "分类",
        dataIndex: "category",
        key: "category",
        width: 90,
        render: (v: string) => {
          if (!v) return "-";
          const display = v.length > 5 ? `${v.slice(0, 5)}…` : v;
          return <Tooltip title={v}><StatusTag>{display}</StatusTag></Tooltip>;
        },
      },
      {
        title: "封装",
        dataIndex: "package_type",
        key: "package_type",
        width: 90,
        render: (v: string | null) => {
          if (!v) return "-";
          const display = v.length > 7 ? `${v.slice(0, 7)}…` : v;
          return <Tooltip title={v}>{display}</Tooltip>;
        },
      },
      {
        title: "规格",
        dataIndex: "specs",
        key: "specs",
        width: 180,
        render: (v: string | null) => {
          if (!v) return "-";
          return (
            <Tooltip
              title={
                <div style={{ maxWidth: 520, whiteSpace: "normal", wordBreak: "break-word" }}>
                  {v}
                </div>
              }
            >
              <span
                style={{
                  display: "block",
                  maxWidth: 164,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {v}
              </span>
            </Tooltip>
          );
        },
      },
      {
        title: "单位",
        dataIndex: "unit",
        key: "unit",
        width: 80,
        render: (v: string | null) => v || "-",
      },
      {
        title: "品牌",
        dataIndex: "brand_name",
        key: "brand_name",
        width: 130,
        render: (v: string | null) => v || "-",
      },
      {
        title: "完整度",
        dataIndex: "completion_score",
        key: "completion_score",
        width: 120,
        render: (v: number | null, r: Product) => {
          const score = v ?? 0;
          const missing = r.missing_fields?.length
            ? `缺少：${r.missing_fields.join("、")}`
            : "资料完整";
          return (
            <Tooltip title={missing}>
              <Progress
                percent={score}
                size="small"
                showInfo={false}
                strokeColor={score >= 80 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"}
              />
            </Tooltip>
          );
        },
      },
      {
        title: "供应商",
        dataIndex: "supplier_count",
        key: "supplier_count",
        width: 90,
        align: "right",
        render: (v: number | null) => v ?? 0,
      },
      {
        title: "分仓",
        dataIndex: "inventory_location_count",
        key: "inventory_location_count",
        width: 80,
        align: "right",
        render: (v: number | null) => v ?? 0,
      },
      {
        title: "库存状态",
        key: "stock_state",
        width: 110,
        render: (_: unknown, r: Product) => {
          const state = getStockState(r);
          if (state === "out") return <StatusTag tone="danger">缺货</StatusTag>;
          if (state === "low") return <StatusTag tone="warning">低库存</StatusTag>;
          return <StatusTag tone="success">在库</StatusTag>;
        },
      },
      {
        title: "库存",
        dataIndex: "quantity",
        key: "quantity",
        width: 90,
        align: "right",
        render: (v: number | null) => <span className="product-number">{v != null ? v : 0}</span>,
      },
      {
        title: "可用",
        dataIndex: "available",
        key: "available",
        width: 90,
        align: "right",
        render: (_: number | null, r: Product) => (
          <span className={`product-number${getAvailableQty(r) <= 0 ? " is-danger" : ""}`}>
            {getAvailableQty(r)}
          </span>
        ),
      },
      {
        title: "锁定",
        dataIndex: "locked_quantity",
        key: "locked",
        width: 90,
        align: "right",
        render: (v: number | null) => (v != null ? v : 0),
      },
      {
        title: "安全库存",
        dataIndex: "safety_stock",
        key: "safety_stock",
        width: 100,
        align: "right",
        render: (v: number | null) => (v != null ? v : "-"),
      },
      {
        title: "单价",
        dataIndex: "unit_price",
        key: "unit_price",
        width: 110,
        align: "right",
        render: (v: number | null) => (
          <span className="product-number">{v != null ? `¥${v.toFixed(2)}` : "-"}</span>
        ),
      },
      {
        title: "最近销售",
        dataIndex: "last_sale_at",
        key: "last_sale_at",
        width: 170,
        render: (v: string | null) => formatDateTime(v),
      },
      {
        title: "操作",
        key: "actions",
        width: 92,
        align: "center",
        fixed: "right",
        render: (_: unknown, r: Product) => (
          <div
            style={{ display: "flex", justifyContent: "center", gap: 2 }}
            onClick={(event) => event.stopPropagation()}
          >
            <Tooltip title="查看详情">
              <Button
                type="text"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onOpenDetail(r)}
                aria-label={`查看产品 ${r.name}`}
              />
            </Tooltip>
            <Dropdown
              trigger={["click"]}
              placement="bottomRight"
              menu={{
                items: [
                  { key: "price", icon: <DollarOutlined />, label: "快捷改价" },
                  { key: "safety", icon: <SafetyCertificateOutlined />, label: "修改安全库存" },
                  { key: "edit", icon: <EditOutlined />, label: "编辑产品" },
                  { type: "divider" },
                  { key: "delete", icon: <DeleteOutlined />, label: "删除产品", danger: true },
                ],
                onClick: ({ key, domEvent }) => {
                  domEvent.stopPropagation();
                  if (key === "price") onOpenQuickPrice(r);
                  if (key === "safety") onOpenQuickSafety(r);
                  if (key === "edit") onOpenEdit(r);
                  if (key === "delete") {
                    Modal.confirm({
                      title: "确认删除产品",
                      content: `确定要删除 ${r.name} 吗？`,
                      okText: "删除",
                      cancelText: "取消",
                      okButtonProps: { danger: true },
                      onOk: () => onDelete(r.id),
                    });
                  }
                },
              }}
            >
              <Button
                type="text"
                size="small"
                icon={<EllipsisOutlined />}
                aria-label={`操作产品 ${r.name}`}
                title="更多操作"
              />
            </Dropdown>
          </div>
        ),
      },
    ],
    [onOpenDetail, onOpenEdit, onOpenQuickPrice, onOpenQuickSafety, onDelete],
  );
}
