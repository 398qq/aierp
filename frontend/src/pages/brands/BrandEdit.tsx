import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Alert, Button, Card, Col, Row, Spin, Tabs, Typography, message } from "antd";
import {
  ProForm,
  ProFormSelect,
  ProFormText,
  ProFormDigit,
  ProFormSwitch,
  ProFormTextArea,
} from "@ant-design/pro-components";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
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
const POSITIONING_OPTIONS = [
  { label: "高端", value: "high" },
  { label: "中端", value: "mid" },
  { label: "低端", value: "low" },
];

export default function BrandEdit(): React.JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
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
      })
      .catch((error: unknown) => message.error(getApiErrorMessage(error, "加载品牌失败")))
      .finally(() => setLoading(false));
  }, [brandId]);

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
      <Card title={`${brand.name} · 主数据维护`}>
        <ProForm<Brand>
          layout="vertical"
          initialValues={brand as unknown as Record<string, unknown>}
          onFinish={async (values) => {
            setSaving(true);
            try {
              await updateBrand(brandId, values as unknown as Brand);
              message.success("更新成功");
              navigate(`/brands/${brandId}`);
            } catch (error: unknown) {
              message.error(getApiErrorMessage(error, "更新品牌失败"));
            } finally {
              setSaving(false);
            }
          }}
          submitter={{
            render: () => [
              <Button key="cancel" onClick={() => navigate(`/brands/${brandId}`)}>
                取消
              </Button>,
              <Button
                key="submit"
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                htmlType="submit"
              >
                保存
              </Button>,
            ],
          }}
        >
          <Tabs
            items={[
              {
                key: "basic",
                label: "基础信息",
                children: (
                  <Row gutter={16}>
                    <Col xs={24} md={8}>
                      <ProFormText name="code" label="品牌编码" placeholder="唯一编码" />
                    </Col>
                    <Col xs={24} md={16}>
                      <ProFormText
                        name="name"
                        label="品牌名称"
                        rules={[{ required: true, message: "请输入品牌名称" }]}
                      />
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormText name="name_cn" label="中文名" />
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormText name="short_name" label="简称" />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSelect name="status" label="状态" options={STATUS_OPTIONS} />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSelect
                        name="brand_type"
                        label="类型"
                        allowClear
                        options={TYPE_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormText name="category" label="分类" />
                    </Col>
                    <Col span={24}>
                      <ProFormText name="logo" label="Logo URL" />
                    </Col>
                    <Col span={24}>
                      <ProFormTextArea name="description" label="品牌介绍" rows={3} />
                    </Col>
                    <Col span={24}>
                      <ProFormTextArea name="notes" label="备注" rows={3} />
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
                      <ProFormSelect
                        name="level"
                        label="品牌等级"
                        allowClear
                        options={LEVEL_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSelect
                        name="positioning"
                        label="品牌定位"
                        allowClear
                        options={POSITIONING_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormText name="owner" label="负责人" />
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormTextArea name="product_lines" label="产品线" rows={3} />
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormTextArea name="target_markets" label="目标市场" rows={3} />
                    </Col>
                    <Col span={24}>
                      <ProFormText name="website" label="官网" />
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
                      <ProFormText name="manufacturer_name" label="原厂名称" />
                    </Col>
                    <Col xs={24} md={12}>
                      <ProFormDigit
                        name="supplier_id"
                        label="关联供应商"
                        min={1}
                        fieldProps={{ style: { width: "100%" } }}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSelect
                        name="authorization_status"
                        label="授权状态"
                        allowClear
                        options={AUTH_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSelect
                        name="lifecycle_stage"
                        label="生命周期"
                        allowClear
                        options={LIFECYCLE_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormSwitch name="is_automotive" label="车规" />
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormDigit
                        name="moq"
                        label="MOQ"
                        min={0}
                        fieldProps={{ style: { width: "100%" } }}
                      />
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormDigit
                        name="lead_time_days"
                        label="交期（天）"
                        min={0}
                        fieldProps={{ style: { width: "100%" } }}
                      />
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormSelect
                        name="risk_level"
                        label="风险等级"
                        allowClear
                        options={RISK_OPTIONS}
                      />
                    </Col>
                    <Col xs={24} md={6}>
                      <ProFormSelect
                        name="rohs_status"
                        label="RoHS"
                        allowClear
                        options={ROHS_OPTIONS}
                      />
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
                      <ProFormTextArea name="ai_keywords" label="AI 关键词" rows={3} />
                    </Col>
                    <Col xs={24} md={8}>
                      <ProFormDigit
                        name="risk_score"
                        label="风险评分"
                        min={0}
                        max={100}
                        fieldProps={{ style: { width: "100%" } }}
                      />
                    </Col>
                    <Col xs={24} md={16}>
                      <ProFormTextArea name="alternative_brands" label="替代品牌" rows={3} />
                    </Col>
                  </Row>
                ),
              },
            ]}
          />
        </ProForm>
      </Card>
    </div>
  );
}
