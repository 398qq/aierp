import { useEffect, useState } from "react";
import { Card, Select, Table, Typography, Spin, Alert, Button, Space, Row, Col } from "antd";
import { TrophyOutlined, SwapOutlined, DashboardOutlined } from "@ant-design/icons";
import { compareSuppliers, getSuppliers } from "../../api";
import type { SupplierComparison } from "../../types";
import { StatusTag } from "../../ui";

const { Title, Text } = Typography;

export default function SupplierComparePage() {
  const [supplierOptions, setSupplierOptions] = useState<{ value: number; label: string }[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [data, setData] = useState<SupplierComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getSuppliers({ page: 1, page_size: 100 })
      .then((r) => {
        const list = r.data.data?.list || r.data.data || [];
        setSupplierOptions(list.map((s: { id: number; name: string }) => ({ value: s.id, label: s.name })));
      })
      .catch(() => setError("加载供应商列表失败"));
    return () => controller.abort();
  }, []);

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setLoading(true);
    setError("");
    try {
      const r = await compareSuppliers(selectedIds);
      const raw = r.data.data as (Record<string, unknown> & SupplierComparison) | null;
      if (raw?.error) {
        setError(String(raw.error));
        setData(null);
        return;
      }
      setData(raw as SupplierComparison | null);
    } catch (err: unknown) {
      // 优先读取 axios 封装的后端错误体（err.response.data.msg），其次读取 HTTP 状态文本，最后用默认文案
      const axiosErr = err as { response?: { data?: { msg?: string }; status?: number }; message?: string };
      const backendMsg = axiosErr.response?.data?.msg;
      const httpStatus = axiosErr.response?.status;
      const msg = axiosErr.message || String(err);
      if (backendMsg) {
        setError(backendMsg);
      } else if (httpStatus === 404 || msg.includes("404") || msg.includes("未找到") || msg.includes("不存在")) {
        setError(msg.replace(/^\d+\s*/, "").trim() || "未找到有效的供应商数据");
      } else {
        setError("对比分析失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const rankColumns = [
    { title: "排名", dataIndex: "rank", width: 60, render: (r: number | undefined) => r != null ? <StatusTag status={String(r)} tone={r === 1 ? "processing" : r === 2 ? "info" : "neutral"} /> : "-" },
    { title: "供应商", dataIndex: "supplier_name" },
    { title: "总分", dataIndex: "total_score", render: (s: number | undefined) => s != null ? s.toFixed(1) : "-" },
    { title: "等级", dataIndex: "tier", render: (t: string) => <StatusTag status={t} tone={t === "A" ? "success" : t === "B" ? "info" : t === "C" ? "warning" : "danger"} /> },
  ];

  const matrixColumns = data?.comparison_matrix?.[0]?.scores
    ? [
        { title: "维度", dataIndex: "dimension", width: 100 },
        { title: "权重", dataIndex: "weight", width: 60, render: (w: number) => `${(w * 100).toFixed(0)}%` },
        ...Object.keys(data.comparison_matrix[0].scores).map((name) => ({
          title: name,
          // dataIndex 保留为 "dimension" 是为了 Ant Design Table 排序/过滤能力；
          // 实际单元格值由 render 函数从 record.scores[name] 取值
          dataIndex: "dimension",
          render: (_: unknown, record: { scores: Record<string, number> }) => {
            const val = record.scores?.[name];
            return val != null ? val.toFixed(1) : "-";
          },
        })),
      ]
    : [];

  // Derive per-dimension winners from comparison_matrix when best_in_category is unavailable
  const derivedBestInCategory = data?.comparison_matrix?.map((row): { category: string; winner: string; reason: string } | null => {
    const scores = row.scores || {};
    const entries = Object.entries(scores);
    if (entries.length === 0) return null;
    const winnerEntry = entries.reduce((best, [name, score]) =>
      score > (scores[best[0]] ?? -Infinity) ? [name, score] : best,
      entries[0] || ["", 0]);
    return { category: row.dimension, winner: winnerEntry[0], reason: `得分${winnerEntry[1]}` };
  }).filter((item): item is { category: string; winner: string; reason: string } => item !== null) || [];

  const displayBestInCategory = (data?.best_in_category && data.best_in_category.length > 0)
    ? data.best_in_category
    : derivedBestInCategory;

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
          {selectedIds.length === 1 && !loading && (
            <Text type="secondary" style={{ fontSize: 12 }}>⚠ 至少需要选择 2 个供应商才能开始对比</Text>
          )}
        </Space>
      </Card>

      {error && !loading && <Alert type="error" message={error} style={{ marginBottom: 24 }} />}
      {loading && <Spin size="large" style={{ display: "block", margin: "40px auto" }} />}

      {data && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={24}>
              <Card title={<><TrophyOutlined /> 总体排名</>}>
                <Table columns={rankColumns} dataSource={data?.overall_ranking} rowKey={(r) => r.rank + "-" + r.supplier_name} pagination={false} size="small" />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col span={12}>
              <Card title="最佳供应商">
                {displayBestInCategory.map((b, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <Text strong>{b.category}: </Text>
                    <StatusTag status={String(b.winner)} tone="success" />
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
                <Table columns={matrixColumns} dataSource={data?.comparison_matrix} rowKey="dimension" pagination={false} size="small" />
              </Card>
            </Col>
          </Row>

          <Card title="推荐建议"><Text>{data.recommendation}</Text></Card>
        </>
      )}
    </div>
  );
}
