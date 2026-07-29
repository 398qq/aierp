import { useState } from "react";
import { Modal, App, Input, Select } from "antd";
import { ProForm, ProFormText, ProFormTextArea, ProFormSelect } from "@ant-design/pro-components";
import { createSupplier } from "../../api";
import type { Customer } from "../../types";

interface Props {
  customer: Customer;
  open: boolean;
  onCancel: () => void;
  onSuccess?: (supplierId: number) => void;
}

interface VendAsSupplierValues {
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  region?: string;
  product_lines?: string;
  supplier_type?: string;
  certifications?: string;
  payment_terms?: string;
  website?: string;
  financial_rating?: string;
  notes?: string;
}

const SUPPLIER_TYPE_OPTIONS = [
  { label: "授权代理", value: "授权代理" },
  { label: "原厂", value: "原厂" },
  { label: "贸易商", value: "贸易商" },
  { label: "OEM", value: "OEM" },
  { label: "其他", value: "其他" },
];

const RATING_OPTIONS = ["A", "B", "C", "D"].map((v) => ({ label: v, value: v }));

export default function VendAsSupplierModal({
  customer,
  open,
  onCancel,
  onSuccess,
}: Props): React.JSX.Element {
  const [form] = ProForm.useForm();
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const values = (await form.validateFields()) as VendAsSupplierValues;
      const resp = await createSupplier(values);
      const newId = (resp.data.data as Record<string, unknown>)?.id as number | undefined;
      message.success(
        <span>
          供应商已创建
          {newId ? (
            <span>
              {" "}
              — <a href={`/suppliers/${newId}`}>查看详情</a>
            </span>
          ) : null}
        </span>,
        5,
      );
      form.resetFields();
      onCancel();
      if (newId) onSuccess?.(newId);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { msg?: string; detail?: string } } })?.response?.data?.msg ||
        (err as { response?: { data?: { msg?: string; detail?: string } } })?.response?.data
          ?.detail ||
        (err as { message?: string })?.message ||
        "创建失败";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

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
      <ProForm
        form={form}
        layout="vertical"
        submitter={false}
        onFinish={handleSubmit}
      >
        <ProFormText
          name="name"
          label="名称"
          rules={[{ required: true, message: "请输入名称" }]}
          placeholder="供应商名称"
        />
        <ProFormText name="contact_person" label="联系人" />
        <ProFormText name="phone" label="电话" />
        <ProFormText name="email" label="邮箱" />
        <ProFormText name="address" label="地址" />
        <ProFormText name="region" label="区域" />
        <ProFormTextArea
          name="product_lines"
          label="产品线"
          fieldProps={{ rows: 3, placeholder: "描述供应商经营的产品线" }}
        />
        <ProFormSelect
          name="supplier_type"
          label="供应商类型"
          options={SUPPLIER_TYPE_OPTIONS}
          allowClear
          placeholder="选择类型"
        />
        <ProFormText name="certifications" label="资质认证" placeholder="如 ISO9001, ISO14001 等" />
        <ProFormText name="payment_terms" label="付款条款" placeholder="如 月结30天, 款到发货 等" />
        <ProFormText name="website" label="官网" placeholder="https://" />
        <ProFormSelect
          name="financial_rating"
          label="财务评级"
          options={RATING_OPTIONS}
          allowClear
          placeholder="选择评级"
        />
        <ProFormTextArea name="notes" label="备注" fieldProps={{ rows: 2 }} />
      </ProForm>
    </Modal>
  );
}