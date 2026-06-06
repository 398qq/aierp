import { useState, useCallback } from "react";
import {
  Card,
  Upload,
  Button,
  Table,
  Select,
  Space,
  Result,
  Tag,
  Typography,
  message,
  Alert,
  Divider,
} from "antd";
import { StatusTag } from "../../ui";
import { CloudUploadOutlined, InboxOutlined, CheckCircleOutlined } from "@ant-design/icons";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";
import readXlsxFile from "read-excel-file/browser";
import type { Row as ExcelRow } from "read-excel-file/browser";
import { priceImport } from "../../api";

const { Dragger } = Upload;
const { Text, Title } = Typography;

type CellValue = string | number | null;

interface ParsedRow {
  sku: string;
  warehouse_id: number;
  unit_price: number | null;
  quantity: number | null;
  _raw: Record<string, string | number | null>;
}

interface ImportResult {
  success: number;
  failed: number;
  errors: string[];
}

const REQUIRED_FIELDS = ["SKU / 货号", "仓库", "含税单价", "库存数量"];
const FIELD_ALIASES: Record<string, string[]> = {
  sku: ["sku", "SKU", "货号", "商品编码", "型号", "part number", "part_number", "p/n"],
  warehouse_id: ["仓库", "仓库名", "仓库名称", "warehouse", "warehouse_id", "warehouseid"],
  unit_price: ["含税单价", "单价", "价格", "unit_price", "unitprice", "price", "含税价"],
  quantity: ["库存数量", "数量", "qty", "quantity", "stock", "库存"],
};

const WAREHOUSE_MAP: Record<string, number> = {
  "深圳": 1,
  "shenzhen": 1,
  "SZ": 1,
  "上海": 2,
  "shanghai": 2,
  "SH": 2,
  "北京": 3,
  "beijing": 3,
  "BJ": 3,
};

function normalizeWarehouse(val: string | number | null): number {
  if (val == null) return 1;
  if (typeof val === "number") return val;
  const s = String(val).trim();
  return (WAREHOUSE_MAP[s] ?? parseInt(s, 10)) || 1;
}

function matchField(colName: string, field: string): boolean {
  const aliases = FIELD_ALIASES[field] ?? [field];
  const normalized = colName.trim().toLowerCase();
  return aliases.some((a) => normalized === a.toLowerCase() || normalized.includes(a.toLowerCase()));
}

function detectFields(headers: string[]): Record<string, string | null> {
  const mapping: Record<string, string | null> = {};
  for (const field of REQUIRED_FIELDS) {
    const found = headers.find((h) => matchField(h, field));
    mapping[field] = found ?? null;
  }
  return mapping;
}

function normalizeCell(value: unknown): CellValue {
  if (value == null) return null;
  if (typeof value === "number") return value;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value).trim();
}

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
      continue;
    }
    if (char === '"') {
      quoted = !quoted;
      continue;
    }
    if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
      continue;
    }
    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }
    cell += char;
  }
  if (cell || row.length) {
    row.push(cell.trim());
    rows.push(row);
  }
  return rows;
}

export default function PriceImport() {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [rawData, setRawData] = useState<CellValue[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string | null>>({});
  const [previewRows, setPreviewRows] = useState<ParsedRow[]>([]);
  const [step, setStep] = useState<"upload" | "mapping" | "preview" | "result">("upload");
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  const parseFile = useCallback(async (file: File) => {
    const fileName = file.name.toLowerCase();
    const rows: CellValue[][] = fileName.endsWith(".csv")
      ? parseCsvRows(await file.text())
      : ((await readXlsxFile(file))[0]?.data ?? []).map((row: ExcelRow) => row.map(normalizeCell));
    if (rows.length < 2) {
      message.error("文件数据少于2行，请检查格式");
      return;
    }
    const hdrs = rows[0].map((cell) => String(cell ?? "").trim());
    const dataRows = rows.slice(1).filter((r) => r.some((c) => c != null && String(c).trim() !== ""));
    setHeaders(hdrs);
    setRawData(dataRows);
    setFieldMapping(detectFields(hdrs));
    setStep("mapping");
    message.success(`已解析 ${dataRows.length} 行数据`);
  }, []);

  const uploadProps: UploadProps = {
    name: "file",
    fileList,
    accept: ".xlsx,.csv",
    beforeUpload: (f) => {
      parseFile(f as File);
      return false;
    },
    onChange: ({ fileList: fl }) => setFileList(fl),
    onRemove: () => {
      setFileList([]);
      setRawData([]);
      setHeaders([]);
      setFieldMapping({});
      setPreviewRows([]);
      setStep("upload");
    },
  };

  const handleMappingConfirm = () => {
    const { sku, warehouse_id, unit_price, quantity } = fieldMapping;
    if (!sku || !warehouse_id) {
      message.error("请至少映射「SKU」和「仓库」字段");
      return;
    }

    const skuIdx = headers.indexOf(sku);
    const whIdx = headers.indexOf(warehouse_id);
    const priceIdx = unit_price ? headers.indexOf(unit_price) : -1;
    const qtyIdx = quantity ? headers.indexOf(quantity) : -1;

    const parsed: ParsedRow[] = rawData.slice(0, 10).map((row) => ({
      sku: String(row[skuIdx] ?? "").trim(),
      warehouse_id: normalizeWarehouse(row[whIdx]),
      unit_price: priceIdx >= 0 ? parseFloat(String(row[priceIdx] ?? "")) || null : null,
      quantity: qtyIdx >= 0 ? parseInt(String(row[qtyIdx] ?? ""), 10) || null : null,
      _raw: Object.fromEntries(headers.map((h, i) => [h, row[i] ?? null])),
    }));

    setPreviewRows(parsed);
    setStep("preview");
  };

  const handleImport = async () => {
    const { sku, warehouse_id, unit_price, quantity } = fieldMapping;
    if (!sku || !warehouse_id) {
      message.error("字段映射不完整");
      return;
    }

    const skuIdx = headers.indexOf(sku);
    const whIdx = headers.indexOf(warehouse_id);
    const priceIdx = unit_price ? headers.indexOf(unit_price) : -1;
    const qtyIdx = quantity ? headers.indexOf(quantity) : -1;

    const items = rawData.map((row) => ({
      sku: String(row[skuIdx] ?? "").trim(),
      warehouse_id: normalizeWarehouse(row[whIdx]),
      unit_price: priceIdx >= 0 ? parseFloat(String(row[priceIdx] ?? "")) || 0 : 0,
      quantity: qtyIdx >= 0 ? parseInt(String(row[qtyIdx] ?? ""), 10) || 0 : 0,
    })).filter((r) => r.sku !== "");

    if (items.length === 0) {
      message.error("没有有效数据可导入");
      return;
    }

    setImporting(true);
    try {
      const resp = await priceImport(items);
      if (resp.data.code === 0) {
        setResult(resp.data.data);
        setStep("result");
        message.success("导入完成");
      } else {
        message.error("导入失败");
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { msg?: string } } };
      message.error(err?.response?.data?.msg || "导入请求失败");
    } finally {
      setImporting(false);
    }
  };

  const previewColumns = [
    { title: "SKU", dataIndex: "sku", key: "sku" },
    { title: "仓库ID", dataIndex: "warehouse_id", key: "warehouse_id" },
    { title: "含税单价", dataIndex: "unit_price", key: "unit_price" },
    { title: "库存数量", dataIndex: "quantity", key: "quantity" },
  ];

  const rawPreviewColumns = headers.map((h) => ({ title: h, dataIndex: h, key: h, width: 120 }));

  return (
    <div>
      <Title level={4}>价格数据导入</Title>

      {/* Step 1: Upload */}
      {step === "upload" && (
        <Card>
          <Dragger {...uploadProps} style={{ padding: "40px 0" }}>
            <p><InboxOutlined style={{ fontSize: 48, color: "#1677ff" }} /></p>
            <p style={{ fontSize: 16, marginTop: 16 }}>点击或拖拽上传 Excel / CSV 文件</p>
            <p style={{ color: "#888" }}>支持 .xlsx、.csv 格式</p>
          </Dragger>
        </Card>
      )}

      {/* Step 2: Field Mapping */}
      {step === "mapping" && (
        <Card
          title="字段映射"
          extra={<Button onClick={() => { setStep("upload"); setFileList([]); setRawData([]); }}>重新上传</Button>}
        >
          <Alert
            message="请将文件列名映射到系统字段。系统会尝试自动识别，也可以手动选择对应列。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            {REQUIRED_FIELDS.map((field) => (
              <div key={field} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Text strong style={{ width: 100 }}>{field}</Text>
                <Select
                  placeholder="选择对应列名"
                  allowClear
                  style={{ width: 280 }}
                  value={fieldMapping[field]}
                  onChange={(val) => setFieldMapping((prev) => ({ ...prev, [field]: val }))}
                  options={headers.map((h) => ({ value: h, label: h }))}
                />
                {fieldMapping[field] && <StatusTag tone="success">已映射</StatusTag>}
              </div>
            ))}
          </Space>
          <Divider />
          <Space>
            <Button type="primary" onClick={handleMappingConfirm}>预览数据</Button>
          </Space>
        </Card>
      )}

      {/* Step 3: Preview */}
      {step === "preview" && (
        <Card
          title="数据预览（前10行）"
          extra={
            <Space>
              <Button onClick={() => setStep("mapping")}>返回修改映射</Button>
              <Button type="primary" loading={importing} onClick={handleImport} icon={<CloudUploadOutlined />}>
                执行导入（{rawData.length} 行）
              </Button>
            </Space>
          }
        >
          <Alert
            message={`共 ${rawData.length} 行数据待导入。确认无误后点击「执行导入」。`}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Table
            rowKey={(_, i) => String(i)}
            columns={previewColumns}
            dataSource={previewRows}
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
          {headers.length > 0 && (
            <>
              <Divider titlePlacement="left">原始数据预览</Divider>
              <Table
                rowKey={(_, i) => String(i)}
                columns={rawPreviewColumns}
                dataSource={previewRows.map((r) => r._raw)}
                pagination={false}
                size="small"
                scroll={{ x: headers.length * 120 }}
              />
            </>
          )}
        </Card>
      )}

      {/* Step 4: Result */}
      {step === "result" && result && (
        <Card>
          <Result
            icon={result.failed === 0 ? <CheckCircleOutlined /> : <CheckCircleOutlined style={{ color: "#faad14" }} />}
            title="导入完成"
            subTitle={`成功 ${result.success} 条，失败 ${result.failed} 条`}
            extra={
              <Space direction="vertical">
                {result.errors.length > 0 && (
                  <Alert
                    type="error"
                    message="失败记录"
                    description={
                      <ul style={{ margin: 0, paddingLeft: 20, maxHeight: 300, overflow: "auto" }}>
                        {result.errors.slice(0, 50).map((e, i) => (
                          <li key={i}><Text code>{e}</Text></li>
                        ))}
                        {result.errors.length > 50 && (
                          <li>…还有 {result.errors.length - 50} 条错误</li>
                        )}
                      </ul>
                    }
                    style={{ maxWidth: 600, textAlign: "left" }}
                  />
                )}
                <Space>
                  <Button onClick={() => {
                    setStep("upload");
                    setFileList([]);
                    setRawData([]);
                    setHeaders([]);
                    setFieldMapping({});
                    setPreviewRows([]);
                    setResult(null);
                  }}>
                    继续导入
                  </Button>
                </Space>
              </Space>
            }
          />
        </Card>
      )}
    </div>
  );
}
