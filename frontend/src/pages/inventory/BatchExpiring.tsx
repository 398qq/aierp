/**
 * Batch Expiry Alert — Stage 18 / Production Batch Management
 *
 * Shows batches grouped by expiry urgency:
 *   - 已过期 (expired)
 *   - 7天内到期
 *   - 30天内到期
 *   - 90天内到期
 *
 * Route: /inventory/expiring
 * API:   GET /api/v1/inventory/batches/expiring
 *        GET /api/v1/inventory/batches/expiring/summary
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  Col,
  Empty,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

const { Title, Text } = Typography;

interface ExpiringBatch {
  id: number;
  batch_no: string;
  product_id: number;
  warehouse_id: number;
  quantity: number;
  unit_cost: number;
  expiry_date: string | null;
  received_date: string | null;
  msl_level: string | null;
  rohs_compliant: boolean;
  status: string;
  days_until_expiry: number | null;
}

interface ScanResponse {
  buckets: Record<string, ExpiringBatch[]>;
  total: number;
}

interface BucketSummary {
  name: string;
  label: string;
  severity: string;
  count: number;
}

interface SummaryResponse {
  total_expiring: number;
  counts_by_bucket: Record<string, number>;
  buckets: BucketSummary[];
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: "red",
  high: "volcano",
  medium: "orange",
  low: "gold",
};

export default function BatchExpiring() {
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [scanResp, summaryResp] = await Promise.all([
          client.get<{ data: ScanResponse }>("/inventory/batches/expiring"),
          client.get<{ data: SummaryResponse }>(
            "/inventory/batches/expiring/summary",
          ),
        ]);
        if (!cancelled) {
          setScan(scanResp.data.data);
          setSummary(summaryResp.data.data);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Spin size="large" tip="扫描中..." />
      </div>
    );
  }

  if (!scan || !summary) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="暂无数据" />
      </div>
    );
  }

  const columns = (bucketName: string): ColumnsType<ExpiringBatch> => [
    {
      title: "批次号",
      dataIndex: "batch_no",
      key: "batch_no",
      render: (v: string, r) => (
        <Link to={`/inventory/batches/${r.id}/traceability`}>{v}</Link>
      ),
    },
    { title: "产品 ID", dataIndex: "product_id", key: "product_id", width: 90 },
    { title: "仓库 ID", dataIndex: "warehouse_id", key: "warehouse_id", width: 90 },
    {
      title: "剩余数量",
      dataIndex: "quantity",
      key: "quantity",
      width: 100,
    },
    {
      title: "有效期",
      dataIndex: "expiry_date",
      key: "expiry_date",
      width: 120,
      render: (v: string | null) => (v ? v.slice(0, 10) : "-"),
    },
    {
      title:
        bucketName === "expired" ? "已过期天数" : "距离到期",
      dataIndex: "days_until_expiry",
      key: "days_until_expiry",
      width: 120,
      render: (v: number | null) => {
        if (v === null) return "-";
        if (v < 0) return <Tag color="red">{Math.abs(v)} 天</Tag>;
        if (v === 0) return <Tag color="red">今天到期</Tag>;
        if (v <= 7) return <Tag color="volcano">{v} 天</Tag>;
        if (v <= 30) return <Tag color="orange">{v} 天</Tag>;
        return <Tag>{v} 天</Tag>;
      },
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: "MSL",
      dataIndex: "msl_level",
      key: "msl_level",
      width: 70,
      render: (v: string | null) => v || "-",
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>批次有效期预警</Title>
      <Text type="secondary">
        扫描库存批次中即将过期 / 已过期的库存，帮助提前处理临期批次或启动召回流程。
      </Text>

      {/* Summary cards */}
      <Row gutter={16} style={{ marginTop: 16, marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="待处理总数" value={summary.total_expiring} />
          </Card>
        </Col>
        {summary.buckets.map((b) => (
          <Col span={4} key={b.name}>
            <Card>
              <Statistic
                title={
                  <Space>
                    <Tag color={SEVERITY_COLOR[b.severity]}>{b.label}</Tag>
                  </Space>
                }
                value={b.count}
                valueStyle={{
                  color:
                    SEVERITY_COLOR[b.severity] === "red" ? "#cf1322" : undefined,
                }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Tabbed bucket views */}
      <Card>
        <Tabs
          items={summary.buckets.map((b) => ({
            key: b.name,
            label: (
              <Space>
                <Tag color={SEVERITY_COLOR[b.severity]}>{b.label}</Tag>
                <span>({scan.buckets[b.name]?.length ?? 0})</span>
              </Space>
            ),
            children: (
              <Table<ExpiringBatch>
                rowKey="id"
                columns={columns(b.name)}
                dataSource={scan.buckets[b.name] ?? []}
                size="small"
                pagination={{ pageSize: 20, showSizeChanger: true }}
                locale={{ emptyText: <Empty description="该桶无批次" /> }}
              />
            ),
          }))}
        />
      </Card>
    </div>
  );
}