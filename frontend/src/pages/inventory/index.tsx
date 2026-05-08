import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, message, Card, Row, Col, Statistic, List, Typography, Progress, InputNumber, Modal, Input, Space, Button } from "antd";
import { WarningOutlined, FallOutlined, RiseOutlined, SwapOutlined, ReloadOutlined, BarChartOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getInventory, getInventoryOverview, adjustInventory, getDemandForecast } from "../../api";
import type { InventoryItem } from "../../types";

const { Text } = Typography;

export default function InventoryList() {
  const [data, setData] = useState<InventoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [adjustProduct, setAdjustProduct] = useState<InventoryItem | null>(null);
  const [adjustQty, setAdjustQty] = useState(0);
  const [adjustReason, setAdjustReason] = useState("");
  const [adjusting, setAdjusting] = useState(false);
  const [forecastData, setForecastData] = useState<Record<string, unknown>[]>([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const navigate = useNavigate();

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const [invResp, ovResp] = await Promise.all([
        getInventory({ page: p, page_size: 20 }),
        getInventoryOverview(),
      ]);
      setData(invResp.data.data.list as InventoryItem[]);
      setTotal(invResp.data.data.total as number);
      if (ovResp.data.code === 0) setOverview(ovResp.data.data as Record<string, unknown>);
    } catch {
      message.error("加载库存失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetch(); }, [page]);

  useEffect(() => {
    setForecastLoading(true);
    getDemandForecast(undefined, 20)
      .then((r) => setForecastData((r.data.data || []) as Record<string, unknown>[]))
      .catch(() => {})
      .finally(() => setForecastLoading(false));
  }, []);

  const handleAdjust = async () => {
    if (!adjustProduct || adjustQty === 0) return;
    setAdjusting(true);
    try {
      await adjustInventory(
        adjustProduct.product_id,
        adjustProduct.warehouse_id,
        adjustQty,
        adjustReason || "manual",
      );
      message.success("库存调整成功");
      setAdjustModalOpen(false);
      fetch();
    } catch { message.error("调整失败"); }
    finally { setAdjusting(false); }
  };

  const openAdjust = (item: InventoryItem) => {
    setAdjustProduct(item);
    setAdjustQty(0);
    setAdjustReason("");
    setAdjustModalOpen(true);
  };

  const columns: ColumnsType<InventoryItem> = [
    {
      title: "仓库", dataIndex: "warehouse_name", key: "wh", width: 100,
      render: (v, r) => <a>{String(v || `#${r.warehouse_id}`)}</a>,
    },
    {
      title: "产品", dataIndex: "product_name", key: "prod", width: 180,
      render: (v, r) => <a onClick={() => navigate(`/products/${r.product_id}`)}>{String(v || `#${r.product_id}`)}</a>,
    },
    { title: "SKU", dataIndex: "sku", key: "sku", width: 100 },
    { title: "分类", dataIndex: "category", key: "cat", width: 60, render: (v) => v ? <Tag>{v}</Tag> : null },
    { title: "品牌", dataIndex: "brand_name", key: "brand", width: 80 },
    { title: "数量", dataIndex: "quantity", key: "qty", width: 60 },
    { title: "安全库存", dataIndex: "safety_stock", key: "safe", width: 70 },
    {
      title: "库存水位", key: "level", width: 120,
      render: (_: unknown, r) => {
        const qty = r.quantity || 0;
        const safe = r.safety_stock || 1;
        const pct = Math.min(100, Math.round((qty / Math.max(safe, 1)) * 100));
        return (
          <Progress
            percent={pct} size="small"
            status={qty <= safe ? "exception" : "success"}
            format={() => `${qty}/${safe}`}
          />
        );
      },
    },
    {
      title: "状态", key: "status", width: 60,
      render: (_: unknown, r) => {
        const qty = r.quantity || 0;
        const safe = r.safety_stock || 0;
        if (qty === 0) return <Tag color="red">缺货</Tag>;
        if (qty <= safe) return <Tag color="orange">低库存</Tag>;
        return <Tag color="green">正常</Tag>;
      },
    },
    {
      title: "操作", key: "action", width: 80,
      render: (_: unknown, r) => (
        <Button size="small" icon={<SwapOutlined />} onClick={() => openAdjust(r)}>调整</Button>
      ),
    },
  ];

  const restockList = overview?.restock_suggestions as Record<string, unknown>[] | undefined;
  const deadStockList = overview?.dead_stock as Record<string, unknown>[] | undefined;

  return (
    <div>
      {/* Intelligence Overview */}
      {overview && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="总库存" value={Number(overview.total_quantity)} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ borderColor: (overview.low_stock_items as number) > 0 ? "#ff4d4f" : undefined }}>
              <Statistic
                title={<span><WarningOutlined /> 低库存项</span>}
                value={Number(overview.low_stock_items)}
                valueStyle={{ color: (overview.low_stock_items as number) > 0 ? "#ff4d4f" : undefined }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<span><FallOutlined /> 呆滞品</span>}
                value={Number(overview.dead_stock_items)}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<span><RiseOutlined /> 建议补货</span>}
                value={restockList?.length || 0}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Restock Suggestions */}
      {restockList && restockList.length > 0 && (
        <Card
          title={<span><RiseOutlined /> 补货建议</span>}
          size="small"
          style={{ marginBottom: 16, borderColor: "#faad14" }}
        >
          <List
            size="small"
            dataSource={restockList}
            renderItem={(s) => (
              <List.Item>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <span>
                    <a onClick={() => navigate(`/products/${s.product_id}`)}>
                      {String(s.sku || "")} {String(s.name || "")}
                    </a>
                    <Tag style={{ marginLeft: 8 }}>{String(s.category || "")}</Tag>
                  </span>
                  <Space>
                    <Text type="secondary">月均消耗: {String(s.monthly_rate)}</Text>
                    <Text>库存: {String(s.current_qty)}</Text>
                    <Tag color="blue">建议补: {String(s.suggested_order)}</Tag>
                    <Tag color={s.urgency === "紧急" ? "red" : s.urgency === "建议" ? "orange" : "default"}>
                      {String(s.urgency)}
                    </Tag>
                  </Space>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Dead Stock */}
      {deadStockList && deadStockList.length > 0 && (
        <Card
          title={<span><FallOutlined /> 呆滞库存（180天+ 未动）</span>}
          size="small"
          style={{ marginBottom: 16, borderColor: "#ff4d4f" }}
        >
          <List
            size="small"
            dataSource={deadStockList}
            renderItem={(s) => (
              <List.Item>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <span>
                    <a onClick={() => navigate(`/products/${s.product_id}`)}>
                      {String(s.sku || "")} {String(s.name || "")}
                    </a>
                    <Tag style={{ marginLeft: 8 }}>{String(s.category || "")}</Tag>
                  </span>
                  <Space>
                    <Text>库存: {String(s.quantity)} (仓库 #{String(s.warehouse_id)})</Text>
                    <Text type="danger">{String(s.suggestion)}</Text>
                  </Space>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Inventory Table */}
      <Card
        title="库存列表"
        extra={<Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>}
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          pagination={{
            current: page, total, pageSize: 20,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>

      {/* Adjust Modal */}
      <Modal
        title="库存调整"
        open={adjustModalOpen}
        onCancel={() => setAdjustModalOpen(false)}
        onOk={handleAdjust}
        confirmLoading={adjusting}
        okText="确认调整"
      >
        {adjustProduct && (
          <>
            <p>
              <Text strong>产品: </Text>
              {adjustProduct.product_name} ({adjustProduct.sku})
            </p>
            <p>
              <Text strong>仓库: </Text>
              {adjustProduct.warehouse_name || `#${adjustProduct.warehouse_id}`}
            </p>
            <p>
              <Text strong>当前库存: </Text>
              <Tag>{adjustProduct.quantity}</Tag>
              <Text type="secondary">安全库存: {adjustProduct.safety_stock}</Text>
            </p>
            <Space direction="vertical" style={{ width: "100%" }}>
              <div>
                <Text>调整数量（正数入库，负数出库）:</Text>
                <InputNumber
                  value={adjustQty}
                  onChange={(v) => setAdjustQty(v || 0)}
                  style={{ width: "100%", marginTop: 4 }}
                />
              </div>
              <div>
                <Text>原因:</Text>
                <Input
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  placeholder="手动调整/采购入库/盘点差异等"
                  style={{ marginTop: 4 }}
                />
              </div>
            </Space>
          </>
        )}
      </Modal>

      {/* Demand Forecast Section */}
      <Card
        title={<><BarChartOutlined /> AI 需求预测（前20）</>}
        style={{ marginTop: 24 }}
        loading={forecastLoading}
      >
        {forecastData.length > 0 ? (
          <Table
            size="small"
            dataSource={forecastData as Record<string, unknown>[]}
            rowKey="product_id"
            pagination={false}
            columns={[
              { title: "SKU", dataIndex: "sku", width: 100, ellipsis: true },
              { title: "产品名", dataIndex: "name", ellipsis: true },
              {
                title: "月预测需求", dataIndex: "monthly_forecast", width: 110,
                render: (v: number) => v != null ? v.toFixed(0) : "-",
              },
              {
                title: "趋势", dataIndex: "trend", width: 80,
                render: (t: string) => {
                  const color = t === "上升" ? "green" : t === "下降" || t === "衰退" ? "red" : t === "新增长" ? "blue" : "default";
                  return <Tag color={color}>{t}</Tag>;
                },
              },
              {
                title: "安全库存", dataIndex: "suggested_safety_stock", width: 90,
                render: (v: number, r: Record<string, unknown>) => {
                  const current = Number(r.current_safety_stock) || 0;
                  const suggested = Number(v) || 0;
                  const gap = suggested - current;
                  const color = gap > 10 ? "red" : gap > 0 ? "orange" : "green";
                  return <Tag color={color}>{suggested}{gap > 0 ? ` (+${gap})` : ""}</Tag>;
                },
              },
              {
                title: "置信度", dataIndex: "confidence", width: 70,
                render: (c: string) => <Tag color={c === "高" ? "green" : c === "中" ? "orange" : "red"}>{c}</Tag>,
              },
              { title: "交货期(天)", dataIndex: "lead_time_days", width: 80 },
            ]}
          />
        ) : (
          <Text type="secondary" style={{ display: "block", textAlign: "center", padding: 24 }}>
            暂无预测数据（需有销售历史记录）
          </Text>
        )}
      </Card>
    </div>
  );
}
