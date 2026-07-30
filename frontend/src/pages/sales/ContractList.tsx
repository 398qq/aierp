import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Dropdown, Modal, Select, Space, Typography, Upload, message } from "antd";
import { StatusTag } from "../../ui";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import type { MenuProps } from "antd";
import { DeleteOutlined, DownloadOutlined, EditOutlined, EllipsisOutlined, EyeOutlined, PlusOutlined, UploadOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import { getContracts, deleteContract, importContractPDF, getApiErrorMessage } from "../../api";
import client from "../../api/client";
import type { Contract, PageData } from "@/types";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import { CustomerLink, CustomerSelect, ErpExportButton, SalesModuleShell, erpRowClass, money, statusDot, ERP_STATUS_DOT } from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" },
  expired: { color: "orange", label: "已到期" },
  terminated: { color: "red", label: "已终止" },
};

export default function ContractList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<UploadFile | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; errors: string[] } | null>(null);
  const [pdfImportOpen, setPdfImportOpen] = useState(false);
  const [pdfFile, setPdfFile] = useState<UploadFile | null>(null);
  const [pdfImporting, setPdfImporting] = useState(false);
  const [pdfResult, setPdfResult] = useState<{ id: number; parsed: Record<string, unknown>; raw_text_preview: string } | null>(null);

  const params: Record<string, unknown> = {};
  if (status) params.status = status;
  if (customerId) params.customer_id = customerId;

  const query = useApiQuery<PageData<Contract>>(
    ["sales-contracts", status ?? "", customerId ?? ""],
    "/sales/contracts",
    params,
    { staleTime: 30 * 1000 },
  );

  const list = query.data?.list || [];

  const exportData = useMemo(
    () =>
      list.map((r) => ({
        contract_no: r.contract_no || `#${r.id}`,
        title: r.title,
        amount: r.amount,
        status: STATUS[r.status]?.label || r.status,
        signed_date: r.signed_date?.slice(0, 10) || "",
        expire_date: r.expire_date?.slice(0, 10) || "",
      })),
    [list],
  );

  const invalidateContracts = () =>
    queryClient.invalidateQueries({ queryKey: ["sales-contracts"] });

  const handleDelete = async (id: number) => {
    try {
      await deleteContract(id);
      message.success("已删除");
      invalidateContracts();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const columns: ProColumns<Contract>[] = [
    { title: "#", width: 45, fixed: "left", render: (_, __, index) => index + 1 },
    {
      title: "合同号", dataIndex: "contract_no", width: 140, fixed: "left",
      render: (_, r) => (
        <div>
          <div className="erp-cell-primary">
            <Typography.Link strong onClick={() => navigate(`/sales/contracts/${r.id}`)}>
              {r.contract_no || `#${r.id}`}
            </Typography.Link>
          </div>
          <div className="erp-cell-secondary">{r.title}</div>
        </div>
      ),
    },
    { title: "客户", dataIndex: "customer_id", width: 180, render: (_, r) => <CustomerLink id={r.customer_id} /> },
    { title: "金额", dataIndex: "amount", width: 120, align: "right", sorter: (a, b) => a.amount - b.amount, render: (_, r) => <Typography.Text strong>{money(r.amount)}</Typography.Text> },
    {
      title: "状态", dataIndex: "status", width: 90,
      sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
      render: (_, r) => (
        <>
          {statusDot(ERP_STATUS_DOT[r.status] || "#d9d9d9")}
          <StatusTag tone={STATUS[r.status]?.color}>{STATUS[r.status]?.label || r.status}</StatusTag>
        </>
      ),
    },
    { title: "签署日期", dataIndex: "signed_date", width: 110, sorter: (a, b) => (a.signed_date || "").localeCompare(b.signed_date || ""), render: (_, r) => r.signed_date?.slice(0, 10) || "-" },
    { title: "到期日期", dataIndex: "expire_date", width: 110, sorter: (a, b) => (a.expire_date || "").localeCompare(b.expire_date || ""), render: (_, r) => r.expire_date?.slice(0, 10) || "-" },
    {
      title: "操作", width: 60, fixed: "right",
      render: (_, r) => {
        const items: MenuProps["items"] = [
          { key: "view", icon: <EyeOutlined />, label: "查看详情", onClick: () => navigate(`/sales/contracts/${r.id}`) },
          { key: "edit", icon: <EditOutlined />, label: "编辑", onClick: () => navigate(`/sales/contracts/${r.id}/edit`) },
          { type: "divider" as const },
          {
            key: "delete", icon: <DeleteOutlined />, label: "删除", danger: true,
            onClick: () => {
              Modal.confirm({
                title: "确定删除?",
                content: `删除合同 #${r.id}？`,
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
      title="合同管理"
      subtitle="管理销售合同签署、履行、到期和导入识别"
      activeKey="contracts"
    >
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/contracts/new")}>新增合同</Button>
        <Button icon={<UploadOutlined />} onClick={() => { setImportOpen(true); setImportFile(null); setImportResult(null); }}>导入合同</Button>
        <Button onClick={() => { setPdfImportOpen(true); setPdfFile(null); setPdfResult(null); }}>导入PDF</Button>
        <Button icon={<DownloadOutlined />} onClick={() => { window.open("/api/v1/export/contracts?format=csv", "_blank"); }}>导出</Button>
        <ErpExportButton
          data={exportData}
          columns={[
            { key: "contract_no", title: "合同号" },
            { key: "title", title: "标题" },
            { key: "amount", title: "金额" },
            { key: "status", title: "状态" },
            { key: "signed_date", title: "签署日期" },
            { key: "expire_date", title: "到期日期" },
          ]}
          filename="contracts_export.csv"
        />
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "signed", label: "已签署" }, { value: "active", label: "履行中" },
        ]} />
        <div style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
        </div>
      </Space>
      <ProTable<Contract>
        rowKey="id"
        columns={columns}
        dataSource={list}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: () => query.refetch(), density: true, setting: true }}
        rowClassName={erpRowClass}
        scroll={{ x: "max-content" }}
        className="erp-table"
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => query.refetch(),
        }}
        summary={(data: readonly Contract[]) => {
          const totalAmt = data.reduce((s, r) => s + r.amount, 0);
          return (
            <ProTable.Summary.Row>
              <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={1} colSpan={2} />
              <ProTable.Summary.Cell index={3} align="right"><Typography.Text strong>{money(totalAmt)}</Typography.Text></ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={4} colSpan={4} />
            </ProTable.Summary.Row>
          );
        }}
      />

      <Modal
        title="导入合同"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        confirmLoading={importing}
        onOk={async () => {
          if (!importFile) { message.warning("请选择文件"); return; }
          setImporting(true);
          try {
            const formData = new FormData();
            formData.append("file", importFile as unknown as File);
            const resp = await client.post("/import/contracts", formData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            const data = resp.data.data;
            setImportResult({ created: data.created, errors: data.errors || [] });
            if (data.created > 0) { message.success(`成功导入 ${data.created} 条合同`); invalidateContracts(); }
            if (data.errors?.length > 0) { message.warning(`${data.errors.length} 行导入失败`); }
          } catch (e: unknown) { message.error(getApiErrorMessage(e, "导入失败")); }
          finally { setImporting(false); }
        }}
        okText="开始导入"
      >
        <Upload
          accept=".csv,.xlsx"
          maxCount={1}
          beforeUpload={(file) => { setImportFile(file as unknown as UploadFile); return false; }}
          onRemove={() => setImportFile(null)}
          fileList={importFile ? [importFile] : []}
        >
          <Button icon={<UploadOutlined />}>选择文件 (CSV / Excel)</Button>
        </Upload>
        <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
          支持列：contract_no(合同号), title(标题), customer_id(客户ID), amount(金额), signed_date(签署日期), expire_date(到期日期), status(状态), notes(备注)
        </div>
        {importResult && (
          <div style={{ marginTop: 12 }}>
            <p>导入完成：成功 {importResult.created} 条{importResult.errors.length > 0 && `，失败 ${importResult.errors.length} 条`}</p>
            {importResult.errors.length > 0 && (
              <ul style={{ maxHeight: 120, overflow: "auto", fontSize: 12, color: "red" }}>
                {importResult.errors.slice(0, 10).map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="导入PDF合同（AI识别）"
        open={pdfImportOpen}
        onCancel={() => setPdfImportOpen(false)}
        confirmLoading={pdfImporting}
        onOk={async () => {
          if (!pdfFile) { message.warning("请选择PDF文件"); return; }
          setPdfImporting(true);
          try {
            const resp = await importContractPDF(pdfFile as unknown as File);
            if (resp.data.code !== 0) {
              message.error(resp.data.msg || "导入失败");
              return;
            }
            setPdfResult(resp.data.data);
            message.success(resp.data.msg || "PDF合同导入成功");
            invalidateContracts();
          } catch (err: unknown) {
            const serverMsg = (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg;
            message.error(serverMsg || "导入失败");
          }
          finally { setPdfImporting(false); }
        }}
        okText="开始导入"
      >
        <Upload
          accept=".pdf"
          maxCount={1}
          beforeUpload={(file) => { setPdfFile(file as unknown as UploadFile); return false; }}
          onRemove={() => setPdfFile(null)}
          fileList={pdfFile ? [pdfFile] : []}
        >
          <Button icon={<UploadOutlined />}>选择PDF文件</Button>
        </Upload>
        <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
          系统将自动提取PDF中的合同文本，通过AI识别合同标题、合同号、金额、签署日期、买方名称等关键字段，并自动关联客户。
        </div>
        {pdfResult && (
          <div style={{ marginTop: 12 }}>
            <p>导入成功：合同ID {pdfResult.id}</p>
            <ul style={{ fontSize: 12, color: "#555" }}>
              {pdfResult.parsed?.title ? <li>标题：{String(pdfResult.parsed.title)}</li> : null}
              {pdfResult.parsed?.amount ? <li>金额：¥{String(pdfResult.parsed.amount)}</li> : null}
              {pdfResult.parsed?.buyer_name ? <li>买方：{String(pdfResult.parsed.buyer_name)}</li> : null}
            </ul>
          </div>
        )}
      </Modal>
    </SalesModuleShell>
  );
}