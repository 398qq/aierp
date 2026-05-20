import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Descriptions, Tag, Button, Space, Spin, Alert, Table, message, Typography, Row, Col, List, Progress, Modal, Select, Input } from "antd";
import { ArrowLeftOutlined, EditOutlined, ThunderboltOutlined, PieChartOutlined, SwapOutlined, ImportOutlined, NodeIndexOutlined, DashboardOutlined, AlertOutlined, ApartmentOutlined, BulbOutlined, TrophyOutlined, TeamOutlined, RocketOutlined, LineChartOutlined, RobotOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { getBrand, getBrands, getProducts, getBrandProfile, getBrandPortfolio, getSimilarBrands, compareBrands, importBrandFromText, getBrandHealth, getBrandRisk, getBrandSupplierMatrix, getBrandRecommendations, getBrandProductPerformance, getBrandCustomerPenetration, getBrandLifecycle, getBrandPriceTrends, autoCompleteBrand } from "../../api";
import type { Brand, Product, BrandProfile, BrandPortfolio, SimilarBrand, BrandComparison, BrandHealth, BrandRisk, BrandSupplierMatrix, BrandRecommendation, BrandProductPerformance, BrandCustomerPenetration, BrandLifecycle, BrandPriceTrends } from "../../types";

const { Text, Title } = Typography;

export default function BrandDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [brand, setBrand] = useState<Brand | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<BrandProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [portfolio, setPortfolio] = useState<BrandPortfolio | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [similarBrands, setSimilarBrands] = useState<SimilarBrand[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareBrandId, setCompareBrandId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<BrandComparison | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [allBrands, setAllBrands] = useState<Brand[]>([]);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importLoading, setImportLoading] = useState(false);
  const [health, setHealth] = useState<BrandHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [risk, setRisk] = useState<BrandRisk | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [supplierMatrix, setSupplierMatrix] = useState<BrandSupplierMatrix | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<BrandRecommendation | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const [perf, setPerf] = useState<BrandProductPerformance | null>(null);
  const [perfLoading, setPerfLoading] = useState(false);
  const [penetration, setPenetration] = useState<BrandCustomerPenetration | null>(null);
  const [penetrationLoading, setPenetrationLoading] = useState(false);
  const [lifecycle, setLifecycle] = useState<BrandLifecycle | null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);
  const [priceTrends, setPriceTrends] = useState<BrandPriceTrends | null>(null);
  const [priceTrendsLoading, setPriceTrendsLoading] = useState(false);
  const [autoCompleteLoading, setAutoCompleteLoading] = useState(false);

  useEffect(() => { loadData(); }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [brandRes, prodRes] = await Promise.all([
        getBrand(Number(id)),
        getProducts({ brand_id: Number(id), page_size: 100 }),
      ]);
      setBrand(brandRes.data.data as Brand);
      setProducts(prodRes.data.data.list as Product[]);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const loadProfile = async () => {
    setProfileLoading(true);
    try {
      const resp = await getBrandProfile(Number(id));
      if (resp.data.code === 0) setProfile(resp.data.data as BrandProfile);
    } catch { message.error("生成品牌画像失败"); }
    finally { setProfileLoading(false); }
  };

  const loadPortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const resp = await getBrandPortfolio(Number(id));
      if (resp.data.code === 0) setPortfolio(resp.data.data as BrandPortfolio);
    } catch { message.error("产品线分析失败"); }
    finally { setPortfolioLoading(false); }
  };

  const loadSimilar = async () => {
    setSimilarLoading(true);
    try {
      const resp = await getSimilarBrands(Number(id));
      if (resp.data.code === 0) setSimilarBrands(resp.data.data as SimilarBrand[]);
    } catch { message.error("加载相似品牌失败"); }
    finally { setSimilarLoading(false); }
  };

  const openCompare = async () => {
    const resp = await getBrands();
    setAllBrands((resp.data.data as Brand[]).filter((b) => b.id !== Number(id)));
    setCompareModalOpen(true);
  };

  const handleCompare = async () => {
    if (!compareBrandId) return;
    setCompareLoading(true);
    try {
      const resp = await compareBrands(Number(id), compareBrandId);
      if (resp.data.code === 0) setComparison(resp.data.data as BrandComparison);
    } catch { message.error("品牌对比失败"); }
    finally { setCompareLoading(false); }
  };

  const handleImport = async () => {
    setImportLoading(true);
    try {
      const resp = await importBrandFromText(importText, true);
      if (resp.data.code === 0) {
        const data = resp.data.data as unknown as Record<string, unknown>;
        if (data.created_id) {
          message.success(`已创建品牌: ${data.name}`);
          navigate(`/brands/${data.created_id}`);
        } else {
          message.success(`已解析: ${data.name}`);
        }
        setImportModalOpen(false);
      }
    } catch { message.error("导入失败"); }
    finally { setImportLoading(false); }
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const resp = await getBrandHealth(Number(id));
      if (resp.data.code === 0) setHealth(resp.data.data as BrandHealth);
    } catch { message.error("健康分析失败"); }
    finally { setHealthLoading(false); }
  };

  const loadRisk = async () => {
    setRiskLoading(true);
    try {
      const resp = await getBrandRisk(Number(id));
      if (resp.data.code === 0) setRisk(resp.data.data as BrandRisk);
    } catch { message.error("风险评估失败"); }
    finally { setRiskLoading(false); }
  };

  const loadSupplierMatrix = async () => {
    setMatrixLoading(true);
    try {
      const resp = await getBrandSupplierMatrix(Number(id));
      if (resp.data.code === 0) setSupplierMatrix(resp.data.data as BrandSupplierMatrix);
    } catch { message.error("供应商矩阵分析失败"); }
    finally { setMatrixLoading(false); }
  };

  const loadRecommendations = async () => {
    setRecLoading(true);
    try {
      const resp = await getBrandRecommendations(Number(id));
      if (resp.data.code === 0) setRecommendations(resp.data.data as BrandRecommendation);
    } catch { message.error("品牌推荐失败"); }
    finally { setRecLoading(false); }
  };

  const loadPerformance = async () => {
    setPerfLoading(true);
    try { const r = await getBrandProductPerformance(Number(id)); if (r.data.code === 0) setPerf(r.data.data as BrandProductPerformance); }
    catch { message.error("产品绩效分析失败"); } finally { setPerfLoading(false); }
  };

  const loadPenetration = async () => {
    setPenetrationLoading(true);
    try { const r = await getBrandCustomerPenetration(Number(id)); if (r.data.code === 0) setPenetration(r.data.data as BrandCustomerPenetration); }
    catch { message.error("客户渗透分析失败"); } finally { setPenetrationLoading(false); }
  };

  const loadLifecycle = async () => {
    setLifecycleLoading(true);
    try { const r = await getBrandLifecycle(Number(id)); if (r.data.code === 0) setLifecycle(r.data.data as BrandLifecycle); }
    catch { message.error("生命周期预测失败"); } finally { setLifecycleLoading(false); }
  };

  const loadPriceTrends = async () => {
    setPriceTrendsLoading(true);
    try { const r = await getBrandPriceTrends(Number(id)); if (r.data.code === 0) setPriceTrends(r.data.data as BrandPriceTrends); }
    catch { message.error("价格趋势分析失败"); } finally { setPriceTrendsLoading(false); }
  };

  const handleAutoComplete = async () => {
    setAutoCompleteLoading(true);
    try {
      const resp = await autoCompleteBrand(Number(id));
      if (resp.data.code === 0) {
        const d = resp.data.data as { filled: Record<string, string>; message: string };
        message.success(d.message);
        await loadData();
      }
    } catch { message.error("AI补全失败"); }
    finally { setAutoCompleteLoading(false); }
  };

  if (loading) return <Spin style={{ margin: 40 }} />;
  if (!brand) return <Alert type="error" message="品牌未找到" />;

  const productColumns: ColumnsType<Product> = [
    { title: "SKU", dataIndex: "sku", width: 120, render: (v) => v || "-" },
    {
      title: "名称", dataIndex: "name", width: 200,
      render: (v, r) => <a onClick={() => navigate(`/products/${r.id}`)}>{v}</a>,
    },
    { title: "分类", dataIndex: "category", width: 100, render: (v) => v ? <Tag>{v}</Tag> : null },
    { title: "封装", dataIndex: "package_type", width: 100 },
    { title: "单位", dataIndex: "unit", width: 60 },
  ];

  const productCount = brand.product_count ?? products.length;
  const completionScore = Math.round(brand.completion_score ?? 0);
  const riskScore = Math.round(brand.risk_score ?? 0);
  const missingFields = brand.missing_fields || [];
  const statusLabel = brand.status === "active" ? "启用" : brand.status === "inactive" ? "停用" : brand.status === "frozen" ? "冻结" : brand.status;
  const statusColor = brand.status === "active" ? "green" : brand.status === "inactive" ? "orange" : "red";
  const typeLabel = brand.brand_type === "own_brand" ? "自有品牌" : brand.brand_type === "agency" ? "代理品牌" : brand.brand_type === "oem" ? "OEM" : brand.brand_type || "未分类";
  const lifecycleColor = brand.lifecycle_stage === "active" ? "green" : brand.lifecycle_stage === "nrnd" ? "orange" : brand.lifecycle_stage === "eol" ? "red" : "default";
  const riskLabel = brand.risk_level === "low" ? "低" : brand.risk_level === "medium" ? "中" : brand.risk_level === "high" ? "高" : brand.risk_level === "critical" ? "严重" : "未评估";
  const riskColor = brand.risk_level === "low" ? "green" : brand.risk_level === "medium" ? "orange" : brand.risk_level === "high" ? "red" : brand.risk_level === "critical" ? "purple" : "default";
  const nextAction = !productCount ? "补充产品" : completionScore < 70 ? "完善资料" : brand.lifecycle_stage === "eol" || brand.lifecycle_stage === "nrnd" ? "替代评估" : brand.authorization_status === "unauthorized" ? "授权核验" : riskScore >= 70 ? "风险复核" : "正常维护";

  return (
    <div>
      <style>{`
        .brand-detail-hero {
          margin-bottom: 12px;
        }
        .brand-detail-hero .ant-card-body {
          padding: 16px;
        }
        .brand-detail-head {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: flex-start;
          justify-content: space-between;
        }
        .brand-detail-title {
          min-width: 260px;
          flex: 1 1 360px;
        }
        .brand-detail-title h3 {
          margin: 0 0 6px;
        }
        .brand-detail-actions {
          display: flex;
          flex: 1 1 420px;
          flex-direction: column;
          gap: 8px;
          align-items: flex-end;
        }
        .brand-detail-ai-actions {
          justify-content: flex-end;
        }
        .brand-detail-summary {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
        }
        .brand-detail-metric {
          height: 100%;
          padding: 10px 12px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-detail-metric-label {
          display: block;
          margin-bottom: 8px;
          font-size: 12px;
        }
        @media (max-width: 768px) {
          .brand-detail-title {
            min-width: 0;
          }
          .brand-detail-actions {
            align-items: stretch;
            flex-basis: 100%;
          }
          .brand-detail-actions .ant-space {
            width: 100%;
          }
        }
      `}</style>

      <Card className="brand-detail-hero">
        <div className="brand-detail-head">
          <div className="brand-detail-title">
            <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate("/brands")}>返回列表</Button>
            <Title level={3}>{brand.name}</Title>
            <Space wrap size={6}>
              {brand.name_cn && <Text type="secondary">{brand.name_cn}</Text>}
              {brand.code && <Tag>{brand.code}</Tag>}
              <Tag color={statusColor}>{statusLabel}</Tag>
              <Tag color="blue">{typeLabel}</Tag>
              {brand.level && <Tag color={brand.level === "A" ? "red" : brand.level === "B" ? "blue" : "default"}>{brand.level}级</Tag>}
              {brand.lifecycle_stage && <Tag color={lifecycleColor}>{brand.lifecycle_stage.toUpperCase()}</Tag>}
              {brand.is_automotive && <Tag color="geekblue">车规</Tag>}
            </Space>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">{brand.description || brand.product_lines || "暂无品牌介绍"}</Text>
            </div>
          </div>
          <div className="brand-detail-actions">
            <Space wrap>
              <Button icon={<EditOutlined />} onClick={() => navigate(`/brands/${id}/edit`)}>编辑</Button>
              <Button icon={<RobotOutlined />} loading={autoCompleteLoading} onClick={handleAutoComplete}>AI 补全</Button>
              <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>AI 导入</Button>
            </Space>
            <Space wrap className="brand-detail-ai-actions">
              <Button size="small" icon={<ThunderboltOutlined />} loading={profileLoading} onClick={loadProfile}>画像</Button>
              <Button size="small" icon={<PieChartOutlined />} loading={portfolioLoading} onClick={loadPortfolio}>产品线</Button>
              <Button size="small" icon={<NodeIndexOutlined />} loading={similarLoading} onClick={loadSimilar}>相似</Button>
              <Button size="small" icon={<SwapOutlined />} onClick={openCompare}>对比</Button>
              <Button size="small" icon={<DashboardOutlined />} loading={healthLoading} onClick={loadHealth}>健康</Button>
              <Button size="small" icon={<AlertOutlined />} loading={riskLoading} onClick={loadRisk}>风险</Button>
              <Button size="small" icon={<ApartmentOutlined />} loading={matrixLoading} onClick={loadSupplierMatrix}>供应商</Button>
              <Button size="small" icon={<BulbOutlined />} loading={recLoading} onClick={loadRecommendations}>推荐</Button>
              <Button size="small" icon={<TrophyOutlined />} loading={perfLoading} onClick={loadPerformance}>绩效</Button>
              <Button size="small" icon={<TeamOutlined />} loading={penetrationLoading} onClick={loadPenetration}>客户</Button>
              <Button size="small" icon={<RocketOutlined />} loading={lifecycleLoading} onClick={loadLifecycle}>周期</Button>
              <Button size="small" icon={<LineChartOutlined />} loading={priceTrendsLoading} onClick={loadPriceTrends}>价格</Button>
            </Space>
          </div>
        </div>
        <Row gutter={[12, 12]} className="brand-detail-summary">
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">建议动作</Text>
              <Tag color={nextAction === "正常维护" ? "green" : "orange"}>{nextAction}</Tag>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">风险评分</Text>
              <Space>
                <Tag color={riskColor}>{riskLabel}</Tag>
                <Progress percent={riskScore} size="small" style={{ width: 96 }} status={riskScore >= 70 ? "exception" : "normal"} />
              </Space>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">资料完整度</Text>
              <Space>
                <Progress percent={completionScore} size="small" style={{ width: 96 }} status={completionScore < 50 ? "exception" : completionScore < 80 ? "normal" : "success"} />
                {missingFields.length > 0 && <Tag color="gold">缺 {missingFields.length} 项</Tag>}
              </Space>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">产品覆盖</Text>
              <Space>
                <Tag color={productCount > 0 ? "blue" : "orange"}>{productCount} 个产品</Tag>
                {brand.authorization_status === "unauthorized" && <Tag color="red">未授权</Tag>}
              </Space>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Brand Info */}
      <Card title="品牌信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small" title="基础信息" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="编码">{brand.code || "-"}</Descriptions.Item>
          <Descriptions.Item label="名称">{brand.name}</Descriptions.Item>
          <Descriptions.Item label="中文名">{brand.name_cn || "-"}</Descriptions.Item>
          <Descriptions.Item label="简称">{brand.short_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={brand.status === "active" ? "green" : brand.status === "inactive" ? "orange" : "red"}>
              {brand.status === "active" ? "启用" : brand.status === "inactive" ? "停用" : brand.status === "frozen" ? "冻结" : brand.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            {brand.brand_type === "own_brand" ? "自有品牌" : brand.brand_type === "agency" ? "代理品牌" : brand.brand_type === "oem" ? "OEM" : brand.brand_type || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="分类">{brand.category || "-"}</Descriptions.Item>
          <Descriptions.Item label="产品数"><Tag color="blue">{brand.product_count || products.length}</Tag></Descriptions.Item>
          <Descriptions.Item label="Logo">{brand.logo ? <a href={brand.logo} target="_blank" rel="noopener noreferrer">查看</a> : "-"}</Descriptions.Item>
          <Descriptions.Item label="官网">
            {brand.website ? <a href={brand.website} target="_blank" rel="noopener noreferrer">{brand.website}</a> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="品牌介绍" span={2}>{brand.description || "-"}</Descriptions.Item>
        </Descriptions>

        <Descriptions bordered column={3} size="small" title="商业信息" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="品牌等级">
            {brand.level ? <Tag color={brand.level === "A" ? "red" : brand.level === "B" ? "blue" : "default"}>{brand.level}级</Tag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="品牌定位">
            {brand.positioning === "high" ? "高端" : brand.positioning === "mid" ? "中端" : brand.positioning === "low" ? "低端" : brand.positioning || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="负责人">{brand.owner || "-"}</Descriptions.Item>
          <Descriptions.Item label="产品线" span={3}>{brand.product_lines || "-"}</Descriptions.Item>
          <Descriptions.Item label="目标市场" span={3}>{brand.target_markets || "-"}</Descriptions.Item>
        </Descriptions>

        <Descriptions bordered column={3} size="small" title="供应链信息" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="原厂">{brand.manufacturer_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="授权状态">
            {brand.authorization_status === "authorized" ? <Tag color="green">已授权</Tag> : brand.authorization_status === "unauthorized" ? <Tag color="red">未授权</Tag> : brand.authorization_status || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="生命周期">
            {brand.lifecycle_stage ? <Tag color={brand.lifecycle_stage === "active" ? "green" : brand.lifecycle_stage === "nrnd" ? "orange" : "red"}>{brand.lifecycle_stage.toUpperCase()}</Tag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="车规">{brand.is_automotive ? <Tag color="blue">是</Tag> : "否"}</Descriptions.Item>
          <Descriptions.Item label="MOQ">{brand.moq ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="交期">{brand.lead_time_days ? `${brand.lead_time_days}天` : "-"}</Descriptions.Item>
          <Descriptions.Item label="风险等级">
            {brand.risk_level ? <Tag color={brand.risk_level === "low" ? "green" : brand.risk_level === "medium" ? "orange" : brand.risk_level === "high" ? "red" : "red"}>{brand.risk_level === "low" ? "低" : brand.risk_level === "medium" ? "中" : brand.risk_level === "high" ? "高" : "严重"}</Tag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="RoHS">
            {brand.rohs_status ? <Tag color={brand.rohs_status === "compliant" ? "green" : "red"}>{brand.rohs_status === "compliant" ? "合规" : brand.rohs_status === "non_compliant" ? "不合规" : brand.rohs_status === "exempt" ? "豁免" : brand.rohs_status}</Tag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="关联供应商">{brand.supplier_id ?? "-"}</Descriptions.Item>
        </Descriptions>

        <Descriptions bordered column={3} size="small" title="AI & 元数据">
          <Descriptions.Item label="AI关键词">{brand.ai_keywords || "-"}</Descriptions.Item>
          <Descriptions.Item label="风险评分">{brand.risk_score != null ? <Progress percent={Math.round(brand.risk_score)} size="small" status={brand.risk_score > 70 ? "exception" : brand.risk_score > 40 ? "active" : "success"} /> : "-"}</Descriptions.Item>
          <Descriptions.Item label="替代品牌">{brand.alternative_brands || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{brand.created_at ? new Date(brand.created_at).toLocaleDateString("zh-CN") : "-"}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{brand.updated_at ? new Date(brand.updated_at).toLocaleDateString("zh-CN") : "-"}</Descriptions.Item>
          <Descriptions.Item label="备注">{brand.notes || "-"}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* AI Brand Profile */}
      {profile && (
        <Card title={<><ThunderboltOutlined /> AI 品牌画像</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">市场地位</Text>
                <div><Tag color="blue">{profile.market_position}</Tag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">品牌实力</Text>
                <Progress percent={profile.brand_strength_score} size="small" status={profile.brand_strength_score > 70 ? "success" : "normal"} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">采购难度</Text>
                <div><Tag color={profile.procurement_difficulty.includes("容易") ? "green" : profile.procurement_difficulty.includes("中等") ? "orange" : "red"}>{profile.procurement_difficulty}</Tag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">价格定位</Text>
                <div><Tag color={profile.price_positioning === "高端" ? "purple" : profile.price_positioning === "中端" ? "blue" : "green"}>{profile.price_positioning}</Tag></div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="技术优势">
                <List size="small" dataSource={profile.technology_advantages} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{i}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="竞争优势">
                <List size="small" dataSource={profile.competitive_advantages} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="green">{i}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="竞争对手">
                <List size="small" dataSource={profile.key_competitors} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="orange">{i}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="目标市场">
                <List size="small" dataSource={profile.target_markets} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}>{i}</List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="典型应用">
                <List size="small" dataSource={profile.typical_applications} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}>{i}</List.Item>} />
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                <Text strong>合作建议：</Text><Text>{profile.recommendation}</Text>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* AI Portfolio Analysis */}
      {portfolio && (
        <Card title={<><PieChartOutlined /> AI 产品线分析</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">产品线完整度</Text>
                <div><Tag color={portfolio.portfolio_strength === "完整" ? "green" : portfolio.portfolio_strength === "较全" ? "blue" : "orange"}>{portfolio.portfolio_strength}</Tag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">库存健康度</Text><div>{portfolio.inventory_health}</div></Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="分类分析">
                {portfolio.category_analysis?.map((c, i) => (
                  <Tag key={i} style={{ marginBottom: 4 }}>{c.category}: {c.count}个 ({c.pct}%) — {c.assessment}</Tag>
                ))}
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="增长方向">
                <List size="small" dataSource={portfolio.growth_areas} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="green">{i}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="产品线缺口">
                <List size="small" dataSource={portfolio.gap_analysis} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="orange">{i}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="交叉销售机会">
                <List size="small" dataSource={portfolio.cross_sell_opportunities} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{i}</Tag></List.Item>} />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Similar Brands */}
      {similarBrands.length > 0 && (
        <Card title={<><NodeIndexOutlined /> 相似品牌</>} style={{ marginBottom: 16 }}>
          <Table size="small" dataSource={similarBrands} rowKey="id" pagination={false}
            columns={[
              { title: "品牌", key: "name", width: 150, render: (_: unknown, r: SimilarBrand) => <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}{r.name_cn ? ` (${r.name_cn})` : ""}</a> },
              { title: "分类", dataIndex: "category", width: 100, render: (v: string) => v ? <Tag>{v}</Tag> : null },
              { title: "产品数", dataIndex: "product_count", width: 80 },
              { title: "共同分类", dataIndex: "shared_categories", width: 80, render: (v: number) => <Tag color="blue">{v}</Tag> },
            ]}
          />
        </Card>
      )}

      {/* AI Brand Health Dashboard */}
      {health && (
        <Card title={<><DashboardOutlined /> AI 健康看板</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">综合评分</Text>
                <Progress percent={health.overall_health_score} size="small" status={health.overall_health_score > 70 ? "success" : health.overall_health_score > 40 ? "normal" : "exception"} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">健康等级</Text>
                <div><Tag color={health.health_label === "优秀" ? "green" : health.health_label === "良好" ? "blue" : health.health_label === "一般" ? "orange" : "red"}>{health.health_label}</Tag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">趋势</Text>
                <div><Tag color={health.trend_direction === "上升" ? "green" : health.trend_direction === "稳定" ? "blue" : "red"}>{health.trend_direction}</Tag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">经营概览</Text>
                <div><Text style={{ fontSize: 12 }}>
                  {health.context?.total_orders as number} 订单 / {health.context?.active_customers as number} 客户
                </Text></div>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="收入评估"><Text>{health.revenue_assessment}</Text></Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="利润评估"><Text>{health.margin_assessment}</Text></Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="客户健康"><Text>{health.customer_assessment}</Text></Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="库存健康"><Text>{health.inventory_assessment}</Text></Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="风险信号">
                <List size="small" dataSource={health.risk_signals} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="red">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                <Text strong>改进建议：</Text>
                <List size="small" dataSource={health.improvement_suggestions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}>{s}</List.Item>} />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* AI Brand Risk Assessment */}
      {risk && (
        <Card title={<><AlertOutlined /> AI 风险评估</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={4}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Text type="secondary">综合风险评分</Text>
                <Progress type="circle" percent={risk.risk_score} size={80} status={risk.risk_score > 70 ? "exception" : risk.risk_score > 40 ? "normal" : "success"} />
                <div style={{ marginTop: 8 }}><Tag color={risk.risk_level === "低" ? "green" : risk.risk_level === "中" ? "orange" : risk.risk_level === "高" ? "red" : "#f5222d"}>{risk.risk_level}</Tag></div>
              </Card>
            </Col>
            <Col span={10}>
              <Card size="small" type="inner" title="风险维度分解">
                <div style={{ marginBottom: 8 }}><Text type="secondary" style={{ width: 80, display: "inline-block" }}>供应商风险</Text><Progress percent={parseInt(risk.supplier_risk) || 0} size="small" /></div>
                <div style={{ marginBottom: 8 }}><Text type="secondary" style={{ width: 80, display: "inline-block" }}>生命周期风险</Text><Progress percent={parseInt(risk.lifecycle_risk) || 0} size="small" /></div>
                <div style={{ marginBottom: 8 }}><Text type="secondary" style={{ width: 80, display: "inline-block" }}>客户集中度</Text><Progress percent={parseInt(risk.concentration_risk) || 0} size="small" /></div>
                <div><Text type="secondary" style={{ width: 80, display: "inline-block" }}>市场替代风险</Text><Progress percent={parseInt(risk.market_risk) || 0} size="small" /></div>
              </Card>
            </Col>
            <Col span={10}>
              <Card size="small" type="inner" title="主要风险">
                <List size="small" dataSource={risk.top_risks} renderItem={(s: string, i: number) => (
                  <List.Item style={{ padding: '2px 0' }}>
                    <Tag color={i === 0 ? "red" : i === 1 ? "orange" : "gold"}>{i + 1}. {s}</Tag>
                  </List.Item>
                )} />
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#fffbe6" }}>
                <Text strong>缓解建议：</Text>
                <List size="small" dataSource={risk.mitigation_suggestions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* AI Brand-Supplier Matrix */}
      {supplierMatrix && (
        <Card title={<><ApartmentOutlined /> AI 供应商矩阵</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={8}>
              <Card size="small" type="inner">
                <Text type="secondary">供应商覆盖评分</Text>
                <Progress percent={supplierMatrix.coverage_score} size="small" status={supplierMatrix.coverage_score > 70 ? "success" : "normal"} />
                <div style={{ marginTop: 8 }}><Text>{supplierMatrix.overall_assessment}</Text></div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="谈判空间">
                <Text>{supplierMatrix.negotiation_leverage}</Text>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="价格优化建议">
                <List size="small" dataSource={supplierMatrix.price_optimization} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {supplierMatrix.supplier_details && supplierMatrix.supplier_details.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="供应商覆盖明细">
                  <Table size="small" dataSource={supplierMatrix.supplier_details} rowKey="supplier_id" pagination={false}
                    columns={[
                      { title: "供应商", dataIndex: "supplier_name", width: 180 },
                      { title: "产品数", dataIndex: "product_count", width: 80 },
                      { title: "均价", dataIndex: "avg_cost", width: 120, render: (v: number | null) => v ? `¥${v.toFixed(4)}` : "-" },
                      { title: "最低价", dataIndex: "min_cost", width: 120, render: (v: number | null) => v ? `¥${v.toFixed(4)}` : "-" },
                      { title: "平均交期", dataIndex: "avg_lead_time", width: 100, render: (v: number | null) => v ? `${v}天` : "-" },
                    ]}
                  />
                </Card>
              </Col>
            )}
            {supplierMatrix.single_source_products.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="单源风险产品" style={{ background: "#fff2e8" }}>
                  {supplierMatrix.single_source_products.map((p, i) => (
                    <Tag key={i} color="red" style={{ marginBottom: 4 }}>{p.product_name} → {p.supplier} | ¥{p.cost_price} | {p.risk_reason}</Tag>
                  ))}
                </Card>
              </Col>
            )}
            {supplierMatrix.backup_recommendations.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="备选供应商建议">
                  {supplierMatrix.backup_recommendations.map((r, i) => (
                    <Tag key={i} color="green" style={{ marginBottom: 4 }}>{r.current} → {r.recommended} | {r.reason}</Tag>
                  ))}
                </Card>
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* AI Brand Recommendations */}
      {recommendations && (
        <Card title={<><BulbOutlined /> AI 品牌推荐</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                <Text>{recommendations.recommendation_summary}</Text>
              </Card>
            </Col>
            {recommendations.recommended_brands.length > 0 && (
              <Col span={24}>
                <Table size="small" dataSource={recommendations.recommended_brands} rowKey="brand_name" pagination={false}
                  columns={[
                    { title: "推荐品牌", dataIndex: "brand_name", width: 180,
                      render: (v: string, r) => <a onClick={() => {
                        const found = recommendations.co_purchase_raw?.find(b => b.name === v);
                        if (found) navigate(`/brands/${found.id}`);
                      }}>{v}</a>
                    },
                    { title: "推荐度", dataIndex: "overlap_score", width: 100, render: (v: number) => <Progress percent={v} size="small" /> },
                    { title: "原因", dataIndex: "reason" },
                    { title: "优先级", dataIndex: "priority", width: 80, render: (v: string) => <Tag color={v === "高" ? "red" : v === "中" ? "blue" : "default"}>{v}</Tag> },
                  ]}
                />
              </Col>
            )}
            {recommendations.co_purchase_raw && recommendations.co_purchase_raw.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="关联购买数据">
                  <Table size="small" dataSource={recommendations.co_purchase_raw} rowKey="id" pagination={false}
                    columns={[
                      { title: "品牌", key: "name", width: 180, render: (_: unknown, r) => <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}{r.name_cn ? ` (${r.name_cn})` : ""}</a> },
                      { title: "分类", dataIndex: "category", width: 100, render: (v: string) => v ? <Tag>{v}</Tag> : null },
                      { title: "共同客户", dataIndex: "shared_customers", width: 100 },
                      { title: "共同产品", dataIndex: "shared_products", width: 100 },
                    ]}
                  />
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="交叉销售策略">
                <List size="small" dataSource={recommendations.cross_sell_strategies} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" title="目标行业">
                <List size="small" dataSource={recommendations.target_industries} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag>{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" title="预期转化">
                <Text>{recommendations.expected_conversion}</Text>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Brand Product Performance */}
      {perf && (
        <Card title={<><TrophyOutlined /> AI 产品绩效</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                <Typography.Text>{perf.portfolio_assessment}</Typography.Text>
              </Card>
            </Col>
            {perf.star_products.length > 0 && (
              <Col span={14}>
                <Card size="small" type="inner" title="明星产品">
                  <Table size="small" dataSource={perf.star_products} rowKey="product_name" pagination={false}
                    columns={[
                      { title: "产品", dataIndex: "product_name", width: 160, render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
                      { title: "销售额", dataIndex: "revenue", width: 100, render: (v: number) => `¥${v.toLocaleString()}` },
                      { title: "毛利率", dataIndex: "margin_pct", width: 80, render: (v: number) => <Tag color="green">{v}%</Tag> },
                      { title: "增幅", dataIndex: "growth", width: 80 },
                      { title: "建议", dataIndex: "recommendation" },
                    ]}
                  />
                </Card>
              </Col>
            )}
            {perf.problem_products.length > 0 && (
              <Col span={10}>
                <Card size="small" type="inner" title="问题产品" style={{ background: "#fff2e8" }}>
                  {perf.problem_products.map((p, i) => (
                    <Tag key={i} color="orange" style={{ marginBottom: 4 }}>{p.product_name}: {p.issue} → {p.suggestion}</Tag>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="聚焦建议">
                <List size="small" dataSource={perf.focus_recommendations} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {perf.phase_out_candidates.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="淘汰候选" style={{ background: "#fff1f0" }}>
                  <List size="small" dataSource={perf.phase_out_candidates} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="red">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* Brand Customer Penetration */}
      {penetration && (
        <Card title={<><TeamOutlined /> AI 客户渗透</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Progress type="circle" percent={penetration.penetration_score} size={80} status={penetration.penetration_score > 60 ? "success" : penetration.penetration_score > 30 ? "normal" : "exception"} />
                <div style={{ marginTop: 8 }}><Typography.Text>渗透评分</Typography.Text></div>
              </Card>
            </Col>
            <Col span={18}>
              <Card size="small" type="inner">
                <Typography.Text>{penetration.penetration_assessment}</Typography.Text>
              </Card>
            </Col>
            {penetration.key_industries.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="核心覆盖行业">
                  <Table size="small" dataSource={penetration.key_industries} rowKey="industry" pagination={false}
                    columns={[
                      { title: "行业", dataIndex: "industry" },
                      { title: "客户数", dataIndex: "customer_count", width: 70 },
                      { title: "贡献占比", dataIndex: "contribution_pct", width: 80, render: (v: number) => `${v}%` },
                      { title: "评估", dataIndex: "assessment" },
                    ]}
                  />
                </Card>
              </Col>
            )}
            {penetration.untapped_industries.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="待开发行业" style={{ background: "#fffbe6" }}>
                  {penetration.untapped_industries.map((u, i) => (
                    <Tag key={i} color="orange" style={{ marginBottom: 4 }}>{u.industry}: {u.potential_customers}潜在客户 → {u.strategy}</Tag>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="留存策略">
                <List size="small" dataSource={penetration.retention_strategy} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="扩展策略">
                <List size="small" dataSource={penetration.expansion_strategy} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="green">{s}</Tag></List.Item>} />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Brand Lifecycle Prediction */}
      {lifecycle && (
        <Card title={<><RocketOutlined /> AI 生命周期预测</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">所处阶段</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={lifecycle.lifecycle_stage === "成长期" ? "green" : lifecycle.lifecycle_stage === "成熟期" ? "blue" : lifecycle.lifecycle_stage === "衰退期" ? "red" : "orange"} style={{ fontSize: 16, padding: '4px 16px' }}>{lifecycle.lifecycle_stage}</Tag>
                </div>
                <div style={{ marginTop: 8 }}><Typography.Text style={{ fontSize: 12 }}>置信度 {lifecycle.stage_confidence}%</Typography.Text></div>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="阶段依据">
                <List size="small" dataSource={lifecycle.stage_evidence} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}>{s}</List.Item>} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" title="战略建议" style={{ background: "#f6ffed" }}>
                <Typography.Text>{lifecycle.strategic_advice}</Typography.Text>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="12个月展望">
                <Typography.Text>{lifecycle.next_12m_outlook}</Typography.Text>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="关键行动">
                <List size="small" dataSource={lifecycle.key_actions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {lifecycle.risk_signals.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" style={{ background: "#fff2e8" }}>
                  <Typography.Text strong>风险信号：</Typography.Text>
                  {lifecycle.risk_signals.map((s, i) => <Tag key={i} color="red" style={{ marginLeft: 8 }}>{s}</Tag>)}
                </Card>
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* Brand Price Trends */}
      {priceTrends && (
        <Card title={<><LineChartOutlined /> AI 价格走势</>} style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">价格趋势</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={priceTrends.price_trend === "上涨" ? "red" : priceTrends.price_trend === "下降" ? "green" : "blue"} style={{ fontSize: 16 }}>{priceTrends.price_trend}</Tag>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" style={{ textAlign: "center" }}>
                <Typography.Text type="secondary">价格健康度</Typography.Text>
                <Progress percent={priceTrends.trend_score} size="small" status={priceTrends.trend_score > 60 ? "success" : priceTrends.trend_score > 30 ? "normal" : "exception"} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner">
                <Typography.Text>{priceTrends.margin_assessment}</Typography.Text>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="竞争力评估">
                <Typography.Text>{priceTrends.competitiveness}</Typography.Text>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="优化建议">
                <List size="small" dataSource={priceTrends.optimization_suggestions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="blue">{s}</Tag></List.Item>} />
              </Card>
            </Col>
            {priceTrends.pricing_issues.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="定价问题" style={{ background: "#fff2e8" }}>
                  <List size="small" dataSource={priceTrends.pricing_issues} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><Tag color="orange">{s}</Tag></List.Item>} />
                </Card>
              </Col>
            )}
            {priceTrends.opportunity_alert && (
              <Col span={12}>
                <Card size="small" type="inner" style={{ background: "#f6ffed" }}>
                  <Typography.Text strong>机会提示：</Typography.Text><Typography.Text>{priceTrends.opportunity_alert}</Typography.Text>
                </Card>
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* Products */}
      <Card title={`关联产品 (${products.length})`}>
        {products.length > 0 ? (
          <Table rowKey="id" columns={productColumns} dataSource={products} size="small" pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }} />
        ) : (<Text type="secondary">暂无关联产品</Text>)}
      </Card>

      {/* Compare Modal */}
      <Modal
        title="品牌对比" open={compareModalOpen} onCancel={() => { setCompareModalOpen(false); setComparison(null); }}
        width={800}
        footer={[<Button key="close" onClick={() => setCompareModalOpen(false)}>关闭</Button>]}
      >
        <Space style={{ width: "100%", marginBottom: 16 }}>
          <Text strong>对比品牌：</Text>
          <Select
            showSearch style={{ width: 300 }}
            placeholder="选择要对比的品牌"
            filterOption={(input, option) => (option?.label as string || "").toLowerCase().includes(input.toLowerCase())}
            options={allBrands.map((b) => ({ label: `${b.name}${b.name_cn ? ` (${b.name_cn})` : ""}`, value: b.id }))}
            value={compareBrandId}
            onChange={(v) => setCompareBrandId(v)}
          />
          <Button type="primary" onClick={handleCompare} loading={compareLoading} disabled={!compareBrandId}>开始对比</Button>
        </Space>

        {comparison && (
          <div>
            <Card size="small" style={{ marginBottom: 12, background: "#f6ffed" }}>
              <Text>{comparison.comparison_summary}</Text>
            </Card>
            <Table size="small" dataSource={comparison.dimension_scores || []} pagination={false} rowKey="dimension"
              columns={[
                { title: "维度", dataIndex: "dimension", width: 100 },
                { title: comparison.brand_a?.name as string || "品牌A", dataIndex: "a_score", width: 80, render: (v: number) => <Progress percent={v * 10} size="small" /> },
                { title: comparison.brand_b?.name as string || "品牌B", dataIndex: "b_score", width: 80, render: (v: number) => <Progress percent={v * 10} size="small" /> },
                { title: "说明", dataIndex: "note" },
              ]}
            />
            <Card size="small" style={{ marginTop: 12 }} title="替换分析">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="替换可行性">
                  <Tag color={comparison.switching_feasibility === "容易" ? "green" : comparison.switching_feasibility === "中等" ? "orange" : "red"}>{comparison.switching_feasibility}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="推荐策略">
                  <Tag color="blue">{comparison.recommended_strategy}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="注意事项" span={2}>
                  <List size="small" dataSource={comparison.switching_notes} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}>{s}</List.Item>} />
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </div>
        )}
      </Modal>

      {/* Import Modal */}
      <Modal
        title="AI 品牌导入" open={importModalOpen} onCancel={() => setImportModalOpen(false)}
        onOk={handleImport} confirmLoading={importLoading} okText="导入"
      >
        <Text>粘贴品牌描述文本（公司介绍、官网About、供应商目录等），AI 自动提取品牌信息：</Text>
        <Input.TextArea
          rows={6} value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="例如：意法半导体 (STMicroelectronics) 是全球领先的半导体公司，专注于MCU、电源管理、传感器等产品线..."
          style={{ marginTop: 8 }}
        />
      </Modal>
    </div>
  );
}
