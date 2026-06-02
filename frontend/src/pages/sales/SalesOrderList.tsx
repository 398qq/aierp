import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Dropdown, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, Upload, message } from "antd";
import type { MenuProps } from "antd";
import { CarOutlined, DeleteOutlined, DownloadOutlined, EllipsisOutlined, PlusOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import { batchDeleteSalesOrders, convertSalesOrderToDelivery, deleteSalesOrder, getSalesOrders, importSalesOrderPDF } from "../../api";
import type { SalesOrderPDFImportResult } from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { SalesOrder } from "../../types";
import { CustomerLink, CustomerSelect, ErpExportButton, MetricBand, SalesModuleShell, SalesQuickActions, SalesStatusTag, erpRowClass, money, shortDate, statusDot, ERP_STATUS_DOT } from "./salesUi";

export default function SalesOrderList() {
  const [data, setData] = useState<SalesOrder[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { delivery_risk?: string; flag?: string }>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const [pdfImportOpen, setPdfImportOpen] = useState(false);
  const [pdfFile, setPdfFile] = useState<UploadFile | null>(null);
  const [pdfCustomerId, setPdfCustomerId] = useState<number | undefined>();
  const [pdfImporting, setPdfImporting] = useState(false);
  const [pdfResult, setPdfResult] = useState<SalesOrderPDFImportResult | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      if (customerId) params.customer_id = customerId;
      if (q.trim()) params.q = q.trim();
      if (includeAi) params.include_ai = true;
      const resp = await getSalesOrders(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
      setAiMap(includeAi ? ((resp.data.data as unknown as { ai?: Record<number, { delivery_risk?: string; flag?: string }> }).ai || {}) : {});
    } catch {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [page, status, customerId, q, includeAi]);

  const stats = useMemo(() => {
    const amount = data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0);
    const confirmed = data.filter((item) => item.status === "confirmed").length;
    const pending = data.filter((item) => item.status === "pending").length;
    const itemCount = data.reduce((sum, item) => sum + (item.items?.length || 0), 0);
    return { amount, confirmed, pending, itemCount };
  }, [data]);

  const handleBatchDelete = async () => {
    try {
      await batchDeleteSalesOrders(selected);
      message.success("已批量删除");
      setSelected([]);
      load();
    } catch {
      message.error("删除失败");
    }
  };

  const handlePdfImport = async () => {
    if (!pdfFile) {
      message.warning("请选择PDF订单文件");
      return;
    }
    setPdfImporting(true);
    try {
      const resp = await importSalesOrderPDF(pdfFile as unknown as File, pdfCustomerId);
      if (resp.data.code !== 0) {
        message.error(resp.data.msg || "导入失败");
        return;
      }
      setPdfResult(resp.data.data);
      message.success(resp.data.msg || "PDF订单导入成功");
      load();
    } catch (err: unknown) {
      const serverMsg = (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg;
      message.error(serverMsg || "导入失败");
    } finally {
      setPdfImporting(false);
    }
  };

  return (
    <SalesModuleShell
      title="销售订单"
      subtitle="承接报价成交，管理产品明细、交付风险和执行状态"
      activeKey="orders"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "订单数", value: total, suffix: "单" },
          { title: "本页金额", value: stats.amount, prefix: "¥", precision: 0 },
          { title: "待确认", value: stats.pending, suffix: "单" },
          { title: "已确认", value: stats.confirmed, suffix: "单" },
          { title: "产品行", value: stats.itemCount, suffix: "项" },
        ]}
      />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/orders/new")}>新建订单</Button>
          <Button
            icon={<UploadOutlined />}
            onClick={() => {
              setPdfImportOpen(true);
              setPdfFile(null);
              setPdfCustomerId(undefined);
              setPdfResult(null);
            }}
          >
            导入PDF订单
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <ErpExportButton
            data={data as unknown as Record<string, unknown>[]}
            columns={[
              { key: "order_no", title: "订单号" },
              { key: "total_amount", title: "金额" },
              { key: "status", title: "状态" },
              { key: "order_date", title: "下单日期" },
              { key: "delivery_date", title: "交付日期" },
            ]}
            filename="销售订单.csv"
          />
          <Input.Search
            allowClear
            placeholder="搜索客户 / 订单号 / 产品"
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              if (!event.target.value) {
                setPage(1);
                setQ("");
              }
            }}
            onSearch={(value) => {
              setPage(1);
              setQ(value);
            }}
            style={{ width: 260 }}
          />
          <div style={{ width: 260 }}>
            <CustomerSelect value={customerId} onChange={(next) => { setCustomerId(next); setPage(1); }} />
          </div>
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>删除 {selected.length}</Button>
            </Popconfirm>
          ) : null}
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={(next) => {
              setPage(1);
              setStatus(next);
            }}
            options={[
              { value: "pending", label: "待确认" },
              { value: "confirmed", label: "已确认" },
              { value: "shipped", label: "已发货" },
              { value: "delivered", label: "已完成" },
            ]}
          />
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={(
          <Space size={8} wrap>
            <Typography.Text strong>销售订单单据</Typography.Text>
            <Typography.Text type="secondary">{data.length} / {total} 单</Typography.Text>
            {selected.length > 0 && <Tag color="blue">已选 {selected.length}</Tag>}
          </Space>
        )}
      >
        <Table
          rowKey="id"
          size="small"
          bordered
          loading={loading}
          dataSource={data}
          rowClassName={erpRowClass}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "#", width: 40, fixed: "left" as const, render: (_: unknown, __: SalesOrder, index: number) => (page - 1) * 20 + index + 1 },
            {
              title: "订单",
              dataIndex: "order_no",
              fixed: "left",
              minWidth: 220,
              render: (value: string | null, record: SalesOrder) => (
                <div>
                  <div className="erp-cell-primary">
                    <Typography.Link strong onClick={() => navigate(`/sales/orders/${record.id}`)}>{value || `#${record.id}`}</Typography.Link>
                  </div>
                  <div className="erp-cell-secondary">
                    <Space size={8}>
                      <CustomerLink id={record.customer_id} />
                      <span>产品行 {record.items?.length || 0}</span>
                    </Space>
                  </div>
                </div>
              ),
            },
            { title: "金额", dataIndex: "total_amount", width: 130, sorter: (a, b) => Number(a.total_amount || 0) - Number(b.total_amount || 0), render: money },
            {
              title: "状态", dataIndex: "status", width: 100,
              sorter: (a, b) => (a.status || "").localeCompare(b.status || ""),
              render: (value: string) => (
                <>
                  {statusDot(ERP_STATUS_DOT[value] || "#d9d9d9")}
                  <SalesStatusTag value={value} />
                </>
              ),
            },
            { title: "下单", dataIndex: "order_date", width: 120, sorter: (a, b) => (a.order_date || "").localeCompare(b.order_date || ""), render: shortDate },
            { title: "交付", dataIndex: "delivery_date", width: 120, sorter: (a, b) => (a.delivery_date || "").localeCompare(b.delivery_date || ""), render: shortDate },
            {
              title: "AI",
              width: 100,
              render: (_: unknown, record: SalesOrder) => <AIInlineBadge riskLevel={aiMap[record.id]?.delivery_risk} flag={aiMap[record.id]?.flag} />,
            },
            {
              title: "操作",
              width: 60,
              fixed: "right" as const,
              render: (_: unknown, record: SalesOrder) => {
                const items: MenuProps["items"] = [
                  { key: "view", label: "查看详情", onClick: () => navigate(`/sales/orders/${record.id}`) },
                  { key: "delivery", label: "转为发货单", icon: <CarOutlined />, onClick: () => {
                    Modal.confirm({ title: "转为发货单?", content: `将订单 ${record.order_no || `#${record.id}`} 转为发货单`, onOk: async () => {
                      try { await convertSalesOrderToDelivery(record.id); message.success("已转为发货单"); load(); } catch { message.error("转换失败"); }
                    } });
                  }},
                  { type: "divider" as const },
                  { key: "delete", label: "删除", danger: true, icon: <DeleteOutlined />, onClick: () => {
                    Modal.confirm({ title: "确定删除?", content: `删除订单 ${record.order_no || `#${record.id}`}`, onOk: async () => {
                      try { await deleteSalesOrder(record.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                    } });
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
          pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (count) => `共 ${count} 条` }}
        />
      </Card>

      <Modal
        title="导入PDF订单"
        open={pdfImportOpen}
        onCancel={() => setPdfImportOpen(false)}
        onOk={handlePdfImport}
        confirmLoading={pdfImporting}
        okText="开始导入"
        width={720}
      >
        <Space direction="vertical" size={14} style={{ width: "100%" }}>
          <Upload
            accept=".pdf"
            maxCount={1}
            beforeUpload={(file) => {
              setPdfFile(file as unknown as UploadFile);
              setPdfResult(null);
              return false;
            }}
            onRemove={() => {
              setPdfFile(null);
              setPdfResult(null);
            }}
            fileList={pdfFile ? [pdfFile] : []}
          >
            <Button icon={<UploadOutlined />}>选择PDF订单文件</Button>
          </Upload>
          <div>
            <Typography.Text strong>客户匹配</Typography.Text>
            <div style={{ marginTop: 8, width: 320 }}>
              <CustomerSelect value={pdfCustomerId} onChange={setPdfCustomerId} />
            </div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              PDF 内客户名称无法准确匹配时，可手工指定客户；系统会保留 PDF 文件名和识别摘要到订单备注。
            </Typography.Text>
          </div>
          <Alert
            type="info"
            showIcon
            message="支持文本型 PDF 订单，自动识别订单号、客户、日期、产品明细、数量、单价和金额。扫描件需先转为可复制文字的 PDF。"
          />
          {pdfResult ? (
            <div style={{ borderTop: "1px solid #eef2f7", paddingTop: 12 }}>
              <Descriptions size="small" column={2} bordered>
                <Descriptions.Item label="订单号">{pdfResult.order_no || `#${pdfResult.id}`}</Descriptions.Item>
                <Descriptions.Item label="客户">{pdfResult.matched.customer_name}</Descriptions.Item>
                <Descriptions.Item label="明细行">{pdfResult.parsed.item_count}</Descriptions.Item>
                <Descriptions.Item label="金额">{money(pdfResult.parsed.total_amount)}</Descriptions.Item>
              </Descriptions>
              <Space style={{ marginTop: 12 }}>
                <Button type="primary" onClick={() => navigate(`/sales/orders/${pdfResult.id}`)}>查看订单</Button>
                <Button onClick={() => setPdfImportOpen(false)}>关闭</Button>
              </Space>
            </div>
          ) : null}
        </Space>
      </Modal>
    </SalesModuleShell>
  );
}
