import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Select, Slider, Space, Statistic, Tag, Typography, message } from "antd";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import { getOpportunity, createOpportunity, updateOpportunity } from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, ProductSelect, SalesModuleShell, money, stageLabel } from "./salesUi";

const STAGE_OPTIONS = [
  { value: "lead", label: "线索" },
  { value: "qualified", label: "需求确认" },
  { value: "proposal", label: "方案/报价" },
  { value: "negotiation", label: "谈判" },
  { value: "closed_won", label: "赢单" },
  { value: "closed_lost", label: "输单" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "活跃" },
  { value: "won", label: "已赢单" },
  { value: "lost", label: "已输单" },
];

export default function OpportunityForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;
  const watchedAmount = Form.useWatch("amount", form) as number | undefined;
  const watchedWin = Form.useWatch("win_probability", form) as number | undefined;
  const watchedStage = Form.useWatch("stage", form) as string | undefined;

  const weightedAmount = useMemo(
    () => Number(watchedAmount || 0) * Number(watchedWin || 0) / 100,
    [watchedAmount, watchedWin]
  );

  useEffect(() => {
    if (isEdit) {
      getOpportunity(Number(id)).then((r) => {
        const o = r.data.data;
        const nextValues = {
          ...o,
          expected_close_date: o.expected_close_date ? dayjs(o.expected_close_date) : null,
        };
        form.setFieldsValue(nextValues);
        setFormValues(nextValues as unknown as Record<string, unknown>);
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      if (customerId) form.setFieldValue("customer_id", customerId);
    }
  }, [id, searchParams, form, isEdit]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        expected_close_date: values.expected_close_date ? (values.expected_close_date as Dayjs).toISOString() : null,
      };
      if (isEdit) {
        await updateOpportunity(Number(id), payload);
        message.success("商机已更新");
      } else {
        await createOpportunity(payload);
        message.success("商机已创建");
      }
      setLoading(false);
      navigate("/sales/opportunities");
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "保存失败");
      setLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑商机" : "新增商机"}
      subtitle="把客户需求、产品方向、预计金额和推进阶段沉淀为销售管道"
      activeKey="opportunities"
      extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>返回</Button>}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        onValuesChange={(_, v) => setFormValues(v)}
        initialValues={{
          status: "active",
          stage: "lead",
          win_probability: 10,
          expected_close_date: dayjs().add(30, "day"),
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 12, alignItems: "start" }}>
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Card size="small" title="客户与需求">
              <FormAIWarning entityType="opportunity" formData={formValues} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
                <Form.Item name="customer_id" label="客户" rules={[{ required: true, message: "请选择客户" }]}>
                  <CustomerSelect />
                </Form.Item>
                <Form.Item name="product_id" label="意向产品">
                  <ProductSelect />
                </Form.Item>
              </div>
              <Form.Item name="title" label="商机标题" rules={[{ required: true, message: "请输入商机标题" }]}>
                <Input placeholder="例如：华东车规 MCU 替代机会" />
              </Form.Item>
              <Form.Item name="description" label="需求描述">
                <Input.TextArea rows={4} placeholder="客户应用场景、目标型号、数量节奏、关键约束" />
              </Form.Item>
            </Card>

            <Card size="small" title="金额与推进">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                <Form.Item name="amount" label="预计金额">
                  <InputNumber min={0} precision={2} prefix="¥" style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="expected_close_date" label="预计成交日期">
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item name="stage" label="阶段">
                  <Select options={STAGE_OPTIONS} />
                </Form.Item>
                <Form.Item name="status" label="状态">
                  <Select options={STATUS_OPTIONS} />
                </Form.Item>
              </div>
              <Form.Item name="win_probability" label="赢单概率">
                <Slider marks={{ 0: "0%", 50: "50%", 100: "100%" }} min={0} max={100} />
              </Form.Item>
            </Card>

            <Card size="small" title="负责人和下一步">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                <Form.Item name="assigned_to" label="负责人">
                  <Input placeholder="销售负责人" />
                </Form.Item>
                <Form.Item name="source" label="来源">
                  <Input placeholder="客户拜访 / 询价 / 展会 / 转介绍" />
                </Form.Item>
              </div>
              <Form.Item name="notes" label="备注">
                <Input.TextArea rows={3} placeholder="下一步动作、竞争情况、客户决策链" />
              </Form.Item>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card size="small" title="管道摘要">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Statistic title="预计金额" value={Number(watchedAmount || 0)} prefix="¥" precision={2} />
                <Statistic title="加权金额" value={weightedAmount} prefix="¥" precision={2} />
                <Space wrap>
                  <StatusTag tone="info">{stageLabel[watchedStage || "lead"] || watchedStage || "线索"}</StatusTag>
                  <StatusTag tone={Number(watchedWin || 0) >= 50 ? "success" : "warning"}>赢率 {Number(watchedWin || 0)}%</StatusTag>
                  <StatusTag>{money(weightedAmount)}</StatusTag>
                </Space>
                <Alert
                  showIcon
                  type={Number(watchedWin || 0) >= 70 ? "success" : "info"}
                  message={Number(watchedWin || 0) >= 70 ? "高概率商机，建议尽快推进报价或合同确认" : "补充客户需求、预算和决策链可提升商机质量"}
                />
              </Space>
            </Card>
            <Card size="small">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                  {isEdit ? "保存商机" : "创建商机"}
                </Button>
                <Button block onClick={() => navigate("/sales/opportunities")}>取消</Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  商机进入方案/报价阶段后，可从详情页直接创建报价。
                </Typography.Text>
              </Space>
            </Card>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
