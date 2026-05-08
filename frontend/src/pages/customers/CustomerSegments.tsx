import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Col, Row, Select, Spin, Table, Tag, Typography, Empty, Slider } from "antd";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PieChartOutlined } from "@ant-design/icons";
import { getCustomerSegments } from "../../api";
import type { SegmentCluster } from "../../types";

const { Title, Text } = Typography;

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
    <div style={{ padding: 24 }}>
      <Title level={4}><PieChartOutlined /> 客户分群分析</Title>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row align="middle" gutter={16}>
          <Col>
            <Text strong>聚类数：{nClusters}</Text>
          </Col>
          <Col flex="auto">
            <Slider min={2} max={10} value={nClusters} onChange={(v) => setNClusters(v)} style={{ width: 200 }} />
          </Col>
          <Col>
            <Text type="secondary">共 {total} 个客户参与分群</Text>
          </Col>
        </Row>
      </Card>

      {loading ? (
        <Spin size="large" style={{ display: "block", margin: "60px auto" }} />
      ) : clusters.length === 0 ? (
        <Empty description="暂无分群数据，请确保客户已生成嵌入向量" />
      ) : (
        <>
          <Card title="聚类分布" style={{ marginBottom: 16 }}>
            <ResponsiveContainer width="100%" height={350}>
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

          <Card title="聚类详情">
            <Table
              columns={columns}
              dataSource={clusters}
              rowKey="id"
              pagination={false}
              size="middle"
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
    </div>
  );
}
