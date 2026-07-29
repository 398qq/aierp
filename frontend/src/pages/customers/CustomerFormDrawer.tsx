/**
 * CustomerFormDrawer — 规格化客户表单（Drawer 模式）
 *
 * 必填：名称、行业、地区、联系方式、信用额度
 * 高级：税号、注册号、付款条款、送货地址（可折叠）
 * 行为：实时验证、自动草稿（3s）、RBAC
 */

import React, { useCallback, useEffect, useState } from "react";
import { App, Button, Collapse, Drawer, Input, Select, Typography } from "antd";
import {
  ProForm,
  ProFormText,
  ProFormSelect,
  ProFormDigit,
  ProFormTextArea,
} from "@ant-design/pro-components";
import { SaveOutlined } from "@ant-design/icons";
import { createCustomer, updateCustomer } from "@/api";

const { Text } = Typography;

// ── 类型 ──

interface CustomerFormDrawerProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialValues?: Record<string, unknown>;
  customerId?: number;
}

const INDUSTRIES = [
  "电子产品", "半导体", "汽车电子", "工业控制",
  "通信设备", "医疗器械", "消费电子", "新能源", "其他",
].map((v) => ({ value: v, label: v }));

const REGIONS = ["华北", "华东", "华南", "华中", "西南", "西北", "东北", "海外"].map(
  (v) => ({ value: v, label: v })
);

const CONTACT_METHOD_OPTIONS = [
  { value: "phone", label: "电话" },
  { value: "email", label: "邮箱" },
];

const PAYMENT_TERMS_OPTIONS = [
  { value: "Net 30", label: "Net 30" },
  { value: "Net 60", label: "Net 60" },
  { value: "T/T in advance", label: "T/T 预付" },
  { value: "月结30天", label: "月结30天" },
];

const PAYMENT_METHOD_OPTIONS = [
  { value: "T/T", label: "T/T" },
  { value: "L/C", label: "L/C" },
];

const CURRENCY_OPTIONS = [
  { value: "CNY", label: "CNY" },
  { value: "USD", label: "USD" },
];

const DRAFT_KEY = "customer_form_draft";

export function buildCustomerPayload(
  values: Record<string, unknown>,
): Record<string, unknown> {
  const {
    contact_method: contactMethod,
    contact_info: contactInfo,
    ...payload
  } = values;
  const normalizedContact = typeof contactInfo === "string" ? contactInfo.trim() : "";
  if (normalizedContact) {
    if (contactMethod === "email") payload.email = normalizedContact;
    else payload.phone = normalizedContact;
  }
  return payload;
}

function loadDraft(): Record<string, unknown> | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveDraft(values: Record<string, unknown>): void {
  try { localStorage.setItem(DRAFT_KEY, JSON.stringify(values)); } catch { /* ignore */ }
}

function clearDraft(): void {
  localStorage.removeItem(DRAFT_KEY);
}

// ── 组件 ──

export const CustomerFormDrawer: React.FC<CustomerFormDrawerProps> = ({
  open, onClose, onSuccess, initialValues, customerId,
}) => {
  const [form] = ProForm.useForm();
  const [saving, setSaving] = useState(false);
  const { message } = App.useApp();
  const isEdit = Boolean(customerId);

  useEffect(() => {
    if (open) {
      form.resetFields();
      if (initialValues && isEdit) {
        const contactMethod = initialValues.email && !initialValues.phone ? "email" : "phone";
        form.setFieldsValue({
          ...initialValues,
          contact_method: contactMethod,
          contact_info: contactMethod === "email" ? initialValues.email : initialValues.phone,
        });
      } else {
        const draft = loadDraft();
        if (draft) {
          form.setFieldsValue(draft);
          message.info("已恢复草稿");
        }
      }
    }
  }, [open, initialValues, isEdit, form, message]);

  // 自动草稿 3s
  useEffect(() => {
    if (isEdit || !open) return;
    const t = setInterval(() => {
      const v = form.getFieldsValue();
      if (v.name) saveDraft(v);
    }, 3000);
    return () => clearInterval(t);
  }, [isEdit, open, form]);

  const handleSubmit = useCallback(async () => {
    try {
      const values = await form.validateFields();
      const payload = buildCustomerPayload(values);
      setSaving(true);
      if (isEdit && customerId) {
        await updateCustomer(customerId, payload);
        message.success("已更新");
      } else {
        await createCustomer(payload);
        message.success("已创建");
        clearDraft();
      }
      form.resetFields();
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "errorFields" in err) return;
      message.error(isEdit ? "更新失败" : "创建失败");
    } finally {
      setSaving(false);
    }
  }, [form, isEdit, customerId, onSuccess, onClose, message]);

  return (
    <Drawer
      title={isEdit ? "编辑客户" : "新增客户"}
      open={open}
      onClose={onClose}
      width={480}
      extra={
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSubmit}>
          {isEdit ? "保存" : "创建"}
        </Button>
      }
    >
      <ProForm
        form={form}
        layout="vertical"
        initialValues={{ contact_method: "phone", currency: "CNY", credit_limit: 100000 }}
        submitter={false}
      >
        <ProFormText
          name="name"
          label="客户名称 *"
          rules={[{ required: true, message: "请输入" }, { max: 100 }]}
          placeholder="公司全称"
        />
        <ProFormSelect
          name="industry"
          label="行业 *"
          rules={[{ required: true, message: "请选择" }]}
          options={INDUSTRIES}
          placeholder="选择行业"
          showSearch
        />
        <ProFormSelect
          name="region"
          label="地区 *"
          rules={[{ required: true, message: "请选择" }]}
          options={REGIONS}
          placeholder="选择地区"
        />
        <ProFormSelect
          name="contact_method"
          label="主要联系方式 *"
          options={CONTACT_METHOD_OPTIONS}
        />
        <ProFormText
          name="contact_info"
          label="联系信息 *"
          rules={[{ required: true, message: "请输入电话或邮箱" }]}
          placeholder="13800001111 或 name@company.com"
        />
        <ProFormDigit
          name="credit_limit"
          label="信用额度 *"
          rules={[{ required: true }, { type: "number", min: 0 }]}
          fieldProps={{ prefix: "¥", placeholder: "100000", min: 0, precision: 2, style: { width: "100%" } }}
        />

        <Collapse ghost>
          <Collapse.Panel header={<Text type="secondary">高级字段</Text>} key="adv">
            <ProFormText
              name="tax_id"
              label="纳税人识别号"
              placeholder="18位税号"
              fieldProps={{ maxLength: 18 }}
            />
            <ProFormText
              name="registration_number"
              label="统一社会信用代码"
              placeholder="18位代码"
              fieldProps={{ maxLength: 18 }}
            />
            <ProFormSelect
              name="payment_terms"
              label="付款条款"
              placeholder="选择"
              options={PAYMENT_TERMS_OPTIONS}
            />
            <ProFormSelect
              name="payment_method"
              label="支付方式"
              placeholder="选择"
              options={PAYMENT_METHOD_OPTIONS}
            />
            <ProFormTextArea name="delivery_address" label="送货地址" fieldProps={{ rows: 2 }} />
            <ProFormSelect name="currency" label="币种" options={CURRENCY_OPTIONS} />
            <ProFormTextArea name="notes" label="备注" fieldProps={{ rows: 2 }} />
          </Collapse.Panel>
        </Collapse>
      </ProForm>
    </Drawer>
  );
};

export default CustomerFormDrawer;