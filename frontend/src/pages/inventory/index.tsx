import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, message, Card, Row, Col, Statistic, List, Typography, Progress, InputNumber, Modal, Input, Space, Button, Select } from "antd";
import { StatusTag } from "../../ui";
import { WarningOutlined, FallOutlined, RiseOutlined, SwapOutlined, ReloadOutlined, BarChartOutlined, ShoppingCartOutlined, DownloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getInventory, getInventoryOverview, adjustInventory, getDemandForecast, createPOFromRestock, getSuppliers, batchAdjustInventory, getApiErrorMessage } from "../../api";
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
  const [restockModalOpen, setRestockModalOpen] = useState(false);
  const [restockSupplierId, setRestockSupplierId] = useState<number | null>(null);
  const [restockItems, setRestockItems] = useState<{ product_id: number; quantity: number; sku?: string; name?: string }[]>([]);
  const [restocking, setRestocking] = useState(false);
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载库存失败")); } finally {
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "调整失败")); }
    finally { setAdjusting(false); }
  };

  const openAdjust = (item: InventoryItem) => {
    setAdjustProduct(item);
    setAdjustQty(0);
    setAdjustReason("");
    setAdjustModalOpen(true);
  };

  const openRestockModal = async () => {
    const list = restockList as Record<string, unknown>[] | undefined;
    if (!list?.length) return;
    // Pre-fill from restock suggestions
    setRestockItems(list.map((s) => ({
      product_id: s.product_id as number,
      quantity: s.suggested_order as number,
      sku: s.sku as string,
      name: s.name as string,
    })));
    setRestockSupplierId(null);
    setRestockModalOpen(true);
    // Load suppliers if needed
    if (suppliers.length === 0) {
      try {
        const r = await getSuppliers({ page: 1, page_size: 100 });
        setSuppliers((r.data.data?.list || []) as { id: number; name: string }[]);
      } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载供应商列表失败")); }
    }
  };

  const handleRestock = async () => {
    if (!restockSupplierId || restockItems.length === 0) return;
    setRestocking(true);
    try {
      const payload = {
        supplier_id: restockSupplierId,
        items: restockItems.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
        notes: "AI补货建议一键生成",
      };
      await createPOFromRestock(payload);
      message.success("采购订单已生成，请前往采购模块查看");
      setRestockModalOpen(false);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "生成采购订单失败")); }
    finally { setRestocking(false); }
  };

  // --- Batch operations ---
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchAdjustQty, setBatchAdjustQty] = useState(0);
  const [batchReason, setBatchReason] = useState("batch");
  const [batching, setBatching] = useState(false);

  const handleBatchAdjust = async () => {
    if (selectedRowKeys.length === 0 || batchAdjustQty === 0) return;
    setBatching(true);
    try {
      const items = selectedRowKeys.map((key) => {
        const row = data.find((r) => r.id === Number(key));
        return {
          product_id: row!.product_id,
          warehouse_id: row!.warehouse_id,
          adjustment: batchAdjustQty,
          reason: batchReason,
        };
      });
      await batchAdjustInventory(items);
      message.success(`已批量调整 ${items.length} 项`);
      setBatchModalOpen(false);
      setSelectedRowKeys([]);
      fetch();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "批量调整失败")); }
    finally { setBatching(false); }
  };

  const handleBatchExport = () => {
    const rows = selectedRowKeys.length > 0
      ? data.filter((r) => selectedRowKeys.includes(r.id))
      : data;
    const header = "仓库,产品,SKU,分类,品牌,在库,已锁,可用,安全库存\n";
    const csv = header + rows.map((r) => {
      const avail = (r.quantity || 0) - (r.locked_quantity || 0);
      return `${r.warehouse_name || `#${r.warehouse_id}`},${r.product_name || ""},${r.sku || ""},${r.category || ""},${r.brand_name || ""},${r.quantity},${r.locked_quantity || 0},${avail},${r.safety_stock}`;
    }).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `库存导出_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已导出 ${rows.length} 条`);
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
    { title: "分类", dataIndex: "category", key: "cat", width: 60, render: (v) => v ? <StatusTag>{v}</StatusTag> : null },
    { title: "品牌", dataIndex: "brand_name", key: "brand", width: 80 },
    { title: "在库", dataIndex: "quantity", key: "qty", width: 60 },
    {
      title: "已锁", dataIndex: "locked_quantity", key: "locked", width: 50,
      render: (v: number) => v > 0 ? <StatusTag tone="warning">{v}</StatusTag> : <Text type="secondary">0</Text>,
    },
    {
      title: "可用", key: "available", width: 60,
      render: (_: unknown, r: InventoryItem) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        return <Text strong style={{ color: avail <= 0 ? "#ff4d4f" : "#52c41a" }}>{avail}</Text>;
      },
    },
    { title: "安全库存", dataIndex: "safety_stock", key: "safe", width: 70 },
    {
      title: "库存水位", key: "level", width: 120,
      render: (_: unknown, r) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        const safe = r.safety_stock || 1;
        const pct = Math.min(100, Math.round((avail / Math.max(safe, 1)) * 100));
        return (
          <Progress
            percent={pct} size="small"
            status={avail <= safe ? "exception" : "success"}
            format={() => `${avail}/${safe}`}
          />
        );
      },
    },
    {
      title: "状态", key: "status", width: 60,
      render: (_: unknown, r) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        const safe = r.safety_stock || 0;
        if (r.quantity === 0) return <StatusTag tone="danger">缺货</StatusTag>;
        if (avail <= 0) return <StatusTag tone="warning">已锁</StatusTag>;
        if (avail <= safe) return <StatusTag tone="warning">低库存</StatusTag>;
        return <StatusTag tone="success">正常</StatusTag>;
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
          extra={<Button type="primary" size="small" icon={<ShoppingCartOutlined />} onClick={openRestockModal}>一键补货</Button>}
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
                    <StatusTag style={{ marginLeft: 8 }}>{String(s.category || "")}</StatusTag>
                  </span>
                  <Space>
                    <Text type="secondary">月均消耗: {String(s.monthly_rate)}</Text>
                    <Text>库存: {String(s.current_qty)}</Text>
                    <StatusTag tone="info">建议补: {String(s.suggested_order)}</StatusTag>
                    <StatusTag tone={s.urgency === "紧急" ? "danger" : s.urgency === "建议" ? "warning" : "neutral"}>
                      {String(s.urgency)}
                    </StatusTag>
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
                    <StatusTag style={{ marginLeft: 8 }}>{String(s.category || "")}</StatusTag>
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
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <>
                <Button size="small" icon={<SwapOutlined />} onClick={() => setBatchModalOpen(true)}>
                  批量调整 ({selectedRowKeys.length})
                </Button>
                <Button size="small" icon={<DownloadOutlined />} onClick={handleBatchExport}>
                  导出 ({selectedRowKeys.length})
                </Button>
              </>
            )}
            <Button size="small" icon={<DownloadOutlined />} onClick={handleBatchExport}>全部导出</Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetch()}>刷新</Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="small"
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
          }}
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
              <Text strong>在库: </Text>
              <StatusTag>{adjustProduct.quantity}</StatusTag>
              <Text type="secondary"> | 已锁: {adjustProduct.locked_quantity || 0}</Text>
              <Text type="secondary"> | 可用: {(adjustProduct.quantity || 0) - (adjustProduct.locked_quantity || 0)}</Text>
              <Text type="secondary"> | 安全库存: {adjustProduct.safety_stock}</Text>
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

      {/* Restock Modal */}
      <Modal
        title="一键补货 — 生成采购订单"
        open={restockModalOpen}
        onCancel={() => setRestockModalOpen(false)}
        onOk={handleRestock}
        confirmLoading={restocking}
        okText="生成采购订单"
        width={640}
      >
        <div style={{ marginBottom: 16 }}>
          <Text strong>选择供应商: </Text>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="搜索并选择供应商"
            value={restockSupplierId}
            onChange={(v) => setRestockSupplierId(v)}
            style={{ width: "100%", marginTop: 8 }}
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          />
        </div>
        <div>
          <Text strong>补货清单:</Text>
          <Table
            size="small"
            style={{ marginTop: 8 }}
            dataSource={restockItems.map((item, idx) => ({ ...item, key: idx }))}
            rowKey="key"
            pagination={false}
            columns={[
              { title: "SKU", dataIndex: "sku", width: 100 },
              { title: "产品", dataIndex: "name", ellipsis: true },
              {
                title: "补货数量", dataIndex: "quantity", width: 100,
                render: (_: unknown, r: Record<string, unknown>, idx: number) => (
                  <InputNumber
                    min={1}
                    value={r.quantity as number}
                    onChange={(v) => {
                      const next = [...restockItems];
                      next[idx] = { ...next[idx], quantity: v || 1 };
                      setRestockItems(next);
                    }}
                  />
                ),
              },
            ]}
          />
        </div>
      </Modal>

      {/* Batch Adjust Modal */}
      <Modal
        title={`批量调整库存 (${selectedRowKeys.length} 项)`}
        open={batchModalOpen}
        onCancel={() => setBatchModalOpen(false)}
        onOk={handleBatchAdjust}
        confirmLoading={batching}
        okText="确认调整"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>
            <Text>调整数量（正数入库，负数出库）:</Text>
            <InputNumber
              value={batchAdjustQty}
              onChange={(v) => setBatchAdjustQty(v || 0)}
              style={{ width: "100%", marginTop: 4 }}
            />
          </div>
          <div>
            <Text>原因:</Text>
            <Input
              value={batchReason}
              onChange={(e) => setBatchReason(e.target.value)}
              placeholder="批量调整/盘点差异等"
              style={{ marginTop: 4 }}
            />
          </div>
        </Space>
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
                  return <StatusTag tone={color}>{t}</StatusTag>;
                },
              },
              {
                title: "安全库存", dataIndex: "suggested_safety_stock", width: 90,
                render: (v: number, r: Record<string, unknown>) => {
                  const current = Number(r.current_safety_stock) || 0;
                  const suggested = Number(v) || 0;
                  const gap = suggested - current;
                  const color = gap > 10 ? "red" : gap > 0 ? "orange" : "green";
                  return <StatusTag tone={color}>{suggested}{gap > 0 ? ` (+${gap})` : ""}</StatusTag>;
                },
              },
              {
                title: "置信度", dataIndex: "confidence", width: 70,
                render: (c: string) => <StatusTag tone={c === "高" ? "success" : c === "中" ? "warning" : "danger"}>{c}</StatusTag>,
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
