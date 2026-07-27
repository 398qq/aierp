import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  Alert, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Spin, Switch,
  Tabs, Typography, message,
} from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import { getBrand, getApiErrorMessage, updateBrand } from "../../api";
import type { Brand } from "../../types";

const STATUS_OPTIONS = [
  { label: "启用", value: "active" }, { label: "停用", value: "inactive" }, { label: "冻结", value: "frozen" },
];
const LEVEL_OPTIONS = ["A", "B", "C"].map((value) => ({ label: `${value}级`, value }));
const TYPE_OPTIONS = [
  { label: "自有品牌", value: "own_brand" }, { label: "代理品牌", value: "agency" }, { label: "OEM", value: "oem" },
];
const LIFECYCLE_OPTIONS = ["active", "nrnd", "eol"].map((value) => ({ label: value.toUpperCase(), value }));
const RISK_OPTIONS = [
  { label: "低", value: "low" }, { label: "中", value: "medium" }, { label: "高", value: "high" }, { label: "严重", value: "critical" },
];
const AUTH_OPTIONS = [
  { label: "已授权", value: "authorized" }, { label: "未授权", value: "unauthorized" }, { label: "未知", value: "unknown" },
];
const ROHS_OPTIONS = [
  { label: "合规", value: "compliant" }, { label: "不合规", value: "non_compliant" }, { label: "豁免", value: "exempt" }, { label: "未知", value: "unknown" },
];

export default function BrandEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
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

  const save = async () => {
    const values = await form.validateFields();
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
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/brands/${brandId}`)}>返回详情</Button>
        <Typography.Title level={3} style={{ margin: 0 }}>编辑品牌主数据</Typography.Title>
      </Space>
      <Form form={form} layout="vertical">
        <Card
          title={`${brand.name} · 主数据维护`}
          extra={<Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>保存</Button>}
        >
          <Tabs items={[
            { key: "basic", label: "基础信息", children: <Row gutter={16}>
              <Col xs={24} md={8}><Form.Item name="code" label="品牌编码"><Input placeholder="唯一编码" /></Form.Item></Col>
              <Col xs={24} md={16}><Form.Item name="name" label="品牌名称" rules={[{ required: true, message: "请输入品牌名称" }]}><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="name_cn" label="中文名"><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="short_name" label="简称"><Input /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="status" label="状态"><Select options={STATUS_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="brand_type" label="类型"><Select allowClear options={TYPE_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="category" label="分类"><Input /></Form.Item></Col>
              <Col span={24}><Form.Item name="logo" label="Logo URL"><Input /></Form.Item></Col>
              <Col span={24}><Form.Item name="description" label="品牌介绍"><Input.TextArea rows={3} /></Form.Item></Col>
              <Col span={24}><Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item></Col>
            </Row> },
            { key: "business", label: "商业信息", children: <Row gutter={16}>
              <Col xs={24} md={8}><Form.Item name="level" label="品牌等级"><Select allowClear options={LEVEL_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="positioning" label="品牌定位"><Select allowClear options={[{ label: "高端", value: "high" }, { label: "中端", value: "mid" }, { label: "低端", value: "low" }]} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="owner" label="负责人"><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="product_lines" label="产品线"><Input.TextArea rows={3} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="target_markets" label="目标市场"><Input.TextArea rows={3} /></Form.Item></Col>
              <Col span={24}><Form.Item name="website" label="官网"><Input /></Form.Item></Col>
            </Row> },
            { key: "supply", label: "供应链", children: <Row gutter={16}>
              <Col xs={24} md={12}><Form.Item name="manufacturer_name" label="原厂名称"><Input /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="supplier_id" label="关联供应商"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="authorization_status" label="授权状态"><Select allowClear options={AUTH_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="lifecycle_stage" label="生命周期"><Select allowClear options={LIFECYCLE_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="is_automotive" label="车规" valuePropName="checked"><Switch /></Form.Item></Col>
              <Col xs={24} md={6}><Form.Item name="moq" label="MOQ"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item></Col>
              <Col xs={24} md={6}><Form.Item name="lead_time_days" label="交期（天）"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item></Col>
              <Col xs={24} md={6}><Form.Item name="risk_level" label="风险等级"><Select allowClear options={RISK_OPTIONS} /></Form.Item></Col>
              <Col xs={24} md={6}><Form.Item name="rohs_status" label="RoHS"><Select allowClear options={ROHS_OPTIONS} /></Form.Item></Col>
            </Row> },
            { key: "ai", label: "AI 参数", children: <Row gutter={16}>
              <Col span={24}><Form.Item name="ai_keywords" label="AI 关键词"><Input.TextArea rows={3} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="risk_score" label="风险评分"><InputNumber min={0} max={100} style={{ width: "100%" }} /></Form.Item></Col>
              <Col xs={24} md={16}><Form.Item name="alternative_brands" label="替代品牌"><Input.TextArea rows={3} /></Form.Item></Col>
            </Row> },
          ]} />
          <Space style={{ width: "100%", justifyContent: "flex-end" }}>
            <Button onClick={() => navigate(`/brands/${brandId}`)}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>保存</Button>
          </Space>
        </Card>
      </Form>
    </div>
  );
}
