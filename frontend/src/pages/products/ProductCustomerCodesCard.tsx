import { useEffect, useState } from "react";
import { App, Button, Card, Input, Modal, Popconfirm, Space, Typography } from "antd";
import {
  ProForm,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
  ProFormTextArea,
  ProTable,
} from "@ant-design/pro-components";
import { DeleteOutlined, EditOutlined, PlusOutlined, TeamOutlined } from "@ant-design/icons";
import {
  createProductCustomerCode,
  deleteProductCustomerCode,
  getApiErrorMessage,
  getCustomers,
  getProductCustomerCodes,
  updateProductCustomerCode,
} from "../../api";
import type { Customer, CustomerProductCode } from "../../types";
import { StatusTag } from "../../ui";

interface Props {
  productId: number;
}

export default function ProductCustomerCodesCard({ productId }: Props) {
  const { message } = App.useApp();
  const [links, setLinks] = useState<CustomerProductCode[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [editing, setEditing] = useState<CustomerProductCode | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = ProForm.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [linkResponse, customerResponse] = await Promise.all([
        getProductCustomerCodes(productId),
        getCustomers({ page: 1, page_size: 100 }),
      ]);
      setLinks(linkResponse.data.data || []);
      setCustomers(customerResponse.data.data.list || []);
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "加载客户料号失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [productId]);

  const startCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setOpen(true);
  };

  const startEdit = (link: CustomerProductCode) => {
    setEditing(link);
    form.setFieldsValue(link);
    setOpen(true);
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        const { customer_id: _customerId, ...changes } = values;
        await updateProductCustomerCode(productId, editing.id, changes);
      } else {
        await createProductCustomerCode(productId, values);
      }
      message.success(editing ? "客户料号已更新" : "客户料号已添加");
      setOpen(false);
      await load();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "保存客户料号失败"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (linkId: number) => {
    try {
      await deleteProductCustomerCode(productId, linkId);
      message.success("客户料号映射已解除");
      await load();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "解除客户料号失败"));
    }
  };

  return (
    <Card
      title={<><TeamOutlined /> 客户料号映射 ({links.length})</>}
      extra={<Button icon={<PlusOutlined />} onClick={startCreate}>添加客户料号</Button>}
      style={{ marginBottom: 16 }}
    >
      <ProTable search={false} options={false}
        size="small"
        loading={loading}
        dataSource={links}
        rowKey="id"
        pagination={false}
        locale={{ emptyText: "暂无客户料号；同一内部产品可按客户维护不同料号" }}
        columns={[
          { title: "客户", dataIndex: "customer_name", width: 180 },
          { title: "客户料号", dataIndex: "customer_part_no", width: 180, render: (value: string) => <Typography.Text copyable strong>{value}</Typography.Text> },
          { title: "客户品名", dataIndex: "customer_product_name", width: 200, render: (value: string | null) => value || "-" },
          { title: "状态", dataIndex: "is_active", width: 80, render: (value: boolean) => <StatusTag tone={value ? "success" : "default"}>{value ? "启用" : "停用"}</StatusTag> },
          { title: "备注", dataIndex: "notes", ellipsis: true, render: (value: string | null) => value || "-" },
          { title: "操作", width: 150, render: (_: unknown, link: CustomerProductCode) => <Space size={0}>
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => startEdit(link)}>编辑</Button>
            <Popconfirm title="解除该客户料号映射？" description="历史销售单据中的料号快照不会变化。" onConfirm={() => remove(link.id)}>
              <Button type="link" danger size="small" icon={<DeleteOutlined />}>解除</Button>
            </Popconfirm>
          </Space> },
        ] as any}
      />
      <Modal title={editing ? "编辑客户料号" : "添加客户料号"} open={open} onCancel={() => setOpen(false)} onOk={save} confirmLoading={saving} okText="保存">
        <ProForm form={form} layout="vertical" submitter={false}>
          <ProFormSelect
            name="customer_id"
            label="客户"
            rules={[{ required: true, message: "请选择客户" }]}
            showSearch
            disabled={Boolean(editing)}
            placeholder="选择客户"
            fieldProps={{
              optionFilterProp: "label",
              options: customers
                .filter((customer) => editing?.customer_id === customer.id || !links.some((link) => link.customer_id === customer.id))
                .map((customer) => ({ value: customer.id, label: customer.code ? `${customer.code} · ${customer.name}` : customer.name })),
            }}
          />
          <ProFormText
            name="customer_part_no"
            label="客户料号"
            rules={[{ required: true, whitespace: true, message: "请输入客户料号" }]}
            fieldProps={{ maxLength: 150, placeholder: "客户采购、收货和对账使用的料号" }}
          />
          <ProFormText
            name="customer_product_name"
            label="客户品名"
            fieldProps={{ maxLength: 255, placeholder: "可选，客户侧对该产品的名称" }}
          />
          <ProFormSwitch name="is_active" label="启用" />
          <ProFormTextArea name="notes" label="备注" fieldProps={{ rows: 3 }} />
        </ProForm>
      </Modal>
    </Card>
  );
}
