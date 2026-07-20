import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Spin,
  Typography,
  message,
} from "antd";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { UomSelect } from "../../ui";
import {
  getApiErrorMessage,
  getBrands,
  getProduct,
  getWarehouses,
  updateProduct,
} from "../../api";
import type { Brand, Product, Warehouse } from "../../types";
import { getBrandSelectLabel } from "./constants";
import "./products.css";

const statusOptions = [
  { value: "draft", label: "草稿" },
  { value: "active", label: "已启用" },
  { value: "frozen", label: "已冻结" },
  { value: "inactive", label: "已停用" },
];

const productTypeOptions = [
  { value: "finished_good", label: "成品" },
  { value: "raw_material", label: "原材料" },
  { value: "semi_finished", label: "半成品" },
  { value: "service", label: "服务" },
];

type SpecParameter = { name?: string; value?: string };

const toSpecParameters = (specs?: string | null): SpecParameter[] => {
  if (!specs?.trim()) return [];
  try {
    const parsed = JSON.parse(specs) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return Object.entries(parsed as Record<string, unknown>).map(([name, value]) => ({
        name,
        value: String(value ?? ""),
      }));
    }
  } catch {
    // Historical free-text specifications are retained as one editable parameter.
  }
  return [{ name: "规格描述", value: specs }];
};

const serializeSpecParameters = (parameters: SpecParameter[]): string | null => {
  const entries = parameters
    .map((item) => [item.name?.trim(), item.value?.trim()] as const)
    .filter(([name, value]) => Boolean(name && value));
  return entries.length ? JSON.stringify(Object.fromEntries(entries)) : null;
};

export default function ProductEdit() {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const status = Form.useWatch("status", form) as string | undefined;
  const [product, setProduct] = useState<Product | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!productId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      getProduct(productId),
      getBrands({ page: 1, page_size: 200 }).catch(() => null),
      getWarehouses({ page: 1, page_size: 200 }).catch(() => null),
    ])
      .then(([productResponse, brandResponse, warehouseResponse]) => {
        const nextProduct = productResponse.data.data;
        setProduct(nextProduct);
        form.setFieldsValue({
          ...nextProduct,
          spec_parameters: toSpecParameters(nextProduct.specs),
        });
        const brandPayload = brandResponse?.data.data as Brand[] | { list?: Brand[] } | undefined;
        setBrands(Array.isArray(brandPayload) ? brandPayload : brandPayload?.list || []);
        setWarehouses((warehouseResponse?.data.data.list || []) as Warehouse[]);
      })
      .catch((error: unknown) => message.error(getApiErrorMessage(error, "加载产品失败")))
      .finally(() => setLoading(false));
  }, [form, productId]);

  const handleSave = async (values: Record<string, unknown>) => {
    if (!productId) return;
    setSaving(true);
    try {
      const { spec_parameters: specParameters = [], ...productValues } = values;
      await updateProduct(productId, {
        ...productValues,
        specs: serializeSpecParameters(specParameters as SpecParameter[]),
      });
      message.success("产品主数据已更新");
      navigate(`/products/${productId}`);
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "更新产品失败"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "120px auto" }} />;
  if (!product) return <Empty description="产品不存在" />;

  return (
    <div className="product-workbench-page product-edit-page">
      <div className="product-edit-header">
        <div>
          <Typography.Title level={3}>编辑产品主数据</Typography.Title>
          <Typography.Text type="secondary">
            {product.sku || `#${product.id}`} · {product.name}
          </Typography.Text>
        </div>
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/products/${productId}`)}>
            返回详情
          </Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => form.submit()}>
            保存修改
          </Button>
        </Space>
      </div>

      {status && status !== "active" ? (
        <Alert
          showIcon
          type={status === "frozen" ? "warning" : "info"}
          message={status === "frozen" ? "产品已冻结" : status === "inactive" ? "产品已停用" : "产品处于草稿状态"}
          description="该状态会影响报价、销售订单及后续业务单据，请确认状态变更符合业务规则。"
        />
      ) : null}

      <Form form={form} layout="vertical" onFinish={handleSave} requiredMark="optional">
        <Card size="small" title="基础标识">
          <Row gutter={16}>
            <Col xs={24} md={12}><Form.Item name="name" label="产品名称" rules={[{ required: true, message: "请输入产品名称" }]}><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="sku" label="SKU / 料号"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="mpn" label="MPN"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="barcode" label="条码"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="datecode" label="生产日期"><Input placeholder="如 2026-07-16 / 2026W18" /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="status" label="产品状态"><Select options={statusOptions} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="product_type" label="产品类型"><Select options={productTypeOptions} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="owner" label="产品负责人"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="brand_id" label="品牌"><Select allowClear showSearch optionFilterProp="label" options={brands.map((brand) => ({ value: brand.id, label: getBrandSelectLabel(brand) }))} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="category" label="分类"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="unit" label="单位"><UomSelect uomType="count" /></Form.Item></Col>
          </Row>
        </Card>

        <Card size="small" title="技术参数">
          <Row gutter={16}>
            <Col xs={24} md={8}><Form.Item name="package_type" label="封装"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="package_case" label="封装尺寸"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="pin_count" label="针脚数"><InputNumber min={0} precision={0} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="voltage_rating" label="额定电压"><Input /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="tolerance_pct" label="容差"><Input /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="temperature_range" label="温度范围"><Input /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="power_rating" label="额定功率"><Input /></Form.Item></Col>
          </Row>
          <Form.List name="spec_parameters">
            {(fields, { add, remove }) => (
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <div className="product-spec-header">
                  <Typography.Text strong>规格参数</Typography.Text>
                  <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()}>
                    添加规格字段
                  </Button>
                </div>
                {fields.length ? fields.map((field) => (
                  <Row key={field.key} gutter={12} align="middle" className="product-spec-row">
                    <Col xs={24} md={8}>
                      <Form.Item
                        {...field}
                        name={[field.name, "name"]}
                        label="参数名称"
                        rules={[{ required: true, message: "请输入参数名称" }]}
                      >
                        <Input placeholder="如 工作电压" />
                      </Form.Item>
                    </Col>
                    <Col xs={21} md={14}>
                      <Form.Item
                        {...field}
                        name={[field.name, "value"]}
                        label="参数值"
                        rules={[{ required: true, message: "请输入参数值" }]}
                      >
                        <Input placeholder="如 2.7V～3.6V" />
                      </Form.Item>
                    </Col>
                    <Col xs={3} md={2}>
                      <Button
                        danger
                        type="text"
                        aria-label="删除规格字段"
                        icon={<DeleteOutlined />}
                        onClick={() => remove(field.name)}
                      />
                    </Col>
                  </Row>
                )) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无规格参数，请添加字段" />
                )}
              </Space>
            )}
          </Form.List>
        </Card>

        <Card size="small" title="库存控制">
          <Row gutter={16} align="middle">
            <Col xs={24} md={10}><Form.Item name="default_warehouse_id" label="默认仓库"><Select allowClear showSearch optionFilterProp="label" options={warehouses.map((warehouse) => ({ value: warehouse.id, label: `${warehouse.name}${warehouse.location ? ` · ${warehouse.location}` : ""}` }))} /></Form.Item></Col>
            <Col xs={24} md={14}>
              <Space wrap size={20}>
                <Form.Item name="batch_control" valuePropName="checked"><Checkbox>启用批次管理</Checkbox></Form.Item>
                <Form.Item name="serial_control" valuePropName="checked"><Checkbox>启用序列号管理</Checkbox></Form.Item>
                <Form.Item name="shelf_life_control" valuePropName="checked"><Checkbox>启用保质期管理</Checkbox></Form.Item>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card size="small" title="价格与成本">
          <Row gutter={16}>
            <Col xs={12} md={4}><Form.Item name="currency" label="币种"><Select options={["CNY", "USD", "EUR", "HKD"].map((value) => ({ value, label: value }))} /></Form.Item></Col>
            <Col xs={12} md={4}><Form.Item name="tax_rate" label="税率(%)"><InputNumber min={0} max={100} precision={2} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item name="standard_cost" label="标准成本"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item name="list_price" label="目录价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item name="wholesale_price" label="批发价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item name="minimum_sale_price" label="最低销售价"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="latest_purchase_cost" label="最新采购成本"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="weighted_avg_cost" label="加权平均成本"><InputNumber min={0} precision={4} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="price_valid_from" label="价格生效日"><Input placeholder="YYYY-MM-DD" /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="price_valid_to" label="价格失效日"><Input placeholder="YYYY-MM-DD" /></Form.Item></Col>
          </Row>
        </Card>

        <Card size="small" title="生命周期与合规">
          <Row gutter={16}>
            <Col xs={24} md={6}><Form.Item name="lifecycle_status" label="生命周期"><Select allowClear options={["active", "nrnd", "eol", "obsolete"].map((value) => ({ value, label: value.toUpperCase() }))} /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="eol_date" label="EOL 日期"><Input placeholder="YYYY-MM-DD" /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="alternative_mpn" label="替代料 MPN"><Input /></Form.Item></Col>
            <Col xs={24} md={6}><Form.Item name="msl_level" label="MSL 等级"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="origin_country" label="原产国"><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="hs_code" label="HS 编码"><Input /></Form.Item></Col>
            <Col xs={24} md={8}>
              <Space wrap size={18} style={{ paddingTop: 30 }}>
                <Form.Item name="rohs_compliant" valuePropName="checked"><Checkbox>RoHS</Checkbox></Form.Item>
                <Form.Item name="reach_compliant" valuePropName="checked"><Checkbox>REACH</Checkbox></Form.Item>
                <Form.Item name="esd_sensitive" valuePropName="checked"><Checkbox>ESD 敏感</Checkbox></Form.Item>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card size="small" title="文档与备注">
          <Row gutter={16}>
            <Col xs={24} md={12}><Form.Item name="datasheet_url" label="Datasheet URL"><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="image_url" label="产品图片 URL"><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="rohs_cert_url" label="RoHS 证书 URL"><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="reach_cert_url" label="REACH 证书 URL"><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item>
        </Card>

        <div className="product-edit-footer">
          <Button onClick={() => navigate(`/products/${productId}`)}>取消</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} htmlType="submit">保存修改</Button>
        </div>
      </Form>
    </div>
  );
}
