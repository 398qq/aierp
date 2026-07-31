import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Dropdown,
  Modal,
  Select,
  Space,
  Typography,
  Upload,
} from "antd";
import { StatusTag } from "../../ui";
import type { ActionType } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import type { MenuProps } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EllipsisOutlined,
  EyeOutlined,
  PlusOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  getApiErrorMessage,
  importContractPDF,
} from "../../api";
import client from "../../api/client";
import type { Contract, PageData } from "../../types";
import { useApiMutation, useApiQuery } from "../../lib/queries";
import {
  CustomerLink,
  CustomerSelect,
  ErpExportButton,
  SalesModuleShell,
  erpRowClass,
  money,
  statusDot,
  ERP_STATUS_DOT,
} from "./salesUi";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" },
  expired: { color: "orange", label: "已到期" },
  terminated: { color: "red", label: "已终止" },
};

const EMPTY_ROWS: Contract[] = [];

interface ContractImportResult {
  created: number;
  errors: string[];
}

interface ContractPdfImportResult {
  id: number;
  parsed: Record<string, unknown>;
  raw_text_preview: string;
}

export default function ContractList() {
  const { message, modal } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const navigate = useNavigate();

  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const listQuery = useApiQuery<PageData<Contract>>(
    ["contracts", { status, customer_id: customerId, page, page_size: pageSize }],
    "/api/v1/contracts",
    {
      status,
      customer_id: customerId,
      page,
      page_size: pageSize,
    },
    { keepPreviousData: true, staleTime: 30 * 1000 },
  );

  const deleteMut = useApiMutation<unknown, number>(
    "delete",
    (id) => `/api/v1/contracts/${id}`,
    {
      invalidateKeys: [["contracts"]],
      onSuccess: () => message.success("已删除"),
      onError: (err) => message.error(getApiErrorMessage(err, "删除失败")),
    },
  );

  const dataSource = useMemo(
    () => listQuery.data?.list ?? EMPTY_ROWS,
    [listQuery.data],
  );

  const exportData = useMemo(
    () =>
      dataSource.map((r) => ({
        contract_no: r.contract_no || `#${r.id}`,
        title: r.title,
        amount: r.amount,
        status: STATUS[r.status]?.label || r.status,
        signed_date: r.signed_date?.slice(0, 10) || "",
        expire_date: r.expire_date?.slice(0, 10) || "",
      })),
    [dataSource],
  );

  return (
    <SalesModuleShell
      title="合同管理"
      subtitle="管理销售合同签署、履行、到期和导入识别"
      activeKey="contracts"
    >
      <Space style={{ marginBottom: 16 }} wrap>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate("/sales/contracts/new")}
        >
          新增合同
        </Button>
        <ContractImportButton
          onSuccess={() => actionRef.current?.reload()}
        />
        <ContractPdfImportButton
          onSuccess={() => actionRef.current?.reload()}
        />
        <Button
          icon={<DownloadOutlined />}
          onClick={() => {
            window.open("/api/v1/export/contracts?format=csv", "_blank");
          }}
        >
          导出
        </Button>
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
        <Select
          placeholder="状态筛选"
          allowClear
          style={{ width: 120 }}
          value={status}
          onChange={setStatus}
          options={[
            { value: "draft", label: "草稿" },
            { value: "signed", label: "已签署" },
            { value: "active", label: "履行中" },
          ]}
        />
        <div style={{ width: 280 }}>
          <CustomerSelect value={customerId} onChange={setCustomerId} />
        </div>
      </Space>
      <ProTable<Contract>
        actionRef={actionRef}
        rowKey="id"
        search={false}
        options={{ reload: () => listQuery.refetch(), density: true, setting: true }}
        rowClassName={erpRowClass}
        scroll={{ x: "max-content" }}
        className="erp-table"
        dataSource={dataSource}
        loading={listQuery.isLoading || listQuery.isFetching}
        columns={[
          {
            title: "#",
            width: 45,
            fixed: "left",
            render: (_dom, _r, index) => (page - 1) * pageSize + index + 1,
          },
          {
            title: "合同号",
            dataIndex: "contract_no",
            width: 140,
            fixed: "left",
            render: (_dom, r: Contract) => (
              <div>
                <div className="erp-cell-primary">
                  <Typography.Link
                    strong
                    onClick={() => navigate(`/sales/contracts/${r.id}`)}
                  >
                    {r.contract_no || `#${r.id}`}
                  </Typography.Link>
                </div>
                <div className="erp-cell-secondary">{r.title}</div>
              </div>
            ),
          },
          {
            title: "客户",
            dataIndex: "customer_id",
            width: 180,
            render: (_dom, r: Contract) => <CustomerLink id={r.customer_id} />,
          },
          {
            title: "金额",
            dataIndex: "amount",
            width: 120,
            align: "right",
            sorter: (a, b) => a.amount - b.amount,
            render: (_dom, r: Contract) => (
              <Typography.Text strong>{money(r.amount)}</Typography.Text>
            ),
          },
          {
            title: "状态",
            dataIndex: "status",
            width: 90,
            sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
            render: (_dom, r: Contract) => (
              <>
                {statusDot(ERP_STATUS_DOT[r.status] || "#d9d9d9")}
                <StatusTag tone={STATUS[r.status]?.color}>
                  {STATUS[r.status]?.label || r.status}
                </StatusTag>
              </>
            ),
          },
          {
            title: "签署日期",
            dataIndex: "signed_date",
            width: 110,
            sorter: (a, b) => (a.signed_date || "").localeCompare(b.signed_date || ""),
            render: (_dom, r: Contract) => r.signed_date?.slice(0, 10) || "-",
          },
          {
            title: "到期日期",
            dataIndex: "expire_date",
            width: 110,
            sorter: (a, b) => (a.expire_date || "").localeCompare(b.expire_date || ""),
            render: (_dom, r: Contract) => r.expire_date?.slice(0, 10) || "-",
          },
          {
            title: "操作",
            width: 60,
            fixed: "right",
            render: (_dom, r: Contract) => {
              const items: MenuProps["items"] = [
                {
                  key: "view",
                  icon: <EyeOutlined />,
                  label: "查看详情",
                  onClick: () => navigate(`/sales/contracts/${r.id}`),
                },
                {
                  key: "edit",
                  icon: <EditOutlined />,
                  label: "编辑",
                  onClick: () => navigate(`/sales/contracts/${r.id}/edit`),
                },
                { type: "divider" as const },
                {
                  key: "delete",
                  icon: <DeleteOutlined />,
                  label: "删除",
                  danger: true,
                  onClick: () => {
                    modal.confirm({
                      title: "确定删除?",
                      content: `删除合同 #${r.id}？`,
                      okButtonProps: { danger: true },
                      onOk: async () => {
                        try {
                          await deleteMut.mutateAsync(r.id);
                        } catch {
                          // useApiMutation onError already shows the message
                        }
                      },
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
        ]}
        summary={() => {
          const totalAmt = dataSource.reduce((s, r) => s + r.amount, 0);
          return (
            <ProTable.Summary.Row>
              <ProTable.Summary.Cell index={0}>合计</ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={1} colSpan={2} />
              <ProTable.Summary.Cell index={3} align="right">
                <Typography.Text strong>{money(totalAmt)}</Typography.Text>
              </ProTable.Summary.Cell>
              <ProTable.Summary.Cell index={4} colSpan={4} />
            </ProTable.Summary.Row>
          );
        }}
        pagination={{
          current: page,
          pageSize,
          total: listQuery.data?.total ?? 0,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
          showTotal: (t, range) => `第 ${range[0]}-${range[1]} 条 / 共 ${t} 条`,
          onChange: (nextPage, nextSize) => {
            setPage(nextPage);
            setPageSize(nextSize);
          },
        }}
      />
    </SalesModuleShell>
  );
}

/* ------------------------------------------------------------------ */
/* CSV import sub-component                                            */
/* ------------------------------------------------------------------ */

function ContractImportButton({ onSuccess }: { onSuccess: () => void }) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<UploadFile | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ContractImportResult | null>(null);

  return (
    <>
      <Button
        icon={<UploadOutlined />}
        onClick={() => {
          setOpen(true);
          setFile(null);
          setResult(null);
        }}
      >
        导入合同
      </Button>
      <Modal
        title="导入合同"
        open={open}
        onCancel={() => setOpen(false)}
        confirmLoading={importing}
        onOk={async () => {
          if (!file) {
            message.warning("请选择文件");
            return;
          }
          setImporting(true);
          try {
            const formData = new FormData();
            formData.append("file", file as unknown as File);
            const resp = await client.post("/import/contracts", formData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            const data = resp.data.data;
            setResult({ created: data.created, errors: data.errors || [] });
            if (data.created > 0) {
              message.success(`成功导入 ${data.created} 条合同`);
              onSuccess();
            }
            if (data.errors?.length > 0) {
              message.warning(`${data.errors.length} 行导入失败`);
            }
          } catch (err: unknown) {
            message.error(getApiErrorMessage(err, "导入失败"));
          } finally {
            setImporting(false);
          }
        }}
        okText="开始导入"
      >
        <Upload
          accept=".csv,.xlsx"
          maxCount={1}
          beforeUpload={(f) => {
            setFile(f as unknown as UploadFile);
            return false;
          }}
          onRemove={() => setFile(null)}
          fileList={file ? [file] : []}
        >
          <Button icon={<UploadOutlined />}>选择文件 (CSV / Excel)</Button>
        </Upload>
        <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
          支持列：contract_no(合同号), title(标题), customer_id(客户ID), amount(金额),
          signed_date(签署日期), expire_date(到期日期), status(状态), notes(备注)
        </div>
        {result && (
          <div style={{ marginTop: 12 }}>
            <p>
              导入完成：成功 {result.created} 条
              {result.errors.length > 0 && `，失败 ${result.errors.length} 条`}
            </p>
            {result.errors.length > 0 && (
              <ul style={{ maxHeight: 120, overflow: "auto", fontSize: 12, color: "red" }}>
                {result.errors.slice(0, 10).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Modal>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* PDF import sub-component                                            */
/* ------------------------------------------------------------------ */

function ContractPdfImportButton({ onSuccess }: { onSuccess: () => void }) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<UploadFile | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ContractPdfImportResult | null>(null);

  return (
    <>
      <Button
        onClick={() => {
          setOpen(true);
          setFile(null);
          setResult(null);
        }}
      >
        导入PDF
      </Button>
      <Modal
        title="导入PDF合同（AI识别）"
        open={open}
        onCancel={() => setOpen(false)}
        confirmLoading={importing}
        onOk={async () => {
          if (!file) {
            message.warning("请选择PDF文件");
            return;
          }
          setImporting(true);
          try {
            const resp = await importContractPDF(file as unknown as File);
            if (resp.data.code !== 0) {
              message.error(resp.data.msg || "导入失败");
              return;
            }
            setResult(resp.data.data);
            message.success(resp.data.msg || "PDF合同导入成功");
            onSuccess();
          } catch (err: unknown) {
            const serverMsg = (
              err as { response?: { data?: { msg?: string } } }
            )?.response?.data?.msg;
            message.error(serverMsg || "导入失败");
          } finally {
            setImporting(false);
          }
        }}
        okText="开始导入"
      >
        <Upload
          accept=".pdf"
          maxCount={1}
          beforeUpload={(f) => {
            setFile(f as unknown as UploadFile);
            return false;
          }}
          onRemove={() => setFile(null)}
          fileList={file ? [file] : []}
        >
          <Button icon={<UploadOutlined />}>选择PDF文件</Button>
        </Upload>
        <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
          系统将自动提取PDF中的合同文本，通过AI识别合同标题、合同号、金额、签署日期、
          买方名称等关键字段，并自动关联客户。
        </div>
        {result && (
          <div style={{ marginTop: 12 }}>
            <p>导入成功：合同ID {result.id}</p>
            <ul style={{ fontSize: 12, color: "#555" }}>
              {result.parsed?.title ? <li>标题：{String(result.parsed.title)}</li> : null}
              {result.parsed?.amount ? <li>金额：¥{String(result.parsed.amount)}</li> : null}
              {result.parsed?.buyer_name ? (
                <li>买方：{String(result.parsed.buyer_name)}</li>
              ) : null}
            </ul>
          </div>
        )}
      </Modal>
    </>
  );
}
