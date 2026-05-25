import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Popconfirm, Select, Space, Switch, Table, Typography, message } from "antd";
import { DeleteOutlined, DownloadOutlined, PlusOutlined, ReloadOutlined, ShoppingCartOutlined } from "@ant-design/icons";
import { batchDeleteQuotations, convertQuotationToOrder, deleteQuotation, downloadQuotationPDF, getQuotations } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { Quotation } from "../../types";
import { CustomerLink, MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, money, shortDate } from "./salesUi";

export default function QuotationList() {
  const [data, setData] = useState<Quotation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { pricing_health?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (includeAi) params.include_ai = true;
      const resp = await getQuotations(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { pricing_health?: string; flag?: string }> }).ai || {}) : {});
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, status, includeAi]);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const sent = data.filter((item) => item.status === "sent").length;
    const won = data.filter((item) => item.status === "won").length;
    const itemCount = data.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { amount, sent, won, itemCount };
  }, [data]);

  const handleBatchDelete = async () => {
    try {
      await batchDeleteQuotations(selected);
      message.success("已批量删除");
      setSelected([]);
      load();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <SalesModuleShell
      title="报价管理"
      subtitle="承接客户需求和产品选型，管理报价、有效期、转订单动作"
      activeKey="quotations"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "当前报价", value: total, suffix: "张" },
          { title: "本页金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "已发送", value: stats.sent, suffix: "张" },
          { title: "已成交", value: stats.won, suffix: "张" },
          { title: "产品行", value: stats.itemCount, suffix: "项" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/quotations/new")}>新建报价</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除 {selected.length}</Button>
            </Popconfirm>
          ) : null}
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={(next) => {
              setPage(1);
              setStatus(next);
            }}
            options={[
              { value: "draft", label: "草稿" },
              { value: "sent", label: "已发送" },
              { value: "won", label: "成交" },
              { value: "lost", label: "丢失" },
            ]}
          />
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={data}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          columns={[
            {
              title: "报价单",
              dataIndex: "quotation_no",
              minWidth: 220,
              render: (value: string | null, record: Quotation) => (
                <Space direction="vertical" size={0}>
                  <a onClick={() => navigate(`/sales/quotations/${record.id}`)}>{value || record.title || `#${record.id}`}</a>
                  <Space size={8}>
                    <CustomerLink id={record.customer_id} />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>产品行 {record.items?.length || 0}</Typography.Text>
                  </Space>
                </Space>
              ),
            },
            { title: "金额", dataIndex: "total_amount", width: 130, render: money },
            { title: "状态", dataIndex: "status", width: 100, render: (value: string) => <SalesStatusTag value={value} /> },
            { title: "有效期", dataIndex: "valid_until", width: 120, render: shortDate },
            {
              title: "AI",
              width: 100,
              render: (_: unknown, record: Quotation) => (
                <AIInlineBadge
                  riskLevel={aiMap[record.id]?.pricing_health === "poor" ? "high" : aiMap[record.id]?.pricing_health === "fair" ? "medium" : "low"}
                  flag={aiMap[record.id]?.flag}
                />
              ),
            },
            {
              title: "操作",
              width: 260,
              render: (_: unknown, record: Quotation) => (
                <Space size="small">
                  <Button size="small" onClick={() => navigate(`/sales/quotations/${record.id}`)}>详情</Button>
                  <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadQuotationPDF(record.id, `quotation_${record.quotation_no || record.id}.pdf`).catch(() => message.error("下载失败"))}>PDF</Button>
                  {record.status !== "won" ? (
                    <Popconfirm title="转为销售订单?" onConfirm={async () => {
                      try {
                        await convertQuotationToOrder(record.id);
                        message.success("已转为订单");
                        load();
                      } catch {
                        message.error("转换失败");
                      }
                    }}>
                      <Button size="small" type="primary" icon={<ShoppingCartOutlined />}>转订单</Button>
                    </Popconfirm>
                  ) : null}
                  <Popconfirm title="确定删除?" onConfirm={async () => {
                    try {
                      await deleteQuotation(record.id);
                      message.success("已删除");
                      load();
                    } catch {
                      message.error("删除失败");
                    }
                  }}>
                    <Button size="small" danger>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
          pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (count) => `共 ${count} 条` }}
        />
      </Card>
    </SalesModuleShell>
  );
}
