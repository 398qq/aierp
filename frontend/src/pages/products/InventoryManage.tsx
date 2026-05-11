import { useEffect, useState } from "react";
import {
  Table, Button, Space, message, Card, Input, Select, Modal, Form,
  InputNumber, Popconfirm, Typography, Row, Col, Tag,
} from "antd";
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getProductInventories, createProductInventory,
  updateProductInventory, deleteProductInventory,
  getProducts, getWarehouses,
} from "../../api";
import type { InventoryItem, Product, Warehouse } from "../../types";

const { Title, Text } = Typography;

interface InventoryRecord extends InventoryItem {
  key?: React.Key;
}

export default function InventoryManage() {
  const [data, setData] = useState<InventoryRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);

  // Search/filter state
  const [searchQ, setSearchQ] = useState("");
  const [searchWarehouse, setSearchWarehouse] = useState<number | undefined>();
  const [searchBrand, setSearchBrand] = useState<number | undefined>();

  // Modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<InventoryRecord | null>(null);
  const [saving, setSaving] = useState(false);

  // Dropdown options
  const [products, setProducts] = useState<Product[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [brands, setBrands] = useState<{ id: number; name: string }[]>([]);

  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetchData = async (p = page, ps = pageSize) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: ps };
      if (searchQ) params.q = searchQ;
      if (searchWarehouse) params.warehouse_id = searchWarehouse;
      if (searchBrand) params.brand_id = searchBrand;

      const resp = await getProductInventories(params);
      if (resp.data.code === 0) {
        const list = (resp.data.data.list as InventoryItem[]).map((item) => ({
          ...item,
          key: item.id,
        }));
        setData(list);
        setTotal(resp.data.data.total as number);
      }
    } catch {
      message.error("加载库存数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, pageSize]);

  // Load filter options
  useEffect(() => {
    getWarehouses().then((r) => {
      if (r.data.code === 0) setWarehouses(r.data.data as Warehouse[]);
    }).catch(() => {});

    getProducts({ page: 1, page_size: 200 }).then((r) => {
      if (r.data.code === 0) {
        const list = r.data.data.list as Product[];
        setProducts(list);
        // Extract unique brands
        const brandMap = new Map<number, { id: number; name: string }>();
        list.forEach((p) => {
          if (p.brand_id && p.brand_name && !brandMap.has(p.brand_id)) {
            brandMap.set(p.brand_id, { id: p.brand_id, name: p.brand_name });
          }
        });
        setBrands(Array.from(brandMap.values()));
      }
    }).catch(() => {});
  }, []);

  const handleSearch = () => {
    setPage(1);
    fetchData(1, pageSize);
  };

  const handleReset = () => {
    setSearchQ("");
    setSearchWarehouse(undefined);
    setSearchBrand(undefined);
    setPage(1);
    fetchData(1, pageSize);
  };

  const handleCreate = async () => {
    try {
      const vals = await form.validateFields();
      setSaving(true);
      await createProductInventory(vals);
      message.success("库存记录创建成功");
      setCreateOpen(false);
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (!err?.errorFields) {
        message.error(err?.response?.data?.msg || "创建失败");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async () => {
    if (!editingRecord) return;
    try {
      const vals = await editForm.validateFields();
      setSaving(true);
      await updateProductInventory(editingRecord.id, vals);
      message.success("库存记录更新成功");
      setEditOpen(false);
      setEditingRecord(null);
      editForm.resetFields();
      fetchData();
    } catch (err: any) {
      if (!err?.errorFields) {
        message.error(err?.response?.data?.msg || "更新失败");
      }
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (record: InventoryRecord) => {
    setEditingRecord(record);
    editForm.setFieldsValue({
      quantity: record.quantity,
      safety_stock: record.safety_stock,
      unit_price: record.unit_price,
    });
    setEditOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProductInventory(id);
      message.success("库存记录已删除");
      fetchData();
    } catch (err: any) {
      message.error(err?.response?.data?.msg || "删除失败");
    }
  };

  const columns: ColumnsType<InventoryRecord> = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "SKU", dataIndex: "sku", key: "sku", width: 140,
      render: (v) => <Text code>{v || "-"}</Text> },
    { title: "产品名称", dataIndex: "product_name", key: "product_name", width: 180,
      ellipsis: true },
    { title: "品牌", dataIndex: "brand_name", key: "brand_name", width: 120,
      render: (v) => v || "-" },
    { title: "仓库", dataIndex: "warehouse_name", key: "warehouse_name", width: 100 },
    { title: "库存数量", dataIndex: "quantity", key: "quantity", width: 100,
      render: (v, r) => {
        const low = v < r.safety_stock;
        return <Text type={low ? "danger" : undefined}>{v}</Text>;
      },
    },
    { title: "安全库存", dataIndex: "safety_stock", key: "safety_stock", width: 100 },
    { title: "单价 (含税)", dataIndex: "unit_price", key: "unit_price", width: 110,
      render: (v) => v != null ? `¥${Number(v).toFixed(4)}` : "-" },
    {
      title: "操作", key: "action", width: 140, fixed: "right",
      render: (_, r) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Popconfirm
            title="确定删除此库存记录？"
            onConfirm={() => handleDelete(r.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>库存管理</Title>

      {/* Search Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={12} align="middle">
          <Col>
            <Input
              placeholder="搜索 SKU / 产品名称"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 200 }}
              allowClear
            />
          </Col>
          <Col>
            <Select
              placeholder="选择仓库"
              value={searchWarehouse}
              onChange={(v) => setSearchWarehouse(v)}
              allowClear
              style={{ width: 160 }}
              options={warehouses.map((w) => ({ value: w.id, label: w.name }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="选择品牌"
              value={searchBrand}
              onChange={(v) => setSearchBrand(v)}
              allowClear
              style={{ width: 160 }}
              options={brands.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
            </Space>
          </Col>
          <Col style={{ marginLeft: "auto" }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新增库存
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card bodyStyle={{ padding: 0 }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="新增库存记录"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        confirmLoading={saving}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="product_id"
            label="产品"
            rules={[{ required: true, message: "请选择产品" }]}
          >
            <Select
              showSearch
              placeholder="选择或搜索产品"
              optionFilterProp="label"
              options={products.map((p) => ({
                value: p.id,
                label: `${p.sku || ""} - ${p.name} ${p.brand_name ? `(${p.brand_name})` : ""}`.trim(),
              }))}
            />
          </Form.Item>
          <Form.Item
            name="warehouse_id"
            label="仓库"
            rules={[{ required: true, message: "请选择仓库" }]}
          >
            <Select
              placeholder="选择仓库"
              options={warehouses.map((w) => ({ value: w.id, label: w.name }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                name="quantity"
                label="库存数量"
                rules={[{ required: true, message: "请输入数量" }]}
                initialValue={0}
              >
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="safety_stock" label="安全库存" initialValue={0}>
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="unit_price" label="单价 (含税)">
            <InputNumber min={0} step={0.0001} style={{ width: "100%" }} placeholder="0.0000" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="编辑库存记录"
        open={editOpen}
        onOk={handleEdit}
        onCancel={() => { setEditOpen(false); setEditingRecord(null); editForm.resetFields(); }}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        {editingRecord && (
          <div style={{ marginBottom: 12 }}>
            <Text>
              <strong>SKU:</strong> {editingRecord.sku || "-"} &nbsp;&nbsp;
              <strong>产品:</strong> {editingRecord.product_name || "-"} &nbsp;&nbsp;
              <strong>仓库:</strong> {editingRecord.warehouse_name || "-"}
            </Text>
          </div>
        )}
        <Form form={editForm} layout="vertical" style={{ marginTop: 8 }}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="quantity" label="库存数量" rules={[{ required: true }]}>
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="safety_stock" label="安全库存">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="unit_price" label="单价 (含税)">
            <InputNumber min={0} step={0.0001} style={{ width: "100%" }} placeholder="0.0000" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
