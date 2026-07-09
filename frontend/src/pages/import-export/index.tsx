import { useState } from "react";
import { Button, Card, Col, message, Row, Select, Space, Table, Tabs, Typography, Upload } from "antd";
import { DownloadOutlined, InboxOutlined, UploadOutlined } from "@ant-design/icons";
import { exportEntity, importEntity, getApiErrorMessage } from "../../api";

const { Title, Text } = Typography;
const { Dragger } = Upload;

const EXPORT_ENTITIES = [
  { value: "customers", label: "客户" },
  { value: "products", label: "产品" },
  { value: "suppliers", label: "供应商" },
  { value: "brands", label: "品牌" },
  { value: "purchase_orders", label: "采购订单" },
  { value: "sales_orders", label: "销售订单" },
  { value: "quotations", label: "报价单" },
  { value: "contracts", label: "合同" },
];

const IMPORT_ENTITIES = [
  { value: "customers", label: "客户" },
  { value: "products", label: "产品" },
  { value: "suppliers", label: "供应商" },
  { value: "contracts", label: "合同" },
];

export default function ImportExportPage() {
  const [exportEntity_, setExportEntity] = useState("customers");
  const [exportFormat, setExportFormat] = useState("csv");
  const [exporting, setExporting] = useState(false);
  const [importEntity_, setImportEntity] = useState("customers");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ created: number; errors: string[] } | null>(null);

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await exportEntity(exportEntity_, exportFormat);
      const ext = exportFormat === "xlsx" ? "xlsx" : "csv";
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${exportEntity_}_${new Date().toISOString().slice(0, 10)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "导出失败")); } finally {
      setExporting(false);
    }
  };

  const handleImport = async (file: File) => {
    setImporting(true);
    setImportResult(null);
    try {
      const resp = await importEntity(importEntity_, file);
      setImportResult(resp.data.data as { created: number; errors: string[] });
      message.success("导入完成");
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "导入失败")); } finally {
      setImporting(false);
    }
    return false;
  };

  return (
    <div>
      <Title level={4}>数据导入导出</Title>

      <Tabs
        items={[
          {
            key: "export",
            label: "导出数据",
            children: (
              <Card>
                <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                  <Row gutter={16} align="middle">
                    <Col>
                      <Text strong>选择实体：</Text>
                    </Col>
                    <Col>
                      <Select
                        value={exportEntity_}
                        onChange={setExportEntity}
                        options={EXPORT_ENTITIES}
                        style={{ width: 160 }}
                      />
                    </Col>
                  </Row>
                  <Row gutter={16} align="middle">
                    <Col>
                      <Text strong>导出格式：</Text>
                    </Col>
                    <Col>
                      <Select
                        value={exportFormat}
                        onChange={setExportFormat}
                        options={[
                          { value: "csv", label: "CSV (.csv)" },
                          { value: "xlsx", label: "Excel (.xlsx)" },
                        ]}
                        style={{ width: 160 }}
                      />
                    </Col>
                  </Row>
                  <Button
                    type="primary"
                    icon={<DownloadOutlined />}
                    loading={exporting}
                    onClick={handleExport}
                  >
                    导出
                  </Button>
                </Space>
              </Card>
            ),
          },
          {
            key: "import",
            label: "导入数据",
            children: (
              <Card>
                <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                  <Row gutter={16} align="middle">
                    <Col>
                      <Text strong>选择实体：</Text>
                    </Col>
                    <Col>
                      <Select
                        value={importEntity_}
                        onChange={setImportEntity}
                        options={IMPORT_ENTITIES}
                        style={{ width: 160 }}
                      />
                    </Col>
                  </Row>
                  <Dragger
                    accept=".csv,.xlsx,.xls"
                    showUploadList={false}
                    beforeUpload={handleImport}
                    disabled={importing}
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                    <p className="ant-upload-hint">
                      支持 CSV 和 Excel (.xlsx) 格式，首行必须包含列标题
                    </p>
                  </Dragger>

                  {importResult && (
                    <Card size="small" title="导入结果">
                      <Space direction="vertical">
                        <Text>成功导入：<Text strong type="success">{importResult.created}</Text> 条记录</Text>
                        {importResult.errors.length > 0 && (
                          <>
                            <Text type="danger">失败 {importResult.errors.length} 条：</Text>
                            <Table
                              size="small"
                              dataSource={importResult.errors.map((e, i) => ({ key: i, error: e }))}
                              columns={[{ title: "错误信息", dataIndex: "error" }]}
                              pagination={false}
                            />
                          </>
                        )}
                      </Space>
                    </Card>
                  )}

                  <Text type="secondary">
                    提示：文件首行为列标题，支持中英文列名。导入客户时必需的列为：name（名称），导入产品时必需的列为：name（名称）。
                  </Text>
                </Space>
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
