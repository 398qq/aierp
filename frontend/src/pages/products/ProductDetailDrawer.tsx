import { Card, Descriptions, Drawer, Empty, Progress, Space, Table, Tabs, Typography } from "antd";
import { StatusTag } from "../../ui";
import type { InventoryItem, Product } from "../../types";
import { formatDateTime, getAvailableQty, getStockState, ProductSalesData } from "./constants";

const { Text, Title } = Typography;

interface Props {
  open: boolean;
  loading: boolean;
  product: Product | null;
  inventories: InventoryItem[];
  sales: ProductSalesData | null;
  onClose: () => void;
}

const money = (value?: number | null) => (value != null ? `¥${Number(value).toFixed(2)}` : "-");
const documentRowKey = (row: Record<string, unknown>) =>
  String(row.id || row.order_no || row.quotation_no || row.delivery_no || row.created_at);

export default function ProductDetailDrawer({
  open,
  loading,
  product,
  inventories,
  sales,
  onClose,
}: Props) {
  const stockState = product ? getStockState(product) : "in";
  const salesColumns = [
    {
      title: "单据编号",
      dataIndex: "order_no",
      key: "order_no",
      width: 150,
      render: (value: string) => value || "-",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (value: string) => <StatusTag status={value || "-"} />,
    },
    {
      title: "数量",
      dataIndex: "quantity",
      key: "quantity",
      width: 80,
      align: "right" as const,
      render: (value: number) => value || 0,
    },
    {
      title: "单价",
      dataIndex: "unit_price",
      key: "unit_price",
      width: 100,
      align: "right" as const,
      render: money,
    },
    {
      title: "日期",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: formatDateTime,
    },
  ];

  return (
    <Drawer
      title="产品运营详情"
      placement="right"
      size="large"
      open={open}
      onClose={onClose}
      className="product-detail-drawer"
    >
      {loading ? (
        <Card loading />
      ) : !product ? (
        <Empty description="暂无详情" />
      ) : (
        <div className="product-detail-content">
          <section className="product-detail-heading">
            <div>
              <Space size={8} wrap>
                <Title level={4}>{product.name}</Title>
                <StatusTag
                  tone={
                    stockState === "out" ? "danger" : stockState === "low" ? "warning" : "success"
                  }
                >
                  {stockState === "out" ? "缺货" : stockState === "low" ? "低库存" : "正常在库"}
                </StatusTag>
                {product.lifecycle_status && <StatusTag>{product.lifecycle_status}</StatusTag>}
              </Space>
              <Text type="secondary">
                {[
                  product.sku,
                  product.mpn,
                  product.brand_name,
                  product.category,
                  product.package_type,
                ]
                  .filter(Boolean)
                  .join(" / ") || "暂无产品标识"}
              </Text>
            </div>
            <div className="product-detail-completion">
              <Progress
                type="circle"
                size={64}
                percent={product.completion_score ?? 0}
                strokeColor={(product.completion_score ?? 0) >= 80 ? "#10b981" : "#f59e0b"}
              />
              <Text type="secondary">资料完整度</Text>
            </div>
          </section>

          <section className="product-detail-metrics">
            <div>
              <strong>{product.quantity ?? 0}</strong>
              <span>总库存</span>
            </div>
            <div className={getAvailableQty(product) <= 0 ? "is-risk" : ""}>
              <strong>{getAvailableQty(product)}</strong>
              <span>可用库存</span>
            </div>
            <div>
              <strong>{product.locked_quantity ?? 0}</strong>
              <span>锁定库存</span>
            </div>
            <div>
              <strong>{product.safety_stock ?? 0}</strong>
              <span>安全库存</span>
            </div>
            <div>
              <strong>{product.supplier_count ?? 0}</strong>
              <span>供应商</span>
            </div>
            <div>
              <strong>{product.inventory_location_count ?? 0}</strong>
              <span>分仓</span>
            </div>
          </section>

          <Card size="small" title="主数据">
            <Descriptions column={3} size="small">
              <Descriptions.Item label="SKU">{product.sku || "-"}</Descriptions.Item>
              <Descriptions.Item label="MPN">{product.mpn || "-"}</Descriptions.Item>
              <Descriptions.Item label="条码">{product.barcode || "-"}</Descriptions.Item>
              <Descriptions.Item label="品牌">{product.brand_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="分类">{product.category || "-"}</Descriptions.Item>
              <Descriptions.Item label="单位">{product.unit || "-"}</Descriptions.Item>
              <Descriptions.Item label="封装">{product.package_type || "-"}</Descriptions.Item>
              <Descriptions.Item label="封装尺寸">{product.package_case || "-"}</Descriptions.Item>
              <Descriptions.Item label="针脚数">{product.pin_count ?? "-"}</Descriptions.Item>
              <Descriptions.Item label="规格" span={3}>
                {product.specs || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={3}>
                {product.notes || "-"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card size="small" title="商务与合规">
            <Descriptions column={3} size="small">
              <Descriptions.Item label="标准成本">{money(product.standard_cost)}</Descriptions.Item>
              <Descriptions.Item label="目录价">{money(product.list_price)}</Descriptions.Item>
              <Descriptions.Item label="库存单价">{money(product.unit_price)}</Descriptions.Item>
              <Descriptions.Item label="币种">{product.currency || "-"}</Descriptions.Item>
              <Descriptions.Item label="税率">
                {product.tax_rate != null ? `${product.tax_rate}%` : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="生命周期">
                {product.lifecycle_status || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="RoHS">
                <StatusTag tone={product.rohs_compliant ? "success" : "neutral"}>
                  {product.rohs_compliant ? "符合" : "未确认"}
                </StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="REACH">
                <StatusTag tone={product.reach_compliant ? "success" : "neutral"}>
                  {product.reach_compliant ? "符合" : "未确认"}
                </StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="原产国">{product.origin_country || "-"}</Descriptions.Item>
              <Descriptions.Item label="HS 编码">{product.hs_code || "-"}</Descriptions.Item>
              <Descriptions.Item label="最近销售">
                {formatDateTime(product.last_sale_at)}
              </Descriptions.Item>
              <Descriptions.Item label="库存更新">
                {formatDateTime(product.inventory_updated_at)}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {product.missing_fields?.length ? (
            <div className="product-detail-warning">
              <Text strong>待完善字段</Text>
              <Space wrap>
                {product.missing_fields.map((field) => (
                  <StatusTag key={field} tone="warning">
                    {field}
                  </StatusTag>
                ))}
              </Space>
            </div>
          ) : null}

          <Card size="small" title={`库存分仓 (${inventories.length})`}>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={inventories}
              scroll={{ x: 680 }}
              columns={[
                { title: "仓库", dataIndex: "warehouse_name", width: 150, fixed: "left" },
                { title: "库存", dataIndex: "quantity", width: 90, align: "right" },
                { title: "可用", dataIndex: "available_quantity", width: 90, align: "right" },
                { title: "锁定", dataIndex: "locked_quantity", width: 90, align: "right" },
                { title: "安全库存", dataIndex: "safety_stock", width: 100, align: "right" },
                {
                  title: "状态",
                  key: "status",
                  width: 100,
                  render: (_: unknown, row: InventoryItem) => {
                    const available = row.available_quantity ?? 0;
                    const safety = row.safety_stock ?? 0;
                    return available <= 0 ? (
                      <StatusTag tone="danger">缺货</StatusTag>
                    ) : available <= safety ? (
                      <StatusTag tone="warning">低库存</StatusTag>
                    ) : (
                      <StatusTag tone="success">正常</StatusTag>
                    );
                  },
                },
                {
                  title: "单价",
                  dataIndex: "unit_price",
                  width: 100,
                  align: "right",
                  render: money,
                },
              ]}
            />
          </Card>

          <Card size="small" title="关联业务单据">
            <Tabs
              items={[
                {
                  key: "orders",
                  label: `销售订单 ${sales?.orders?.length || 0}`,
                  children: (
                    <Table
                      rowKey={documentRowKey}
                      size="small"
                      pagination={false}
                      dataSource={sales?.orders || []}
                      columns={salesColumns}
                    />
                  ),
                },
                {
                  key: "quotations",
                  label: `报价 ${sales?.quotations?.length || 0}`,
                  children: (
                    <Table
                      rowKey={documentRowKey}
                      size="small"
                      pagination={false}
                      dataSource={sales?.quotations || []}
                      columns={salesColumns}
                    />
                  ),
                },
                {
                  key: "deliveries",
                  label: `发货 ${sales?.deliveries?.length || 0}`,
                  children: (
                    <Table
                      rowKey={documentRowKey}
                      size="small"
                      pagination={false}
                      dataSource={sales?.deliveries || []}
                      columns={salesColumns}
                    />
                  ),
                },
              ]}
            />
          </Card>
        </div>
      )}
    </Drawer>
  );
}
