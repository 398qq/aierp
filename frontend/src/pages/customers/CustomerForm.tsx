import { useEffect, useRef, type ReactNode } from "react";
import { Form, Input, Select, InputNumber } from "antd";

const { Item: FormItem } = Form;
const opts = (arr: string[]) => arr.map((v) => ({ label: v, value: v }));

const levelOptions = ["A", "B", "C", "D"];
const industryOptions = [
  "汽车电子",
  "消费电子",
  "工业控制",
  "通信设备",
  "医疗器械",
  "安防监控",
  "其他",
];
const typeOptions = ["终端", "贸易商", "方案商", "OEM"];
const regionOptions = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
const sourceOptions = ["展会", "转介绍", "线上推广", "电话开发", "公司资源"];

const COMPANY_SUFFIXES = [
  "有限责任公司",
  "股份有限公司",
  "集团有限公司",
  "控股有限公司",
  "有限公司",
  "责任公司",
  "股份公司",
  "控股集团",
  "集团",
  "公司",
];

export function generateCustomerShortName(name?: string | null) {
  if (!name) return "";
  let value = name.normalize("NFKC").trim().replace(/\s+/g, "");
  value = value.replace(/\([^()]*\)/g, "");
  for (const suffix of COMPANY_SUFFIXES) {
    if (value.endsWith(suffix) && value.length > suffix.length) {
      value = value.slice(0, -suffix.length);
      break;
    }
  }
  return (value || name.trim()).slice(0, 100);
}

function FormRow({ cols, children }: { cols: number; children: ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: "0 16px" }}>
      {children}
    </div>
  );
}

export default function CustomerFormFields() {
  const form = Form.useFormInstance();
  const customerName = Form.useWatch("name", form) as string | undefined;
  const shortName = Form.useWatch("short_name", form) as string | undefined;
  const previousGeneratedRef = useRef("");

  useEffect(() => {
    const generated = generateCustomerShortName(customerName);
    const current = typeof shortName === "string" ? shortName.trim() : "";
    const previousGenerated = previousGeneratedRef.current;

    if (!generated) {
      if (current && current === previousGenerated) {
        form.setFieldValue("short_name", undefined);
      }
      previousGeneratedRef.current = "";
      return;
    }

    const canAutoFill = !current || current === previousGenerated || current === generated;
    if (canAutoFill && current !== generated) {
      form.setFieldValue("short_name", generated);
    }
    previousGeneratedRef.current = generated;
  }, [customerName, shortName, form]);

  return (
    <>
      <FormRow cols={2}>
        <FormItem
          name="name"
          label="客户名称"
          rules={[{ required: true, message: "请输入客户名称" }]}
        >
          <Input placeholder="公司全称" />
        </FormItem>
        <FormItem name="code" label="客户编码">
          <Input placeholder="自动生成或手动输入" />
        </FormItem>
      </FormRow>
      <FormRow cols={3}>
        <FormItem name="short_name" label="简称">
          <Input placeholder="根据客户名称自动生成，可手动修改" />
        </FormItem>
        <FormItem name="customer_type" label="客户类型">
          <Select placeholder="选择类型" options={opts(typeOptions)} allowClear />
        </FormItem>
        <FormItem name="industry" label="行业">
          <Select placeholder="选择行业" options={opts(industryOptions)} allowClear />
        </FormItem>
      </FormRow>
      <FormRow cols={3}>
        <FormItem name="level" label="等级">
          <Select placeholder="选择等级" options={opts(levelOptions)} allowClear />
        </FormItem>
        <FormItem name="region" label="区域">
          <Select placeholder="选择区域" options={opts(regionOptions)} allowClear />
        </FormItem>
        <FormItem name="source" label="来源">
          <Select placeholder="选择来源" options={opts(sourceOptions)} allowClear />
        </FormItem>
      </FormRow>
      <FormRow cols={3}>
        <FormItem name="contact_person" label="联系人">
          <Input placeholder="主要联系人姓名" />
        </FormItem>
        <FormItem name="phone" label="电话">
          <Input placeholder="联系电话" />
        </FormItem>
        <FormItem name="email" label="邮箱">
          <Input placeholder="联系邮箱" />
        </FormItem>
      </FormRow>
      <FormRow cols={3}>
        <FormItem name="owner" label="负责人">
          <Input placeholder="客户归属负责人" />
        </FormItem>
        <FormItem name="credit_limit" label="信用额度">
          <InputNumber min={0} style={{ width: "100%" }} placeholder="授信额度" />
        </FormItem>
        <FormItem name="credit_level" label="信用等级">
          <Select placeholder="选择信用等级" options={opts(levelOptions)} allowClear />
        </FormItem>
      </FormRow>

      <FormRow cols={3}>
        <FormItem name="tax_id" label="纳税人识别号">
          <Input placeholder="纳税人识别号" maxLength={50} />
        </FormItem>
        <FormItem name="invoice_title" label="发票抬头">
          <Input placeholder="发票抬头" maxLength={255} />
        </FormItem>
        <FormItem name="invoice_address" label="发票地址">
          <Input placeholder="发票地址" />
        </FormItem>
      </FormRow>

      <FormRow cols={2}>
        <FormItem name="bank_name" label="开户行">
          <Input placeholder="开户银行" maxLength={255} />
        </FormItem>
        <FormItem name="bank_account" label="银行账号">
          <Input placeholder="银行账号" maxLength={50} />
        </FormItem>
      </FormRow>

      <FormRow cols={2}>
        <FormItem name="payment_terms" label="付款条件">
          <Select
            placeholder="付款条件"
            allowClear
            options={[
              { label: "款到发货", value: "款到发货" },
              { label: "月结30天", value: "月结30天" },
              { label: "月结60天", value: "月结60天" },
              { label: "Net 30", value: "Net 30" },
            ]}
          />
        </FormItem>
        <FormItem name="payment_method" label="付款方式">
          <Select
            placeholder="付款方式"
            allowClear
            options={[
              { label: "T/T", value: "T/T" },
              { label: "L/C", value: "L/C" },
              { label: "银行承兑", value: "银行承兑" },
            ]}
          />
        </FormItem>
      </FormRow>

      <FormRow cols={3}>
        <FormItem name="currency" label="币种">
          <Select
            placeholder="币种"
            options={[
              { label: "CNY", value: "CNY" },
              { label: "USD", value: "USD" },
              { label: "EUR", value: "EUR" },
            ]}
          />
        </FormItem>
        <FormItem name="price_tier" label="价格等级">
          <Select
            placeholder="价格等级"
            allowClear
            options={[
              { label: "A", value: "A" },
              { label: "B", value: "B" },
              { label: "C", value: "C" },
            ]}
          />
        </FormItem>
        <FormItem name="default_incoterm" label="默认贸易条款">
          <Select
            placeholder="贸易条款"
            allowClear
            options={[
              { label: "FOB", value: "FOB" },
              { label: "CIF", value: "CIF" },
              { label: "EXW", value: "EXW" },
              { label: "DDP", value: "DDP" },
            ]}
          />
        </FormItem>
      </FormRow>

      <FormRow cols={2}>
        <FormItem name="delivery_address" label="收货地址">
          <Input placeholder="收货地址" />
        </FormItem>
        <FormItem name="website" label="网站">
          <Input placeholder="https://" maxLength={500} />
        </FormItem>
      </FormRow>

      <FormItem name="address" label="地址">
        <Input.TextArea rows={2} placeholder="公司地址" />
      </FormItem>
      <FormItem name="notes" label="备注">
        <Input.TextArea rows={3} placeholder="其他备注信息" />
      </FormItem>
    </>
  );
}
