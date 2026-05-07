import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Descriptions, Card, Spin, Alert, Empty, Popconfirm, message, Modal, Statistic, Row, Col } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, PlusOutlined, SwapOutlined, RocketOutlined } from "@ant-design/icons";
import { getQuotation, deleteQuotation, getQuotationItems, deleteQuotationItem, convertQuotationToOrder, optimizeQuotation } from "../../api";
import type { Quotation, QuotationItem, QuotationOptimizeResult } from "../../types";

const statusColors: Record<string, string> = {
  draft: "default", sent: "blue", approved: "green", rejected: "red", expired: "orange",
};

export default function QuotationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Quotation | null>(null);
  const [items, setItems] = useState<QuotationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState<QuotationOptimizeResult | null>(null);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [quoResp, itemsResp] = await Promise.all([
        getQuotation(Number(id)),
        getQuotationItems(Number(id)),
      ]);
      setData(quoResp.data.data as Quotation);
      setItems((itemsResp.data.data as QuotationItem[]) || []);
    } catch (e) {
      setError((e as Error).message || "加载失败");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const handleDelete = async () => {
    try { await deleteQuotation(Number(id)); message.success("已删除"); navigate("/sales/quotations"); }
    catch { message.error("删除失败"); }
  };

  const handleDeleteItem = async (itemId: number) => {
    try { await deleteQuotationItem(Number(id), itemId); message.success("已删除"); load(); }
    catch { message.error("删除失败"); }
  };

  const handleConvert = async () => {
    try {
      const resp = await convertQuotationToOrder(Number(id));
      message.success(resp.data.data.msg || "已转为销售订单");
      navigate("/sales/orders");
    } catch { message.error("转换失败"); }
  };

  const handleOptimize = async () => {
    setOptimizing(true);
    try {
      const res = await optimizeQuotation(Number(id));
      const data = (res as { data?: { data?: QuotationOptimizeResult } })?.data?.data;
      if (data) { setOptimizeResult(data); message.success("AI 优化完成"); }
    } catch { message.error("AI 优化失败"); }
    finally { setOptimizing(false); }
  };

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Empty description="未找到该报价单" />;

  const itemColumns = [
    { title: "产品ID", dataIndex: "product_id", width: 100 },
    { title: "数量", dataIndex: "quantity", width: 80 },
    { title: "单价", dataIndex: "unit_price", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
    {
      title: "操作", width: 80, render: (_: unknown, record: QuotationItem) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDeleteItem(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/quotations")}>返回列表</Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/quotations/${data.id}/edit`)}>编辑</Button>
        <Popconfirm title="确定删除?" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
        {data.status !== "approved" && (
          <Popconfirm title="将此报价单转为销售订单?" onConfirm={handleConvert}>
            <Button type="primary" icon={<SwapOutlined />}>转为订单</Button>
          </Popconfirm>
        )}
        <Button icon={<RocketOutlined />} loading={optimizing} onClick={handleOptimize} style={{ color: "#722ed1", borderColor: "#722ed1" }}>
          AI 优化
        </Button>
      </Space>
      <Card title={`报价单: ${data.quotation_no || "NO-" + data.id}`} style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status] || "default"}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="总金额">¥{data.total_amount.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="有效期至">{data.valid_until || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="报价项" extra={<Button icon={<PlusOutlined />} onClick={() => navigate(`/sales/quotations/${data.id}/edit`)}>管理报价项</Button>}>
        <Table rowKey="id" columns={itemColumns} dataSource={items} pagination={false} />
      </Card>

      <Modal title="AI 定价优化建议" open={!!optimizeResult} onCancel={() => setOptimizeResult(null)} footer={null} width={640}>
        {optimizeResult && (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic title="建议总价" value={optimizeResult.optimal_total} precision={2} prefix="¥" />
              </Col>
              <Col span={6}>
                <Statistic title="让利空间" value={optimizeResult.discount_room} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="当前赢单率" value={optimizeResult.win_probability_current} suffix="%" />
              </Col>
              <Col span={6}>
                <Statistic title="优化后赢单率" value={optimizeResult.win_probability_optimal} suffix="%" valueStyle={{ color: "#52c41a" }} />
              </Col>
            </Row>
            {optimizeResult.pricing_strategy && (
              <Alert type="info" message={optimizeResult.pricing_strategy} style={{ marginBottom: 12 }} />
            )}
            {optimizeResult.item_adjustments?.length > 0 && (
              <Table
                rowKey={(r) => r.product_name || r.current_price}
                dataSource={optimizeResult.item_adjustments}
                columns={[
                  { title: "产品", dataIndex: "product_name" },
                  { title: "当前价", dataIndex: "current_price", render: (v: number) => `¥${v}` },
                  { title: "建议价", dataIndex: "suggested_price", render: (v: number) => <span style={{ color: "#52c41a" }}>¥{v}</span> },
                  { title: "原因", dataIndex: "reason" },
                ]}
                pagination={false}
                size="small"
                style={{ marginBottom: 12 }}
              />
            )}
            {optimizeResult.negotiation_guardrails && (
              <Alert type="warning" message={`谈判底线: ${optimizeResult.negotiation_guardrails}`} />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
