import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Dropdown, Modal, Select, Space, Typography, message } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import type { MenuProps } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  EllipsisOutlined,
  EyeOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { getInvoices, deleteInvoice, getApiErrorMessage } from "../../api";
import type { Invoice, PageData } from "@/types";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import {
  CustomerLink,
  CustomerSelect,
  ErpExportButton,
  MetricBand,
  SalesModuleShell,
  erpRowClass,
  money,
  statusDot,
  ERP_STATUS_DOT,
} from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  issued: { color: "blue", label: "已开票" },
  paid: { color: "green", label: "已付款" },
  overdue: { color: "red", label: "逾期" },
  cancelled: { color: "default", label: "已取消" },
};

export default function InvoiceList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();

  const params: Record<string, unknown> = {};
  if (status) params.status = status;
  if (customerId) params.customer_id = customerId;

  const query = useApiQuery<PageData<Invoice>>(
    ["invoices", status ?? "", customerId ?? ""],
    "/sales/invoices",
    params,
    { staleTime: 30 * 1000 },
  );

  const list = query.data?.list || [];

  const metrics = useMemo(
    () => ({
      totalCount: list.length,
      totalAmount: list.reduce((sum, inv) => sum + inv.amount, 0),
      draftCount: list.filter((inv) => inv.status === "draft").length,
      issuedCount: list.filter((inv) => ["issued", "paid"].includes(inv.status)).length,
    }),
    [list],
  );

  const exportData = useMemo(
    () =>
      list.map((inv) => ({
        invoice_no: inv.invoice_no || `#${inv.id}`,
        customer_id: inv.customer_id,
        amount: inv.amount,
        tax_amount: inv.tax_amount,
        invoice_type: inv.invoice_type,
        status: STATUS[inv.status]?.label || inv.status,
        invoice_date: inv.invoice_date?.slice(0, 10) || "",
      })),
    [list],
  );

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["invoices"] });

  const handleDelete = async (id: number) => {
    try {
      await deleteInvoice(id);
      message.success("已删除");
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const columns: ProColumns<Invoice>[] = [
    { title: "#", width: 45, fixed: "left", render: (_, __, index) => index + 1 },
    {
      title: "发票号",
      dataIndex: "invoice_no",
      width: 140,
      fixed: "left",
      render: (_, r) => (
        <Typography.Link strong onClick={() => navigate(`/sales/invoices/${r.id}`)}>
          {r.invoice_no || `#${r.id}`}
        </Typography.Link>
      ),
    },
    {
      title: "客户",
      dataIndex: "customer_name",
      width: 180,
      render: (_, r) =>
        r.customer_name ? (
          <Link to={`/customers/${r.customer_id}`}>{r.customer_name}</Link>
        ) : (
          <CustomerLink id={r.customer_id} />
        ),
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 120,
      align: "right",
      sorter: (a, b) => a.amount - b.amount,
      render: (v: number) => money(v),
    },
    {
      title: "税额",
      dataIndex: "tax_amount",
      width: 100,
      align: "right",
      sorter: (a, b) => (a.tax_amount || 0) - (b.tax_amount || 0),
      render: (v: number) => money(v),
    },
    { title: "类型", dataIndex: "invoice_type", width: 100 },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
      render: (_, r) => (
        <>
          {statusDot(ERP_STATUS_DOT[r.status] || "#d9d9d9")}
          <StatusTag tone={STATUS[r.status]?.color}>
            {STATUS[r.status]?.label || r.status}
          </StatusTag>
        </>
      ),
    },
    {
      title: "开票日期",
      dataIndex: "invoice_date",
      width: 110,
      sorter: (a, b) => (a.invoice_date || "").localeCompare(b.invoice_date || ""),
      render: (_, r) => r.invoice_date?.slice(0, 10) || "-",
    },
    {
      title: "操作",
      width: 60,
      fixed: "right",
      render: (_, r) => {
        const items: MenuProps["items"] = [
          {
            key: "view",
            icon: <EyeOutlined />,
            label: "查看详情",
            onClick: () => navigate(`/sales/invoices/${r.id}`),
          },
          {
            key: "edit",
            icon: <EditOutlined />,
            label: "编辑",
            onClick: () => navigate(`/sales/invoices/${r.id}/edit`),
          },
          { type: "divider" as const },
          {
            key: "delete",
            icon: <DeleteOutlined />,
            label: "删除",
            danger: true,
            onClick: () => {
              Modal.confirm({
                title: "确定删除?",
                content: `删除发票 #${r.id}？`,
                okText: "删除",
                cancelText: "取消",
                okButtonProps: { danger: true },
                onOk: () => handleDelete(r.id),
              });
            },
          },
        ];
        return (
          <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
            <Button size="small" icon={<EllipsisOutlined />} type="text" />
          </Dropdown>
        );
      },
    },
  ];

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
      <Space wrap className="sales-list-toolbar" style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate("/sales/invoices/new")}
        >
          新增发票
        </Button>
        <Select
          placeholder="状态筛选"
          allowClear
          style={{ width: 120 }}
          value={status}
          onChange={setStatus}
          options={[
            { value: "draft", label: "草稿" },
            { value: "issued", label: "已开票" },
            { value: "paid", label: "已付款" },
          ]}
        />
        <div className="sales-customer-filter" style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
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
      <ProTable<Invoice>
        className="erp-table"
        rowKey="id"
        columns={columns}
        dataSource={list}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: () => query.refetch(), density: true, setting: true }}
        rowClassName={erpRowClass}
        scroll={{ x: "max-content" }}
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => query.refetch(),
        }}
        summary={(data: readonly Invoice[]) => {
          const totalAmount = data.reduce((s, r) => s + r.amount, 0);
          const totalTax = data.reduce((s, r) => s + (r.tax_amount || 0), 0);
          return (
            <ProTable.Summary.Row>
              <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={1} colSpan={2} />
              <ProTable.Summary.Cell index={3} align="right">
                <Typography.Text strong>{money(totalAmount)}</Typography.Text>
              </ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={4} align="right">
                <Typography.Text strong>{money(totalTax)}</Typography.Text>
              </ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={5} colSpan={4} />
            </ProTable.Summary.Row>
          );
        }}
      />
    </SalesModuleShell>
  );
}
