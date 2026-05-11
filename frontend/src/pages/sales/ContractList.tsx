import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm, Modal, Upload } from "antd";
import { PlusOutlined, UploadOutlined, DownloadOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import { getContracts, deleteContract, importContractPDF } from "../../api";
import client from "../../api/client";
import type { Contract } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" }, expired: { color: "orange", label: "已到期" }, terminated: { color: "red", label: "已终止" },
};

export default function ContractList() {
  const [data, setData] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<UploadFile | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; errors: string[] } | null>(null);
  const [pdfImportOpen, setPdfImportOpen] = useState(false);
  const [pdfFile, setPdfFile] = useState<UploadFile | null>(null);
  const [pdfImporting, setPdfImporting] = useState(false);
  const [pdfResult, setPdfResult] = useState<{ id: number; parsed: Record<string, unknown>; raw_text_preview: string } | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      const resp = await getContracts(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status]);

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/contracts/new")}>新增合同</Button>
        <Button icon={<UploadOutlined />} onClick={() => { setImportOpen(true); setImportFile(null); setImportResult(null); }}>导入合同</Button>
        <Button onClick={() => { setPdfImportOpen(true); setPdfFile(null); setPdfResult(null); }}>导入PDF</Button>
        <Button icon={<DownloadOutlined />} onClick={() => { window.open("/api/v1/export/contracts?format=csv", "_blank"); }}>导出</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "signed", label: "已签署" }, { value: "active", label: "履行中" },
        ]} />
      </Space>
      <Table
        rowKey="id" loading={loading} dataSource={data}
        columns={[
          { title: "合同号", dataIndex: "contract_no", width: 140, render: (v: string, r: Contract) => <a onClick={() => navigate(`/sales/contracts/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "标题", dataIndex: "title", ellipsis: true },
          { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          { title: "签署日期", dataIndex: "signed_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          { title: "到期日期", dataIndex: "expire_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: Contract) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/contracts/${r.id}`)}>详情</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteContract(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
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
            if (data.created > 0) { message.success(`成功导入 ${data.created} 条合同`); load(); }
            if (data.errors?.length > 0) { message.warning(`${data.errors.length} 行导入失败`); }
          } catch { message.error("导入失败"); }
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
            load();
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
    </div>
  );
}
