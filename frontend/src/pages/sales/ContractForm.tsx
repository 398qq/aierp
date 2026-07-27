import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "@/router";
import { Button, Card, DatePicker, Form, Input, InputNumber, message, Select } from "antd";
import { getContract, createContract, updateContract, getSalesOrders } from "../../api";
import dayjs from "dayjs";
import type { SalesOrder } from "../../types";
import { CustomerSelect, SalesModuleShell, shortDate } from "./salesUi";

export default function ContractForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getSalesOrders({ page: 1, page_size: 100 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getContract(Number(id)).then((r) => {
        const c = r.data.data;
        form.setFieldsValue({ ...c, signed_date: c.signed_date ? dayjs(c.signed_date) : null, expire_date: c.expire_date ? dayjs(c.expire_date) : null });
      });
    }
  }, [form, id, isEdit]);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);

  const applyOrder = (orderId?: number) => {
    const order = orderById.get(Number(orderId));
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      amount: form.getFieldValue("amount") ?? order.total_amount,
    });
  };

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = { ...values, signed_date: values.signed_date ? (values.signed_date as string) : null, expire_date: values.expire_date ? (values.expire_date as string) : null };
      if (isEdit) { await updateContract(Number(id), payload); message.success("合同已更新"); }
      else { await createContract(payload); message.success("合同已创建"); }
      navigate("/sales/contracts");
    } catch { message.error("保存失败"); }
    finally { setLoading(false); }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑合同" : "新增合同"}
      subtitle={isEdit ? "修改合同信息" : "创建新合同，关联客户和订单"}
      activeKey="contracts"
    >
      <Card size="small">
        <Form form={form} layout="vertical" size="small" onFinish={onFinish} initialValues={{ status: "draft" }} style={{ maxWidth: 720 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <Form.Item name="customer_id" label="客户" rules={[{ required: true }]}>
              <CustomerSelect />
            </Form.Item>
            <Form.Item name="sales_order_id" label="关联订单">
              <Select
                showSearch
                allowClear
                placeholder="选择订单"
                optionFilterProp="label"
                onChange={applyOrder}
                options={orders.map((order) => ({
                  value: order.id,
                  label: `${order.order_no || `#${order.id}`} / 客户 #${order.customer_id} / ${shortDate(order.delivery_date)}`,
                }))}
              />
            </Form.Item>
            <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="contract_no" label="合同号"><Input placeholder="留空自动生成" /></Form.Item>
            <Form.Item name="amount" label="金额"><InputNumber style={{ width: "100%" }} prefix="¥" /></Form.Item>
            <Form.Item name="status" label="状态">
              <Select options={[
                { value: "draft", label: "草稿" }, { value: "signed", label: "已签署" }, { value: "active", label: "履行中" }, { value: "terminated", label: "已终止" },
              ]} />
            </Form.Item>
            <Form.Item name="signed_date" label="签署日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
            <Form.Item name="expire_date" label="到期日期"><DatePicker style={{ width: "100%" }} /></Form.Item>
          </div>
          <Form.Item name="file_url" label="文件URL"><Input /></Form.Item>
          <Card size="small" title="商务条款" style={{ marginBottom: 16 }}>
            <Form.Item name="delivery_address" label="交货地址"><Input.TextArea rows={2} /></Form.Item>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
              <Form.Item name="invoice_type" label="发票类型"><Select allowClear options={[{ value: "增值税专用发票", label: "增值税专用发票" }, { value: "增值税普通发票", label: "增值税普通发票" }]} /></Form.Item>
              <Form.Item name="payment_terms" label="付款条款"><Input placeholder="货到验收后30日付款" /></Form.Item>
            </div>
            <Form.Item name="delivery_terms" label="交付条款"><Input.TextArea rows={2} placeholder="交货方式、分批交付和运输责任" /></Form.Item>
            <Form.Item name="acceptance_terms" label="验收条款"><Input.TextArea rows={2} placeholder="验收期限、标准和异议期限" /></Form.Item>
            <Form.Item name="warranty_terms" label="质保与售后"><Input.TextArea rows={2} /></Form.Item>
            <Form.Item name="dispute_terms" label="违约与争议解决"><Input.TextArea rows={2} /></Form.Item>
          </Card>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>{isEdit ? "保存" : "创建"}</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => navigate("/sales/contracts")}>取消</Button>
          </Form.Item>
        </Form>
      </Card>
    </SalesModuleShell>
  );
}
