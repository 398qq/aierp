// useProductTableColumns — Antd Table columns definition for the
// product workbench. Returns a memoized ColumnsType<Product>.

import { useMemo } from "react";
import { Button, Popconfirm, Progress, Space, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import { DeleteOutlined, EditOutlined, EyeOutlined } from "@ant-design/icons";
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
  return useMemo<ColumnsType<Product>>(() => [
    {
      title: "SKU",
      dataIndex: "sku",
      key: "sku",
      width: 140,
      fixed: "left",
      render: (v: string | null) => <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{v || "-"}</span>,
    },
    {
      title: "产品名称",
      dataIndex: "name",
      key: "name",
      width: 220,
      fixed: "left",
      sorter: true,
      render: (text: string, r: Product) => <a onClick={() => onOpenDetail(r)}>{text}</a>,
    },
    { title: "分类", dataIndex: "category", key: "category", width: 100, render: (v: string) => (v ? <StatusTag>{v}</StatusTag> : "-") },
    { title: "封装", dataIndex: "package_type", key: "package_type", width: 100, render: (v: string | null) => v || "-" },
    { title: "规格", dataIndex: "specs", key: "specs", width: 220, ellipsis: true, render: (v: string | null) => v || "-" },
    { title: "单位", dataIndex: "unit", key: "unit", width: 80, render: (v: string | null) => v || "-" },
    { title: "品牌", dataIndex: "brand_name", key: "brand_name", width: 130, render: (v: string | null) => v || "-" },
    {
      title: "完整度",
      dataIndex: "completion_score",
      key: "completion_score",
      width: 120,
      render: (v: number | null, r: Product) => {
        const score = v ?? 0;
        const missing = r.missing_fields?.length ? `缺少：${r.missing_fields.join("、")}` : "资料完整";
        return (
          <Tooltip title={missing}>
            <Progress percent={score} size="small" showInfo={false} strokeColor={score >= 80 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"} />
          </Tooltip>
        );
      },
    },
    { title: "供应商", dataIndex: "supplier_count", key: "supplier_count", width: 90, align: "right", render: (v: number | null) => v ?? 0 },
    { title: "分仓", dataIndex: "inventory_location_count", key: "inventory_location_count", width: 80, align: "right", render: (v: number | null) => v ?? 0 },
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
    { title: "库存", dataIndex: "quantity", key: "quantity", width: 90, align: "right", render: (v: number | null) => v != null ? v : 0 },
    { title: "可用", dataIndex: "available", key: "available", width: 90, align: "right", render: (_: number | null, r: Product) => getAvailableQty(r) },
    { title: "锁定", dataIndex: "locked_quantity", key: "locked", width: 90, align: "right", render: (v: number | null) => v != null ? v : 0 },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock", width: 100, align: "right", render: (v: number | null) => v != null ? v : "-" },
    { title: "单价", dataIndex: "unit_price", key: "unit_price", width: 110, align: "right", render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : "-" },
    { title: "最近销售", dataIndex: "last_sale_at", key: "last_sale_at", width: 170, render: (v: string | null) => formatDateTime(v) },
    {
      title: "操作",
      key: "actions",
      width: 230,
      fixed: "right",
      render: (_: unknown, r: Product) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => onOpenDetail(r)} />
          </Tooltip>
          <Tooltip title="快捷改价">
            <Button size="small" onClick={() => onOpenQuickPrice(r)}>改价</Button>
          </Tooltip>
          <Tooltip title="快捷改安全库存">
            <Button size="small" onClick={() => onOpenQuickSafety(r)}>安库</Button>
          </Tooltip>
          <Tooltip title="编辑产品">
            <Button size="small" icon={<EditOutlined />} onClick={() => onOpenEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除?" onConfirm={() => onDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ], [onOpenDetail, onOpenEdit, onOpenQuickPrice, onOpenQuickSafety, onDelete]);
}
