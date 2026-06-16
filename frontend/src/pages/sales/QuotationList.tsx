import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Dropdown, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tabs, Tag, Tooltip, Typography, message } from "antd";
import { StatusTag, type StatusTone } from "../../ui";
import type { MenuProps } from "antd";
import {
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EllipsisOutlined,
  FileDoneOutlined,
  PlusOutlined,
  ReloadOutlined,
  SendOutlined,
  ShoppingCartOutlined,
} from "@ant-design/icons";
import {
  batchDeleteQuotations,
  convertQuotationToOrder,
  deleteQuotation,
  downloadQuotationPDF,
  duplicateQuotation,
  getQuotationStats,
  getQuotations,
  sendQuotation,
} from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { Quotation, QuotationStats } from "../../types";
import { CustomerLink, CustomerSelect, MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, erpRowClass, money, shortDate, statusDot, ERP_STATUS_DOT } from "./salesUi";

type QuoteScene = "all" | "draft" | "sent" | "expiring" | "expired" | "won" | "lost";

const SCENE_LABELS: Record<QuoteScene, string> = {
  all: "全部报价",
  draft: "待发送",
  sent: "已发送待跟进",
  expiring: "即将过期",
  expired: "已过期",
  won: "已成交",
  lost: "已丢失",
};

const getDueMeta = (validUntil?: string | null, status?: string) => {
  if (!validUntil || status === "won" || status === "lost") return { text: "-", tone: "neutral" as StatusTone, scene: "normal" };
  const due = new Date(validUntil).getTime();
  if (Number.isNaN(due)) return { text: shortDate(validUntil), tone: "neutral" as StatusTone, scene: "normal" };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((due - today.getTime()) / (24 * 60 * 60 * 1000));
  if (diffDays < 0) return { text: `已过期 ${Math.abs(diffDays)} 天`, tone: "danger" as StatusTone, scene: "expired" };
  if (diffDays === 0) return { text: "今日到期", tone: "danger" as StatusTone, scene: "expiring" };
  if (diffDays <= 7) return { text: `${diffDays} 天后到期`, tone: "warning" as StatusTone, scene: "expiring" };
  return { text: shortDate(validUntil), tone: "info" as StatusTone, scene: "normal" };
};

export default function QuotationList() {
  const [data, setData] = useState<Quotation[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<QuotationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [scene, setScene] = useState<QuoteScene>("all");
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { pricing_health?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const status = ["draft", "sent", "won", "lost"].includes(scene) ? scene : undefined;

  const loadStats = async () => {
    try {
      const resp = await getQuotationStats();
      setStats(resp.data.data);
    } catch {
      // 页面主列表加载即可，统计失败不阻塞操作。
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20, sort_by: "updated_at", sort_order: "desc" };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      if (q.trim()) params.q = q.trim();
      if (includeAi) params.include_ai = true;
      const resp = await getQuotations(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { pricing_health?: string; flag?: string }> }).ai || {}) : {});
    } catch {
      message.error("加载报价失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, scene, customerId, q, includeAi]);

  useEffect(() => {
    loadStats();
  }, []);

  const visibleData = useMemo(() => {
    if (scene === "expiring") return data.filter((item) => getDueMeta(item.valid_until, item.status).scene === "expiring");
    if (scene === "expired") return data.filter((item) => getDueMeta(item.valid_until, item.status).scene === "expired");
    return data;
  }, [data, scene]);

  const pageStats = useMemo(() => {
    const amount = visibleData.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const sent = visibleData.filter((item) => item.status === "sent").length;
    const won = visibleData.filter((item) => item.status === "won").length;
    const itemCount = visibleData.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { amount, sent, won, itemCount };
  }, [visibleData]);

  const refreshAll = async () => {
    await Promise.all([load(), loadStats()]);
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeleteQuotations(selected);
      message.success("已批量删除");
      setSelected([]);
      refreshAll();
    } catch {
      message.error("删除失败");
    }
  };

  const handleDuplicate = async (record: Quotation) => {
    try {
      const resp = await duplicateQuotation(record.id);
      message.success("已复制为新报价");
      navigate(`/sales/quotations/${resp.data.data.id}/edit`);
    } catch {
      message.error("复制失败");
    }
  };

  const handleSend = async (record: Quotation) => {
    try {
      await sendQuotation(record.id);
      message.success("已标记为已发送");
      refreshAll();
    } catch {
      message.error("发送失败");
    }
  };

  const handleConvert = async (record: Quotation) => {
    try {
      await convertQuotationToOrder(record.id);
      message.success("已转为订单");
      refreshAll();
    } catch {
      message.error("转换失败");
    }
  };

  const sceneCount = (key: QuoteScene) => {
    if (!stats) return undefined;
    if (key === "all") return stats.total;
    if (key === "expiring") return stats.expiring_soon;
    if (key === "expired") return stats.expired;
    return stats[key];
  };

  return (
    <SalesModuleShell
      title="报价工作台"
      subtitle="处理待发送、临期、已发送待跟进报价，并推动报价转订单"
      activeKey="quotations"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "报价总数", value: stats?.total ?? total, suffix: "张" },
          { title: "报价总额", value: stats?.total_amount ?? pageStats.amount, prefix: "¥", precision: 0 },
          { title: "即将过期", value: stats?.expiring_soon ?? 0, suffix: "张" },
          { title: "已过期", value: stats?.expired ?? 0, suffix: "张" },
          { title: "成交金额", value: stats?.won_amount ?? 0, prefix: "¥", precision: 0 },
          { title: "转订单率", value: stats?.quote_to_order_rate ?? 0, suffix: "%", precision: 1 },
        ]}
      />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/quotations/new")}>新建报价</Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={refreshAll}>刷新</Button>
          <Input.Search
            allowClear
            placeholder="搜索客户 / 报价单 / 产品"
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              if (!event.target.value) {
                setPage(1);
                setQ("");
              }
            }}
            onSearch={(value) => {
              setPage(1);
              setQ(value);
            }}
            style={{ width: 280 }}
          />
          <div style={{ width: 280 }}>
            <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
          </div>
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={(next) => {
              setScene((next as QuoteScene) || "all");
              setPage(1);
            }}
            options={[
              { value: "draft", label: "草稿" },
              { value: "sent", label: "已发送" },
              { value: "won", label: "成交" },
              { value: "lost", label: "丢失" },
            ]}
          />
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除选中的报价?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除 {selected.length}</Button>
            </Popconfirm>
          ) : null}
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={(
          <Space size={8} wrap>
            <Typography.Text strong>报价单据</Typography.Text>
            <Typography.Text type="secondary">{visibleData.length} / {total} 张</Typography.Text>
            {selected.length > 0 && <StatusTag status={`已选 ${selected.length}`} tone="info" />}
          </Space>
        )}
      >
        <Tabs
          activeKey={scene}
          onChange={(key) => {
            setScene(key as QuoteScene);
            setPage(1);
          }}
          items={(Object.keys(SCENE_LABELS) as QuoteScene[]).map((key) => ({
            key,
            label: (
              <Space size={6}>
                <span>{SCENE_LABELS[key]}</span>
                {sceneCount(key) !== undefined && <StatusTag status={String(sceneCount(key))} tone={key === "expired" ? "danger" : key === "expiring" ? "warning" : "neutral"} />}
              </Space>
            ),
          }))}
        />
        <Table
          rowKey="id"
          size="small"
          bordered
          loading={loading}
          dataSource={visibleData}
          expandable={{
            expandedRowRender: (record: Quotation) => {
              const items = record.items || [];
              if (items.length === 0) return <Typography.Text type="secondary">无明细</Typography.Text>;
              return (
                <Table
                  rowKey="id"
                  size="small"
                  dataSource={items}
                  pagination={false}
                  columns={[
                    { title: "#", width: 40, render: (_: unknown, __: unknown, i: number) => i + 1 },
                    { title: "产品名称", dataIndex: "product_name", ellipsis: true },
                    { title: "数量", dataIndex: "quantity", width: 80, align: "right" as const },
                    { title: "单价", dataIndex: "unit_price", width: 110, align: "right" as const, render: (v: number) => money(v) },
                    { title: "小计", dataIndex: "total_price", width: 120, align: "right" as const, render: (v: number) => <Typography.Text strong>{money(v)}</Typography.Text> },
                  ]}
                />
              );
            },
          }}
          rowClassName={erpRowClass}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          columns={[
            {
              title: "单号", dataIndex: "quotation_no", width: 150, fixed: "left",
              render: (v: string | null, r: Quotation) => (
                <Typography.Link strong onClick={() => navigate(`/sales/quotations/${r.id}`)}>
                  {v || `#${r.id}`}
                </Typography.Link>
              ),
            },
            {
              title: "公司名称", dataIndex: "customer_name", width: 180, ellipsis: true,
              render: (v: string | null, r: Quotation) => (
                v
                  ? <Typography.Link onClick={() => navigate(`/customers/${r.customer_id}`)}>{v}</Typography.Link>
                  : <CustomerLink id={r.customer_id} />
              ),
            },
            {
              title: "含税金额", dataIndex: "total_amount", width: 130, align: "right",
              sorter: (a, b) => Number(a.total_amount || 0) - Number(b.total_amount || 0),
              render: (v: number) => <Typography.Text strong>{money(v)}</Typography.Text>,
            },
            {
              title: "状态", dataIndex: "status", width: 80,
              sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
              render: (value: string) => (
                <Space size={4}>
                  {statusDot(ERP_STATUS_DOT[value] || "#d9d9d9")}
                  <SalesStatusTag value={value} />
                </Space>
              ),
            },
            {
              title: "有效期", dataIndex: "valid_until", width: 110,
              sorter: (a, b) => (a.valid_until || "").localeCompare(b.valid_until || ""),
              render: (value: string | null, record: Quotation) => {
                const due = getDueMeta(value, record.status);
                return <StatusTag status={due.text} tone={due.tone} />;
              },
            },
            {
              title: "AI", width: 70,
              render: (_: unknown, record: Quotation) => (
                <AIInlineBadge
                  riskLevel={aiMap[record.id]?.pricing_health === "poor" ? "high" : aiMap[record.id]?.pricing_health === "fair" ? "medium" : "low"}
                  flag={aiMap[record.id]?.flag}
                />
              ),
            },
            {
              title: "下一步", width: 90,
              render: (_: unknown, record: Quotation) => {
                const due = getDueMeta(record.valid_until, record.status);
                if (record.status === "draft") return <StatusTag status="发送报价" tone="info" icon={<SendOutlined />} />;
                if (record.status === "sent" && due.scene === "expired") return <StatusTag status="重新报价" tone="danger" />;
                if (record.status === "sent") return <StatusTag status="跟进转单" tone="success" icon={<FileDoneOutlined />} />;
                if (record.status === "won") return <StatusTag status="已转订单" tone="success" />;
                return <Tag>复盘</Tag>;
              },
            },
            {
              title: "操作", width: 50, fixed: "right",
              render: (_: unknown, record: Quotation) => {
                const items: MenuProps["items"] = [
                  { key: "view", icon: <FileDoneOutlined />, label: "查看详情", onClick: () => navigate(`/sales/quotations/${record.id}`) },
                  ...(record.status === "draft" ? [{ key: "send", icon: <SendOutlined />, label: "标记发送", onClick: () => handleSend(record) }] : []),
                  { key: "pdf", icon: <DownloadOutlined />, label: "智能 PDF", onClick: () => downloadQuotationPDF(record.id, `quotation_${record.quotation_no || record.id}.pdf`).catch(() => message.error("下载失败")) },
                  { key: "copy", icon: <CopyOutlined />, label: "复制", onClick: () => handleDuplicate(record) },
                  { key: "convert", icon: <ShoppingCartOutlined />, label: "转订单", onClick: () => {
                    Modal.confirm({ title: "转为销售订单?", content: `将报价 ${record.quotation_no || `#${record.id}`} 转为销售订单`, onOk: () => handleConvert(record) });
                  } },
                  { type: "divider" as const },
                  { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                    Modal.confirm({ title: "确定删除?", content: `删除报价 ${record.quotation_no || `#${record.id}`}`, onOk: () => deleteQuotation(record.id).then(() => { message.success("已删除"); refreshAll(); }).catch(() => message.error("删除失败")) });
                  }},
                ];
                return (
                  <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
                    <Button size="small" icon={<EllipsisOutlined />} type="text" />
                  </Dropdown>
                );
              },
            },
          ]}
          scroll={{ x: "max-content" }}
          pagination={{
            current: page,
            total: scene === "expiring" || scene === "expired" ? visibleData.length : total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (count) => `共 ${count} 条`,
          }}
        />
      </Card>
    </SalesModuleShell>
  );
}
