import { useMemo } from "react";
import { Button, Dropdown, Modal, Progress, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  CheckCircleFilled,
  CloseCircleFilled,
  DeleteOutlined,
  DollarOutlined,
  EditOutlined,
  EllipsisOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
  WarningFilled,
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

const MONO: React.CSSProperties = {
  fontFamily: "ui-monospace, SFMono-Regular, Consolas, Menlo, monospace",
  fontSize: 13,
};

const lifecycleTone: Record<string, string> = {
  active: "success",
  nrnd: "warning",
  eol: "danger",
  obsolete: "neutral",
};

const productTypeLabel: Record<string, string> = {
  finished_good: "成品",
  raw_material: "原材料",
  semi_finished: "半成品",
  service: "服务",
};

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
        width: 130,
        fixed: "left",
        render: (v: string | null) => (
          <span className="product-sku" style={MONO}>
            {v || "-"}
          </span>
        ),
      },
      {
        title: "产品名称",
        dataIndex: "name",
        key: "name",
        width: 200,
        fixed: "left",
        sorter: true,
        render: (text: string, r: Product) => (
          <div>
            <button type="button" className="product-name-link" onClick={() => onOpenDetail(r)}>
              {text}
            </button>
            {r.lifecycle_status && (
              <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 1 }}>
                <StatusTag tone={lifecycleTone[r.lifecycle_status] || "info"}>
                  {r.lifecycle_status === "active"
                    ? "量产"
                    : r.lifecycle_status === "nrnd"
                      ? "NRND"
                      : r.lifecycle_status === "eol"
                        ? "EOL"
                        : r.lifecycle_status}
                </StatusTag>
              </div>
            )}
          </div>
        ),
      },
      {
        title: "MPN",
        dataIndex: "mpn",
        key: "mpn",
        width: 140,
        render: (v: string | null) => (v ? <span style={MONO}>{v}</span> : "-"),
      },
      {
        title: "产品状态",
        dataIndex: "status",
        key: "status",
        width: 90,
        render: (value: string | undefined) => (
          <StatusTag tone={value === "active" ? "success" : value === "frozen" ? "warning" : "danger"}>
            {value === "active" ? "已启用" : value === "frozen" ? "已冻结" : value === "inactive" ? "已停用" : "草稿"}
          </StatusTag>
        ),
      },
      {
        title: "产品类型",
        dataIndex: "product_type",
        key: "product_type",
        width: 90,
        render: (value: string | undefined) => productTypeLabel[value || ""] || value || "成品",
      },
      {
        title: "品牌",
        dataIndex: "brand_name",
        key: "brand_name",
        width: 110,
        render: (v: string | null) => v || "-",
      },
      {
        title: "负责人",
        dataIndex: "owner",
        key: "owner",
        width: 90,
        render: (v: string | null) => v || "-",
      },
      {
        title: "分类",
        dataIndex: "category",
        key: "category",
        width: 80,
        render: (v: string) => (
          v ? (
            <span title={v}>
              <StatusTag style={{ maxWidth: 68, display: "inline-block" }}>{v}</StatusTag>
            </span>
          ) : "-"
        ),
      },
      {
        title: "封装",
        key: "package",
        width: 110,
        render: (_: unknown, r: Product) => {
          if (!r.package_type && !r.package_case) return "-";
          return <span style={{ fontSize: 13 }}>{r.package_case || r.package_type}</span>;
        },
      },
      {
        title: "合规",
        key: "compliance",
        width: 90,
        render: (_: unknown, r: Product) => (
          <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
            {r.rohs_compliant ? (
              <CheckCircleFilled style={{ color: "#52c41a", fontSize: 14 }} title="RoHS" />
            ) : (
              <CloseCircleFilled style={{ color: "#d9d9d9", fontSize: 14 }} title="RoHS" />
            )}
            {r.reach_compliant ? (
              <SafetyCertificateOutlined style={{ color: "#1677ff", fontSize: 14 }} title="REACH" />
            ) : null}
            {r.esd_sensitive && (
              <WarningFilled style={{ color: "#faad14", fontSize: 14 }} title="ESD" />
            )}
            {r.msl_level && (
              <span style={{ fontSize: 11, color: "#595959", fontWeight: 600 }}>{r.msl_level}</span>
            )}
          </span>
        ),
      },
      {
        title: "单位",
        dataIndex: "unit",
        key: "unit",
        width: 60,
        render: (v: string | null) => v || "-",
      },
      {
        title: "规格",
        dataIndex: "specs",
        key: "specs",
        width: 150,
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
                  maxWidth: 134,
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
        title: "完整度",
        dataIndex: "completion_score",
        key: "completion_score",
        width: 100,
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
        width: 70,
        align: "right",
        render: (v: number | null) => v ?? 0,
      },
      {
        title: "库存状态",
        key: "stock_state",
        width: 90,
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
        width: 70,
        align: "right",
        render: (v: number | null) => <span className="product-number">{v != null ? v : 0}</span>,
      },
      {
        title: "可用",
        key: "available",
        width: 70,
        align: "right",
        render: (_: number | null, r: Product) => (
          <span className={`product-number${getAvailableQty(r) <= 0 ? " is-danger" : ""}`}>
            {getAvailableQty(r)}
          </span>
        ),
      },
      {
        title: "列表价",
        dataIndex: "list_price",
        key: "list_price",
        width: 90,
        align: "right",
        render: (v: number | null) => (
          <span className="product-number">{v != null ? `¥${v.toFixed(2)}` : "-"}</span>
        ),
      },
      {
        title: "最低销售价",
        dataIndex: "minimum_sale_price",
        key: "minimum_sale_price",
        width: 105,
        align: "right",
        render: (v: number | null) => (
          <span className="product-number">{v != null ? `¥${v.toFixed(2)}` : "-"}</span>
        ),
      },
      {
        title: "加权成本",
        dataIndex: "weighted_avg_cost",
        key: "weighted_avg_cost",
        width: 95,
        align: "right",
        render: (v: number | null) => (
          <span className="product-number">{v != null ? `¥${v.toFixed(2)}` : "-"}</span>
        ),
      },
      {
        title: "币种",
        dataIndex: "currency",
        key: "currency",
        width: 60,
        align: "center",
        render: (v: string) => <span style={MONO}>{v || "CNY"}</span>,
      },
      {
        title: "最近销售",
        dataIndex: "last_sale_at",
        key: "last_sale_at",
        width: 140,
        render: (v: string | null) => formatDateTime(v),
      },
      {
        title: "操作",
        key: "actions",
        width: 80,
        align: "center",
        fixed: "right",
        render: (_: unknown, r: Product) => (
          <div
            style={{ display: "flex", justifyContent: "center", gap: 2 }}
            onClick={(e) => e.stopPropagation()}
          >
            <Tooltip title="查看详情">
              <Button
                type="text"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onOpenDetail(r)}
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
                  if (key === "delete")
                    Modal.confirm({
                      title: "确认删除产品",
                      content: `确定要删除 ${r.name} 吗？`,
                      okText: "删除",
                      cancelText: "取消",
                      okButtonProps: { danger: true },
                      onOk: () => onDelete(r.id),
                    });
                },
              }}
            >
              <Button type="text" size="small" icon={<EllipsisOutlined />} />
            </Dropdown>
          </div>
        ),
      },
    ],
    [onOpenDetail, onOpenEdit, onOpenQuickPrice, onOpenQuickSafety, onDelete],
  );
}
