import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Col, Row, Spin, Table, Tag, Typography, Empty, Slider, Space } from "antd";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getCustomerSegments } from "../../api";
import type { SegmentCluster } from "../../types";
import CustomerModuleShell from "./CustomerModuleShell";

const { Text } = Typography;

const COLORS = ["#1677ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2", "#eb2f96", "#fa8c16"];

export default function CustomerSegmentsPage() {
  const [clusters, setClusters] = useState<SegmentCluster[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [nClusters, setNClusters] = useState(5);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    getCustomerSegments(nClusters)
      .then((r) => {
        setClusters(r.data.data?.clusters || []);
        setTotal(r.data.data?.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [nClusters]);

  const chartData = clusters.map((c, i) => ({
    name: c.label,
    size: c.size,
    fill: COLORS[i % COLORS.length],
  }));
  const largestCluster = clusters.reduce<SegmentCluster | null>(
    (largest, item) => (!largest || item.size > largest.size ? item : largest),
    null,
  );
  const avgSimilarity = clusters.length
    ? clusters.reduce((sum, item) => sum + item.avg_similarity, 0) / clusters.length
    : 0;

  const columns = [
    { title: "聚类", dataIndex: "label", key: "label", render: (_: string, r: SegmentCluster, i: number) => <Tag color={COLORS[i % COLORS.length]}>{r.label}</Tag> },
    { title: "客户数", dataIndex: "size", key: "size", sorter: (a: SegmentCluster, b: SegmentCluster) => a.size - b.size },
    { title: "平均相似度", dataIndex: "avg_similarity", key: "avg_similarity", render: (v: number) => (v * 100).toFixed(1) + "%" },
    { title: "常见行业", dataIndex: "common_industry", key: "common_industry", render: (v: string) => <Tag>{v || "-"}</Tag> },
    { title: "常见等级", dataIndex: "common_level", key: "common_level", render: (v: string) => <Tag>{v || "-"}</Tag> },
    {
      title: "样本客户", dataIndex: "sample_names", key: "sample_names",
      render: (names: string[]) => names?.slice(0, 5).map((n, i) => <Tag key={i} style={{ marginBottom: 2 }}>{n}</Tag>),
    },
  ];

  return (
    <CustomerModuleShell title="客户分群" subtitle="按行业、价值与行为自动聚类，便于分层运营">
      <style>{`
        .customer-segments-control {
          padding: 12px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-segments-control-row {
          display: grid;
          grid-template-columns: minmax(220px, 360px) 1fr;
          gap: 16px;
          align-items: center;
        }
        .customer-segments-summary {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          flex-wrap: wrap;
        }
        .customer-segments-chip {
          min-width: 112px;
          padding: 6px 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-segments-chip-label {
          display: block;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-segments-chip-value {
          color: #262626;
          font-weight: 600;
        }
        .customer-segments-grid {
          margin-top: 12px;
        }
        .customer-segments-panel .ant-card-head {
          min-height: 44px;
        }
        .customer-segments-panel .ant-card-body {
          padding: 12px;
        }
        @media (max-width: 900px) {
          .customer-segments-control-row {
            grid-template-columns: 1fr;
          }
          .customer-segments-summary {
            justify-content: flex-start;
          }
        }
      `}</style>

      <div className="customer-segments-control">
        <div className="customer-segments-control-row">
          <div>
            <Space align="center" style={{ width: "100%", justifyContent: "space-between" }}>
              <Text strong>聚类数：{nClusters}</Text>
              <Text type="secondary">2-10</Text>
            </Space>
            <Slider min={2} max={10} value={nClusters} onChange={(v) => setNClusters(v)} />
          </div>
          <div className="customer-segments-summary">
            <div className="customer-segments-chip">
              <span className="customer-segments-chip-label">参与客户</span>
              <span className="customer-segments-chip-value">{total}</span>
            </div>
            <div className="customer-segments-chip">
              <span className="customer-segments-chip-label">有效分群</span>
              <span className="customer-segments-chip-value">{clusters.length}</span>
            </div>
            <div className="customer-segments-chip">
              <span className="customer-segments-chip-label">最大分群</span>
              <span className="customer-segments-chip-value">{largestCluster ? largestCluster.size : "-"}</span>
            </div>
            <div className="customer-segments-chip">
              <span className="customer-segments-chip-label">平均相似度</span>
              <span className="customer-segments-chip-value">{clusters.length ? `${(avgSimilarity * 100).toFixed(1)}%` : "-"}</span>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "60px auto" }} />
      ) : clusters.length === 0 ? (
        <Empty description="暂无分群数据，请确保客户已生成嵌入向量" />
      ) : (
        <>
          <Card size="small" className="customer-segments-panel customer-segments-grid" title="聚类分布" extra={<Text type="secondary">{clusters.length} 组</Text>}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value: number) => [value, "客户数"]} />
                <Bar dataKey="size" name="客户数" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card size="small" className="customer-segments-panel customer-segments-grid" title="聚类详情" extra={<Text type="secondary">点击行查看客户</Text>}>
            <Table
              columns={columns}
              dataSource={clusters}
              rowKey="id"
              pagination={false}
              size="middle"
              scroll={{ x: "max-content" }}
              onRow={(record) => ({
                style: { cursor: "pointer" },
                onClick: () => {
                  if (record.sample_names.length > 0) {
                    navigate(`/customers?q=${encodeURIComponent(record.label)}`);
                  }
                },
              })}
            />
          </Card>
        </>
      )}
    </CustomerModuleShell>
  );
}
