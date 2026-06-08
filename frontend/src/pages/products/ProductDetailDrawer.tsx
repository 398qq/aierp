// ProductDetailDrawer — right-side drawer with product profile, basic
// fields, inventory-by-warehouse table, and recent sales list.

import {
  Card,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  List,
  Space,
  Table,
} from "antd";
import { StatusTag } from "../../ui";
import type { InventoryItem, Product } from "../../types";
import { formatDateTime, getAvailableQty, ProductSalesData } from "./constants";

interface Props {
  open: boolean;
  loading: boolean;
  product: Product | null;
  inventories: InventoryItem[];
  sales: ProductSalesData | null;
  onClose: () => void;
}

export default function ProductDetailDrawer({
  open,
  loading,
  product,
  inventories,
  sales,
  onClose,
}: Props) {
  return (
    <Drawer
      title={product ? `产品详情 - ${product.name}` : "产品详情"}
      placement="right"
      width={680}
      open={open}
      onClose={onClose}
    >
      {loading ? (
        <Card loading />
      ) : !product ? (
        <Empty description="暂无详情" />
      ) : (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="SKU">{product.sku || "-"}</Descriptions.Item>
            <Descriptions.Item label="品牌">{product.brand_name || "-"}</Descriptions.Item>
            <Descriptions.Item label="分类">{product.category || "-"}</Descriptions.Item>
            <Descriptions.Item label="封装">{product.package_type || "-"}</Descriptions.Item>
            <Descriptions.Item label="单位">{product.unit || "-"}</Descriptions.Item>
            <Descriptions.Item label="最近销售">{formatDateTime(product.last_sale_at)}</Descriptions.Item>
            <Descriptions.Item label="资料完整度">{product.completion_score ?? 0}%</Descriptions.Item>
            <Descriptions.Item label="供应商数">{product.supplier_count ?? 0}</Descriptions.Item>
            <Descriptions.Item label="分仓数">{product.inventory_location_count ?? 0}</Descriptions.Item>
            <Descriptions.Item label="总库存">{product.quantity ?? 0}</Descriptions.Item>
            <Descriptions.Item label="可用库存">{getAvailableQty(product)}</Descriptions.Item>
            <Descriptions.Item label="锁定库存">{product.locked_quantity ?? 0}</Descriptions.Item>
            <Descriptions.Item label="规格" span={2}>{product.specs || "-"}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{product.notes || "-"}</Descriptions.Item>
          </Descriptions>

          <Divider style={{ margin: "4px 0" }}>库存分仓</Divider>
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={inventories}
            columns={[
              { title: "仓库", dataIndex: "warehouse_name", width: 120 },
              { title: "库存", dataIndex: "quantity", width: 90, align: "right" },
              { title: "可用", dataIndex: "available_quantity", width: 90, align: "right" },
              { title: "锁定", dataIndex: "locked_quantity", width: 90, align: "right" },
              { title: "安全库存", dataIndex: "safety_stock", width: 100, align: "right" },
              { title: "单价", dataIndex: "unit_price", width: 100, align: "right", render: (v: number | null) => (v != null ? `¥${Number(v).toFixed(2)}` : "-") },
            ]}
          />

          <Divider style={{ margin: "4px 0" }}>最近销售动作</Divider>
          <List
            size="small"
            bordered
            dataSource={sales?.orders || []}
            locale={{ emptyText: "暂无销售订单记录" }}
            renderItem={(item) => {
              const row = item as { order_no?: string; status?: string; quantity?: number; unit_price?: number; created_at?: string };
              return (
                <List.Item>
                  <Space split={<span>|</span>} size={4}>
                    <span>{row.order_no || "-"}</span>
                    <StatusTag>{row.status || "-"}</StatusTag>
                    <span>数量 {row.quantity || 0}</span>
                    <span>单价 {row.unit_price != null ? `¥${Number(row.unit_price).toFixed(2)}` : "-"}</span>
                    <span>{formatDateTime(row.created_at || null)}</span>
                  </Space>
                </List.Item>
              );
            }}
          />
        </Space>
      )}
    </Drawer>
  );
}
