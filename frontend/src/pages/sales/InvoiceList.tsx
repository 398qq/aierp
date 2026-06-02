import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Dropdown, Modal, Popconfirm, Select, Space, Table, Tag, Typography, message } from "antd";
import type { MenuProps } from "antd";
import { DeleteOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { getInvoices, deleteInvoice } from "../../api";
import type { Invoice } from "../../types";
import { CustomerLink, CustomerSelect, ErpExportButton, MetricBand, SalesModuleShell, erpRowClass, money, shortDate, statusDot, ERP_STATUS_DOT } from "./salesUi";

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

  const metrics = useMemo(() => ({
    totalCount: data.length,
    totalAmount: data.reduce((sum, inv) => sum + inv.amount, 0),
    draftCount: data.filter((inv) => inv.status === "draft").length,
    issuedCount: data.filter((inv) => ["issued", "paid"].includes(inv.status)).length,
  }), [data]);

  const exportData = useMemo(() =>
    data.map((inv) => ({
      invoice_no: inv.invoice_no || `#${inv.id}`,
      customer_id: inv.customer_id,
      amount: inv.amount,
      tax_amount: inv.tax_amount,
      invoice_type: inv.invoice_type,
      status: STATUS[inv.status]?.label || inv.status,
      invoice_date: inv.invoice_date?.slice(0, 10) || "",
    })),
  [data]);

  return (
    <SalesModuleShell
      title="开票管理"
      subtitle="按销售订单和客户跟踪发票、税额、开票状态"
      activeKey="invoices"
    >
      <MetricBand
        items={[
          { title: "发票总数", value: metrics.totalCount, suffix: "项" },
          { title: "总金额", value: metrics.totalAmount, prefix: "¥", precision: 0 },
          { title: "待开票", value: metrics.draftCount, suffix: "项" },
          { title: "已开票", value: metrics.issuedCount, suffix: "项" },
        ]}
      />
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/invoices/new")}>新增发票</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "issued", label: "已开票" }, { value: "paid", label: "已付款" },
        ]} />
        <div style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
        </div>
        <ErpExportButton
          data={exportData}
          columns={[
            { key: "invoice_no", title: "发票号" },
            { key: "customer_id", title: "客户ID" },
            { key: "amount", title: "金额" },
            { key: "tax_amount", title: "税额" },
            { key: "invoice_type", title: "类型" },
            { key: "status", title: "状态" },
            { key: "invoice_date", title: "开票日期" },
          ]}
          filename="invoices_export.csv"
        />
      </Space>
      <Table
        rowKey="id" loading={loading} dataSource={data}
        rowClassName={erpRowClass}
        scroll={{ x: "max-content" }}
        columns={[
          { title: "#", width: 45, fixed: "left", render: (_: unknown, __: Invoice, index: number) => (page - 1) * 20 + index + 1 },
          {
            title: "发票号", dataIndex: "invoice_no", width: 140, fixed: "left",
            render: (v: string, r: Invoice) => (
              <div>
                <div className="erp-cell-primary">
                  <Typography.Link strong onClick={() => navigate(`/sales/invoices/${r.id}`)}>{v || `#${r.id}`}</Typography.Link>
                </div>
                <div className="erp-cell-secondary"><CustomerLink id={r.customer_id} /></div>
              </div>
            ),
          },
          { title: "客户", dataIndex: "customer_id", width: 180, render: (value: number) => <CustomerLink id={value} /> },
          { title: "金额", dataIndex: "amount", width: 120, align: "right", sorter: (a, b) => a.amount - b.amount, render: (v: number) => money(v) },
          { title: "税额", dataIndex: "tax_amount", width: 100, align: "right", sorter: (a, b) => (a.tax_amount || 0) - (b.tax_amount || 0), render: (v: number) => money(v) },
          { title: "类型", dataIndex: "invoice_type", width: 100 },
          {
            title: "状态", dataIndex: "status", width: 90,
            sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
            render: (v: string) => (
              <>
                {statusDot(ERP_STATUS_DOT[v] || "#d9d9d9")}
                <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag>
              </>
            ),
          },
          { title: "开票日期", dataIndex: "invoice_date", width: 110, sorter: (a, b) => (a.invoice_date || "").localeCompare(b.invoice_date || ""), render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "操作", width: 60, fixed: "right",
            render: (_: unknown, r: Invoice) => {
              const items: MenuProps["items"] = [
                { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/invoices/${r.id}`) },
                { key: "edit", icon: <EditOutlined />, label: "编辑", onClick: () => navigate(`/sales/invoices/${r.id}/edit`) },
                { type: "divider" as const },
                { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                  Modal.confirm({ title: "确定删除?", content: `删除发票 #${r.id}？`, onOk: async () => {
                    try { await deleteInvoice(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                  }});
                }},
              ];
              return (
                <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
                  <Button size="small" icon={<EllipsisOutlined />} type="text" />
                </Dropdown>
              );
            },
          },
        ]}
        summary={(pageData: readonly Invoice[]) => {
          const totalAmount = pageData.reduce((s, r) => s + r.amount, 0);
          const totalTax = pageData.reduce((s, r) => s + (r.tax_amount || 0), 0);
          return (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0}>合计</Table.Summary.Cell>
              <Table.Summary.Cell index={1} colSpan={2} />
              <Table.Summary.Cell index={3} align="right"><Typography.Text strong>{money(totalAmount)}</Typography.Text></Table.Summary.Cell>
              <Table.Summary.Cell index={4} align="right"><Typography.Text strong>{money(totalTax)}</Typography.Text></Table.Summary.Cell>
              <Table.Summary.Cell index={5} colSpan={4} />
            </Table.Summary.Row>
          );
        }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </SalesModuleShell>
  );
}
