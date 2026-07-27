import { useEffect, useState } from "react";
import { useParams, useNavigate } from "@/router";
import { Card, Form, Input, Select, InputNumber, DatePicker, Button, message } from "antd";
import { getTarget, createTarget, updateTarget, getApiErrorMessage } from "../../api";
import { SalesModuleShell } from "./salesUi";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";

const toIso = (value: unknown) => value && dayjs.isDayjs(value) ? (value as Dayjs).toISOString() : null;

export default function TargetForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit) {
      getTarget(Number(id)).then((r) => {
        const t = r.data.data;
        form.setFieldsValue({ ...t, period_start: t.period_start ? dayjs(t.period_start) : null, period_end: t.period_end ? dayjs(t.period_end) : null });
      });
    }
  }, [id]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, period_start: toIso(values.period_start), period_end: toIso(values.period_end) };
      if (isEdit) { await updateTarget(Number(id), payload); message.success("目标已更新"); }
      else { await createTarget(payload); message.success("目标已创建"); }
      navigate("/sales/targets");
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "保存失败")); }
    finally { setLoading(false); }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑销售目标" : "新增销售目标"}
      subtitle="设定销售人员的月度/季度/年度业绩目标，跟踪完成进度"
      activeKey="targets"
    >
      <Card size="small">
        <Form form={form} layout="vertical" size="small" onFinish={onFinish} initialValues={{ status: "active", target_type: "monthly" }}>
        <Form.Item name="user_id" label="用户ID" rules={[{ required: true }]}><InputNumber style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="target_amount" label="目标金额" rules={[{ required: true }]}><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="actual_amount" label="实际完成"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
        <Form.Item name="target_type" label="目标类型">
          <Select options={[
            { value: "monthly", label: "月度" }, { value: "quarterly", label: "季度" }, { value: "annual", label: "年度" },
          ]} />
        </Form.Item>
        <Form.Item name="period_start" label="期间开始"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="period_end" label="期间结束"><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select options={[
            { value: "active", label: "进行中" }, { value: "completed", label: "已完成" }, { value: "cancelled", label: "已取消" },
          ]} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/targets")}>取消</Button>
        </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
