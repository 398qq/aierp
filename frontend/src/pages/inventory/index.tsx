import { useEffect, useState } from "react";
import { useNavigate } from "@/router";
import {
  Table,
  message,
  Typography,
  Progress,
  InputNumber,
  Modal,
  Input,
  Space,
  Button,
  Select,
} from "antd";
import {
  WarningOutlined,
  FallOutlined,
  RiseOutlined,
  SwapOutlined,
  ReloadOutlined,
  BarChartOutlined,
  ShoppingCartOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getInventory,
  getInventoryOverview,
  adjustInventory,
  getDemandForecast,
  createPOFromRestock,
  getSuppliers,
  batchAdjustInventory,
  getApiErrorMessage,
} from "../../api";
import type { InventoryItem } from "../../types";
import { erpPagination } from "../../ui/pagination";
import "./neo-brutalist.css";

const { Text } = Typography;

export default function InventoryList() {
  const [data, setData] = useState<InventoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
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
  const [restockItems, setRestockItems] = useState<
    { product_id: number; quantity: number; sku?: string; name?: string }[]
  >([]);
  const [restocking, setRestocking] = useState(false);
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  const navigate = useNavigate();

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const [invResp, ovResp] = await Promise.all([
        getInventory({ page: p, page_size: pageSize }),
        getInventoryOverview(),
      ]);
      setData(invResp.data.data.list as InventoryItem[]);
      setTotal(invResp.data.data.total as number);
      if (ovResp.data.code === 0) setOverview(ovResp.data.data as Record<string, unknown>);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载库存失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, [page, pageSize]);

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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "调整失败"));
    } finally {
      setAdjusting(false);
    }
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
    setRestockItems(
      list.map((s) => ({
        product_id: s.product_id as number,
        quantity: s.suggested_order as number,
        sku: s.sku as string,
        name: s.name as string,
      })),
    );
    setRestockSupplierId(null);
    setRestockModalOpen(true);
    if (suppliers.length === 0) {
      try {
        const r = await getSuppliers({ page: 1, page_size: 100 });
        setSuppliers((r.data.data?.list || []) as { id: number; name: string }[]);
      } catch (e: unknown) {
        message.error(getApiErrorMessage(e, "加载供应商列表失败"));
      }
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "生成采购订单失败"));
    } finally {
      setRestocking(false);
    }
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量调整失败"));
    } finally {
      setBatching(false);
    }
  };

  const handleBatchExport = () => {
    const rows =
      selectedRowKeys.length > 0 ? data.filter((r) => selectedRowKeys.includes(r.id)) : data;
    const header = "仓库,产品,SKU,分类,品牌,在库,已锁,可用,安全库存\n";
    const csv =
      header +
      rows
        .map((r) => {
          const avail = (r.quantity || 0) - (r.locked_quantity || 0);
          return `${r.warehouse_name || `#${r.warehouse_id}`},${r.product_name || ""},${r.sku || ""},${r.category || ""},${r.brand_name || ""},${r.quantity},${r.locked_quantity || 0},${avail},${r.safety_stock}`;
        })
        .join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `库存导出_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已导出 ${rows.length} 条`);
  };

  const tagTone = (tone: string): string => {
    switch (tone) {
      case "success":
        return "nb-tag--success";
      case "danger":
        return "nb-tag--danger";
      case "warning":
        return "nb-tag--warning";
      case "info":
        return "nb-tag--info";
      default:
        return "nb-tag--neutral";
    }
  };

  const columns: ColumnsType<InventoryItem> = [
    {
      title: "仓库",
      dataIndex: "warehouse_name",
      key: "wh",
      width: 100,
      render: (v) => (
        <a
          style={{
            fontWeight: 700,
            color: "var(--nb-text)",
            textDecoration: "underline",
            textDecorationThickness: 2,
            textUnderlineOffset: 3,
          }}
        >
          {String(v || "未知仓库")}
        </a>
      ),
    },
    {
      title: "产品",
      dataIndex: "product_name",
      key: "prod",
      width: 180,
      render: (v, r) => (
        <a
          onClick={() => navigate(`/products/${r.product_id}`)}
          style={{
            fontWeight: 700,
            color: "var(--nb-text)",
            textDecoration: "underline",
            textDecorationThickness: 2,
            textUnderlineOffset: 3,
          }}
        >
          {String(v || `#${r.product_id}`)}
        </a>
      ),
    },
    {
      title: "SKU",
      dataIndex: "sku",
      key: "sku",
      width: 100,
      render: (v: string) =>
        v ? (
          <span style={{ fontFamily: "var(--nb-font-mono)", fontSize: "0.8rem", fontWeight: 700 }}>
            {v}
          </span>
        ) : null,
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "cat",
      width: 60,
      render: (v) => (v ? <span className={`nb-tag ${tagTone("neutral")}`}>{v}</span> : null),
    },
    { title: "品牌", dataIndex: "brand_name", key: "brand", width: 80 },
    {
      title: "在库",
      dataIndex: "quantity",
      key: "qty",
      width: 60,
      render: (v: number) => (
        <span style={{ fontFamily: "var(--nb-font-mono)", fontWeight: 900, fontSize: "0.9rem" }}>
          {v}
        </span>
      ),
    },
    {
      title: "已锁",
      dataIndex: "locked_quantity",
      key: "locked",
      width: 50,
      render: (v: number) =>
        v > 0 ? (
          <span className="nb-tag nb-tag--warning">{v}</span>
        ) : (
          <Text type="secondary">0</Text>
        ),
    },
    {
      title: "可用",
      key: "available",
      width: 60,
      render: (_: unknown, r: InventoryItem) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        return (
          <span
            style={{
              fontFamily: "var(--nb-font-mono)",
              fontWeight: 900,
              color: avail <= 0 ? "var(--nb-red)" : "var(--nb-green)",
              fontSize: "0.9rem",
            }}
          >
            {avail}
          </span>
        );
      },
    },
    {
      title: "安全库存",
      dataIndex: "safety_stock",
      key: "safe",
      width: 70,
      render: (v: number) => <span style={{ fontFamily: "var(--nb-font-mono)" }}>{v}</span>,
    },
    {
      title: "库存水位",
      key: "level",
      width: 120,
      render: (_: unknown, r) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        const safe = r.safety_stock || 1;
        const pct = Math.min(100, Math.round((avail / Math.max(safe, 1)) * 100));
        return (
          <Progress
            className="nb-progress"
            percent={pct}
            size="small"
            status={avail <= safe ? "exception" : "success"}
            format={() => `${avail}/${safe}`}
          />
        );
      },
    },
    {
      title: "状态",
      key: "status",
      width: 60,
      render: (_: unknown, r) => {
        const avail = (r.quantity || 0) - (r.locked_quantity || 0);
        const safe = r.safety_stock || 0;
        if (r.quantity === 0) return <span className="nb-tag nb-tag--danger">缺货</span>;
        if (avail <= 0) return <span className="nb-tag nb-tag--warning">已锁</span>;
        if (avail <= safe) return <span className="nb-tag nb-tag--warning">低库存</span>;
        return <span className="nb-tag nb-tag--success">正常</span>;
      },
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_: unknown, r) => (
        <Button
          size="small"
          className="nb-btn nb-btn--small"
          icon={<SwapOutlined />}
          onClick={() => openAdjust(r)}
        >
          调整
        </Button>
      ),
    },
  ];

  const restockList = overview?.restock_suggestions as Record<string, unknown>[] | undefined;
  const deadStockList = overview?.dead_stock as Record<string, unknown>[] | undefined;

  return (
    <div className="nb-page">
      {/* ===== HEADER ===== */}
      <header className="nb-header">
        <h1 className="nb-header-title">库存管理</h1>
        <p className="nb-header-subtitle">INVENTORY CONTROL</p>
        <div className="nb-header-underline" />
        <div className="nb-header-actions">
          <button
            className="nb-btn nb-btn--primary"
            onClick={() => setBatchModalOpen(true)}
            disabled={selectedRowKeys.length === 0}
          >
            <SwapOutlined /> 批量调整
            {selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ""}
          </button>
          <button className="nb-btn nb-btn--info" onClick={handleBatchExport}>
            <DownloadOutlined /> 导出{" "}
            {selectedRowKeys.length > 0 ? `(${selectedRowKeys.length})` : "全部"}
          </button>
          <button className="nb-btn" onClick={() => fetch()}>
            <ReloadOutlined /> 刷新
          </button>
        </div>
      </header>

      {/* ===== KPI BAND ===== */}
      {overview && (
        <div className="nb-kpi-grid">
          <div className="nb-kpi-card nb-kpi-card--default">
            <p className="nb-kpi-label">📦 TOTAL QTY</p>
            <p className="nb-kpi-value">{String(overview.total_quantity ?? 0)}</p>
          </div>
          <div
            className={`nb-kpi-card ${Number(overview.low_stock_items ?? 0) > 0 ? "nb-kpi-card--alert" : "nb-kpi-card--default"}`}
          >
            <p className="nb-kpi-label">
              <WarningOutlined /> LOW STOCK
            </p>
            <p className="nb-kpi-value">{String(overview.low_stock_items ?? 0)}</p>
          </div>
          <div className="nb-kpi-card nb-kpi-card--alert">
            <p className="nb-kpi-label">
              <FallOutlined /> DEAD STOCK
            </p>
            <p className="nb-kpi-value">{String(overview.dead_stock_items ?? 0)}</p>
          </div>
          <div className="nb-kpi-card nb-kpi-card--info">
            <p className="nb-kpi-label">
              <RiseOutlined /> RESTOCK
            </p>
            <p className="nb-kpi-value">{String(restockList?.length || 0)}</p>
          </div>
        </div>
      )}

      {/* ===== RESTOCK SUGGESTIONS ===== */}
      {restockList && restockList.length > 0 && (
        <div className="nb-card nb-card--info" style={{ marginBottom: 24 }}>
          <div className="nb-card-header">
            <h3>
              <RiseOutlined /> 补货建议
            </h3>
            <button className="nb-btn nb-btn--primary nb-btn--small" onClick={openRestockModal}>
              <ShoppingCartOutlined /> 一键补货
            </button>
          </div>
          {restockList.map((s, i) => (
            <div key={i} className="nb-list-item">
              <div className="nb-list-item-meta">
                <a onClick={() => navigate(`/products/${s.product_id}`)}>
                  {String(s.sku || "")} {String(s.name || "")}
                </a>
                <span className="nb-tag nb-tag--neutral">{String(s.category || "")}</span>
              </div>
              <div className="nb-list-item-actions">
                <Text type="secondary">月均: {String(s.monthly_rate)}</Text>
                <Text>库存: {String(s.current_qty)}</Text>
                <span className="nb-tag nb-tag--info">补 {String(s.suggested_order)}</span>
                <span
                  className={`nb-tag ${s.urgency === "紧急" ? "nb-tag--danger" : s.urgency === "建议" ? "nb-tag--warning" : "nb-tag--neutral"}`}
                >
                  {String(s.urgency)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ===== DEAD STOCK ===== */}
      {deadStockList && deadStockList.length > 0 && (
        <div className="nb-card nb-card--alert" style={{ marginBottom: 24 }}>
          <div className="nb-card-header">
            <h3>
              <FallOutlined /> 呆滞库存（180天+ 未动）
            </h3>
          </div>
          {deadStockList.map((s, i) => (
            <div key={i} className="nb-list-item">
              <div className="nb-list-item-meta">
                <a onClick={() => navigate(`/products/${s.product_id}`)}>
                  {String(s.sku || "")} {String(s.name || "")}
                </a>
                <span className="nb-tag nb-tag--neutral">{String(s.category || "")}</span>
              </div>
              <div className="nb-list-item-actions">
                <Text>
                  库存: {String(s.quantity)}（{String(s.warehouse_name || "未知仓库")}）
                </Text>
                <span className="nb-tag nb-tag--danger">{String(s.suggestion)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ===== INVENTORY TABLE ===== */}
      <div className="nb-card nb-table-card" style={{ marginBottom: 24 }}>
        <div className="nb-card-header">
          <h3>库存列表</h3>
          <Space>
            {selectedRowKeys.length > 0 && (
              <>
                <button className="nb-btn nb-btn--small" onClick={() => setBatchModalOpen(true)}>
                  <SwapOutlined /> 批量调整 ({selectedRowKeys.length})
                </button>
                <button className="nb-btn nb-btn--small" onClick={handleBatchExport}>
                  <DownloadOutlined /> 导出 ({selectedRowKeys.length})
                </button>
              </>
            )}
            <button className="nb-btn nb-btn--small" onClick={handleBatchExport}>
              <DownloadOutlined /> 全部导出
            </button>
            <button className="nb-btn nb-btn--small" onClick={() => fetch()}>
              <ReloadOutlined /> 刷新
            </button>
          </Space>
        </div>
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
          pagination={erpPagination({
            current: page,
            total,
            pageSize,
            onChange: (p, ps) => { setPage(ps !== pageSize ? 1 : p); setPageSize(ps); },
          })}
        />
      </div>

      {/* ===== DEMAND FORECAST ===== */}
      <div className="nb-card nb-forecast-card" style={{ background: "var(--nb-white)" }}>
        <div className="nb-card-header">
          <h3>
            <BarChartOutlined /> AI 需求预测（前20）
          </h3>
        </div>
        {forecastLoading ? (
          <div className="nb-empty">LOADING...</div>
        ) : forecastData.length > 0 ? (
          <Table
            size="small"
            dataSource={forecastData as Record<string, unknown>[]}
            rowKey="product_id"
            pagination={false}
            columns={[
              {
                title: "SKU",
                dataIndex: "sku",
                width: 100,
                ellipsis: true,
                render: (v: string) => (
                  <span style={{ fontFamily: "var(--nb-font-mono)", fontWeight: 700 }}>{v}</span>
                ),
              },
              { title: "产品名", dataIndex: "name", ellipsis: true },
              {
                title: "月预测需求",
                dataIndex: "monthly_forecast",
                width: 110,
                render: (v: number) =>
                  v != null ? (
                    <span style={{ fontFamily: "var(--nb-font-mono)", fontWeight: 900 }}>
                      {v.toFixed(0)}
                    </span>
                  ) : (
                    "-"
                  ),
              },
              {
                title: "趋势",
                dataIndex: "trend",
                width: 80,
                render: (t: string) => {
                  const tone =
                    t === "上升"
                      ? "nb-tag--success"
                      : t === "下降" || t === "衰退"
                        ? "nb-tag--danger"
                        : t === "新增长"
                          ? "nb-tag--info"
                          : "nb-tag--neutral";
                  return <span className={`nb-tag ${tone}`}>{t}</span>;
                },
              },
              {
                title: "安全库存",
                dataIndex: "suggested_safety_stock",
                width: 90,
                render: (v: number, r: Record<string, unknown>) => {
                  const current = Number(r.current_safety_stock) || 0;
                  const suggested = Number(v) || 0;
                  const gap = suggested - current;
                  const tone =
                    gap > 10 ? "nb-tag--danger" : gap > 0 ? "nb-tag--warning" : "nb-tag--success";
                  return (
                    <span className={`nb-tag ${tone}`}>
                      {suggested}
                      {gap > 0 ? ` (+${gap})` : ""}
                    </span>
                  );
                },
              },
              {
                title: "置信度",
                dataIndex: "confidence",
                width: 70,
                render: (c: string) => {
                  const tone =
                    c === "高"
                      ? "nb-tag--success"
                      : c === "中"
                        ? "nb-tag--warning"
                        : "nb-tag--danger";
                  return <span className={`nb-tag ${tone}`}>{c}</span>;
                },
              },
              { title: "交货期(天)", dataIndex: "lead_time_days", width: 80 },
            ]}
          />
        ) : (
          <div className="nb-empty">暂无预测数据（需有销售历史记录）</div>
        )}
      </div>

      {/* ===== ADJUST MODAL ===== */}
      <Modal
        className="nb-modal"
        title="库存调整"
        open={adjustModalOpen}
        onCancel={() => setAdjustModalOpen(false)}
        onOk={handleAdjust}
        confirmLoading={adjusting}
        okText="确认调整"
      >
        {adjustProduct && (
          <div className="nb-input">
            <p>
              <Text strong>产品: </Text>
              {adjustProduct.product_name} ({adjustProduct.sku})
            </p>
            <p>
              <Text strong>仓库: </Text>
              {adjustProduct.warehouse_name || "未知仓库"}
            </p>
            <p>
              <Text strong>在库: </Text>
              <span className="nb-tag nb-tag--neutral">{adjustProduct.quantity}</span>
              <Text type="secondary"> | 已锁: {adjustProduct.locked_quantity || 0}</Text>
              <Text type="secondary">
                {" "}
                | 可用: {(adjustProduct.quantity || 0) - (adjustProduct.locked_quantity || 0)}
              </Text>
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
          </div>
        )}
      </Modal>

      {/* ===== RESTOCK MODAL ===== */}
      <Modal
        className="nb-modal"
        title="一键补货 — 生成采购订单"
        open={restockModalOpen}
        onCancel={() => setRestockModalOpen(false)}
        onOk={handleRestock}
        confirmLoading={restocking}
        okText="生成采购订单"
        width={640}
      >
        <div className="nb-input">
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
                  title: "补货数量",
                  dataIndex: "quantity",
                  width: 100,
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
        </div>
      </Modal>

      {/* ===== BATCH ADJUST MODAL ===== */}
      <Modal
        className="nb-modal"
        title={`批量调整库存 (${selectedRowKeys.length} 项)`}
        open={batchModalOpen}
        onCancel={() => setBatchModalOpen(false)}
        onOk={handleBatchAdjust}
        confirmLoading={batching}
        okText="确认调整"
      >
        <div className="nb-input">
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
        </div>
      </Modal>
    </div>
  );
}
