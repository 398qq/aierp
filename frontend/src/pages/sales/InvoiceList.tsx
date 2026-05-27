import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getInvoices, deleteInvoice } from "../../api";
import type { Invoice } from "../../types";
import { CustomerLink, CustomerSelect, SalesModuleShell } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, issued: { color: "blue", label: "已开票" },
  paid: { color: "green", label: "已付款" }, overdue: { color: "red", label: "逾期" }, cancelled: { color: "default", label: "已取消" },
};

export default function InvoiceList() {
  const [data, setData] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      const resp = await getInvoices(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status, customerId]);

  return (
    <SalesModuleShell
      title="开票管理"
      subtitle="按销售订单和客户跟踪发票、税额、开票状态"
      activeKey="invoices"
    >
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/invoices/new")}>新增发票</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "issued", label: "已开票" }, { value: "paid", label: "已付款" },
        ]} />
        <div style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
        </div>
      </Space>
      <Table
        rowKey="id" loading={loading} dataSource={data}
        columns={[
          { title: "发票号", dataIndex: "invoice_no", width: 140, render: (v: string, r: Invoice) => <a onClick={() => navigate(`/sales/invoices/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "客户", dataIndex: "customer_id", width: 180, render: (value: number) => <CustomerLink id={value} /> },
          { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "税额", dataIndex: "tax_amount", width: 100, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "类型", dataIndex: "invoice_type", width: 100 },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          { title: "开票日期", dataIndex: "invoice_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: Invoice) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/invoices/${r.id}`)}>详情</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteInvoice(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </SalesModuleShell>
  );
}
