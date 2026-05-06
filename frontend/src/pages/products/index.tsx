import { useEffect, useState } from "react";
import { Table, Button, Input, Space, Tag, message, Modal, Form, Select } from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import { getProducts, createProduct, getBrands } from "../../api";
import type { Product, Brand } from "../../types";

export default function ProductList() {
  const [data, setData] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [form] = Form.useForm();

  const fetch = async (p = page, search = q) => {
    setLoading(true);
    try {
      const resp = await getProducts({ page: p, page_size: 20, q: search || undefined });
      setData(resp.data.data.list);
      setTotal(resp.data.data.total);
    } catch {
      message.error("加载产品列表失败");
    } finally {
      setLoading(false);
    }
  };

  const loadBrands = async () => {
    try {
      const resp = await getBrands();
      setBrands(resp.data.data || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetch(); loadBrands(); }, [page]);

  const handleCreate = async (values: Record<string, unknown>) => {
    try {
      await createProduct(values);
      message.success("产品创建成功");
      form.resetFields();
      setModalOpen(false);
      fetch(1);
    } catch {
      message.error("创建失败");
    }
  };

  const columns = [
    { title: "SKU", dataIndex: "sku", width: 120 },
    { title: "产品名称", dataIndex: "name", width: 200 },
    { title: "分类", dataIndex: "category", width: 100 },
    { title: "封装", dataIndex: "package_type", width: 100 },
    { title: "规格", dataIndex: "specs", width: 150 },
    { title: "单位", dataIndex: "unit", width: 60 },
    { title: "品牌ID", dataIndex: "brand_id", width: 80 },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: "space-between", width: "100%" }}>
        <Space>
          <Input
            placeholder="搜索产品名称/SKU"
            prefix={<SearchOutlined />}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onPressEnter={() => { setPage(1); fetch(1, q); }}
            style={{ width: 300 }}
          />
          <Button onClick={() => { setPage(1); fetch(1, q); }}>搜索</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { loadBrands(); setModalOpen(true); }}>
          新建产品
        </Button>
      </Space>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
      <Modal title="新建产品" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="sku" label="SKU"><Input /></Form.Item>
          <Form.Item name="category" label="分类"><Input /></Form.Item>
          <Form.Item name="package_type" label="封装"><Input /></Form.Item>
          <Form.Item name="specs" label="规格"><Input /></Form.Item>
          <Form.Item name="unit" label="单位"><Input /></Form.Item>
          <Form.Item name="brand_id" label="品牌">
            <Select allowClear placeholder="选择品牌">
              {brands.map((b) => <Select.Option key={b.id} value={b.id}>{b.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
