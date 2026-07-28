import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router";
import { Alert, Button, Card, DatePicker, Space, Statistic, Typography, message } from "antd";
import {
  ProForm,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  ProFormDigit,
  ProFormDatePicker,
  ProFormSlider,
} from "@ant-design/pro-components";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  getOpportunity,
  createOpportunity,
  updateOpportunity,
  getApiErrorMessage,
} from "../../api";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import FormAIWarning from "../../components/sales/FormAIWarning";
import { CustomerSelect, ProductSelect, SalesModuleShell, money, stageLabel } from "./salesUi";
import { StatusTag } from "../../ui";

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

export default function OpportunityForm(): React.JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const isEdit = !!id;
  const watchedAmount = Number(formValues.amount || 0);
  const watchedWin = Number(formValues.win_probability || 0);
  const watchedStage = (formValues.stage as string) || "lead";

  const weightedAmount = useMemo(
    () => (watchedAmount * watchedWin) / 100,
    [watchedAmount, watchedWin],
  );

  useEffect(() => {
    if (isEdit) {
      getOpportunity(Number(id)).then((r) => {
        const o = r.data.data;
        const nextValues = {
          ...o,
          expected_close_date: o.expected_close_date ? dayjs(o.expected_close_date) : null,
        };
        setFormValues(nextValues as unknown as Record<string, unknown>);
      });
    } else {
      const customerId = Number(searchParams.get("customer_id"));
      if (customerId) {
        setFormValues((prev) => ({ ...prev, customer_id: customerId }));
      }
    }
  }, [id, searchParams, isEdit]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        expected_close_date: values.expected_close_date
          ? (values.expected_close_date as Dayjs).toISOString()
          : null,
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
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "保存失败"));
      setLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑商机" : "新增商机"}
      subtitle="把客户需求、产品方向、预计金额和推进阶段沉淀为销售管道"
      activeKey="opportunities"
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/opportunities")}>
          返回
        </Button>
      }
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 12,
          alignItems: "start",
        }}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card size="small" title="客户与需求">
            <FormAIWarning entityType="opportunity" formData={formValues} />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: 12,
              }}
            >
              <ProForm.Item
                name="customer_id"
                label="客户"
                rules={[{ required: true, message: "请选择客户" }]}
              >
                <CustomerSelect />
              </ProForm.Item>
              <ProForm.Item name="product_id" label="意向产品">
                <ProductSelect />
              </ProForm.Item>
            </div>
            <ProFormText
              name="title"
              label="商机标题"
              rules={[{ required: true, message: "请输入商机标题" }]}
              placeholder="例如：华东车规 MCU 替代机会"
            />
            <ProFormTextArea
              name="description"
              label="需求描述"
              placeholder="客户应用场景、目标型号、数量节奏、关键约束"
              fieldProps={{ rows: 4 }}
            />
          </Card>

          <Card size="small" title="金额与推进">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 12,
              }}
            >
              <ProFormDigit
                name="amount"
                label="预计金额"
                min={0}
                precision={2}
                fieldProps={{ prefix: "¥", style: { width: "100%" } }}
              />
              <ProFormDatePicker
                name="expected_close_date"
                label="预计成交日期"
                fieldProps={{ style: { width: "100%" } }}
              />
              <ProFormSelect name="stage" label="阶段" options={STAGE_OPTIONS} />
              <ProFormSelect name="status" label="状态" options={STATUS_OPTIONS} />
            </div>
            <ProFormSlider
              name="win_probability"
              label="赢单概率"
              min={0}
              max={100}
              marks={{ 0: "0%", 50: "50%", 100: "100%" }}
            />
          </Card>

          <Card size="small" title="负责人和下一步">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 12,
              }}
            >
              <ProFormText name="assigned_to" label="负责人" placeholder="销售负责人" />
              <ProFormText
                name="source"
                label="来源"
                placeholder="客户拜访 / 询价 / 展会 / 转介绍"
              />
            </div>
            <ProFormTextArea
              name="notes"
              label="备注"
              placeholder="下一步动作、竞争情况、客户决策链"
              fieldProps={{ rows: 3 }}
            />
          </Card>
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title="管道摘要">
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Statistic title="预计金额" value={watchedAmount} prefix="¥" precision={2} />
              <Statistic title="加权金额" value={weightedAmount} prefix="¥" precision={2} />
              <Space wrap>
                <StatusTag tone="info">
                  {stageLabel[watchedStage] || watchedStage || "线索"}
                </StatusTag>
                <StatusTag tone={watchedWin >= 50 ? "success" : "warning"}>
                  赢率 {watchedWin}%
                </StatusTag>
                <StatusTag>{money(weightedAmount)}</StatusTag>
              </Space>
              <Alert
                showIcon
                type={watchedWin >= 70 ? "success" : "info"}
                message={
                  watchedWin >= 70
                    ? "高概率商机，建议尽快推进报价或合同确认"
                    : "补充客户需求、预算和决策链可提升商机质量"
                }
              />
            </Space>
          </Card>
          <Card size="small">
            <ProForm
              layout="vertical"
              initialValues={formValues}
              onValuesChange={(_, v) => setFormValues(v)}
              onFinish={onFinish}
              submitter={{
                render: () => [
                  <Button
                    key="submit"
                    block
                    type="primary"
                    icon={<SaveOutlined />}
                    htmlType="submit"
                    loading={loading}
                  >
                    {isEdit ? "保存商机" : "创建商机"}
                  </Button>,
                  <Button key="cancel" block onClick={() => navigate("/sales/opportunities")}>
                    取消
                  </Button>,
                ],
              }}
            >
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                商机进入方案/报价阶段后，可从详情页直接创建报价。
              </Typography.Text>
            </ProForm>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
