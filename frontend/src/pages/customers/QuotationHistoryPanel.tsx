import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Card, Statistic, Row, Col, Tag, Button, Spin, message, Select, Space } from "antd";
import { StatusTag } from "../../ui";
import { DownloadOutlined, EyeOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { getCustomerQuotationHistory, downloadQuotationPDF } from "../../api";
import type { CustomerQuotationHistory } from "../../types";

interface Props {
  customerId: number;
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "default" },
  pending: { label: "待处理", color: "default" },
  sent: { label: "已发送", color: "processing" },
  won: { label: "已成交", color: "green" },
  lost: { label: "已输单", color: "red" },
  expired: { label: "已过期", color: "orange" },
};

export default function QuotationHistoryPanel({ customerId }: Props) {
  const navigate = useNavigate();
  const [data, setData] = useState<CustomerQuotationHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getCustomerQuotationHistory(customerId, statusFilter);
      setData(res.data.data);
    } catch {
      message.error("加载报价历史失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [customerId, statusFilter]);

  if (loading) return <Spin style={{ display: "block", margin: "40px auto" }} />;
  if (!data) return null;

  const { stats, quotations } = data;

  const columns: ColumnsType<typeof quotations[0]> = [
    {
      title: "报价单号",
      dataIndex: "quotation_no",
      key: "quotation_no",
      width: 150,
      render: (v: string, record) => (
        <Button type="link" size="small" onClick={() => navigate(`/sales/quotations/${record.id}`)}>
          {v || `#${record.id}`}
        </Button>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { label: v, color: "default" };
        return <StatusTag tone={s.color}>{s.label}</StatusTag>;
      },
    },
    {
      title: "金额",
      dataIndex: "total_amount",
      key: "total_amount",
      width: 120,
      align: "right",
      render: (v: number) => v.toLocaleString("zh-CN", { style: "currency", currency: "CNY" }),
    },
    {
      title: "有效期至",
      dataIndex: "valid_until",
      key: "valid_until",
      width: 120,
      render: (v: string | null) => v ? dayjs(v).format("YYYY-MM-DD") : "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 120,
      render: (v: string | null) => v ? dayjs(v).format("YYYY-MM-DD") : "-",
    },
    {
      title: "明细项",
      dataIndex: "items",
      key: "items",
      render: (items: typeof quotations[0]["items"]) => items?.length ?? 0,
      width: 70,
      align: "center",
    },
    {
      title: "操作",
      key: "action",
      width: 150,
      render: (_: unknown, record: typeof quotations[0]) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/sales/quotations/${record.id}`)}>
            详情
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => {
              downloadQuotationPDF(record.id, `${record.quotation_no}.pdf`).catch(() =>
                message.error("下载失败")
              );
            }}
          >
            智能PDF
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Stats Row */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic title="报价总数" value={data.total} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="成交" value={stats.won} valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="输单" value={stats.lost} valueStyle={{ color: "#ff4d4f" }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="跟进中" value={stats.pending} valueStyle={{ color: "#1677ff" }} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="成交率"
              value={stats.conversion_rate}
              suffix="%"
              valueStyle={{ color: stats.conversion_rate >= 50 ? "#52c41a" : "#faad14" }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="成交总额"
              value={stats.total_won_amount}
              precision={0}
              valueStyle={{ color: "#52c41a", fontSize: 16 }}
              formatter={(v) => `¥${Number(v).toLocaleString()}`}
            />
          </Card>
        </Col>
      </Row>

      {/* Filter */}
      <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>
        <span>状态筛选：</span>
        <Select
          allowClear
          placeholder="全部"
          style={{ width: 120 }}
          value={statusFilter}
          onChange={(v) => setStatusFilter(v || undefined)}
          options={[
            { label: "全部", value: "" },
            ...Object.entries(STATUS_MAP).map(([k, v]) => ({ label: v.label, value: k })),
          ]}
        />
      </div>

      {/* Table */}
      <Table
        size="small"
        columns={columns}
        dataSource={quotations}
        rowKey="id"
        pagination={{ pageSize: 10, size: "small" }}
        scroll={{ x: 760 }}
      />
    </div>
  );
}
