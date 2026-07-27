import { useMemo, useRef, useState } from "react";
import { useNavigate } from "@/router";
import { Button, Dropdown, Form, InputNumber, Modal, Select, Space, Typography, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import type { MenuProps } from "antd";
import { DeleteOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { allocatePayment, getInvoices, getPayments, deletePayment, getPaymentStats, getApiErrorMessage } from "../../api";
import type { Invoice, PaymentRecord } from "../../types";
import { CustomerLink, CustomerSelect, ErpExportButton, MetricBand, SalesModuleShell, erpRowClass, money, shortDate, statusDot, ERP_STATUS_DOT } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  pending: { color: "orange", label: "待收款" }, completed: { color: "green", label: "已收款" },
  overdue: { color: "red", label: "逾期" }, cancelled: { color: "default", label: "已取消" },
};

export default function PaymentList() {
  const [pageData, setPageData] = useState<PaymentRecord[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentPageSize, setCurrentPageSize] = useState(20);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [stats, setStats] = useState<{ total_received: number; total_pending: number; total_overdue: number }>({ total_received: 0, total_pending: 0, total_overdue: 0 });
  const [allocationTarget, setAllocationTarget] = useState<PaymentRecord | null>(null);
  const [invoiceOptions, setInvoiceOptions] = useState<Invoice[]>([]);
  const [allocating, setAllocating] = useState(false);
  const [allocationForm] = Form.useForm();
  const navigate = useNavigate();
  const actionRef = useRef<ActionType>(null);

  const openAllocation = async (payment: PaymentRecord) => {
    try {
      const response = await getInvoices({ customer_id: payment.customer_id, page_size: 100 });
      setInvoiceOptions((response.data.data.list || []).filter((invoice) => invoice.status !== "paid" && invoice.status !== "cancelled"));
      allocationForm.setFieldsValue({ allocations: [{ invoice_id: payment.invoice_id, amount: payment.amount }] });
      setAllocationTarget(payment);
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "加载待核销发票失败"));
    }
  };

  const submitAllocation = async () => {
    if (!allocationTarget) return;
    const values = await allocationForm.validateFields();
    setAllocating(true);
    try {
      await allocatePayment(allocationTarget.id, values.allocations);
      message.success("回款核销完成");
      setAllocationTarget(null);
      actionRef.current?.reload();
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "回款核销失败"));
    } finally {
      setAllocating(false);
    }
  };

  const exportData = useMemo(() =>
    pageData.map((r) => ({
      id: r.id,
      sales_order_no: r.sales_order_no || `#${r.sales_order_id}`,
      delivery_note_no: r.delivery_note_no || (r.delivery_note_id ? `#${r.delivery_note_id}` : ""),
      invoice_no: r.invoice_no || "",
      amount: r.amount,
      payment_method: r.payment_method || "",
      payment_date: r.payment_date?.slice(0, 10) || "",
      status: STATUS[r.status]?.label || r.status,
    })),
  [pageData]);

  return (
    <SalesModuleShell
      title="回款管理"
      subtitle="按客户和订单跟踪待收、已收、逾期回款"
      activeKey="payments"
    >
      <MetricBand
        items={[
          { title: "已收款", value: stats.total_received, prefix: "¥", precision: 0 },
          { title: "待收款", value: stats.total_pending, prefix: "¥", precision: 0 },
          { title: "逾期", value: stats.total_overdue, prefix: "¥", precision: 0 },
        ]}
      />

      <Space wrap className="sales-list-toolbar" style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/payments/new")}>新增回款</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "pending", label: "待收款" }, { value: "completed", label: "已收款" },
        ]} />
        <div className="sales-customer-filter" style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
        </div>
        <ErpExportButton
          data={exportData}
          columns={[
            { key: "id", title: "ID" },
            { key: "sales_order_no", title: "关联订单号" },
            { key: "delivery_note_no", title: "关联发货单号" },
            { key: "invoice_no", title: "发票" },
            { key: "amount", title: "金额" },
            { key: "payment_method", title: "方式" },
            { key: "payment_date", title: "付款日期" },
            { key: "status", title: "状态" },
          ]}
          filename="payments_export.csv"
        />
      </Space>

      <ProTable<PaymentRecord>
        className="erp-table"
        actionRef={actionRef}
        rowKey="id"
        search={false}
        options={{ reload: true, density: true, setting: true }}
        rowClassName={erpRowClass}
        scroll={{ x: "max-content" }}
        params={{ status, customerId }}
        request={async (params) => {
          setCurrentPage(params.current || 1);
          setCurrentPageSize(params.pageSize || 20);
          const apiParams: Record<string, unknown> = { page: params.current, page_size: params.pageSize };
          if (status) apiParams.status = status;
          if (customerId) apiParams.customer_id = customerId;
          const [resp, s] = await Promise.all([getPayments(apiParams), getPaymentStats()]);
          setStats(s.data.data);
          return { data: resp.data.data.list || [], success: true, total: resp.data.data.total || 0 };
        }}
        onLoad={(ds) => setPageData(ds as PaymentRecord[])}
        columns={[
          { title: "#", width: 45, fixed: "left", render: (_: unknown, __: PaymentRecord, index: number) => (currentPage - 1) * currentPageSize + index + 1 },
          {
            title: "关联订单号", dataIndex: "sales_order_no", width: 160,
            render: (value: string | null, record: PaymentRecord) => (
              <div>
                <div className="erp-cell-primary">
                  <Typography.Link strong onClick={() => navigate(`/sales/orders/${record.sales_order_id}`)}>
                    {value || `#${record.sales_order_id}`}
                  </Typography.Link>
                </div>
              </div>
            ),
          },
          {
            title: "关联发货单号", dataIndex: "delivery_note_no", width: 160,
            render: (value: string | null, record: PaymentRecord) => {
              if (!record.delivery_note_id) return <span style={{ color: "#999" }}>-</span>;
              return (
                <a onClick={() => navigate(`/sales/delivery-notes/${record.delivery_note_id}`)}>
                  {value || `#${record.delivery_note_id}`}
                </a>
              );
            },
          },
          {
            title: "发票", dataIndex: "invoice_id", width: 110,
            render: (value: number | null, r: PaymentRecord) => {
              if (!value) return <span style={{ color: "#999" }}>-</span>;
              return (
                <Typography.Link onClick={() => navigate(`/sales/invoices/${value}`)}>
                  {r.invoice_no || `#${value}`}
                </Typography.Link>
              );
            },
          },
          { title: "客户", dataIndex: "customer_id", width: 180, render: (value: number) => <CustomerLink id={value} /> },
          { title: "金额", dataIndex: "amount", width: 120, align: "right", sorter: (a: any, b: any) => a.amount - b.amount, render: (v: number) => <Typography.Text strong>{money(v)}</Typography.Text> },
          { title: "方式", dataIndex: "payment_method", width: 80 },
          { title: "付款日期", dataIndex: "payment_date", width: 110, sorter: (a: any, b: any) => (a.payment_date || "").localeCompare(b.payment_date || ""), render: shortDate },
          {
            title: "状态", dataIndex: "status", width: 90,
            sorter: (a: any, b: any) => (a.status || "").localeCompare(b.status || ""),
            render: (v: string) => (
              <>
                {statusDot(ERP_STATUS_DOT[v] || "#d9d9d9")}
                <StatusTag tone={STATUS[v]?.color}>{STATUS[v]?.label || v}</StatusTag>
              </>
            ),
          },
          {
            title: "操作", width: 60, fixed: "right",
            render: (_: unknown, r: PaymentRecord) => {
              const items: MenuProps["items"] = [
                { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/payments/${r.id}`) },
                { key: "edit", icon: <EditOutlined />, label: "编辑", onClick: () => navigate(`/sales/payments/${r.id}/edit`) },
                { key: "allocate", label: "核销发票", onClick: () => openAllocation(r) },
                { type: "divider" as const },
                { key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true, onClick: () => {
                  Modal.confirm({ title: "确定删除?", content: `删除回款 #${r.id}？`, onOk: async () => {
                    try { await deletePayment(r.id); message.success("已删除"); actionRef.current?.reload(); } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
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
        ] as any}
        summary={(pageData: readonly PaymentRecord[]) => {
          const total = pageData.reduce((s, r) => s + r.amount, 0);
          return (
            <ProTable.Summary.Row>
              <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={1}><Typography.Text strong>{pageData.length} 项</Typography.Text></ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={2} />
              <ProTable.Summary.Cell index={3} />
              <ProTable.Summary.Cell index={4} align="right"><Typography.Text strong>{money(total)}</Typography.Text></ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={5} colSpan={4} />
            </ProTable.Summary.Row>
          );
        }}
        pagination={{ defaultPageSize: 20, showSizeChanger: true }}
      />

      <Modal
        title={`回款核销 ${allocationTarget?.transaction_ref || (allocationTarget ? `#${allocationTarget.id}` : "")}`}
        open={Boolean(allocationTarget)}
        onCancel={() => setAllocationTarget(null)}
        onOk={submitAllocation}
        confirmLoading={allocating}
        width={680}
      >
        <Typography.Paragraph type="secondary">
          回款金额：{money(allocationTarget?.amount || 0)}。可拆分核销同一客户的多张发票，核销合计不能超过回款金额。
        </Typography.Paragraph>
        <Form form={allocationForm} layout="vertical">
          <Form.List name="allocations">
            {(fields, { add, remove }) => (
              <Space direction="vertical" style={{ width: "100%" }}>
                {fields.map((field) => (
                  <Space key={field.key} align="start">
                    <Form.Item {...field} name={[field.name, "invoice_id"]} label="发票" rules={[{ required: true }]}>
                      <Select
                        style={{ width: 300 }}
                        options={invoiceOptions.map((invoice) => ({
                          value: invoice.id,
                          label: `${invoice.invoice_no || `#${invoice.id}`} · ${money(invoice.amount)}`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item {...field} name={[field.name, "amount"]} label="核销金额" rules={[{ required: true }]}>
                      <InputNumber min={0.01} precision={2} style={{ width: 180 }} />
                    </Form.Item>
                    {fields.length > 1 && <Button danger onClick={() => remove(field.name)}>删除</Button>}
                  </Space>
                ))}
                <Button onClick={() => add({ amount: 0 })}>增加核销发票</Button>
              </Space>
            )}
          </Form.List>
        </Form>
      </Modal>
    </SalesModuleShell>
  );
}
