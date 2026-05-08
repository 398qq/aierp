import { useEffect, useState } from "react";
import { Card, Select, Table, Tag, Typography, Spin, Alert, Button, Space, Row, Col, Statistic, Divider } from "antd";
import { TrophyOutlined, SwapOutlined, DashboardOutlined } from "@ant-design/icons";
import { compareSuppliers, getSuppliers } from "../../api";
import type { SupplierComparison } from "../../types";

const { Title, Text } = Typography;

export default function SupplierComparePage() {
  const [supplierOptions, setSupplierOptions] = useState<{ value: number; label: string }[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [data, setData] = useState<SupplierComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSuppliers({ page: 1, page_size: 200 })
      .then((r) => {
        const list = r.data.data?.list || r.data.data || [];
        setSupplierOptions(list.map((s: { id: number; name: string }) => ({ value: s.id, label: s.name })));
      })
      .catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setLoading(true);
    setError("");
    try {
      const r = await compareSuppliers(selectedIds);
      setData(r.data.data);
    } catch {
      setError("对比分析失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const rankColumns = [
    { title: "排名", dataIndex: "rank", width: 60, render: (r: number) => <Tag color={r === 1 ? "gold" : r === 2 ? "blue" : "default"}>{r}</Tag> },
    { title: "供应商", dataIndex: "supplier_name" },
    { title: "总分", dataIndex: "total_score", render: (s: number) => s.toFixed(1) },
    { title: "等级", dataIndex: "tier", render: (t: string) => <Tag color={t === "A" ? "green" : t === "B" ? "blue" : "orange"}>{t}</Tag> },
  ];

  const matrixColumns = [
    { title: "维度", dataIndex: "dimension", width: 100 },
    { title: "权重", dataIndex: "weight", width: 60, render: (w: number) => `${(w * 100).toFixed(0)}%` },
    ...Object.keys(data?.comparison_matrix?.[0]?.scores || {}).map((name) => ({
      title: name,
      dataIndex: ["scores", name],
      render: (s: number) => s != null ? s.toFixed(1) : "-",
    })),
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>
        <SwapOutlined /> 供应商智能对比
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Text strong>选择供应商（至少2个）</Text>
          <Select
            mode="multiple"
            style={{ width: "100%" }}
            placeholder="搜索并选择供应商..."
            value={selectedIds}
            onChange={setSelectedIds}
            options={supplierOptions}
            filterOption={(input, option) => (option?.label ?? "").toLowerCase().includes(input.toLowerCase())}
          />
          <Button type="primary" onClick={handleCompare} loading={loading} disabled={selectedIds.length < 2}>
            开始对比
          </Button>
        </Space>
      </Card>

      {error && <Alert type="error" message={error} style={{ marginBottom: 24 }} />}
      {loading && <Spin size="large" style={{ display: "block", margin: "40px auto" }} />}

      {data && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={24}>
              <Card title={<><TrophyOutlined /> 总体排名</>}>
                <Table columns={rankColumns} dataSource={data.overall_ranking} rowKey="rank" pagination={false} size="small" />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={12}>
              <Card title="最佳供应商">
                {data.best_in_category?.map((b, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <Text strong>{b.category}: </Text>
                    <Tag color="green">{b.winner}</Tag>
                    <Text type="secondary"> — {b.reason}</Text>
                  </div>
                ))}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="对比总结"><Text>{data.summary}</Text></Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={24}>
              <Card title={<><DashboardOutlined /> 维度对比矩阵</>}>
                <Table columns={matrixColumns} dataSource={data.comparison_matrix} rowKey="dimension" pagination={false} size="small" />
              </Card>
            </Col>
          </Row>

          <Card title="推荐建议"><Text>{data.recommendation}</Text></Card>
        </>
      )}
    </div>
  );
}
