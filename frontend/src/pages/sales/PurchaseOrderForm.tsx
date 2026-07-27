import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "@/router";
import { Alert, Button, Card, Checkbox, DatePicker, Form, Input, InputNumber, Select, Space, Statistic, Typography, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { ArrowLeftOutlined, DeleteOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { createPurchaseOrder, getProducts, getPurchaseOrder, getSalesOrders, getSupplierProducts, getSuppliers, updatePurchaseOrder } from "../../api";
import type { Product, SalesOrder, Supplier, SupplierProductLink } from "../../types";
import { StatusTag, UomSelect } from "../../ui";
import { SalesModuleShell, money } from "./salesUi";

type POItemForm = {
  product_id?: number; sales_order_id?: number; supplier_mpn?: string; product_sku?: string;
  product_name?: string; brand_name?: string; package_type?: string; quantity?: number;
  unit?: string; min_pack_qty?: number; min_pack_unit?: string; date_code_requirement?: string;
  tax_rate?: number; unit_price?: number; amount?: number; customer_name?: string; notes?: string;
};

const num = (value: unknown) => Number(value || 0);
const DEFAULT_ADDRESS = "深圳市福田区深南大道以南6007号安徽创展中心2301";

export default function PurchaseOrderForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [salesOrders, setSalesOrders] = useState<SalesOrder[]>([]);
  const [supplierLinks, setSupplierLinks] = useState<SupplierProductLink[]>([]);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const watchedItems = Form.useWatch("items", form) as POItemForm[] | undefined;
  const taxRate = num(Form.useWatch("tax_rate", form) ?? 13);

  const summary = useMemo(() => {
    const items = watchedItems || [];
    const quantity = items.reduce((sum, item) => sum + num(item?.quantity), 0);
    const total = items.reduce((sum, item) => sum + num(item?.quantity) * num(item?.unit_price), 0);
    const subtotal = total / (1 + taxRate / 100);
    return { lines: items.filter((item) => item?.product_id).length, quantity, total, subtotal, tax: total - subtotal };
  }, [taxRate, watchedItems]);

  useEffect(() => {
    let active = true;

    const loadFormData = async () => {
      const [supplierResult, productResult, salesResult] = await Promise.allSettled([
        getSuppliers({ page: 1, page_size: 200 }),
        getProducts({ page: 1, page_size: 100 }),
        getSalesOrders({ page: 1, page_size: 100 }),
      ]);
      if (!active) return;

      if (supplierResult.status === "fulfilled") {
        setSuppliers((supplierResult.value.data.data?.list || []) as Supplier[]);
      } else {
        message.error("供应商数据加载失败，请稍后重试");
      }
      if (productResult.status === "fulfilled") {
        setProducts((productResult.value.data.data?.list || []) as Product[]);
      } else {
        message.error("产品数据加载失败，请稍后重试");
      }
      if (salesResult.status === "fulfilled") {
        setSalesOrders((salesResult.value.data.data?.list || []) as SalesOrder[]);
      } else {
        message.warning("关联销售订单加载失败，不影响采购订单录入");
      }

      if (!isEdit) return;
      try {
        const response = await getPurchaseOrder(Number(id));
        if (!active) return;
        const po = response.data.data;
        form.setFieldsValue({
          ...po,
          expected_date: po.expected_date ? dayjs(po.expected_date) : null,
          items: po.items,
        });
        try {
          const links = await getSupplierProducts(po.supplier_id);
          if (active) setSupplierLinks(links.data.data || []);
        } catch {
          if (active) message.warning("供应商关联产品加载失败，可手动选择产品");
        }
      } catch {
        if (active) message.error("采购订单详情加载失败，请返回列表后重试");
      }
    };

    void loadFormData().finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [form, id, isEdit]);

  const selectSupplier = async (supplierId: number) => {
    const supplier = suppliers.find((item) => item.id === supplierId);
    form.setFieldsValue({
      supplier_contact: supplier?.contact_person || undefined,
      payment_terms: supplier?.payment_terms || "现款",
      currency: supplier?.currency || "CNY",
    });
    try {
      const response = await getSupplierProducts(supplierId);
      setSupplierLinks(response.data.data || []);
    } catch { setSupplierLinks([]); }
  };

  const selectProduct = (row: number, productId: number) => {
    const product = products.find((item) => item.id === productId);
    const link = supplierLinks.find((item) => item.product_id === productId);
    const items = [...(form.getFieldValue("items") || [])] as POItemForm[];
    items[row] = {
      ...items[row], product_id: productId,
      supplier_mpn: link?.supplier_sku || product?.mpn || product?.sku || "",
      product_sku: product?.sku || "", product_name: product?.name || "",
      brand_name: product?.brand_name || "", package_type: product?.package_type || "",
      unit: product?.unit || "pcs", min_pack_qty: link?.spq || undefined,
      min_pack_unit: link?.spq ? "盘" : undefined, date_code_requirement: items[row]?.date_code_requirement || "不限",
      tax_rate: taxRate, unit_price: link?.cost_price ?? items[row]?.unit_price ?? 0,
    };
    form.setFieldValue("items", items);
  };

  const submit = async (values: Record<string, unknown>) => {
    const items = ((values.items || []) as POItemForm[]).filter((item) => item.product_id);
    if (!items.length) return message.warning("至少添加一条采购明细");
    setSaving(true);
    try {
      const payload = {
        ...values,
        expected_date: values.expected_date ? dayjs(values.expected_date as string).format("YYYY-MM-DD") : undefined,
        contract_terms_version: "v3.4",
        items: items.map((item) => ({ ...item, quantity: num(item.quantity), unit_price: num(item.unit_price), amount: num(item.quantity) * num(item.unit_price), tax_rate: num(item.tax_rate ?? taxRate) })),
      };
      if (isEdit) await updatePurchaseOrder(Number(id), payload);
      else await createPurchaseOrder(payload);
      message.success(isEdit ? "采购订单已更新" : "采购订单已创建");
      navigate("/sales/purchase-orders");
    } catch (error: unknown) {
      const response = error as { response?: { data?: { msg?: string } } };
      message.error(response.response?.data?.msg || "采购订单保存失败");
    } finally { setSaving(false); }
  };

  return (
    <SalesModuleShell title={isEdit ? "编辑采购订单" : "新建采购订单"} subtitle="采购订单模板 v3.4 · 含税采购、批次与供应商确认" activeKey="procurement" extra={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/purchase-orders")}>返回列表</Button>}>
      <Form form={form} layout="vertical" onFinish={submit} requiredMark initialValues={{ currency: "CNY", tax_rate: 13, delivery_address: DEFAULT_ADDRESS, payment_terms: "现款", contract_terms_version: "v3.4", items: [{ quantity: 1, unit: "pcs", tax_rate: 13, date_code_requirement: "不限", unit_price: 0 }] }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: 12, alignItems: "start" }}>
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Card size="small" title="采购订单头信息" loading={loading}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(180px, 1fr))", gap: "0 12px" }}>
                <Form.Item name="supplier_id" label="供应商" rules={[{ required: true }]}><Select showSearch optionFilterProp="label" onChange={selectSupplier} options={suppliers.map((s) => ({ value: s.id, label: s.name }))} /></Form.Item>
                <Form.Item name="supplier_contact" label="供应商联系人" rules={[{ required: true }]}><Input /></Form.Item>
                <Form.Item name="payment_terms" label="付款方式" rules={[{ required: true }]}><Select options={["现款", "月结30天", "T/T"].map((value) => ({ value, label: value }))} /></Form.Item>
                <Form.Item name="expected_date" label="预计交期" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
                <Form.Item name="sales_order_id" label="关联销售订单"><Select allowClear showSearch optionFilterProp="label" options={salesOrders.map((so) => ({ value: so.id, label: `${so.order_no || `SO#${so.id}`} · ${so.customer_name || "客户未命名"}` }))} /></Form.Item>
                <Form.Item name="currency" label="币种" rules={[{ required: true }]}><Select options={["CNY", "USD", "EUR", "HKD"].map((value) => ({ value, label: value }))} /></Form.Item>
                <Form.Item name="tax_rate" label="含税税率(%)"><InputNumber min={0} max={100} style={{ width: "100%" }} /></Form.Item>
                <Form.Item name="incoterms" label="贸易术语"><Select allowClear options={["DDP", "EXW", "FOB", "CIF"].map((value) => ({ value, label: value }))} /></Form.Item>
                <Form.Item name="allow_partial_delivery" valuePropName="checked" label="交付方式"><Checkbox>允许分批交货</Checkbox></Form.Item>
              </div>
              <Form.Item name="delivery_address" label="交货地址" rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="notes" label="订单备注"><Input.TextArea rows={2} placeholder="关联客户、紧急标记、特别包装或验收要求" /></Form.Item>
            </Card>

            <Card size="small" title="采购明细" extra={<Space><StatusTag tone="info">{summary.lines} 行</StatusTag><Typography.Text strong>{money(summary.total)}</Typography.Text></Space>}>
              <Form.List name="items">{(fields, { add, remove }) => <>
                <ProTable search={false} options={false} rowKey="key" size="small" bordered pagination={false} dataSource={fields} scroll={{ x: 1900 }} columns={[
                  { title: "产品", width: 240, fixed: "left", render: (_v, field) => <Form.Item name={[field.name, "product_id"]} rules={[{ required: true }]} style={{ margin: 0 }}><Select showSearch optionFilterProp="label" onChange={(value) => selectProduct(field.name, value)} options={products.map((p) => ({ value: p.id, label: `${p.sku || "-"} · ${p.name}` }))} /></Form.Item> },
                  { title: "供应商型号(MPN)", width: 170, render: (_v, f) => <Form.Item name={[f.name, "supplier_mpn"]} rules={[{ required: true }]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "自有SKU", width: 140, render: (_v, f) => <Form.Item name={[f.name, "product_sku"]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "品名", width: 180, render: (_v, f) => <Form.Item name={[f.name, "product_name"]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "品牌", width: 110, render: (_v, f) => <Form.Item name={[f.name, "brand_name"]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "封装", width: 110, render: (_v, f) => <Form.Item name={[f.name, "package_type"]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "数量", width: 105, render: (_v, f) => <Form.Item name={[f.name, "quantity"]} rules={[{ required: true }]} style={{ margin: 0 }}><InputNumber min={1} style={{ width: "100%" }} /></Form.Item> },
                  { title: "最小包装", width: 150, render: (_v, f) => <Space.Compact><Form.Item name={[f.name, "min_pack_qty"]} style={{ margin: 0 }}><InputNumber min={1} style={{ width: 90 }} /></Form.Item><Form.Item name={[f.name, "min_pack_unit"]} style={{ margin: 0, width: 120 }}><UomSelect uomType="package" placeholder="盘" /></Form.Item></Space.Compact> },
                  { title: "生产批次", width: 130, render: (_v, f) => <Form.Item name={[f.name, "date_code_requirement"]} rules={[{ required: true }, { pattern: /^(?!不限$)/, message: "不能为不限" }]} style={{ margin: 0 }}><Input placeholder="≥24+/2年内" /></Form.Item> },
                  { title: "含税单价", width: 120, render: (_v, f) => <Form.Item name={[f.name, "unit_price"]} rules={[{ required: true }]} style={{ margin: 0 }}><InputNumber min={0} precision={6} style={{ width: "100%" }} /></Form.Item> },
                  { title: "备注", width: 160, render: (_v, f) => <Form.Item name={[f.name, "notes"]} style={{ margin: 0 }}><Input /></Form.Item> },
                  { title: "", width: 45, fixed: "right", render: (_v, f) => <Button danger type="text" icon={<DeleteOutlined />} disabled={fields.length === 1} onClick={() => remove(f.name)} /> },
                ]} />
                <Button type="dashed" icon={<PlusOutlined />} style={{ marginTop: 12 }} onClick={() => add({ quantity: 1, unit: "pcs", tax_rate: taxRate, date_code_requirement: "", unit_price: 0 })}>添加明细</Button>
              </>}</Form.List>
            </Card>
          </Space>

          <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
            <Card size="small" title="采购汇总"><Statistic title="价税合计" value={summary.total} precision={2} prefix="¥" /><div style={{ marginTop: 12 }}><div>未税金额：{money(summary.subtotal)}</div><div>税额：{money(summary.tax)}</div><div>总数量：{summary.quantity.toLocaleString()} pcs</div></div></Card>
            {summary.total > 10000 && <Alert type="warning" showIcon message="大额采购控制" description="订单超过 ¥10,000，保存后须完成二次确认才能审批。" />}
            <Alert type="info" showIcon message="合同条款 v3.4" description="供应商确认 PO 即视为接受随单采购合同条款。" />
            <Button block type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>{isEdit ? "保存修改" : "创建采购订单"}</Button>
          </Space>
        </div>
      </Form>
    </SalesModuleShell>
  );
}
