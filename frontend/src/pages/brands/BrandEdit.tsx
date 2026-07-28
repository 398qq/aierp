import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Typography,
  message,
} from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import { ProForm, ProFormItem } from "@ant-design/pro-components";
import { getBrand, getApiErrorMessage, updateBrand } from "../../api";
import type { Brand } from "../../types";

const STATUS_OPTIONS = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" },
  { label: "冻结", value: "frozen" },
];
const LEVEL_OPTIONS = ["A", "B", "C"].map((value) => ({ label: `${value}级`, value }));
const TYPE_OPTIONS = [
  { label: "自有品牌", value: "own_brand" },
  { label: "代理品牌", value: "agency" },
  { label: "OEM", value: "oem" },
];
const LIFECYCLE_OPTIONS = ["active", "nrnd", "eol"].map((value) => ({
  label: value.toUpperCase(),
  value,
}));
const RISK_OPTIONS = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
  { label: "严重", value: "critical" },
];
const AUTH_OPTIONS = [
  { label: "已授权", value: "authorized" },
  { label: "未授权", value: "unauthorized" },
  { label: "未知", value: "unknown" },
];
const ROHS_OPTIONS = [
  { label: "合规", value: "compliant" },
  { label: "不合规", value: "non_compliant" },
  { label: "豁免", value: "exempt" },
  { label: "未知", value: "unknown" },
];

export default function BrandEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = ProForm.useForm();
  const [brand, setBrand] = useState<Brand | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const brandId = Number(id);

  useEffect(() => {
    if (!Number.isInteger(brandId) || brandId <= 0) {
      setLoading(false);
      return;
    }
    getBrand(brandId)
      .then((response) => {
        const data = response.data.data as Brand;
        setBrand(data);
        form.setFieldsValue(data);
      })
      .catch((error: unknown) => message.error(getApiErrorMessage(error, "加载品牌失败")))
      .finally(() => setLoading(false));
  }, [brandId, form]);

  const handleSave = async (values: Record<string, unknown>) => {
    if (!brandId) return;
    setSaving(true);
    try {
      await updateBrand(brandId, values);
      message.success("更新成功");
      navigate(`/brands/${brandId}`);
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "更新品牌失败"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spin style={{ margin: 40 }} />;
  if (!brand) return <Alert type="error" message="品牌未找到" showIcon />;

  return (
    <div style={{ padding: 16, maxWidth: 1180, margin: "0 auto" }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/brands/${brandId}`)}>
          返回详情
        </Button>
        <Typography.Title level={3} style={{ margin: 0 }}>
          编辑品牌主数据
        </Typography.Title>
      </Space>
      <ProForm form={form} layout="vertical" onFinish={handleSave}>
        <Card
          title={`${brand.name} · 主数据维护`}
          extra={
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={() => form.submit()}
            >
              保存
            </Button>
          }
        >
          <Tabs
            items={[
              {
                key: "basic",
                label: "基础信息",
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={8}>
                      <ProFormItem name="code" label="品牌编码">
                        <Input placeholder="唯一编码" />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={16}>
                      <ProFormItem
                        name="name"
                        label="品牌名称"
                        rules={[{ required: true, message: "请输入品牌名称" }]}
                      >
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormItem name="name_cn" label="中文名">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormItem name="short_name" label="简称">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="status" label="状态">
                        <Select options={STATUS_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="brand_type" label="类型">
                        <Select allowClear options={TYPE_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="category" label="分类">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col span={24}>
                      <ProFormItem name="logo" label="Logo URL">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col span={24}>
                      <ProFormItem name="description" label="品牌介绍">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                    <Col span={24}>
                      <ProFormItem name="notes" label="备注">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "business",
                label: "商业信息",
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={8}>
                      <ProFormItem name="level" label="品牌等级">
                        <Select allowClear options={LEVEL_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="positioning" label="品牌定位">
                        <Select
                          allowClear
                          options={[
                            { label: "高端", value: "high" },
                            { label: "中端", value: "mid" },
                            { label: "低端", value: "low" },
                          ]}
                        />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="owner" label="负责人">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormItem name="product_lines" label="产品线">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormItem name="target_markets" label="目标市场">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                    <Col span={24}>
                      <ProFormItem name="website" label="官网">
                        <Input />
                      </ProFormItem>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "supply",
                label: "供应链",
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={12}>
                      <ProFormItem name="manufacturer_name" label="原厂名称">
                        <Input />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormItem name="supplier_id" label="关联供应商">
                        <InputNumber min={1} style={{ width: "100%" }} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="authorization_status" label="授权状态">
                        <Select allowClear options={AUTH_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="lifecycle_stage" label="生命周期">
                        <Select allowClear options={LIFECYCLE_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="is_automotive" label="车规" valuePropName="checked">
                        <Switch />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormItem name="moq" label="MOQ">
                        <InputNumber min={0} style={{ width: "100%" }} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormItem name="lead_time_days" label="交期（天）">
                        <InputNumber min={0} style={{ width: "100%" }} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormItem name="risk_level" label="风险等级">
                        <Select allowClear options={RISK_OPTIONS} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormItem name="rohs_status" label="RoHS">
                        <Select allowClear options={ROHS_OPTIONS} />
                      </ProFormItem>
                    </Col>
                  </Row>
                ),
              },
              {
                key: "ai",
                label: "AI 参数",
                children: (
                  <Row gutter={16}>
                    <Col span={24}>
                      <ProFormItem name="ai_keywords" label="AI 关键词">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormItem name="risk_score" label="风险评分">
                        <InputNumber min={0} max={100} style={{ width: "100%" }} />
                      </ProFormItem>
                    </Col>
                    <Col xs={24} md={16}>
                      <ProFormItem name="alternative_brands" label="替代品牌">
                        <Input.TextArea rows={3} />
                      </ProFormItem>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
          <Space style={{ width: "100%", justifyContent: "flex-end" }}>
            <Button onClick={() => navigate(`/brands/${brandId}`)}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} htmlType="submit">
              保存
            </Button>
          </Space>
        </Card>
      </ProForm>
    </div>
  );
}
