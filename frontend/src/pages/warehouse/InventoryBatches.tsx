import { useEffect, useState } from "react";
import {
  Card, Table, Tag, Space, Typography, Select, Input, Button, InputNumber,
  Modal, Radio, message, Divider,
} from "antd";
import {
  SearchOutlined, CheckCircleOutlined, CalculatorOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getInventoryBatches, getInventoryCogs, previewAllocation, commitBatchAllocation, getApiErrorMessage } from "../../api";
import type { InventoryBatch, CogsReport } from "../../types";
import { erpPagination } from "../../ui/pagination";

const { Text, Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  available: "green", consumed: "default", quarantined: "orange", expired: "red",
};

const money = (v: number) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(v || 0);

export default function InventoryBatches() {
  const [batches, setBatches] = useState<InventoryBatch[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [cogs, setCogs] = useState<CogsReport | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  // Manual allocation state
  const [modalOpen, setModalOpen] = useState(false);
  const [strategy, setStrategy] = useState<string>("lowest_cost_first");
  const [manualPicks, setManualPicks] = useState<Record<number, number>>({});
  const [previewResult, setPreviewResult] = useState<{
    allocations: { batch_id: number; batch_no: string; quantity: number; unit_cost: number; line_cost: number }[];
    total_cost: number;
    weighted_unit_cost: number;
    unfilled_qty: number;
    is_fully_allocated: boolean;
  } | null>(null);
  const [committing, setCommitting] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const loadBatches = async (requestedPage = page, requestedPageSize = pageSize) => {
    setLoading(true);
    try {
      const r = await getInventoryBatches({ page: requestedPage, page_size: requestedPageSize, status: statusFilter || "available" });
      setBatches(r.data.data.list);
      setTotal(r.data.data.total);
    } catch { /* handled by interceptor */ }
    finally { setLoading(false); }
  };

  const loadCogs = async () => {
    try {
      const r = await getInventoryCogs();
      setCogs(r.data.data);
    } catch { /* */ }
  };

  useEffect(() => { loadBatches(); }, [page, pageSize, statusFilter]);
  useEffect(() => { loadCogs(); }, []);

  // ── Manual Allocation Handlers ──

  const openManualAlloc = () => {
    setManualPicks({});
    setPreviewResult(null);
    setModalOpen(true);
  };

  const handlePreview = async () => {
    // If user has manually set quantities, use manual picks
    const picks = Object.entries(manualPicks)
      .filter(([, qty]) => qty > 0)
      .map(([batchId, qty]) => ({ batch_id: Number(batchId), quantity: qty }));

    if (picks.length > 0) {
      // Manual: validate via commit preview (we'll use allocate API to check)
      setPreviewing(true);
      try {
        const r = await previewAllocation({
          product_id: batches[0]?.product_id || 0,
          warehouse_id: batches[0]?.warehouse_id || 0,
          quantity: picks.reduce((s, p) => s + p.quantity, 0),
          strategy: "lowest_cost_first",
        } as any);
        // For manual, compute cost from selected batches
        const manualAllocations = picks.map((p) => {
          const batch = batches.find((b) => b.id === p.batch_id);
          return {
            batch_id: p.batch_id,
            batch_no: batch?.batch_no || "",
            quantity: p.quantity,
            unit_cost: batch?.unit_cost || 0,
            line_cost: Math.round(p.quantity * (batch?.unit_cost || 0) * 100) / 100,
          };
        });
        const totalCost = manualAllocations.reduce((s, a) => s + a.line_cost, 0);
        setPreviewResult({
          allocations: manualAllocations,
          total_cost: totalCost,
          weighted_unit_cost: picks.length ? totalCost / picks.reduce((s, p) => s + p.quantity, 0) : 0,
          unfilled_qty: 0,
          is_fully_allocated: true,
        });
      } catch (e: unknown) { message.error(getApiErrorMessage(e, "预览失败")); }
      finally { setPreviewing(false); }
    } else {
      // Auto: use strategy-based allocation
      setPreviewing(true);
      try {
        const r = await previewAllocation({
          product_id: batches[0]?.product_id || 0,
          warehouse_id: batches[0]?.warehouse_id || 0,
          quantity: 100,
          strategy,
        } as any);
        setPreviewResult(r.data.data);
      } catch (e: unknown) { message.error(getApiErrorMessage(e, "预览失败")); }
      finally { setPreviewing(false); }
    }
  };

  const handleCommit = async () => {
    if (!previewResult || previewResult.allocations.length === 0) return;
    setCommitting(true);
    try {
      const picks = previewResult.allocations.map((a) => ({
        batch_id: a.batch_id,
        quantity: a.quantity,
      }));
      const r = await commitBatchAllocation({
        product_id: batches[0]?.product_id || 0,
        warehouse_id: batches[0]?.warehouse_id || 0,
        picks,
      });
      message.success(`出库成功！COGS: ${money(r.data.data.total_cogs)}`);
      setModalOpen(false);
      loadBatches();
    } catch (e: any) {
      message.error(e?.response?.data?.msg || "出库失败");
    } finally { setCommitting(false); }
  };

  // ── Columns ──

  const batchColumns: ColumnsType<InventoryBatch> = [
    { title: "批次号", dataIndex: "batch_no", width: 140 },
    { title: "产品", dataIndex: "product_name", width: 160, ellipsis: true,
      render: (v, r) => v || `产品 #${r.product_id}` },
    { title: "供应商", dataIndex: "supplier_name", width: 120, ellipsis: true, render: (v) => v || "-" },
    { title: "库存数量", dataIndex: "quantity", width: 90, align: "right" },
    { title: "进货单价", dataIndex: "unit_cost", width: 120, align: "right", render: (v: number) => money(v) },
    { title: "总成本", dataIndex: "total_value", width: 120, align: "right",
      render: (_: unknown, r: InventoryBatch) => money(r.quantity * r.unit_cost) },
    { title: "入库日期", dataIndex: "received_date", width: 110 },
    { title: "状态", dataIndex: "status", width: 80,
      render: (v: string) => <Tag color={STATUS_COLORS[v] || "default"}>{v}</Tag> },
  ];

  const cogsColumns: ColumnsType<CogsReport["items"][0]> = [
    { title: "产品", dataIndex: "product_name", ellipsis: true },
    { title: "销量", dataIndex: "quantity", width: 80, align: "right" },
    { title: "营收", dataIndex: "revenue", width: 130, align: "right", render: (v: number) => money(v) },
    { title: "成本", dataIndex: "cost", width: 130, align: "right", render: (v: number) => money(v) },
    { title: "毛利", dataIndex: "margin", width: 130, align: "right",
      render: (v: number) => <Text type={v >= 0 ? "success" : "danger"}>{money(v)}</Text> },
    { title: "毛利率", dataIndex: "margin_pct", width: 90, align: "right",
      render: (v: number) => <Text type={v >= 0 ? "success" : "danger"}>{v}%</Text> },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Title level={4}>库存批次管理</Title>

      <Card size="small" title="批次列表"
        extra={
          <Space>
            <Button type="primary" icon={<CheckCircleOutlined />}
              onClick={openManualAlloc} disabled={batches.length === 0}>
              手动出库
            </Button>
            <Select allowClear placeholder="状态" style={{ width: 120 }}
              value={statusFilter}
              onChange={(v) => setStatusFilter(v)}
              options={[
                { label: "可用", value: "available" },
                { label: "已消耗", value: "consumed" },
                { label: "已过期", value: "expired" },
              ]}
            />
            <Input prefix={<SearchOutlined />} placeholder="搜索批次号" style={{ width: 200 }} />
          </Space>
        }>
        <Table
          rowKey="id" columns={batchColumns} dataSource={batches}
          loading={loading} size="small"
          pagination={erpPagination({
            current: page,
            total,
            pageSize,
            onChange: (p, ps) => {
              setPage(ps !== pageSize ? 1 : p);
              setPageSize(ps);
            },
          })}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* ── Manual Allocation Modal ── */}
      <Modal
        title="手动出库（人工选择批次）"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setModalOpen(false)}>取消</Button>,
          <Button key="preview" icon={<CalculatorOutlined />} loading={previewing}
            onClick={handlePreview}>预览成本</Button>,
          <Button key="commit" type="primary" icon={<CheckCircleOutlined />} loading={committing}
            disabled={!previewResult || previewResult.allocations.length === 0}
            onClick={handleCommit}>确认出库</Button>,
        ]}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Radio.Group value={Object.keys(manualPicks).length > 0 ? "manual" : strategy}
            onChange={(e) => {
              if (e.target.value === "manual") {
                setStrategy("manual");
              } else {
                setStrategy(e.target.value);
                setManualPicks({});
                setPreviewResult(null);
              }
            }}>
            <Radio.Button value="lowest_cost_first">最低成本优先</Radio.Button>
            <Radio.Button value="fifo">先入先出 (FIFO)</Radio.Button>
            <Radio.Button value="manual">人工逐批指定</Radio.Button>
          </Radio.Group>

          {strategy === "manual" && (
            <Table
              rowKey="id"
              size="small"
              dataSource={batches}
              pagination={false}
              columns={[
                { title: "批次号", dataIndex: "batch_no", width: 120 },
                { title: "产品", dataIndex: "product_name", width: 140, ellipsis: true,
                  render: (v, r) => v || `#${r.product_id}` },
                { title: "可用库存", dataIndex: "quantity", width: 80, align: "right" },
                { title: "进货单价", dataIndex: "unit_cost", width: 100, align: "right",
                  render: (v: number) => money(v) },
                { title: "入库日期", dataIndex: "received_date", width: 100 },
                {
                  title: "本次出库数量", dataIndex: "id", width: 140,
                  render: (id: number, r: InventoryBatch) => (
                    <InputNumber
                      min={0} max={r.quantity} size="small" style={{ width: 100 }}
                      value={manualPicks[id] || 0}
                      onChange={(v) => setManualPicks((prev) => ({
                        ...prev, [id]: v || 0,
                      }))}
                    />
                  ),
                },
              ]}
            />
          )}

          {previewResult && (
            <>
              <Divider style={{ margin: "8px 0" }} />
              <Text strong>成本预览</Text>
              <Table
                rowKey="batch_id"
                size="small"
                dataSource={previewResult.allocations}
                pagination={false}
                columns={[
                  { title: "批次号", dataIndex: "batch_no", width: 120 },
                  { title: "数量", dataIndex: "quantity", width: 80, align: "right" },
                  { title: "单价", dataIndex: "unit_cost", width: 110, align: "right",
                    render: (v: number) => money(v) },
                  { title: "小计", dataIndex: "line_cost", width: 120, align: "right",
                    render: (v: number) => money(v) },
                ]}
              />
              <Space>
                <Text strong>总成本: {money(previewResult.total_cost)}</Text>
                <Text type="secondary">
                  加权单价: {money(previewResult.weighted_unit_cost)}
                </Text>
                {!previewResult.is_fully_allocated && (
                  <Text type="danger">
                    库存不足！缺 {previewResult.unfilled_qty} 件
                  </Text>
                )}
              </Space>
            </>
          )}
        </Space>
      </Modal>

      {cogs && (
        <Card size="small" title="销售成本 (COGS) 分析"
          extra={<Space>
            {cogs.summary && <>
              <Text type="secondary">总营收: {money(cogs.summary.total_revenue)}</Text>
              <Text type="secondary">总成本: {money(cogs.summary.total_cost)}</Text>
              <Text strong type={cogs.summary.total_margin >= 0 ? "success" : "danger"}>
                总毛利: {money(cogs.summary.total_margin)} ({cogs.summary.margin_pct}%)
              </Text>
            </>}
          </Space>}>
          <Table
            rowKey="product_id" columns={cogsColumns} dataSource={cogs.items || []}
            size="small" pagination={false} scroll={{ x: 700 }}
          />
        </Card>
      )}

    </Space>
  );
}
