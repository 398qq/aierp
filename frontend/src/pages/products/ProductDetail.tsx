import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Card,
  Descriptions,
  Button,
  Space,
  Spin,
  Alert,
  List,
  Typography,
  message,
  Progress,
  Row,
  Col,
  Table,
  InputNumber,
  Collapse,
  Flex,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Popconfirm,
} from "antd";
import { StatusTag } from "../../ui";
import {
  ArrowLeftOutlined,
  EditOutlined,
  ThunderboltOutlined,
  SwapOutlined,
  LinkOutlined,
  DollarOutlined,
  ProfileOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  AlertOutlined,
  OrderedListOutlined,
  PieChartOutlined,
  SmileOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import {
  getProduct,
  getBrands,
  getInventory,
  similarProducts,
  productSubstitutes,
  embedProduct,
  getSuppliers,
  getSupplierProducts,
  linkSupplierProduct,
  updateSupplierProduct,
  unlinkSupplierProduct,
  getPricingBenchmark,
  getPricingRecommend,
  getProductProfile,
  normalizeProductSpecs,
  getProductAssociations,
  getProcurementOptimize,
  getProductLifecycle,
  getProductSales,
  recommendCustomersForProduct,
  getApiErrorMessage,
} from "../../api";
import AttachmentPanel from "../../components/AttachmentPanel";
import ProductCustomerCodesCard from "./ProductCustomerCodesCard";
import type {
  APIResponse,
  Product,
  Brand,
  InventoryItem,
  Supplier,
  SupplierProductLink,
  PriceBenchmark,
  ProductProfile,
  NormalizedSpec,
  ProductAssociation,
  ProcurementPlan,
  LifecycleAnalysis,
  ProductCustomerMatch,
} from "../../types";
import client from "../../api/client";

type PackLevel = { pack_level: number; uom_code: string; qty_per_parent: number };

const { Text, Title } = Typography;

const getBrandDisplayName = (brand: Brand) => brand.name || brand.short_name || brand.name_cn || "";

const getProductIdentityLabel = (sku: unknown, name: unknown) => {
  const normalizedSku = String(sku || "").trim();
  const normalizedName = String(name || "").trim();
  if (!normalizedSku) return normalizedName || "未命名产品";
  if (!normalizedName || normalizedSku.toLowerCase() === normalizedName.toLowerCase())
    return normalizedSku;
  return `${normalizedSku} · ${normalizedName}`;
};

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [brandName, setBrandName] = useState("");
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [similar, setSimilar] = useState<Record<string, unknown>[]>([]);
  const [substitutes, setSubstitutes] = useState<Record<string, unknown> | null>(null);
  const [supplierProducts, setSupplierProducts] = useState<SupplierProductLink[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierModalOpen, setSupplierModalOpen] = useState(false);
  const [editingSupplierLink, setEditingSupplierLink] = useState<SupplierProductLink | null>(null);
  const [supplierLinkSaving, setSupplierLinkSaving] = useState(false);
  const [supplierForm] = Form.useForm();
  const [batchAddingSuppliers, setBatchAddingSuppliers] = useState(false);
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<number[]>([]);
  const [supplierSearch, setSupplierSearch] = useState("");
  const [batchEditOpen, setBatchEditOpen] = useState(false);
  const [batchEditField, setBatchEditField] = useState<string>();
  const [batchEditValue, setBatchEditValue] = useState<unknown>();
  const [benchmark, setBenchmark] = useState<PriceBenchmark | null>(null);
  const [aiPrice, setAiPrice] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [embedding, setEmbedding] = useState(false);
  const [specsObj, setSpecsObj] = useState<Record<string, unknown>>({});
  const [pricingLoading, setPricingLoading] = useState(false);
  const [profile, setProfile] = useState<ProductProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [associations, setAssociations] = useState<ProductAssociation[]>([]);
  const [assocLoading, setAssocLoading] = useState(false);
  const [procurementQty, setProcurementQty] = useState(1000);
  const [procurement, setProcurement] = useState<ProcurementPlan | null>(null);
  const [procurementLoading, setProcurementLoading] = useState(false);
  const [lifecycle, setLifecycle] = useState<LifecycleAnalysis | null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);
  const [specLoading, setSpecLoading] = useState(false);
  const [salesDocs, setSalesDocs] = useState<{
    quotations: Record<string, unknown>[];
    orders: Record<string, unknown>[];
    deliveries: Record<string, unknown>[];
  } | null>(null);
  const [salesDocsLoading, setSalesDocsLoading] = useState(false);
  const [recommendCustomers, setRecommendCustomers] = useState<ProductCustomerMatch | null>(null);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [packLevels, setPackLevels] = useState<PackLevel[]>([]);
  const [packLevelsLoading, setPackLevelsLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [prodRes, brandsRes, invRes, simRes] = await Promise.allSettled([
          getProduct(Number(id)),
          getBrands(),
          getInventory({ product_id: Number(id), page_size: 50 }),
          similarProducts(Number(id)),
        ]);
        let pid = Number(id);
        let resolvedBrandName = "";
        if (prodRes.status === "fulfilled") {
          const p = prodRes.value.data.data;
          setProduct(p);
          pid = p.id;
          if (p.brand_name) resolvedBrandName = p.brand_name;
          if (p.specs) {
            try {
              setSpecsObj(JSON.parse(p.specs));
            } catch {
              setSpecsObj({ raw: p.specs });
            }
          }
        }
        if (!resolvedBrandName && brandsRes.status === "fulfilled") {
          const payload = brandsRes.value.data.data as Brand[] | { list?: Brand[] };
          const brands = Array.isArray(payload) ? payload : payload.list || [];
          const b = brands.find(
            (x) =>
              x.id ===
              (prodRes.status === "fulfilled" ? prodRes.value.data.data.brand_id : undefined),
          );
          if (b) resolvedBrandName = getBrandDisplayName(b);
        }
        if (resolvedBrandName) setBrandName(resolvedBrandName);
        if (invRes.status === "fulfilled") {
          setInventory(invRes.value.data.data.list || []);
        }
        if (simRes.status === "fulfilled" && simRes.value.data.code === 0) {
          setSimilar((simRes.value.data.data || []) as Record<string, unknown>[]);
        }

        // Load suppliers and pricing in background
        loadSuppliersAndPricing(pid);
        // Load packaging levels
        client
          .get<APIResponse<PackLevel[]>>(`/products/${pid}/pack-levels`)
          .then((r) => {
            const data = r.data.data || [];
            if (data.length) setPackLevels(data);
          })
          .catch(() => {});
      } catch {
        /* */
      } finally {
        setLoading(false);
      }
    })();

    // Also try to get substitutes (may fail if AI unavailable)
    productSubstitutes(Number(id))
      .then((r) => {
        if (r.data.code === 0) setSubstitutes(r.data.data as Record<string, unknown>);
      })
      .catch(() => {});
  }, [id]);

  const loadSuppliersAndPricing = async (pid: number) => {
    try {
      const [supRes, benchRes] = await Promise.allSettled([
        getSuppliers({ page_size: 100 }),
        getPricingBenchmark(pid),
      ]);
      if (supRes.status === "fulfilled") {
        const allSuppliers = (supRes.value.data.data.list || []) as Supplier[];
        // Get linked products for each supplier that may carry this product
        setSuppliers(allSuppliers);
        const linkResults = await Promise.allSettled(
          allSuppliers.map(async (supplier) => {
            const response = await getSupplierProducts(supplier.id);
            return ((response.data.data || []) as SupplierProductLink[])
              .filter((link) => link.product_id === pid)
              .map((link) => ({ ...link, supplier_id: supplier.id, supplier_name: supplier.name }));
          }),
        );
        setSupplierProducts(
          linkResults.flatMap((result) => (result.status === "fulfilled" ? result.value : [])),
        );
      }
      if (benchRes.status === "fulfilled" && benchRes.value.data.code === 0) {
        setBenchmark(benchRes.value.data.data as PriceBenchmark);
      }
    } catch {
      /* */
    }
  };

  const reloadSupplierLinks = async () => {
    const results = await Promise.allSettled(
      suppliers.map(async (supplier) => {
        const response = await getSupplierProducts(supplier.id);
        return ((response.data.data || []) as SupplierProductLink[])
          .filter((link) => link.product_id === Number(id))
          .map((link) => ({ ...link, supplier_id: supplier.id, supplier_name: supplier.name }));
      }),
    );
    setSupplierProducts(
      results.flatMap((result) => (result.status === "fulfilled" ? result.value : [])),
    );
  };

  const openCreateSupplierLink = () => {
    setBatchAddingSuppliers(false);
    setEditingSupplierLink(null);
    supplierForm.resetFields();
    supplierForm.setFieldsValue({ currency: "CNY", is_preferred: false });
    setSupplierModalOpen(true);
  };

  const openBatchCreateSupplierLinks = () => {
    setEditingSupplierLink(null);
    setBatchAddingSuppliers(true);
    supplierForm.resetFields();
    supplierForm.setFieldsValue({ currency: "CNY", is_preferred: false });
    setSupplierModalOpen(true);
  };

  const openEditSupplierLink = (link: SupplierProductLink) => {
    setBatchAddingSuppliers(false);
    setEditingSupplierLink(link);
    supplierForm.setFieldsValue(link);
    setSupplierModalOpen(true);
  };

  const saveSupplierLink = async () => {
    const values = await supplierForm.validateFields();
    setSupplierLinkSaving(true);
    try {
      const supplierIds: number[] = batchAddingSuppliers
        ? values.supplier_ids
        : [editingSupplierLink?.supplier_id || values.supplier_id];
      const { supplier_id: _supplierId, supplier_ids: _supplierIds, ...terms } = values;
      const payload = { ...terms, product_id: Number(id) };
      const results = await Promise.allSettled(
        supplierIds.map((supplierId) =>
          editingSupplierLink
            ? updateSupplierProduct(supplierId, Number(id), payload)
            : linkSupplierProduct(supplierId, payload),
        ),
      );
      const succeeded = results.filter((result) => result.status === "fulfilled").length;
      const failed = results.length - succeeded;
      if (failed) message.warning(`完成 ${succeeded} 条，失败 ${failed} 条`);
      else
        message.success(
          editingSupplierLink ? "供应商关系已更新" : `已添加 ${succeeded} 个供应商关系`,
        );
      setSupplierModalOpen(false);
      await reloadSupplierLinks();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "保存供应商关系失败"));
    } finally {
      setSupplierLinkSaving(false);
    }
  };

  const batchUpdateSupplierLinks = async () => {
    if (
      !batchEditField ||
      batchEditValue === undefined ||
      batchEditValue === null ||
      selectedSupplierIds.length === 0
    ) {
      message.warning("请选择修改字段并填写新值");
      return;
    }
    setSupplierLinkSaving(true);
    const results = await Promise.allSettled(
      selectedSupplierIds.map((supplierId) =>
        updateSupplierProduct(supplierId, Number(id), {
          product_id: Number(id),
          [batchEditField]: batchEditValue,
        }),
      ),
    );
    const succeeded = results.filter((result) => result.status === "fulfilled").length;
    const failed = results.length - succeeded;
    if (failed) message.warning(`批量更新完成 ${succeeded} 条，失败 ${failed} 条`);
    else message.success(`已更新 ${succeeded} 条供应商关系`);
    setSupplierLinkSaving(false);
    setBatchEditOpen(false);
    setSelectedSupplierIds([]);
    await reloadSupplierLinks();
  };

  const batchRemoveSupplierLinks = async () => {
    setSupplierLinkSaving(true);
    const results = await Promise.allSettled(
      selectedSupplierIds.map((supplierId) => unlinkSupplierProduct(supplierId, Number(id))),
    );
    const succeeded = results.filter((result) => result.status === "fulfilled").length;
    const failed = results.length - succeeded;
    if (failed) message.warning(`批量解除完成 ${succeeded} 条，失败 ${failed} 条`);
    else message.success(`已解除 ${succeeded} 条供应商关系`);
    setSupplierLinkSaving(false);
    setSelectedSupplierIds([]);
    await reloadSupplierLinks();
  };

  const removeSupplierLink = async (link: SupplierProductLink) => {
    if (!link.supplier_id) return;
    try {
      await unlinkSupplierProduct(link.supplier_id, Number(id));
      message.success("已解除供应商关联");
      await reloadSupplierLinks();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "解除供应商关联失败"));
    }
  };

  const loadSalesDocs = async () => {
    setSalesDocsLoading(true);
    try {
      const resp = await getProductSales(Number(id));
      if (resp.data.code === 0)
        setSalesDocs(
          resp.data.data as {
            quotations: Record<string, unknown>[];
            orders: Record<string, unknown>[];
            deliveries: Record<string, unknown>[];
          },
        );
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载销售数据失败"));
    } finally {
      setSalesDocsLoading(false);
    }
  };

  const handleGetAiPrice = async () => {
    setPricingLoading(true);
    try {
      const resp = await getPricingRecommend({ product_id: Number(id) });
      if (resp.data.code === 0) setAiPrice(resp.data.data as Record<string, unknown>);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "AI 定价失败"));
    } finally {
      setPricingLoading(false);
    }
  };

  const handleGetProfile = async () => {
    setProfileLoading(true);
    try {
      const resp = await getProductProfile(Number(id));
      if (resp.data.code === 0) setProfile(resp.data.data as ProductProfile);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "生成产品画像失败"));
    } finally {
      setProfileLoading(false);
    }
  };

  const handleNormalizeSpecs = async () => {
    setSpecLoading(true);
    try {
      const resp = await normalizeProductSpecs(Number(id));
      if (resp.data.code === 0) {
        message.success("规格参数已标准化");
        if (product) {
          const params = (resp.data.data?.parameters || []) as NormalizedSpec[];
          const newSpecs: Record<string, string> = {};
          params.forEach((p) => {
            newSpecs[p.key] = `${p.value}${p.unit || ""}`;
          });
          setSpecsObj(newSpecs);
        }
      }
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "规格标准化失败"));
    } finally {
      setSpecLoading(false);
    }
  };

  const handleGetAssociations = async () => {
    setAssocLoading(true);
    try {
      const resp = await getProductAssociations(Number(id));
      if (resp.data.code === 0) setAssociations(resp.data.data?.associations || []);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载关联产品失败"));
    } finally {
      setAssocLoading(false);
    }
  };

  const handleGetProcurement = async () => {
    setProcurementLoading(true);
    try {
      const resp = await getProcurementOptimize(Number(id), procurementQty);
      if (resp.data.code === 0) setProcurement(resp.data.data as ProcurementPlan);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "采购优化失败"));
    } finally {
      setProcurementLoading(false);
    }
  };

  const handleGetLifecycle = async () => {
    setLifecycleLoading(true);
    try {
      const resp = await getProductLifecycle(Number(id));
      if (resp.data.code === 0) setLifecycle(resp.data.data as LifecycleAnalysis);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "生命周期分析失败"));
    } finally {
      setLifecycleLoading(false);
    }
  };

  const handleEmbed = async () => {
    setEmbedding(true);
    try {
      await embedProduct(Number(id));
      message.success("Embedding 生成成功");
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "生成失败"));
    } finally {
      setEmbedding(false);
    }
  };

  const handleRecommendCustomers = async () => {
    setRecommendLoading(true);
    try {
      const resp = await recommendCustomersForProduct(Number(id));
      if (resp.data.code === 0) setRecommendCustomers(resp.data.data as ProductCustomerMatch);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "推荐客户加载失败"));
    } finally {
      setRecommendLoading(false);
    }
  };

  if (loading) return <Spin style={{ margin: 40 }} />;
  if (!product) return <Alert type="error" message="产品未找到" />;

  const totalStock = inventory.reduce((s, i) => s + (i.quantity || 0), 0);
  const lowStock = inventory.some((i) => i.quantity <= i.safety_stock);
  const normalizedSupplierSearch = supplierSearch.trim().toLowerCase();
  const filteredSupplierProducts = supplierProducts.filter(
    (link) =>
      !normalizedSupplierSearch ||
      [link.supplier_name, link.supplier_sku].some((value) =>
        value?.toLowerCase().includes(normalizedSupplierSearch),
      ),
  );

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/products")}>
          返回列表
        </Button>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/products/${id}/edit`)}>
          编辑
        </Button>
        <Button icon={<ThunderboltOutlined />} loading={embedding} onClick={handleEmbed}>
          生成 Embedding
        </Button>
        <Button icon={<ProfileOutlined />} loading={profileLoading} onClick={handleGetProfile}>
          AI 产品画像
        </Button>
        <Button icon={<OrderedListOutlined />} loading={specLoading} onClick={handleNormalizeSpecs}>
          标准化规格
        </Button>
        <Button icon={<NodeIndexOutlined />} loading={assocLoading} onClick={handleGetAssociations}>
          关联产品
        </Button>
        <Button
          icon={<ApartmentOutlined />}
          loading={procurementLoading}
          onClick={handleGetProcurement}
        >
          采购优化
        </Button>
        <Button icon={<AlertOutlined />} loading={lifecycleLoading} onClick={handleGetLifecycle}>
          生命周期
        </Button>
        <Button
          icon={<SmileOutlined />}
          loading={recommendLoading}
          onClick={handleRecommendCustomers}
        >
          推荐客户
        </Button>
        <Link to={`/products/${id}/360`}>
          <Button icon={<PieChartOutlined />}>360</Button>
        </Link>
      </Space>

      {product.status && product.status !== "active" ? (
        <Alert
          showIcon
          type={product.status === "frozen" ? "warning" : "info"}
          message={
            product.status === "frozen"
              ? "产品已冻结，新增报价和销售订单将被拦截"
              : product.status === "inactive"
                ? "产品已停用"
                : "产品尚未启用"
          }
          description="请在主数据维护完成并完成状态审批后再恢复正常业务流转。"
          style={{ marginBottom: 16 }}
        />
      ) : null}

      {/* Product Info */}
      <Card title="产品信息" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={3} size="small">
          <Descriptions.Item label="SKU">{product.sku || "-"}</Descriptions.Item>
          <Descriptions.Item label="名称">{product.name}</Descriptions.Item>
          <Descriptions.Item label="品牌">
            {brandName || (product.brand_id ? `#${product.brand_id}` : "-")}
          </Descriptions.Item>
          <Descriptions.Item label="产品状态">
            {product.status === "active"
              ? "已启用"
              : product.status === "frozen"
                ? "已冻结"
                : product.status === "inactive"
                  ? "已停用"
                  : product.status === "draft"
                    ? "草稿"
                    : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="产品类型">{product.product_type || "成品"}</Descriptions.Item>
          <Descriptions.Item label="负责人">{product.owner || "-"}</Descriptions.Item>
          <Descriptions.Item label="默认仓库">
            {product.default_warehouse_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="生产日期">{product.datecode || "-"}</Descriptions.Item>
          <Descriptions.Item label="库存控制">
            {[
              product.batch_control ? "批次" : null,
              product.serial_control ? "序列号" : null,
              product.shelf_life_control ? "保质期" : null,
            ]
              .filter(Boolean)
              .join("、") || "未启用特殊控制"}
          </Descriptions.Item>
          <Descriptions.Item label="分类">{product.category || "-"}</Descriptions.Item>
          <Descriptions.Item label="封装">{product.package_type || "-"}</Descriptions.Item>
          <Descriptions.Item label="单位">{product.unit || "-"}</Descriptions.Item>
        </Descriptions>
        {Object.keys(specsObj).length > 0 && (
          <Card title="规格参数" size="small" type="inner" style={{ marginTop: 12 }}>
            <Descriptions column={4} size="small">
              {Object.entries(specsObj).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {String(v)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        )}
        {product.notes && (
          <Card title="备注" size="small" type="inner" style={{ marginTop: 12 }}>
            <Text>{product.notes}</Text>
          </Card>
        )}
      </Card>

      {/* Packaging Levels */}
      {packLevels.length > 0 && (
        <Card title="包装层级" style={{ marginBottom: 16, marginTop: 16 }}>
          <Table
            size="small"
            bordered
            pagination={false}
            dataSource={packLevels}
            rowKey="pack_level"
            columns={[
              {
                title: "层级",
                width: 100,
                render: (_: unknown, r: PackLevel) => {
                  const labels = ["基本单位", "内包装", "外包装"];
                  return (
                    <Typography.Text strong>{labels[r.pack_level] || r.pack_level}</Typography.Text>
                  );
                },
              },
              { title: "单位", dataIndex: "uom_code", width: 100 },
              {
                title: "含父单位数量",
                width: 140,
                render: (_: unknown, r: PackLevel) =>
                  r.pack_level === 0 ? (
                    <Typography.Text type="secondary">1</Typography.Text>
                  ) : (
                    String(r.qty_per_parent)
                  ),
              },
              {
                title: "含义",
                render: (_: unknown, r: PackLevel) => {
                  if (r.pack_level === 0)
                    return <Typography.Text type="secondary">基础计数单位</Typography.Text>;
                  const parent = packLevels.find((p) => p.pack_level === r.pack_level - 1);
                  return (
                    <Typography.Text type="secondary">
                      1 {r.uom_code} = {r.qty_per_parent} {parent?.uom_code || "?"}
                    </Typography.Text>
                  );
                },
              },
            ]}
          />
        </Card>
      )}

      {/* AI Product Profile */}
      {profile && (
        <Card
          title={
            <>
              <ProfileOutlined /> AI 产品画像
            </>
          }
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 12 }}
        >
          <Row gutter={[12, 12]}>
            <Col span={8}>
              <Card size="small" type="inner">
                <Text type="secondary">市场定位</Text>
                <div>{profile.market_positioning}</div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner">
                <Text type="secondary">生命周期</Text>
                <div>
                  <StatusTag
                    tone={
                      profile.lifecycle_stage.includes("EOL")
                        ? "red"
                        : profile.lifecycle_stage.includes("NRND")
                          ? "orange"
                          : profile.lifecycle_stage.includes("成熟")
                            ? "blue"
                            : "green"
                    }
                  >
                    {profile.lifecycle_stage}
                  </StatusTag>
                  <Text type="secondary"> 置信度 {profile.lifecycle_score}%</Text>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner">
                <Text type="secondary">利润空间 / 需求</Text>
                <div>
                  <StatusTag
                    tone={
                      profile.margin_potential === "高"
                        ? "green"
                        : profile.margin_potential === "中"
                          ? "blue"
                          : "orange"
                    }
                  >
                    {profile.margin_potential}
                  </StatusTag>
                  <StatusTag>{profile.demand_stability}</StatusTag>
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="典型应用">
                <List
                  size="small"
                  dataSource={profile.typical_applications}
                  renderItem={(i: string) => (
                    <List.Item style={{ padding: "2px 0" }}>
                      <StatusTag>{i}</StatusTag>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" type="inner" title="竞品">
                <List
                  size="small"
                  dataSource={profile.competitor_products}
                  renderItem={(i: string) => (
                    <List.Item style={{ padding: "2px 0" }}>
                      <StatusTag tone="warning">{i}</StatusTag>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="目标客户">
                <List
                  size="small"
                  dataSource={profile.target_customers}
                  renderItem={(i: string) => (
                    <List.Item style={{ padding: "2px 0" }}>{i}</List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="核心卖点">
                <List
                  size="small"
                  dataSource={profile.key_selling_points}
                  renderItem={(i: string) => (
                    <List.Item style={{ padding: "2px 0" }}>
                      <StatusTag tone="success">{i}</StatusTag>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" type="inner" title="风险因素" style={{ borderColor: "#ff4d4f" }}>
                <List
                  size="small"
                  dataSource={profile.risk_factors}
                  renderItem={(i: string) => (
                    <List.Item style={{ padding: "2px 0" }}>
                      <StatusTag tone="danger">{i}</StatusTag>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {/* Inventory Overview */}
      <Card title="库存概览" style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col span={8}>
            <Card size="small">
              <Text type="secondary">总库存</Text>
              <Title level={3} style={{ margin: 0 }}>
                {totalStock}
              </Title>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Text type="secondary">仓库数</Text>
              <Title level={3} style={{ margin: 0 }}>
                {inventory.length}
              </Title>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Text type="secondary">状态</Text>
              <div>
                <StatusTag tone={lowStock ? "danger" : "success"}>
                  {lowStock ? "库存不足" : "正常"}
                </StatusTag>
              </div>
            </Card>
          </Col>
        </Row>
        {inventory.length > 0 && (
          <List
            size="small"
            style={{ marginTop: 12 }}
            dataSource={inventory}
            renderItem={(i) => (
              <List.Item>
                <Space>
                  <StatusTag>{i.warehouse_name || "未知仓库"}</StatusTag>
                  <Text>库存: {i.quantity}</Text>
                  <Text type="secondary">安全库存: {i.safety_stock}</Text>
                  <Progress
                    percent={Math.min(
                      100,
                      Math.round((i.quantity / Math.max(i.safety_stock, 1)) * 100),
                    )}
                    size="small"
                    style={{ width: 120 }}
                    status={i.quantity <= i.safety_stock ? "exception" : "success"}
                  />
                </Space>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* Similar Products */}
      {similar.length > 0 && (
        <Card title="相似产品" style={{ marginBottom: 16 }}>
          <List
            size="small"
            dataSource={similar}
            renderItem={(s: Record<string, unknown>) => (
              <List.Item>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <span>
                    <a onClick={() => navigate(`/products/${s.id}`)}>
                      {getProductIdentityLabel(s.sku, s.name)}
                    </a>
                    <StatusTag style={{ marginLeft: 8 }}>{String(s.category || "")}</StatusTag>
                    {s.brand_name ? (
                      <StatusTag tone="info">{String(s.brand_name)}</StatusTag>
                    ) : null}
                  </span>
                  <StatusTag tone={Number(s.similarity) > 0.8 ? "success" : "warning"}>
                    相似度 {(Number(s.similarity) * 100).toFixed(0)}%
                  </StatusTag>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Product Associations (co-purchase) */}
      {associations.length > 0 && (
        <Card
          title={
            <>
              <NodeIndexOutlined /> 关联产品 (共同购买)
            </>
          }
          style={{ marginBottom: 16 }}
        >
          <Table
            size="small"
            dataSource={associations}
            rowKey="product_id"
            pagination={false}
            columns={[
              {
                title: "产品",
                key: "product",
                width: 200,
                render: (_: unknown, r: ProductAssociation) => (
                  <a onClick={() => navigate(`/products/${r.product_id}`)}>
                    {r.sku ? `[${r.sku}] ` : ""}
                    {r.name}
                  </a>
                ),
              },
              {
                title: "分类",
                dataIndex: "category",
                width: 80,
                render: (v: string) => (v ? <StatusTag>{v}</StatusTag> : null),
              },
              { title: "品牌", dataIndex: "brand_name", width: 80 },
              {
                title: "共同购买次数",
                dataIndex: "co_purchase_count",
                width: 100,
                render: (v: number) => <StatusTag tone="info">{v}</StatusTag>,
              },
              { title: "共同数量", dataIndex: "co_quantity", width: 80 },
            ]}
          />
        </Card>
      )}

      {/* Supplier Linkages */}
      <ProductCustomerCodesCard productId={product.id} />

      <Card
        title={
          <>
            <LinkOutlined /> 供应商关联 ({supplierProducts.length})
          </>
        }
        extra={
          <Space>
            <Button icon={<PlusOutlined />} onClick={openCreateSupplierLink}>
              添加供应商
            </Button>
            <Button icon={<PlusOutlined />} onClick={openBatchCreateSupplierLinks}>
              批量添加
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {supplierProducts.length > 0 ? (
          <>
            <Space wrap style={{ marginBottom: 12 }}>
              <Input.Search
                allowClear
                placeholder="查询供应商名称 / 供应商料号"
                value={supplierSearch}
                onChange={(event) => setSupplierSearch(event.target.value)}
                style={{ width: 300 }}
              />
              <Text type="secondary">已选择 {selectedSupplierIds.length} 条</Text>
              <Button
                disabled={!selectedSupplierIds.length}
                onClick={() => {
                  setBatchEditField(undefined);
                  setBatchEditValue(undefined);
                  setBatchEditOpen(true);
                }}
              >
                批量修改
              </Button>
              <Popconfirm
                title={`解除选中的 ${selectedSupplierIds.length} 条关联？`}
                description="不会删除供应商或产品主数据。"
                okText="批量解除"
                cancelText="取消"
                onConfirm={batchRemoveSupplierLinks}
              >
                <Button danger disabled={!selectedSupplierIds.length} loading={supplierLinkSaving}>
                  批量解除
                </Button>
              </Popconfirm>
            </Space>
            <Table
              size="small"
              dataSource={filteredSupplierProducts}
              rowKey={(link) => link.supplier_id!}
              rowSelection={{
                selectedRowKeys: selectedSupplierIds,
                onChange: (keys) => setSelectedSupplierIds(keys.map(Number)),
              }}
              pagination={false}
              columns={[
                {
                  title: "供应商",
                  key: "supplier",
                  width: 150,
                  render: (_: unknown, r: SupplierProductLink) => (
                    <a onClick={() => navigate(`/suppliers/${r.supplier_id || r.id}`)}>
                      {String(r.supplier_name || r.brand_name || "-")}
                    </a>
                  ),
                },
                {
                  title: "供应商料号",
                  dataIndex: "supplier_sku",
                  width: 120,
                  render: (v: string) => v || "-",
                },
                {
                  title: "成本价",
                  dataIndex: "cost_price",
                  width: 100,
                  render: (v: number | null) => (v ? `¥${Number(v).toFixed(4)}` : "-"),
                },
                { title: "交期(天)", dataIndex: "lead_time_days", width: 80 },
                { title: "MOQ", dataIndex: "moq", width: 60 },
                { title: "SPQ", dataIndex: "spq", width: 60 },
                {
                  title: "首选",
                  dataIndex: "is_preferred",
                  width: 60,
                  render: (v: boolean) => (v ? <StatusTag tone="success">是</StatusTag> : null),
                },
                {
                  title: "操作",
                  key: "actions",
                  width: 210,
                  render: (_: unknown, link: SupplierProductLink) => (
                    <Space size={0}>
                      <Button
                        type="link"
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => navigate(`/suppliers/${link.supplier_id}`)}
                      >
                        查看
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEditSupplierLink(link)}
                      >
                        编辑
                      </Button>
                      <Popconfirm
                        title="解除供应商关联？"
                        description="不会删除供应商或产品主数据。"
                        okText="解除关联"
                        cancelText="取消"
                        onConfirm={() => removeSupplierLink(link)}
                      >
                        <Button type="link" danger size="small" icon={<DeleteOutlined />}>
                          解除关联
                        </Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
            />
          </>
        ) : (
          <Text type="secondary">
            暂无供应商关联，前往 <a onClick={() => navigate("/suppliers")}>供应商管理</a> 进行关联
          </Text>
        )}
      </Card>

      <Modal
        title={
          editingSupplierLink
            ? "编辑供应商关系"
            : batchAddingSuppliers
              ? "批量添加供应商关系"
              : "添加供应商关系"
        }
        open={supplierModalOpen}
        onCancel={() => setSupplierModalOpen(false)}
        onOk={saveSupplierLink}
        confirmLoading={supplierLinkSaving}
        okText="保存"
        width={720}
      >
        <Form form={supplierForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name={batchAddingSuppliers ? "supplier_ids" : "supplier_id"}
                label={batchAddingSuppliers ? "供应商（可多选）" : "供应商"}
                rules={[{ required: true, message: "请选择供应商" }]}
              >
                <Select
                  mode={batchAddingSuppliers ? "multiple" : undefined}
                  disabled={Boolean(editingSupplierLink)}
                  showSearch
                  optionFilterProp="label"
                  options={suppliers
                    .filter(
                      (supplier) =>
                        editingSupplierLink?.supplier_id === supplier.id ||
                        !supplierProducts.some((link) => link.supplier_id === supplier.id),
                    )
                    .map((supplier) => ({ value: supplier.id, label: supplier.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="supplier_sku" label="供应商料号">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cost_price" label="采购价">
                <InputNumber min={0} precision={4} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="currency" label="币种">
                <Select
                  options={["CNY", "USD", "EUR", "HKD"].map((value) => ({ value, label: value }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="lead_time_days" label="交期（天）">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="moq" label="MOQ">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="spq" label="SPQ">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_preferred" label="首选供应商" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title={`批量修改 ${selectedSupplierIds.length} 条供应商关系`}
        open={batchEditOpen}
        onCancel={() => setBatchEditOpen(false)}
        onOk={batchUpdateSupplierLinks}
        confirmLoading={supplierLinkSaving}
        okButtonProps={{
          disabled: !batchEditField || batchEditValue === undefined || batchEditValue === null,
        }}
        okText="批量更新"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Alert type="warning" showIcon message="批量修改会用同一个值覆盖所选关系的对应字段" />
          <Select
            placeholder="选择要修改的字段"
            value={batchEditField}
            onChange={(value) => {
              setBatchEditField(value);
              setBatchEditValue(undefined);
            }}
            style={{ width: "100%" }}
            options={[
              { label: "采购价", value: "cost_price" },
              { label: "币种", value: "currency" },
              { label: "交期（天）", value: "lead_time_days" },
              { label: "MOQ", value: "moq" },
              { label: "SPQ", value: "spq" },
              { label: "首选供应商", value: "is_preferred" },
              { label: "备注", value: "notes" },
            ]}
          />
          {batchEditField === "currency" ? (
            <Select
              placeholder="选择币种"
              value={batchEditValue as string}
              onChange={setBatchEditValue}
              style={{ width: "100%" }}
              options={["CNY", "USD", "EUR", "HKD"].map((value) => ({ value, label: value }))}
            />
          ) : batchEditField === "is_preferred" ? (
            <Select
              placeholder="选择是否首选"
              value={batchEditValue as boolean}
              onChange={setBatchEditValue}
              style={{ width: "100%" }}
              options={[
                { label: "是", value: true },
                { label: "否", value: false },
              ]}
            />
          ) : batchEditField === "notes" ? (
            <Input.TextArea
              rows={3}
              placeholder="输入统一备注"
              value={batchEditValue as string}
              onChange={(event) => setBatchEditValue(event.target.value)}
            />
          ) : batchEditField ? (
            <InputNumber
              min={0}
              precision={batchEditField === "cost_price" ? 4 : 0}
              placeholder="输入统一值"
              value={batchEditValue as number}
              onChange={setBatchEditValue}
              style={{ width: "100%" }}
            />
          ) : null}
        </Space>
      </Modal>

      {/* Pricing Intelligence */}
      <Card
        title={
          <>
            <DollarOutlined /> 价格情报
          </>
        }
        style={{ marginBottom: 16 }}
        extra={
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={pricingLoading}
            onClick={handleGetAiPrice}
          >
            AI 定价建议
          </Button>
        }
      >
        {benchmark && (
          <Row gutter={16} style={{ marginBottom: 12 }}>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">历史销售 (N={benchmark.sales_history.count})</Text>
                <div>
                  <Text strong>均价: ¥{benchmark.sales_history.stats.avg?.toFixed(4) || "-"}</Text>
                </div>
                <Text type="secondary">
                  范围: ¥{benchmark.sales_history.stats.min?.toFixed(4) || "-"} ~ ¥
                  {benchmark.sales_history.stats.max?.toFixed(4) || "-"}
                </Text>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">活跃报价 (N={benchmark.active_quotations.count})</Text>
                <div>
                  <Text strong>
                    均价: ¥{benchmark.active_quotations.stats.avg?.toFixed(4) || "-"}
                  </Text>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">供应商成本 (N={benchmark.supplier_costs.count})</Text>
                <div>
                  <Text strong>最低: ¥{benchmark.supplier_costs.stats.min?.toFixed(4) || "-"}</Text>
                </div>
                <Text type="secondary">
                  平均: ¥{benchmark.supplier_costs.stats.avg?.toFixed(4) || "-"}
                </Text>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">成本供应商</Text>
                {(benchmark.supplier_costs.suppliers || [])
                  .slice(0, 2)
                  .map((s: Record<string, unknown>, i: number) => (
                    <div key={i}>
                      <StatusTag>{String(s.name)}</StatusTag> ¥{Number(s.cost_price).toFixed(4)}
                    </div>
                  ))}
              </Card>
            </Col>
          </Row>
        )}

        {aiPrice && (
          <Card size="small" type="inner" style={{ background: "#f6ffed", borderColor: "#b7eb8f" }}>
            <Descriptions column={4} size="small">
              <Descriptions.Item label="建议报价">
                ¥{(aiPrice.recommended_price as number)?.toFixed(4)}
              </Descriptions.Item>
              <Descriptions.Item label="价格范围">
                ¥{(aiPrice.price_range as number[])?.[0]?.toFixed(4)} ~ ¥
                {(aiPrice.price_range as number[])?.[1]?.toFixed(4)}
              </Descriptions.Item>
              <Descriptions.Item label="预估利润率">
                {(aiPrice.margin_pct as number)?.toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="谈判底价">
                ¥{(aiPrice.negotiation_floor as number)?.toFixed(4)}
              </Descriptions.Item>
              <Descriptions.Item label="置信度">
                <StatusTag
                  tone={
                    aiPrice.confidence === "high"
                      ? "success"
                      : aiPrice.confidence === "medium"
                        ? "warning"
                        : "danger"
                  }
                >
                  {String(aiPrice.confidence)}
                </StatusTag>
              </Descriptions.Item>
              <Descriptions.Item label="向上销售" span={2}>
                {String(aiPrice.upsell_suggestion || "无")}
              </Descriptions.Item>
              <Descriptions.Item label="定价理由" span={4}>
                {String(aiPrice.rationale)}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Card>

      {/* Procurement Optimization */}
      {procurement && (
        <Card
          title={
            <>
              <ApartmentOutlined /> AI 采购优化
            </>
          }
          style={{ marginBottom: 16 }}
          extra={
            <Space>
              <Text>需求量:</Text>
              <InputNumber
                value={procurementQty}
                onChange={(v) => setProcurementQty(v || 1000)}
                min={1}
                style={{ width: 100 }}
              />
              <Button size="small" onClick={handleGetProcurement} loading={procurementLoading}>
                重新计算
              </Button>
            </Space>
          }
        >
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">总成本</Text>
                <Title level={4} style={{ margin: 0 }}>
                  ¥{procurement.total_cost?.toFixed(2)}
                </Title>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">均价</Text>
                <Title level={4} style={{ margin: 0 }}>
                  ¥{procurement.avg_unit_cost?.toFixed(4)}
                </Title>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">交期风险</Text>
                <div>
                  <StatusTag
                    tone={
                      procurement.delivery_risk === "低"
                        ? "green"
                        : procurement.delivery_risk === "中"
                          ? "orange"
                          : "red"
                    }
                  >
                    {procurement.delivery_risk}
                  </StatusTag>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Text type="secondary">推荐方案</Text>
                <div>{procurement.recommended_plan}</div>
              </Card>
            </Col>
          </Row>
          <Table
            size="small"
            style={{ marginTop: 12 }}
            dataSource={procurement.allocations || []}
            pagination={false}
            rowKey="supplier_name"
            columns={[
              { title: "供应商", dataIndex: "supplier_name", width: 120 },
              { title: "分配量", dataIndex: "quantity", width: 80 },
              {
                title: "单价",
                dataIndex: "unit_cost",
                width: 80,
                render: (v: number) => (v ? `¥${v.toFixed(4)}` : "-"),
              },
              {
                title: "小计",
                dataIndex: "subtotal",
                width: 100,
                render: (v: number) => (v ? `¥${v.toFixed(2)}` : "-"),
              },
              { title: "交期(天)", dataIndex: "delivery_days", width: 80 },
              { title: "理由", dataIndex: "reason", ellipsis: true },
            ]}
          />
          {procurement.negotiation_tips?.length > 0 && (
            <Card size="small" type="inner" style={{ marginTop: 12 }} title="议价建议">
              <List
                size="small"
                dataSource={procurement.negotiation_tips}
                renderItem={(t: string) => <List.Item style={{ padding: "2px 0" }}>{t}</List.Item>}
              />
            </Card>
          )}
          {procurement.alternative_plan && (
            <Card size="small" type="inner" style={{ marginTop: 8 }} title="备用方案">
              <Text>{procurement.alternative_plan}</Text>
            </Card>
          )}
        </Card>
      )}

      {/* Lifecycle Warning */}
      {lifecycle && (
        <Card
          title={
            <>
              <AlertOutlined /> 生命周期预警
            </>
          }
          style={{
            marginBottom: 16,
            borderColor:
              lifecycle.urgency === "紧急"
                ? "#ff4d4f"
                : lifecycle.urgency === "建议关注"
                  ? "#faad14"
                  : undefined,
          }}
        >
          <Row gutter={16}>
            <Col span={4}>
              <Card size="small" type="inner">
                <Text type="secondary">阶段</Text>
                <div>
                  <StatusTag
                    tone={
                      lifecycle.lifecycle_stage === "EOL"
                        ? "red"
                        : lifecycle.lifecycle_stage === "NRND"
                          ? "orange"
                          : lifecycle.lifecycle_stage === "活跃"
                            ? "green"
                            : "blue"
                    }
                  >
                    {lifecycle.lifecycle_stage}
                  </StatusTag>
                </div>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" type="inner">
                <Text type="secondary">置信度</Text>
                <div>
                  <Progress
                    percent={lifecycle.stage_confidence}
                    size="small"
                    status={lifecycle.stage_confidence > 70 ? "success" : "normal"}
                  />
                </div>
              </Card>
            </Col>
            <Col span={4}>
              <Card
                size="small"
                type="inner"
                style={{ borderColor: lifecycle.eol_risk_score > 50 ? "#ff4d4f" : undefined }}
              >
                <Text type="secondary">EOL风险</Text>
                <div>
                  <Progress
                    percent={lifecycle.eol_risk_score}
                    size="small"
                    status={
                      lifecycle.eol_risk_score > 70
                        ? "exception"
                        : lifecycle.eol_risk_score > 40
                          ? "normal"
                          : "success"
                    }
                  />
                </div>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" type="inner">
                <Text type="secondary">预计窗口</Text>
                <div>
                  {lifecycle.eol_estimated_months
                    ? `${lifecycle.eol_estimated_months} 个月`
                    : "不确定"}
                </div>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" type="inner">
                <Text type="secondary">备货策略</Text>
                <div>
                  <StatusTag
                    tone={
                      lifecycle.stock_strategy.includes("紧急")
                        ? "red"
                        : lifecycle.stock_strategy.includes("不备")
                          ? "default"
                          : "blue"
                    }
                  >
                    {lifecycle.stock_strategy}
                  </StatusTag>
                </div>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" type="inner">
                <Text type="secondary">建议数量</Text>
                <div>
                  <Text strong>{lifecycle.suggested_quantity}</Text>
                </div>
              </Card>
            </Col>
          </Row>
          {lifecycle.warning_signals?.length > 0 && (
            <Card size="small" type="inner" style={{ marginTop: 12 }} title="风险信号">
              {lifecycle.warning_signals.map((s: string, i: number) => (
                <StatusTag key={i} tone="danger" style={{ marginBottom: 4 }}>
                  {s}
                </StatusTag>
              ))}
            </Card>
          )}
          {lifecycle.migration_path && (
            <Card size="small" type="inner" style={{ marginTop: 8 }} title="迁移路径">
              <Text>{lifecycle.migration_path}</Text>
            </Card>
          )}
        </Card>
      )}

      {/* Substitute Recommendations */}
      {substitutes && (
        <Card
          title={
            <>
              <SwapOutlined /> AI 替代料推荐
            </>
          }
          style={{ marginBottom: 16 }}
        >
          {(substitutes.direct_substitutes as string[])?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>直替代（pin-to-pin 兼容）：</Text>
              <List
                size="small"
                dataSource={substitutes.direct_substitutes as string[]}
                renderItem={(s) => (
                  <List.Item>
                    <StatusTag tone="success">{s}</StatusTag>
                  </List.Item>
                )}
              />
            </div>
          )}
          {(substitutes.functional_substitutes as string[])?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <Text strong>功能替代：</Text>
              <List
                size="small"
                dataSource={substitutes.functional_substitutes as string[]}
                renderItem={(s) => (
                  <List.Item>
                    <StatusTag tone="info">{s}</StatusTag>
                  </List.Item>
                )}
              />
            </div>
          )}
          {(substitutes.verification_notes as string[])?.length > 0 && (
            <div>
              <Text strong>验证注意事项：</Text>
              <List
                size="small"
                dataSource={substitutes.verification_notes as string[]}
                renderItem={(s) => (
                  <List.Item>
                    <Text type="secondary">{s}</Text>
                  </List.Item>
                )}
              />
            </div>
          )}
        </Card>
      )}

      {/* Recommend Customers */}
      {recommendCustomers && (
        <Card
          title={
            <>
              <SmileOutlined /> AI 推荐客户
            </>
          }
          style={{ marginBottom: 16 }}
        >
          {recommendCustomers.recommendations?.length > 0 && (
            <List
              size="small"
              dataSource={recommendCustomers.recommendations}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <StatusTag tone="info">{item.customer_name}</StatusTag>
                    <StatusTag
                      tone={
                        item.priority === "高"
                          ? "danger"
                          : item.priority === "中"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {item.priority}优先级
                    </StatusTag>
                    <Text type="secondary">{item.reason}</Text>
                    {item.estimated_potential && (
                      <Text type="secondary">— {item.estimated_potential}</Text>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          )}
          {recommendCustomers.summary && (
            <Card size="small" type="inner" style={{ marginTop: 12 }}>
              <Text>{recommendCustomers.summary}</Text>
            </Card>
          )}
        </Card>
      )}

      {/* Related Sales Documents */}
      <Card
        title="关联销售单据"
        style={{ marginBottom: 16 }}
        extra={
          <Button loading={salesDocsLoading} onClick={loadSalesDocs}>
            {salesDocs ? "刷新" : "加载"}
          </Button>
        }
      >
        {salesDocs ? (
          <Row gutter={16}>
            <Col span={8}>
              <Title level={5}>报价单 ({salesDocs.quotations.length})</Title>
              {salesDocs.quotations.length === 0 ? (
                <Text type="secondary">无</Text>
              ) : (
                <List
                  size="small"
                  dataSource={salesDocs.quotations}
                  renderItem={(q: Record<string, unknown>) => (
                    <List.Item
                      actions={[<a onClick={() => navigate(`/sales/quotations/${q.id}`)}>查看</a>]}
                    >
                      <List.Item.Meta
                        title={String(q.quotation_no || `#${q.id}`)}
                        description={`${String(q.status)} · x${String(q.quantity)} · ¥${Number(q.unit_price || 0).toFixed(2)}`}
                      />
                    </List.Item>
                  )}
                />
              )}
            </Col>
            <Col span={8}>
              <Title level={5}>销售订单 ({salesDocs.orders.length})</Title>
              {salesDocs.orders.length === 0 ? (
                <Text type="secondary">无</Text>
              ) : (
                <List
                  size="small"
                  dataSource={salesDocs.orders}
                  renderItem={(o: Record<string, unknown>) => (
                    <List.Item
                      actions={[<a onClick={() => navigate(`/sales/orders/${o.id}`)}>查看</a>]}
                    >
                      <List.Item.Meta
                        title={String(o.order_no || `#${o.id}`)}
                        description={`${String(o.status)} · x${String(o.quantity)} · ¥${Number(o.unit_price || 0).toFixed(2)}`}
                      />
                    </List.Item>
                  )}
                />
              )}
            </Col>
            <Col span={8}>
              <Title level={5}>发货单 ({salesDocs.deliveries.length})</Title>
              {salesDocs.deliveries.length === 0 ? (
                <Text type="secondary">无</Text>
              ) : (
                <List
                  size="small"
                  dataSource={salesDocs.deliveries}
                  renderItem={(d: Record<string, unknown>) => (
                    <List.Item
                      actions={[
                        <a onClick={() => navigate(`/sales/delivery-notes/${d.id}`)}>查看</a>,
                      ]}
                    >
                      <List.Item.Meta
                        title={String(d.delivery_no || `#${d.id}`)}
                        description={`${String(d.status)} · x${String(d.quantity)}`}
                      />
                    </List.Item>
                  )}
                />
              )}
            </Col>
          </Row>
        ) : (
          <Text type="secondary">点击"加载"查看此产品关联的报价单、销售订单和发货单</Text>
        )}
      </Card>

      <Card title="附件" style={{ marginTop: 16 }}>
        <AttachmentPanel entityType="product" entityId={product.id} />
      </Card>
    </div>
  );
}
