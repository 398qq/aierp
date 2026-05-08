import { useState } from "react";
import { Modal, Form, Input, Select, message } from "antd";
import { createSupplier } from "../../api";
import type { Customer } from "../../types";

interface Props {
  customer: Customer;
  open: boolean;
  onCancel: () => void;
  onSuccess?: (supplierId: number) => void;
}

export default function VendAsSupplierModal({ customer, open, onCancel, onSuccess }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const resp = await createSupplier(values);
      const newId = (resp.data.data as Record<string, unknown>)?.id as number | undefined;
      message.success(
        <span>供应商已创建{newId ? <span> — <a href={`/suppliers/${newId}`}>查看详情</a></span> : null}</span>,
        5,
      );
      form.resetFields();
      onCancel();
      if (newId) onSuccess?.(newId);
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || err?.message || "创建失败");
    } finally {
      setLoading(false);
    }
  };

  const supplierTypeOptions = [
    { label: "授权代理", value: "授权代理" },
    { label: "原厂", value: "原厂" },
    { label: "贸易商", value: "贸易商" },
    { label: "OEM", value: "OEM" },
    { label: "其他", value: "其他" },
  ];

  const ratingOptions = ["A", "B", "C", "D"].map((v) => ({ label: v, value: v }));

  return (
    <Modal
      title={`将客户 "${customer.name}" 转为供应商`}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText="创建供应商"
      width={640}
      afterOpenChange={(visible) => {
        if (visible) {
          form.setFieldsValue({
            name: customer.name,
            contact_person: customer.contact_person,
            phone: customer.phone,
            email: customer.email,
            address: customer.address,
            region: customer.region,
            notes: customer.notes,
          });
        }
      }}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
          <Input placeholder="供应商名称" />
        </Form.Item>
        <Form.Item name="contact_person" label="联系人"><Input /></Form.Item>
        <Form.Item name="phone" label="电话"><Input /></Form.Item>
        <Form.Item name="email" label="邮箱"><Input /></Form.Item>
        <Form.Item name="address" label="地址"><Input /></Form.Item>
        <Form.Item name="region" label="区域"><Input /></Form.Item>
        <Form.Item name="product_lines" label="产品线"><Input.TextArea rows={3} placeholder="描述供应商经营的产品线" /></Form.Item>
        <Form.Item name="supplier_type" label="供应商类型">
          <Select options={supplierTypeOptions} allowClear placeholder="选择类型" />
        </Form.Item>
        <Form.Item name="certifications" label="资质认证"><Input placeholder="如 ISO9001, ISO14001 等" /></Form.Item>
        <Form.Item name="payment_terms" label="付款条款"><Input placeholder="如 月结30天, 款到发货 等" /></Form.Item>
        <Form.Item name="website" label="官网"><Input placeholder="https://" /></Form.Item>
        <Form.Item name="financial_rating" label="财务评级">
          <Select options={ratingOptions} allowClear placeholder="选择评级" />
        </Form.Item>
        <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
      </Form>
    </Modal>
  );
}
