import { Form, Input, Select, InputNumber } from "antd";

const { Item: FormItem } = Form;
const opts = (arr: string[]) => arr.map((v) => ({ label: v, value: v }));

const levelOptions = ["A", "B", "C", "D"];
const industryOptions = ["汽车电子", "消费电子", "工业控制", "通信设备", "医疗器械", "安防监控", "其他"];
const typeOptions = ["终端", "贸易商", "方案商", "OEM"];
const regionOptions = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
const sourceOptions = ["展会", "转介绍", "线上推广", "电话开发", "公司资源"];

function FormRow({ cols, children }: { cols: number; children: React.ReactNode }) {
  return <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: "0 16px" }}>{children}</div>;
}

export default function CustomerFormFields() {
  return (
    <>
      <FormRow cols={2}>
        <FormItem name="name" label="客户名称" rules={[{ required: true, message: "请输入客户名称" }]}>
          <Input placeholder="公司全称" />
        </FormItem>
        <FormItem name="code" label="客户编码">
          <Input placeholder="自动生成或手动输入" />
        </FormItem>
      </FormRow>
      <FormRow cols={3}>
        <FormItem name="short_name" label="简称">
          <Input placeholder="便于检索的简称" />
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
      <FormRow cols={2}>
        <FormItem name="credit_limit" label="信用额度">
          <InputNumber min={0} style={{ width: "100%" }} placeholder="授信额度" />
        </FormItem>
        <FormItem name="credit_level" label="信用等级">
          <Select placeholder="选择信用等级" options={opts(levelOptions)} allowClear />
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
