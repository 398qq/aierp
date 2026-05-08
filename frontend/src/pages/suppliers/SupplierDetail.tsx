import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Card, Descriptions, Tag, Button, Space, Spin, Alert, Table, Modal, Input, InputNumber, message, Switch, Typography, Popconfirm, Progress, Badge, List, Col, Row } from "antd";
import { ArrowLeftOutlined, LinkOutlined, ThunderboltOutlined, DeleteOutlined, DashboardOutlined, ClockCircleOutlined, SwapOutlined, DollarOutlined, PieChartOutlined, FileTextOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getSupplier, getSupplierProducts, linkSupplierProduct, unlinkSupplierProduct, aiMatchSupplierProducts, getProducts, getSupplierScorecard, predictSupplierDelay, getSupplierAlternatives, detectSupplierPriceVariance, getSupplierNegotiation } from "../../api";
import type { Supplier, SupplierProductLink, Product, SupplierScorecard, SupplierDelayPrediction, SupplierAlternatives, SupplierPriceVariance, SupplierNegotiation } from "../../types";

const { Text } = Typography;

export default function SupplierDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [linkedProducts, setLinkedProducts] = useState<SupplierProductLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [matchModalOpen, setMatchModalOpen] = useState(false);
  const [matchText, setMatchText] = useState("");
  const [matchResults, setMatchResults] = useState<Record<string, unknown>[]>([]);
  const [matching, setMatching] = useState(false);
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [linking, setLinking] = useState(false);
  const [linkForm, setLinkForm] = useState({ product_id: 0, cost_price: null as number | null, lead_time_days: null as number | null, moq: null as number | null, spq: null as number | null, is_preferred: false, notes: "" });
  const [productSearch, setProductSearch] = useState("");
  const [productOptions, setProductOptions] = useState<Product[]>([]);
  // AI features
  const [scorecard, setScorecard] = useState<SupplierScorecard | null>(null);
  const [scorecardLoading, setScorecardLoading] = useState(false);
  const [delayPred, setDelayPred] = useState<SupplierDelayPrediction | null>(null);
  const [delayLoading, setDelayLoading] = useState(false);
  const [alternatives, setAlternatives] = useState<SupplierAlternatives | null>(null);
  const [altLoading, setAltLoading] = useState(false);
  const [priceVariance, setPriceVariance] = useState<SupplierPriceVariance | null>(null);
  const [priceVarLoading, setPriceVarLoading] = useState(false);
  const [negotiation, setNegotiation] = useState<SupplierNegotiation | null>(null);
  const [negotiationLoading, setNegotiationLoading] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [supRes, prodRes] = await Promise.all([
        getSupplier(Number(id)),
        getSupplierProducts(Number(id)),
      ]);
      setSupplier(supRes.data.data as Supplier);
      setLinkedProducts((prodRes.data.data || []) as SupplierProductLink[]);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const handleMatch = async () => {
    setMatching(true);
    try {
      const resp = await aiMatchSupplierProducts(Number(id), matchText || undefined, false);
      if (resp.data.code === 0) {
        const data = resp.data.data as Record<string, unknown>;
        const matches = (data.matches || []) as Record<string, unknown>[];
        setMatchResults(matches);
        if (matches.length === 0) message.info("AI 未找到匹配项");
      }
    } catch { message.error("AI 匹配失败"); }
    finally { setMatching(false); }
  };

  const handleAutoLink = async () => {
    setMatching(true);
    try {
      const resp = await aiMatchSupplierProducts(Number(id), matchText || undefined, true);
      if (resp.data.code === 0) {
        const d = resp.data.data as Record<string, unknown>;
        message.success(`已自动关联 ${d.linked} 个产品`);
        setMatchModalOpen(false);
        await loadData();
      }
    } catch { message.error("自动关联失败"); }
    finally { setMatching(false); }
  };

  const handleSearchProducts = async (v: string) => {
    setProductSearch(v);
    if (v.length < 2) { setProductOptions([]); return; }
    try {
      const resp = await getProducts({ q: v, page_size: 10 });
      setProductOptions((resp.data.data.list || []) as Product[]);
    } catch { /* */ }
  };

  const handleLink = async () => {
    if (!linkForm.product_id) return;
    setLinking(true);
    try {
      await linkSupplierProduct(Number(id), linkForm);
      message.success("关联成功");
      setLinkModalOpen(false);
      loadData();
    } catch { message.error("关联失败"); }
    finally { setLinking(false); }
  };

  const handleUnlink = async (productId: number) => {
    try {
      await unlinkSupplierProduct(Number(id), productId);
      message.success("已取消关联");
      loadData();
    } catch { message.error("操作失败"); }
  };

  const loadScorecard = async () => {
    setScorecardLoading(true);
    try {
      const resp = await getSupplierScorecard(Number(id));
      if (resp.data.code === 0) setScorecard(resp.data.data as SupplierScorecard);
    } catch { message.error("供应商评分获取失败"); }
    finally { setScorecardLoading(false); }
  };

  const loadDelayPrediction = async () => {
    setDelayLoading(true);
    try {
      const resp = await predictSupplierDelay(Number(id));
      if (resp.data.code === 0) setDelayPred(resp.data.data as SupplierDelayPrediction);
    } catch { message.error("延迟预测失败"); }
    finally { setDelayLoading(false); }
  };

  const loadAlternatives = async () => {
    setAltLoading(true);
    try {
      const resp = await getSupplierAlternatives(Number(id));
      if (resp.data.code === 0) setAlternatives(resp.data.data as SupplierAlternatives);
    } catch { message.error("替代方案获取失败"); }
    finally { setAltLoading(false); }
  };

  const loadPriceVariance = async () => {
    setPriceVarLoading(true);
    try {
      const resp = await detectSupplierPriceVariance(Number(id));
      if (resp.data.code === 0) setPriceVariance(resp.data.data as SupplierPriceVariance);
    } catch { message.error("价格异常检测失败"); }
    finally { setPriceVarLoading(false); }
  };

  const loadNegotiation = async () => {
    setNegotiationLoading(true);
    try {
      const resp = await getSupplierNegotiation(Number(id));
      if (resp.data.code === 0) setNegotiation(resp.data.data as SupplierNegotiation);
    } catch { message.error("谈判建议加载失败"); }
    finally { setNegotiationLoading(false); }
  };

  if (loading) return <Spin style={{ margin: 40 }} />;
  if (!supplier) return <Alert type="error" message="供应商未找到" />;

  const linkedColumns: ColumnsType<SupplierProductLink> = [
    {
      title: "产品", key: "product", width: 200,
      render: (_: unknown, r) => (
        <a onClick={() => navigate(`/products/${r.product_id}`)}>
          {r.sku ? `[${r.sku}] ` : ""}{r.product_name || `#${r.product_id}`}
        </a>
      ),
    },
    { title: "分类", dataIndex: "category", width: 80, render: (v) => v ? <Tag>{v}</Tag> : null },
    { title: "品牌", dataIndex: "brand_name", width: 80 },
    { title: "封装", dataIndex: "package_type", width: 80 },
    {
      title: "成本价", dataIndex: "cost_price", width: 100,
      render: (v) => v ? `¥${Number(v).toFixed(4)}` : "-",
    },
    { title: "交期(天)", dataIndex: "lead_time_days", width: 80 },
    { title: "MOQ", dataIndex: "moq", width: 60 },
    { title: "SPQ", dataIndex: "spq", width: 60 },
    {
      title: "首选", dataIndex: "is_preferred", width: 60,
      render: (v) => v ? <Tag color="green">是</Tag> : null,
    },
    {
      title: "操作", key: "action", width: 60,
      render: (_: unknown, r) => (
        <Popconfirm title="确认取消关联？" onConfirm={() => handleUnlink(r.product_id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/suppliers")}>返回列表</Button>
        <Button type="primary" icon={<LinkOutlined />} onClick={() => setLinkModalOpen(true)}>关联产品</Button>
        <Button icon={<ThunderboltOutlined />} onClick={() => { setMatchText(""); setMatchResults([]); setMatchModalOpen(true); }}>AI 匹配</Button>
        <Button icon={<DashboardOutlined />} loading={scorecardLoading} onClick={loadScorecard}>供应商评分</Button>
        <Button icon={<ClockCircleOutlined />} loading={delayLoading} onClick={loadDelayPrediction}>延迟预测</Button>
        <Button icon={<SwapOutlined />} loading={altLoading} onClick={loadAlternatives}>替代方案</Button>
        <Button icon={<DollarOutlined />} loading={priceVarLoading} onClick={loadPriceVariance}>价格异常</Button>
        <Button icon={<FileTextOutlined />} loading={negotiationLoading} onClick={loadNegotiation}>谈判建议</Button>
        <Link to={`/suppliers/${id}/360`}><Button icon={<PieChartOutlined />}>360</Button></Link>
      </Space>

      <Card title="供应商信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small">
          <Descriptions.Item label="名称">{supplier.name}</Descriptions.Item>
          <Descriptions.Item label="联系人">{supplier.contact_person || "-"}</Descriptions.Item>
          <Descriptions.Item label="电话">{supplier.phone || "-"}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{supplier.email || "-"}</Descriptions.Item>
          <Descriptions.Item label="地址" span={2}>{supplier.address || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{supplier.created_at ? new Date(supplier.created_at).toLocaleDateString("zh-CN") : "-"}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{supplier.updated_at ? new Date(supplier.updated_at).toLocaleDateString("zh-CN") : "-"}</Descriptions.Item>
          <Descriptions.Item label="产品线" span={3}>
            <Text>{supplier.product_lines || "-"}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="备注" span={3}>{supplier.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={`关联产品 (${linkedProducts.length})`}>
        <Table rowKey="id" columns={linkedColumns} dataSource={linkedProducts} size="small" pagination={false} />
      </Card>

      {/* AI Match Modal */}
      <Modal
        title="AI 产品匹配"
        open={matchModalOpen}
        onCancel={() => setMatchModalOpen(false)}
        width={700}
        footer={matchResults.length > 0 ? [
          <Button key="cancel" onClick={() => setMatchModalOpen(false)}>关闭</Button>,
          <Button key="link" type="primary" onClick={handleAutoLink} loading={matching}>自动关联全部</Button>,
        ] : [
          <Button key="cancel" onClick={() => setMatchModalOpen(false)}>关闭</Button>,
          <Button key="match" type="primary" onClick={handleMatch} loading={matching}>开始匹配</Button>,
        ]}
      >
        <div style={{ marginBottom: 12 }}>
          <Text>粘贴供应商产品目录文本（型号、品牌、价格等），AI 将自动匹配到系统产品：</Text>
          <Input.TextArea
            rows={6}
            value={matchText}
            onChange={(e) => setMatchText(e.target.value)}
            placeholder={supplier.product_lines || "例如：\nSamsung CL05A106MP5NUNC 0402 10uF 10V X5R ¥0.023 MOQ=10000 L/T=4w\nMurata GRM155R61A106KE11D 0402 10uF 10V X5R ¥0.018 MOQ=15000 L/T=6w"}
            style={{ marginTop: 8 }}
          />
        </div>
        {matchResults.length > 0 && (
          <Table
            size="small"
            rowKey="product_id"
            dataSource={matchResults}
            columns={[
              { title: "产品ID", dataIndex: "product_id", width: 70 },
              { title: "供应商型号", dataIndex: "supplier_pn", width: 150, ellipsis: true },
              { title: "成本价", dataIndex: "cost_price", width: 80 },
              { title: "交期", dataIndex: "lead_time_days", width: 60 },
              { title: "MOQ", dataIndex: "moq", width: 60 },
              { title: "置信度", dataIndex: "confidence", width: 80, render: (v: number) => <Tag color={v > 80 ? "green" : v > 50 ? "orange" : "red"}>{v}%</Tag> },
              { title: "理由", dataIndex: "match_reason", ellipsis: true },
            ]}
            pagination={false}
          />
        )}
      </Modal>

      {/* Manual Link Modal */}
      <Modal
        title="手动关联产品"
        open={linkModalOpen}
        onCancel={() => setLinkModalOpen(false)}
        onOk={handleLink}
        confirmLoading={linking}
        okText="关联"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>
            <Text>搜索产品：</Text>
            <Input.Search
              value={productSearch}
              onChange={(e) => handleSearchProducts(e.target.value)}
              placeholder="输入产品名称或SKU搜索"
            />
          </div>
          {productOptions.length > 0 && (
            <div style={{ maxHeight: 200, overflow: "auto", border: "1px solid #f0f0f0", borderRadius: 4, padding: 8 }}>
              {productOptions.map((p) => (
                <div
                  key={p.id}
                  style={{
                    padding: "6px 8px", cursor: "pointer",
                    background: linkForm.product_id === p.id ? "#e6f4ff" : undefined,
                  }}
                  onClick={() => setLinkForm({ ...linkForm, product_id: p.id })}
                >
                  [{p.sku || "-"}] {p.name} <Tag>{p.category || "-"}</Tag>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1 }}>
              <Text>成本价：</Text>
              <InputNumber value={linkForm.cost_price} onChange={(v) => setLinkForm({ ...linkForm, cost_price: v })} style={{ width: "100%" }} />
            </div>
            <div style={{ flex: 1 }}>
              <Text>交期(天)：</Text>
              <InputNumber value={linkForm.lead_time_days} onChange={(v) => setLinkForm({ ...linkForm, lead_time_days: v })} style={{ width: "100%" }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1 }}>
              <Text>MOQ：</Text>
              <InputNumber value={linkForm.moq} onChange={(v) => setLinkForm({ ...linkForm, moq: v })} style={{ width: "100%" }} />
            </div>
            <div style={{ flex: 1 }}>
              <Text>SPQ：</Text>
              <InputNumber value={linkForm.spq} onChange={(v) => setLinkForm({ ...linkForm, spq: v })} style={{ width: "100%" }} />
            </div>
          </div>
          <div>
            <Text>备注：</Text>
            <Input value={linkForm.notes} onChange={(e) => setLinkForm({ ...linkForm, notes: e.target.value })} />
          </div>
          <div>
            <Text>首选供应商：</Text>
            <Switch checked={linkForm.is_preferred} onChange={(v) => setLinkForm({ ...linkForm, is_preferred: v })} />
          </div>
        </Space>
      </Modal>

      {/* Supplier Scorecard Modal */}
      <Modal
        title="供应商评分" open={!!scorecard} onCancel={() => setScorecard(null)}
        width={750} footer={[<Button key="close" onClick={() => setScorecard(null)}>关闭</Button>]}
      >
        {scorecard && (
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">综合评分</Typography.Text>
                <Progress type="circle" percent={scorecard.overall_score} size={80} status={scorecard.overall_score > 70 ? "success" : scorecard.overall_score > 40 ? "normal" : "exception"} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">等级</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={scorecard.tier === "A" || scorecard.tier === "优秀" ? "green" : scorecard.tier === "B" || scorecard.tier === "良好" ? "blue" : scorecard.tier === "C" ? "orange" : "red"} style={{ fontSize: 16, padding: "4px 16px" }}>{scorecard.tier}</Tag>
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="维度评分">
                <div style={{ marginBottom: 8 }}><Typography.Text type="secondary" style={{ width: 80, display: "inline-block" }}>交付</Typography.Text><Progress percent={scorecard.delivery_score} size="small" /></div>
                <div style={{ marginBottom: 8 }}><Typography.Text type="secondary" style={{ width: 80, display: "inline-block" }}>质量</Typography.Text><Progress percent={scorecard.quality_score} size="small" /></div>
                <div style={{ marginBottom: 8 }}><Typography.Text type="secondary" style={{ width: 80, display: "inline-block" }}>价格</Typography.Text><Progress percent={scorecard.price_score} size="small" /></div>
                <div><Typography.Text type="secondary" style={{ width: 80, display: "inline-block" }}>稳定</Typography.Text><Progress percent={scorecard.stability_score} size="small" /></div>
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                <Typography.Text>{scorecard.assessment}</Typography.Text>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="优势">
                <List size="small" dataSource={scorecard.strengths} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="green">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="待改善">
                <List size="small" dataSource={scorecard.weaknesses} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="orange">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {scorecard.recommendations.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" style={{ background: "#fffbe6" }}>
                  <Typography.Text strong>建议：</Typography.Text>
                  <List size="small" dataSource={scorecard.recommendations} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="blue">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            )}
          </Row>
        )}
      </Modal>

      {/* Delay Prediction Modal */}
      <Modal
        title="延迟预测" open={!!delayPred} onCancel={() => setDelayPred(null)}
        width={700} footer={[<Button key="close" onClick={() => setDelayPred(null)}>关闭</Button>]}
      >
        {delayPred && (
          <Row gutter={[12, 12]}>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">延迟风险</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={delayPred.delay_risk === "低" || delayPred.delay_risk === "low" ? "green" : delayPred.delay_risk === "中" || delayPred.delay_risk === "medium" ? "orange" : "red"} style={{ fontSize: 16, padding: "4px 16px" }}>{delayPred.delay_risk}</Tag>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">风险评分</Typography.Text>
                <Progress type="circle" percent={delayPred.risk_score} size={80} status={delayPred.risk_score > 70 ? "exception" : delayPred.risk_score > 40 ? "normal" : "success"} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">预计延迟</Typography.Text>
                <div style={{ fontSize: 28, fontWeight: "bold", marginTop: 8, color: delayPred.predicted_delay_days > 7 ? "#ff4d4f" : delayPred.predicted_delay_days > 3 ? "#faad14" : "#52c41a" }}>
                  {delayPred.predicted_delay_days}<span style={{ fontSize: 14 }}> 天</span>
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="风险因素">
                <List size="small" dataSource={delayPred.risk_factors} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="red">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="缓解措施">
                <List size="small" dataSource={delayPred.mitigation} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {delayPred.alternative_suggestion && (
              <Col span={24}>
                <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                  <Typography.Text strong>备选建议：</Typography.Text><Typography.Text>{delayPred.alternative_suggestion}</Typography.Text>
                </Card>
              </Col>
            )}
          </Row>
        )}
      </Modal>

      {/* Supplier Alternatives Modal */}
      <Modal
        title="替代方案" open={!!alternatives} onCancel={() => setAlternatives(null)}
        width={800} footer={[<Button key="close" onClick={() => setAlternatives(null)}>关闭</Button>]}
      >
        {alternatives && (
          <Row gutter={[12, 12]}>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">紧急程度</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Badge status={alternatives.urgency === "紧急" || alternatives.urgency === "高" ? "error" : alternatives.urgency === "中" ? "warning" : "success"} text={<Tag color={alternatives.urgency === "紧急" || alternatives.urgency === "高" ? "red" : alternatives.urgency === "中" ? "orange" : "blue"}>{alternatives.urgency}</Tag>} />
                </div>
              </Card>
            </Col>
            <Col span={16}>
              <Card size="small" type="inner">
                <Typography.Text>{alternatives.risk_assessment}</Typography.Text>
              </Card>
            </Col>
            {alternatives.recommended_alternatives.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="推荐替代供应商">
                  <Table size="small" dataSource={alternatives.recommended_alternatives} rowKey="supplier_name" pagination={false}
                    columns={[
                      { title: "供应商", dataIndex: "supplier_name", width: 160 },
                      { title: "产品线", dataIndex: "product_lines", ellipsis: true },
                      { title: "匹配度", dataIndex: "score", width: 80, render: (v: number) => <Progress percent={v} size="small" /> },
                      { title: "优势", dataIndex: "advantage" },
                      { title: "切换成本", dataIndex: "switch_cost", width: 100, render: (v: string) => <Tag color={v === "低" ? "green" : v === "中" ? "orange" : "red"}>{v}</Tag> },
                    ]}
                  />
                </Card>
              </Col>
            )}
            {alternatives.diversification_strategy.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="分散策略" style={{ background: "#f6ffed" }}>
                  <List size="small" dataSource={alternatives.diversification_strategy} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="blue">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            )}
          </Row>
        )}
      </Modal>

      {/* Price Variance Modal */}
      <Modal
        title="价格异常" open={!!priceVariance} onCancel={() => setPriceVariance(null)}
        width={800} footer={[<Button key="close" onClick={() => setPriceVariance(null)}>关闭</Button>]}
      >
        {priceVariance && (
          <Row gutter={[12, 12]}>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">价格状态</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={priceVariance.price_status === "正常" ? "green" : priceVariance.price_status === "偏高" ? "orange" : "red"} style={{ fontSize: 16, padding: "4px 16px" }}>{priceVariance.price_status}</Tag>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">异常评分</Typography.Text>
                <Progress type="circle" percent={priceVariance.variance_score} size={80} status={priceVariance.variance_score > 70 ? "exception" : priceVariance.variance_score > 40 ? "normal" : "success"} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner">
                <Typography.Text type="secondary">趋势分析</Typography.Text>
                <Typography.Text style={{ display: "block", marginTop: 8 }}>{priceVariance.trend_analysis}</Typography.Text>
              </Card>
            </Col>
            {priceVariance.anomaly_products.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="异常产品">
                  <Table size="small" dataSource={priceVariance.anomaly_products} rowKey="product_name" pagination={false}
                    columns={[
                      { title: "产品", dataIndex: "product_name", width: 180 },
                      { title: "当前价", dataIndex: "current_price", width: 100, render: (v: number) => `¥${v.toFixed(4)}` },
                      { title: "期望价", dataIndex: "expected_price", width: 100, render: (v: number) => `¥${v.toFixed(4)}` },
                      { title: "偏差", dataIndex: "variance_pct", width: 80, render: (v: number) => <Tag color={v > 20 ? "red" : v > 10 ? "orange" : "blue"}>{v}%</Tag> },
                      { title: "原因", dataIndex: "reason" },
                    ]}
                  />
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="成本节约机会">
                <List size="small" dataSource={priceVariance.cost_saving_opportunities} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="green">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="谈判要点">
                <List size="small" dataSource={priceVariance.negotiation_points} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
          </Row>
        )}
      </Modal>

      {/* Negotiation Modal */}
      <Modal
        title="谈判建议" open={!!negotiation} onCancel={() => setNegotiation(null)}
        footer={<Button onClick={() => setNegotiation(null)}>关闭</Button>}
        width={640}
      >
        {negotiation && (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Card size="small" title="谈判策略"><Text>{negotiation.negotiation_strategy}</Text></Card>
            <Card size="small" title="价格目标"><Text strong style={{ fontSize: 16 }}>{negotiation.price_target}</Text></Card>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="谈判要点">
                  <List size="small" dataSource={negotiation.talking_points} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}>{s}</List.Item>} />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="优势点">
                  <List size="small" dataSource={negotiation.leverage_points} renderItem={(s: string) => <List.Item style={{ padding: "2px 0" }}><Tag color="blue">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            </Row>
            <Card size="small" title="备选方案"><Text>{negotiation.fallback_plan}</Text></Card>
            <Card size="small" title="建议方法"><Text>{negotiation.suggested_approach}</Text></Card>
          </Space>
        )}
      </Modal>
    </div>
  );
}
