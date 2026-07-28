import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Descriptions, Button, Space, Spin, Alert, message, Typography, Row, Col, List, Progress, Modal, Select, Input, Flex, Popconfirm } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { erpPagination } from "../../ui/pagination";
import { ArrowLeftOutlined, EditOutlined, ThunderboltOutlined, PieChartOutlined, ImportOutlined, NodeIndexOutlined, DashboardOutlined, AlertOutlined, ApartmentOutlined, BulbOutlined, TrophyOutlined, TeamOutlined, RocketOutlined, LineChartOutlined, RobotOutlined, PlusOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";

import { getBrand, getBrands, getProducts, updateProduct, getBrandProfile, getBrandPortfolio, getSimilarBrands, compareBrands, importBrandFromText, getBrandHealth, getBrandRisk, getBrandSupplierMatrix, getBrandRecommendations, getBrandProductPerformance, getBrandCustomerPenetration, getBrandLifecycle, getBrandPriceTrends, autoCompleteBrand, getApiErrorMessage } from "../../api";
import type { Brand, Product, BrandProfile, BrandPortfolio, SimilarBrand, BrandComparison, BrandHealth, BrandRisk, BrandSupplierMatrix, BrandRecommendation, BrandProductPerformance, BrandCustomerPenetration, BrandLifecycle, BrandPriceTrends } from "../../types";
import { getBrandAiTasks, getBrandNextAction } from "./brandAiOrchestration";

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
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [linkCandidates, setLinkCandidates] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<number[]>([]);
  const [linkLoading, setLinkLoading] = useState(false);

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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载失败")); }
    finally { setLoading(false); }
  };

  const loadProfile = async () => {
    setProfileLoading(true);
    try {
      const resp = await getBrandProfile(Number(id));
      if (resp.data.code === 0) setProfile(resp.data.data as BrandProfile);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "生成品牌画像失败")); }
    finally { setProfileLoading(false); }
  };

  const loadPortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const resp = await getBrandPortfolio(Number(id));
      if (resp.data.code === 0) setPortfolio(resp.data.data as BrandPortfolio);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "产品线分析失败")); }
    finally { setPortfolioLoading(false); }
  };

  const loadSimilar = async () => {
    setSimilarLoading(true);
    try {
      const resp = await getSimilarBrands(Number(id));
      if (resp.data.code === 0) setSimilarBrands(resp.data.data as SimilarBrand[]);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载相似品牌失败")); }
    finally { setSimilarLoading(false); }
  };

  const openCompare = async () => {
    const resp = await getBrands();
    const payload = resp.data.data as Brand[] | { list?: Brand[] };
    const brands = Array.isArray(payload) ? payload : (payload.list || []);
    setAllBrands(brands.filter((b) => b.id !== Number(id)));
    setCompareModalOpen(true);
  };

  const handleCompare = async () => {
    if (!compareBrandId) return;
    setCompareLoading(true);
    try {
      const resp = await compareBrands(Number(id), compareBrandId);
      if (resp.data.code === 0) setComparison(resp.data.data as BrandComparison);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "品牌对比失败")); }
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "导入失败")); }
    finally { setImportLoading(false); }
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const resp = await getBrandHealth(Number(id));
      if (resp.data.code === 0) setHealth(resp.data.data as BrandHealth);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "健康分析失败")); }
    finally { setHealthLoading(false); }
  };

  const loadRisk = async () => {
    setRiskLoading(true);
    try {
      const resp = await getBrandRisk(Number(id));
      if (resp.data.code === 0) setRisk(resp.data.data as BrandRisk);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "风险评估失败")); }
    finally { setRiskLoading(false); }
  };

  const loadSupplierMatrix = async () => {
    setMatrixLoading(true);
    try {
      const resp = await getBrandSupplierMatrix(Number(id));
      if (resp.data.code === 0) setSupplierMatrix(resp.data.data as BrandSupplierMatrix);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "供应商矩阵分析失败")); }
    finally { setMatrixLoading(false); }
  };

  const loadRecommendations = async () => {
    setRecLoading(true);
    try {
      const resp = await getBrandRecommendations(Number(id));
      if (resp.data.code === 0) setRecommendations(resp.data.data as BrandRecommendation);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "品牌推荐失败")); }
    finally { setRecLoading(false); }
  };

  const loadPerformance = async () => {
    setPerfLoading(true);
    try { const r = await getBrandProductPerformance(Number(id)); if (r.data.code === 0) setPerf(r.data.data as BrandProductPerformance); } catch (e: unknown) { message.error(getApiErrorMessage(e, "产品绩效分析失败")); } finally { setPerfLoading(false); }
  };

  const loadPenetration = async () => {
    setPenetrationLoading(true);
    try { const r = await getBrandCustomerPenetration(Number(id)); if (r.data.code === 0) setPenetration(r.data.data as BrandCustomerPenetration); } catch (e: unknown) { message.error(getApiErrorMessage(e, "客户渗透分析失败")); } finally { setPenetrationLoading(false); }
  };

  const loadLifecycle = async () => {
    setLifecycleLoading(true);
    try { const r = await getBrandLifecycle(Number(id)); if (r.data.code === 0) setLifecycle(r.data.data as BrandLifecycle); } catch (e: unknown) { message.error(getApiErrorMessage(e, "生命周期预测失败")); } finally { setLifecycleLoading(false); }
  };

  const loadPriceTrends = async () => {
    setPriceTrendsLoading(true);
    try { const r = await getBrandPriceTrends(Number(id)); if (r.data.code === 0) setPriceTrends(r.data.data as BrandPriceTrends); } catch (e: unknown) { message.error(getApiErrorMessage(e, "价格趋势分析失败")); } finally { setPriceTrendsLoading(false); }
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
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "AI补全失败")); }
    finally { setAutoCompleteLoading(false); }
  };

  const openLinkProducts = async () => {
    setLinkLoading(true);
    setSelectedProductIds([]);
    try {
      const response = await getProducts({ page: 1, page_size: 100 });
      const payload = response.data.data as { list?: Product[] } | Product[];
      const allProducts = Array.isArray(payload) ? payload : (payload.list || []);
      setLinkCandidates(allProducts.filter((product) => !product.brand_id));
      setLinkModalOpen(true);
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "加载待关联产品失败"));
    } finally {
      setLinkLoading(false);
    }
  };

  const handleLinkProducts = async () => {
    if (selectedProductIds.length === 0) {
      message.warning("请至少选择一个产品");
      return;
    }
    setLinkLoading(true);
    try {
      await Promise.all(selectedProductIds.map((productId) => updateProduct(productId, { brand_id: Number(id) })));
      message.success(`已关联 ${selectedProductIds.length} 个产品`);
      setLinkModalOpen(false);
      await loadData();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "关联产品失败"));
    } finally {
      setLinkLoading(false);
    }
  };

  const handleUnlinkProduct = async (product: Product) => {
    setLinkLoading(true);
    try {
      await updateProduct(product.id, { brand_id: null });
      message.success(`已解除 ${product.name} 的品牌关联`);
      await loadData();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "解除关联失败"));
    } finally {
      setLinkLoading(false);
    }
  };

  if (loading) return <Spin style={{ margin: 40 }} />;
  if (!brand) return <Alert type="error" message="品牌未找到" />;

  const productColumns: any = [
    { title: "SKU", dataIndex: "sku", width: 120, render: (v: any) => v || "-" },
    {
      title: "名称", dataIndex: "name", width: 200,
      render: (v: any, r: any) => <a onClick={() => navigate(`/products/${r.id}`)}>{v}</a>,
    },
    { title: "分类", dataIndex: "category", width: 100, render: (v: any) => v ? <StatusTag>{v}</StatusTag> : null },
    { title: "封装", dataIndex: "package_type", width: 100 },
    { title: "单位", dataIndex: "unit", width: 60 },
    {
      title: "操作",
      key: "actions",
      width: 230,
      fixed: "right",
      render: (_: any, product: any) => (
        <Space size={0}>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/products/${product.id}`)}>查看</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`/products/${product.id}/edit`)}>编辑</Button>
          <Popconfirm
            title="解除产品关联？"
            description="仅清空该产品的品牌归属，不会删除产品主数据。"
            okText="解除关联"
            cancelText="取消"
            onConfirm={() => handleUnlinkProduct(product)}
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>解除关联</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const productCount = brand.product_count ?? products.length;
  const completionScore = Math.round(brand.completion_score ?? 0);
  const riskScore = Math.round(brand.risk_score ?? 0);
  const missingFields = brand.missing_fields || [];
  const statusLabel = brand.status === "active" ? "启用" : brand.status === "inactive" ? "停用" : brand.status === "frozen" ? "冻结" : brand.status;
  const statusTone = brand.status === "active" ? "success" : brand.status === "inactive" ? "warning" : "danger";
  const typeLabel = brand.brand_type === "own_brand" ? "自有品牌" : brand.brand_type === "agency" ? "代理品牌" : brand.brand_type === "oem" ? "OEM" : brand.brand_type || "未分类";
  const lifecycleTone = brand.lifecycle_stage === "active" ? "success" : brand.lifecycle_stage === "nrnd" ? "warning" : brand.lifecycle_stage === "eol" ? "danger" : "neutral";
  const riskLabel = brand.risk_level === "low" ? "低" : brand.risk_level === "medium" ? "中" : brand.risk_level === "high" ? "高" : brand.risk_level === "critical" ? "严重" : "未评估";
  const riskTone = brand.risk_level === "low" ? "success" : brand.risk_level === "medium" ? "warning" : brand.risk_level === "high" ? "danger" : brand.risk_level === "critical" ? "danger" : "neutral";
  const nextAction = getBrandNextAction(brand);
  const aiTasks = getBrandAiTasks(brand);
  const taskActions: Record<string, () => void | Promise<void>> = {
    auto_complete: handleAutoComplete,
    risk: loadRisk,
    lifecycle: loadLifecycle,
    recommendations: loadRecommendations,
    supplier: loadSupplierMatrix,
    portfolio: loadPortfolio,
    profile: loadProfile,
    performance: loadPerformance,
    penetration: loadPenetration,
    similar: loadSimilar,
    compare: openCompare,
    health: loadHealth,
    price: loadPriceTrends,
  };
  const taskLoading: Record<string, boolean> = {
    auto_complete: autoCompleteLoading,
    risk: riskLoading,
    lifecycle: lifecycleLoading,
    recommendations: recLoading,
    supplier: matrixLoading,
    portfolio: portfolioLoading,
    profile: profileLoading,
    performance: perfLoading,
    penetration: penetrationLoading,
    similar: similarLoading,
    compare: compareLoading,
    health: healthLoading,
    price: priceTrendsLoading,
  };

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
        .brand-ai-workflow {
          margin-bottom: 12px;
        }
        .brand-ai-workflow .ant-card-body {
          padding: 12px;
        }
        .brand-ai-task-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }
        .brand-ai-task {
          padding: 10px;
          display: flex;
          min-height: 112px;
          flex-direction: column;
          justify-content: space-between;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .brand-ai-task-head {
          display: flex;
          gap: 8px;
          align-items: flex-start;
          justify-content: space-between;
        }
        .brand-ai-task-title {
          display: block;
          margin-bottom: 4px;
        }
        .brand-ai-task-reason {
          display: block;
          min-height: 36px;
          font-size: 12px;
        }
        .brand-ai-task-foot {
          margin-top: 8px;
          display: flex;
          gap: 8px;
          align-items: center;
          justify-content: space-between;
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
          .brand-ai-task-grid {
            grid-template-columns: 1fr;
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
              {brand.code && <StatusTag>{brand.code}</StatusTag>}
              <StatusTag tone={statusTone}>{statusLabel}</StatusTag>
              <StatusTag tone="info">{typeLabel}</StatusTag>
              {brand.level && <StatusTag tone={brand.level === "A" ? "danger" : brand.level === "B" ? "info" : "neutral"}>{brand.level}级</StatusTag>}
              {brand.lifecycle_stage && <StatusTag tone={lifecycleTone}>{brand.lifecycle_stage.toUpperCase()}</StatusTag>}
              {brand.is_automotive && <StatusTag tone="info">车规</StatusTag>}
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
          </div>
        </div>
        <Row gutter={[12, 12]} className="brand-detail-summary">
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">建议动作</Text>
              <StatusTag tone={nextAction.color}>{nextAction.label}</StatusTag>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">风险评分</Text>
              <Space>
                <StatusTag tone={riskTone}>{riskLabel}</StatusTag>
                <Progress percent={riskScore} size="small" style={{ width: 96 }} status={riskScore >= 70 ? "exception" : "normal"} />
              </Space>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">资料完整度</Text>
              <Space>
                <Progress percent={completionScore} size="small" style={{ width: 96 }} status={completionScore < 50 ? "exception" : completionScore < 80 ? "normal" : "success"} />
                {missingFields.length > 0 && <StatusTag tone="processing">缺 {missingFields.length} 项</StatusTag>}
              </Space>
            </div>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <div className="brand-detail-metric">
              <Text type="secondary" className="brand-detail-metric-label">产品覆盖</Text>
              <Space>
                <StatusTag tone={productCount > 0 ? "info" : "warning"}>{productCount} 个产品</StatusTag>
                {brand.authorization_status === "unauthorized" && <StatusTag tone="danger">未授权</StatusTag>}
              </Space>
            </div>
          </Col>
        </Row>
      </Card>

      <Card
        className="brand-ai-workflow"
        title={<Space><RobotOutlined />AI 推荐工作流</Space>}
        extra={<Text type="secondary">按风险、完整度、生命周期自动编排</Text>}
      >
        <div className="brand-ai-task-grid">
          {aiTasks.slice(0, 6).map((task) => (
            <div key={task.key} className="brand-ai-task">
              <div>
                <div className="brand-ai-task-head">
                  <Text strong className="brand-ai-task-title">{task.title}</Text>
                  <StatusTag tone={task.priority === "high" ? "danger" : task.priority === "medium" ? "warning" : "info"}>{task.priority === "high" ? "高" : task.priority === "medium" ? "中" : "低"}</StatusTag>
                </div>
                <Text type="secondary" className="brand-ai-task-reason">{task.reason}</Text>
              </div>
              <div className="brand-ai-task-foot">
                <StatusTag>{task.statusText}</StatusTag>
                <Button
                  size="small"
                  type={task.priority === "high" ? "primary" : "default"}
                  loading={taskLoading[task.key]}
                  onClick={() => { void taskActions[task.key]?.(); }}
                >
                  {task.actionLabel}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Brand Info */}
      <Card title="品牌信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small" title="基础信息" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="编码">{brand.code || "-"}</Descriptions.Item>
          <Descriptions.Item label="名称">{brand.name}</Descriptions.Item>
          <Descriptions.Item label="中文名">{brand.name_cn || "-"}</Descriptions.Item>
          <Descriptions.Item label="简称">{brand.short_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusTag tone={brand.status === "active" ? "success" : brand.status === "inactive" ? "warning" : "danger"}>
              {brand.status === "active" ? "启用" : brand.status === "inactive" ? "停用" : brand.status === "frozen" ? "冻结" : brand.status}
            </StatusTag>
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            {brand.brand_type === "own_brand" ? "自有品牌" : brand.brand_type === "agency" ? "代理品牌" : brand.brand_type === "oem" ? "OEM" : brand.brand_type || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="分类">{brand.category || "-"}</Descriptions.Item>
          <Descriptions.Item label="产品数"><StatusTag tone="info">{brand.product_count || products.length}</StatusTag></Descriptions.Item>
          <Descriptions.Item label="Logo">{brand.logo ? <a href={brand.logo} target="_blank" rel="noopener noreferrer">查看</a> : "-"}</Descriptions.Item>
          <Descriptions.Item label="官网">
            {brand.website ? <a href={brand.website} target="_blank" rel="noopener noreferrer">{brand.website}</a> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="品牌介绍" span={2}>{brand.description || "-"}</Descriptions.Item>
        </Descriptions>

        <Descriptions bordered column={3} size="small" title="商业信息" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="品牌等级">
            {brand.level ? <StatusTag tone={brand.level === "A" ? "danger" : brand.level === "B" ? "info" : "neutral"}>{brand.level}级</StatusTag> : "-"}
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
            {brand.authorization_status === "authorized" ? <StatusTag tone="success">已授权</StatusTag> : brand.authorization_status === "unauthorized" ? <StatusTag tone="danger">未授权</StatusTag> : brand.authorization_status || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="生命周期">
            {brand.lifecycle_stage ? <StatusTag tone={brand.lifecycle_stage === "active" ? "success" : brand.lifecycle_stage === "nrnd" ? "warning" : "danger"}>{brand.lifecycle_stage.toUpperCase()}</StatusTag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="车规">{brand.is_automotive ? <StatusTag tone="info">是</StatusTag> : "否"}</Descriptions.Item>
          <Descriptions.Item label="MOQ">{brand.moq ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="交期">{brand.lead_time_days ? `${brand.lead_time_days}天` : "-"}</Descriptions.Item>
          <Descriptions.Item label="风险等级">
            {brand.risk_level ? <StatusTag tone={brand.risk_level === "low" ? "success" : brand.risk_level === "medium" ? "warning" : brand.risk_level === "high" ? "danger" : "danger"}>{brand.risk_level === "low" ? "低" : brand.risk_level === "medium" ? "中" : brand.risk_level === "high" ? "高" : "严重"}</StatusTag> : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="RoHS">
            {brand.rohs_status ? <StatusTag tone={brand.rohs_status === "compliant" ? "success" : "danger"}>{brand.rohs_status === "compliant" ? "合规" : brand.rohs_status === "non_compliant" ? "不合规" : brand.rohs_status === "exempt" ? "豁免" : brand.rohs_status}</StatusTag> : "-"}
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
                <div><StatusTag tone="info">{profile.market_position}</StatusTag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">品牌实力</Text>
                <Progress percent={profile.brand_strength_score} size="small" status={profile.brand_strength_score > 70 ? "success" : "normal"} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">采购难度</Text>
                <div><StatusTag tone={profile.procurement_difficulty.includes("容易") ? "success" : profile.procurement_difficulty.includes("中等") ? "warning" : "danger"}>{profile.procurement_difficulty}</StatusTag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">价格定位</Text>
                <div><StatusTag tone={profile.price_positioning === "高端" ? "info" : profile.price_positioning === "中端" ? "info" : "success"}>{profile.price_positioning}</StatusTag></div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="技术优势">
                <List size="small" dataSource={profile.technology_advantages} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{i}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="竞争优势">
                <List size="small" dataSource={profile.competitive_advantages} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="success">{i}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="竞争对手">
                <List size="small" dataSource={profile.key_competitors} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="warning">{i}</StatusTag></List.Item>} />
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
                <div><StatusTag tone={portfolio.portfolio_strength === "完整" ? "success" : portfolio.portfolio_strength === "较全" ? "info" : "warning"}>{portfolio.portfolio_strength}</StatusTag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">库存健康度</Text><div>{portfolio.inventory_health}</div></Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="分类分析">
                {portfolio.category_analysis?.map((c, i) => (
                  <StatusTag key={i} style={{ marginBottom: 4 }}>{c.category}: {c.count}个 ({c.pct}%) — {c.assessment}</StatusTag>
                ))}
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="增长方向">
                <List size="small" dataSource={portfolio.growth_areas} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="success">{i}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="产品线缺口">
                <List size="small" dataSource={portfolio.gap_analysis} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="warning">{i}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="交叉销售机会">
                <List size="small" dataSource={portfolio.cross_sell_opportunities} renderItem={(i: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{i}</StatusTag></List.Item>} />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Similar Brands */}
      {similarBrands.length > 0 && (
        <Card title={<><NodeIndexOutlined /> 相似品牌</>} style={{ marginBottom: 16 }}>
          <ProTable search={false} options={false} size="small" dataSource={similarBrands} rowKey="id" pagination={false}
            columns={[
              { title: "品牌", key: "name", width: 150, render: (_: unknown, r: SimilarBrand) => <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}{r.name_cn ? ` (${r.name_cn})` : ""}</a> },
              { title: "分类", dataIndex: "category", width: 100, render: (v: string) => v ? <StatusTag>{v}</StatusTag> : null },
              { title: "产品数", dataIndex: "product_count", width: 80 },
              { title: "共同分类", dataIndex: "shared_categories", width: 80, render: (v: number) => <StatusTag tone="info">{v}</StatusTag> },
            ] as any}
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
                <div><StatusTag tone={health.health_label === "优秀" ? "success" : health.health_label === "良好" ? "info" : health.health_label === "一般" ? "warning" : "danger"}>{health.health_label}</StatusTag></div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner"><Text type="secondary">趋势</Text>
                <div><StatusTag tone={health.trend_direction === "上升" ? "success" : health.trend_direction === "稳定" ? "info" : "danger"}>{health.trend_direction}</StatusTag></div>
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
                <List size="small" dataSource={health.risk_signals} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="danger">{s}</StatusTag></List.Item>} />
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
                <div style={{ marginTop: 8 }}><StatusTag tone={risk.risk_level === "低" ? "success" : risk.risk_level === "中" ? "warning" : risk.risk_level === "高" ? "danger" : "danger"}>{risk.risk_level}</StatusTag></div>
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
                    <StatusTag tone={i === 0 ? "danger" : i === 1 ? "warning" : "processing"}>{i + 1}. {s}</StatusTag>
                  </List.Item>
                )} />
              </Card>
            </Col>
            <Col span={24}>
              <Card size="small" type="inner" style={{ background: "#fffbe6" }}>
                <Text strong>缓解建议：</Text>
                <List size="small" dataSource={risk.mitigation_suggestions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
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
                <List size="small" dataSource={supplierMatrix.price_optimization} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            {supplierMatrix.supplier_details && supplierMatrix.supplier_details.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="供应商覆盖明细">
                  <ProTable search={false} options={false} size="small" dataSource={supplierMatrix.supplier_details} rowKey="supplier_id" pagination={false}
                    columns={[
                      { title: "供应商", dataIndex: "supplier_name", width: 180 },
                      { title: "产品数", dataIndex: "product_count", width: 80 },
                      { title: "均价", dataIndex: "avg_cost", width: 120, render: (v: number | null) => v ? `¥${v.toFixed(4)}` : "-" },
                      { title: "最低价", dataIndex: "min_cost", width: 120, render: (v: number | null) => v ? `¥${v.toFixed(4)}` : "-" },
                      { title: "平均交期", dataIndex: "avg_lead_time", width: 100, render: (v: number | null) => v ? `${v}天` : "-" },
                    ] as any}
                  />
                </Card>
              </Col>
            )}
            {supplierMatrix.single_source_products.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="单源风险产品" style={{ background: "#fff2e8" }}>
                  {supplierMatrix.single_source_products.map((p, i) => (
                    <StatusTag key={i} tone="danger" style={{ marginBottom: 4 }}>{p.product_name} → {p.supplier} | ¥{p.cost_price} | {p.risk_reason}</StatusTag>
                  ))}
                </Card>
              </Col>
            )}
            {supplierMatrix.backup_recommendations.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="备选供应商建议">
                  {supplierMatrix.backup_recommendations.map((r, i) => (
                    <StatusTag key={i} tone="success" style={{ marginBottom: 4 }}>{r.current} → {r.recommended} | {r.reason}</StatusTag>
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
                <ProTable search={false} options={false} size="small" dataSource={recommendations.recommended_brands} rowKey="brand_name" pagination={false}
                  columns={[
                    { title: "推荐品牌", dataIndex: "brand_name", width: 180,
                      render: (v: string, r: any) => <a onClick={() => {
                        const found = recommendations.co_purchase_raw?.find(b => b.name === v);
                        if (found) navigate(`/brands/${found.id}`);
                      }}>{v}</a>
                    },
                    { title: "推荐度", dataIndex: "overlap_score", width: 100, render: (v: number) => <Progress percent={v} size="small" /> },
                    { title: "原因", dataIndex: "reason" },
                    { title: "优先级", dataIndex: "priority", width: 80, render: (v: string) => <StatusTag tone={v === "高" ? "danger" : v === "中" ? "info" : "neutral"}>{v}</StatusTag> },
                  ] as any}
                />
              </Col>
            )}
            {recommendations.co_purchase_raw && recommendations.co_purchase_raw.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" title="关联购买数据">
                  <ProTable search={false} options={false} size="small" dataSource={recommendations.co_purchase_raw} rowKey="id" pagination={false}
                    columns={[
                      { title: "品牌", key: "name", width: 180, render: (_: unknown, r: any) => <a onClick={() => navigate(`/brands/${r.id}`)}>{r.name}{r.name_cn ? ` (${r.name_cn})` : ""}</a> },
                      { title: "分类", dataIndex: "category", width: 100, render: (v: string) => v ? <StatusTag>{v}</StatusTag> : null },
                      { title: "共同客户", dataIndex: "shared_customers", width: 100 },
                      { title: "共同产品", dataIndex: "shared_products", width: 100 },
                    ] as any}
                  />
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="交叉销售策略">
                <List size="small" dataSource={recommendations.cross_sell_strategies} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" type="inner" title="目标行业">
                <List size="small" dataSource={recommendations.target_industries} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag>{s}</StatusTag></List.Item>} />
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
                  <ProTable search={false} options={false} size="small" dataSource={perf.star_products} rowKey="product_name" pagination={false}
                    columns={[
                      { title: "产品", dataIndex: "product_name", width: 160, render: (v: string) => <Typography.Text strong>{v}</Typography.Text> },
                      { title: "销售额", dataIndex: "revenue", width: 100, render: (v: number) => `¥${v.toLocaleString()}` },
                      { title: "毛利率", dataIndex: "margin_pct", width: 80, render: (v: number) => <StatusTag tone="success">{v}%</StatusTag> },
                      { title: "增幅", dataIndex: "growth", width: 80 },
                      { title: "建议", dataIndex: "recommendation" },
                    ] as any}
                  />
                </Card>
              </Col>
            )}
            {perf.problem_products.length > 0 && (
              <Col span={10}>
                <Card size="small" type="inner" title="问题产品" style={{ background: "#fff2e8" }}>
                  {perf.problem_products.map((p, i) => (
                    <StatusTag key={i} tone="warning" style={{ marginBottom: 4 }}>{p.product_name}: {p.issue} → {p.suggestion}</StatusTag>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="聚焦建议">
                <List size="small" dataSource={perf.focus_recommendations} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            {perf.phase_out_candidates.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="淘汰候选" style={{ background: "#fff1f0" }}>
                  <List size="small" dataSource={perf.phase_out_candidates} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="danger">{s}</StatusTag></List.Item>} />
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
                  <ProTable search={false} options={false} size="small" dataSource={penetration.key_industries} rowKey="industry" pagination={false}
                    columns={[
                      { title: "行业", dataIndex: "industry" },
                      { title: "客户数", dataIndex: "customer_count", width: 70 },
                      { title: "贡献占比", dataIndex: "contribution_pct", width: 80, render: (v: number) => `${v}%` },
                      { title: "评估", dataIndex: "assessment" },
                    ] as any}
                  />
                </Card>
              </Col>
            )}
            {penetration.untapped_industries.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="待开发行业" style={{ background: "#fffbe6" }}>
                  {penetration.untapped_industries.map((u, i) => (
                    <StatusTag key={i} tone="warning" style={{ marginBottom: 4 }}>{u.industry}: {u.potential_customers}潜在客户 → {u.strategy}</StatusTag>
                  ))}
                </Card>
              </Col>
            )}
            <Col span={12}>
              <Card size="small" type="inner" title="留存策略">
                <List size="small" dataSource={penetration.retention_strategy} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="扩展策略">
                <List size="small" dataSource={penetration.expansion_strategy} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="success">{s}</StatusTag></List.Item>} />
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
                  <StatusTag tone={lifecycle.lifecycle_stage === "成长期" ? "success" : lifecycle.lifecycle_stage === "成熟期" ? "info" : lifecycle.lifecycle_stage === "衰退期" ? "danger" : "warning"} style={{ fontSize: 16, padding: '4px 16px' }}>{lifecycle.lifecycle_stage}</StatusTag>
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
                <List size="small" dataSource={lifecycle.key_actions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            {lifecycle.risk_signals.length > 0 && (
              <Col span={24}>
                <Card size="small" type="inner" style={{ background: "#fff2e8" }}>
                  <Typography.Text strong>风险信号：</Typography.Text>
                  {lifecycle.risk_signals.map((s, i) => <StatusTag key={i} tone="danger" style={{ marginLeft: 8 }}>{s}</StatusTag>)}
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
                  <StatusTag tone={priceTrends.price_trend === "上涨" ? "danger" : priceTrends.price_trend === "下降" ? "success" : "info"} style={{ fontSize: 16 }}>{priceTrends.price_trend}</StatusTag>
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
                <List size="small" dataSource={priceTrends.optimization_suggestions} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="info">{s}</StatusTag></List.Item>} />
              </Card>
            </Col>
            {priceTrends.pricing_issues.length > 0 && (
              <Col span={12}>
                <Card size="small" type="inner" title="定价问题" style={{ background: "#fff2e8" }}>
                  <List size="small" dataSource={priceTrends.pricing_issues} renderItem={(s: string) => <List.Item style={{ padding: '2px 0' }}><StatusTag tone="warning">{s}</StatusTag></List.Item>} />
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
      <Card
        title={`关联产品 (${products.length})`}
        extra={<Button icon={<PlusOutlined />} loading={linkLoading} onClick={openLinkProducts}>手动关联产品</Button>}
      >
        {products.length > 0 ? (
          <ProTable search={false} options={false} rowKey="id" columns={productColumns} dataSource={products} size="small" scroll={{ x: 820 }} pagination={erpPagination()} />
        ) : (<Text type="secondary">暂无关联产品</Text>)}
      </Card>

      <Modal
        title="关联产品"
        open={linkModalOpen}
        onCancel={() => setLinkModalOpen(false)}
        onOk={handleLinkProducts}
        confirmLoading={linkLoading}
        okText="确认关联"
        destroyOnHidden
      >
        <Alert
          type="info"
          showIcon
          message="仅显示尚未归属品牌的产品"
          description="关联后，产品主数据的品牌归属将更新为当前品牌。"
          style={{ marginBottom: 16 }}
        />
        <Select
          mode="multiple"
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="按 SKU 或产品名称选择"
          value={selectedProductIds}
          onChange={setSelectedProductIds}
          options={linkCandidates.map((product) => ({
            value: product.id,
            label: `${product.sku || "无 SKU"} · ${product.name}`,
          }))}
          style={{ width: "100%" }}
          notFoundContent="没有可关联的未归属产品"
        />
      </Modal>

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
            options={allBrands.map((b) => ({ label: b.name || b.short_name || b.name_cn, value: b.id }))}
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
            <ProTable search={false} options={false} size="small" dataSource={comparison.dimension_scores || []} pagination={false} rowKey="dimension"
              columns={[
                { title: "维度", dataIndex: "dimension", width: 100 },
                { title: comparison.brand_a?.name as string || "品牌A", dataIndex: "a_score", width: 80, render: (v: number) => <Progress percent={v * 10} size="small" /> },
                { title: comparison.brand_b?.name as string || "品牌B", dataIndex: "b_score", width: 80, render: (v: number) => <Progress percent={v * 10} size="small" /> },
                { title: "说明", dataIndex: "note" },
              ] as any}
            />
            <Card size="small" style={{ marginTop: 12 }} title="替换分析">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="替换可行性">
                  <StatusTag tone={comparison.switching_feasibility === "容易" ? "success" : comparison.switching_feasibility === "中等" ? "warning" : "danger"}>{comparison.switching_feasibility}</StatusTag>
                </Descriptions.Item>
                <Descriptions.Item label="推荐策略">
                  <StatusTag tone="info">{comparison.recommended_strategy}</StatusTag>
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
