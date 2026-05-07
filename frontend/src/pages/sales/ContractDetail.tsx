import { useEffect, useState } from "react";
import { Card, Descriptions, Tag, Spin, Alert, Row, Col, Table, Button, Space, Modal, Progress, Typography, List, Tooltip, Badge, Statistic } from "antd";
import { useParams } from "react-router-dom";
import {
  FileSearchOutlined,
  SafetyCertificateOutlined,
  AlertOutlined,
  DollarOutlined,
} from "@ant-design/icons";
import {
  getContract,
  extractContractTerms,
  assessContractRisk,
  scanContractExpiry,
  trackContractRebate,
} from "../../api";
import type {
  Contract,
  ContractExtraction,
  ContractRisk,
  ContractExpiry,
  ContractRebate,
} from "../../types";

const { Text, Paragraph } = Typography;

const statusColors: Record<string, string> = { draft: "default", active: "green", expired: "orange", terminated: "red" };

const importanceColors: Record<string, string> = { high: "red", medium: "orange", low: "blue" };
const riskFlagColors: Record<string, string> = { high: "red", medium: "orange", low: "green", none: "default" };
const riskLevelColors: Record<string, string> = { low: "green", medium: "orange", high: "red", critical: "#ff0000" };

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // --- AI modal states ---
  const [extraction, setExtraction] = useState<ContractExtraction | null>(null);
  const [extractionLoading, setExtractionLoading] = useState(false);
  const [extractionOpen, setExtractionOpen] = useState(false);

  const [risk, setRisk] = useState<ContractRisk | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskOpen, setRiskOpen] = useState(false);

  const [expiry, setExpiry] = useState<ContractExpiry | null>(null);
  const [expiryLoading, setExpiryLoading] = useState(false);
  const [expiryOpen, setExpiryOpen] = useState(false);

  const [rebate, setRebate] = useState<ContractRebate | null>(null);
  const [rebateLoading, setRebateLoading] = useState(false);
  const [rebateOpen, setRebateOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const resp = await getContract(Number(id));
        setData(resp.data.data);
      } catch { setError("加载失败"); }
      finally { setLoading(false); }
    })();
  }, [id]);

  // --- AI handlers ---
  const handleExtractTerms = async () => {
    setExtractionLoading(true);
    try {
      const resp = await extractContractTerms(Number(id));
      setExtraction(resp.data.data);
      setExtractionOpen(true);
    } catch { /* error handled in UI */ }
    finally { setExtractionLoading(false); }
  };

  const handleAssessRisk = async () => {
    setRiskLoading(true);
    try {
      const resp = await assessContractRisk(Number(id));
      setRisk(resp.data.data);
      setRiskOpen(true);
    } catch { /* error handled in UI */ }
    finally { setRiskLoading(false); }
  };

  const handleScanExpiry = async () => {
    setExpiryLoading(true);
    try {
      const resp = await scanContractExpiry();
      setExpiry(resp.data.data);
      setExpiryOpen(true);
    } catch { /* error handled in UI */ }
    finally { setExpiryLoading(false); }
  };

  const handleTrackRebate = async () => {
    setRebateLoading(true);
    try {
      const resp = await trackContractRebate(Number(id));
      setRebate(resp.data.data);
      setRebateOpen(true);
    } catch { /* error handled in UI */ }
    finally { setRebateLoading(false); }
  };

  if (loading) return <Spin />;
  if (error) return <Alert type="error" message={error} />;
  if (!data) return <Alert type="warning" message="未找到" />;

  return (
    <div>
      <Card title={`合同详情 - ${data.contract_no || `#${data.id}`}`} style={{ marginBottom: 24 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="合同号">{data.contract_no || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[data.status]}>{data.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="标题" span={2}>{data.title}</Descriptions.Item>
          <Descriptions.Item label="客户ID">{data.customer_id}</Descriptions.Item>
          <Descriptions.Item label="金额">¥{data.amount.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="签订日期">{data.signed_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="到期日期">{data.expire_date || "-"}</Descriptions.Item>
          <Descriptions.Item label="备注" span={2}>{data.notes || "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{data.created_at}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* --- AI Intelligence Toolbar --- */}
      <Card size="small" style={{ marginBottom: 24 }}>
        <Space wrap>
          <Tooltip title="提取合同核心条款，自动识别付款/交付/质保条款及缺失条款">
            <Button
              icon={<FileSearchOutlined />}
              loading={extractionLoading}
              onClick={handleExtractTerms}
            >
              条款提取
            </Button>
          </Tooltip>
          <Tooltip title="评估合同财务风险、法律风险与运营风险，提供谈判优先级建议">
            <Button
              icon={<SafetyCertificateOutlined />}
              loading={riskLoading}
              onClick={handleAssessRisk}
            >
              风险评估
            </Button>
          </Tooltip>
          <Tooltip title="扫描全量合同到期情况，识别高风险到期合同">
            <Button
              icon={<AlertOutlined />}
              loading={expiryLoading}
              onClick={handleScanExpiry}
            >
              到期预警
            </Button>
          </Tooltip>
          <Tooltip title="跟踪合同返利达成进度，发现增量销售机会">
            <Button
              icon={<DollarOutlined />}
              loading={rebateLoading}
              onClick={handleTrackRebate}
            >
              返利跟踪
            </Button>
          </Tooltip>
        </Space>
      </Card>

      {data.sales_order && (
        <Card title="关联订单" style={{ marginBottom: 24 }}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="订单号">{data.sales_order.order_no || "-"}</Descriptions.Item>
            <Descriptions.Item label="状态">{data.sales_order.status}</Descriptions.Item>
            <Descriptions.Item label="金额">¥{data.sales_order.total_amount.toFixed(2)}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Row gutter={24}>
        <Col span={12}>
          <Card title="关联发票" style={{ marginBottom: 24 }}>
            {data.invoices?.length ? (
              <Table rowKey="id" dataSource={data.invoices} pagination={false} columns={[
                { title: "发票号", dataIndex: "invoice_no" },
                { title: "金额", dataIndex: "amount", render: (v: number) => `¥${v.toFixed(2)}` },
                { title: "状态", dataIndex: "status" },
              ]} />
            ) : <Alert type="info" message="无关联发票" />}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="关联回款" style={{ marginBottom: 24 }}>
            {data.payments?.length ? (
              <Table rowKey="id" dataSource={data.payments} pagination={false} columns={[
                { title: "金额", dataIndex: "amount", render: (v: number) => `¥${v.toFixed(2)}` },
                { title: "方式", dataIndex: "payment_method" },
                { title: "状态", dataIndex: "status" },
              ]} />
            ) : <Alert type="info" message="无关联回款" />}
          </Card>
        </Col>
      </Row>

      {/* ================================================================ */}
      {/* Modal: 条款提取 (Contract Extraction)                               */}
      {/* ================================================================ */}
      <Modal
        title={<span><FileSearchOutlined /> 条款提取</span>}
        open={extractionOpen}
        onCancel={() => setExtractionOpen(false)}
        footer={null}
        width={900}
      >
        {extraction ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="合同类型">
                <Tag color="blue">{extraction.contract_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="整体风险">
                <Tag color={riskLevelColors[extraction.overall_risk] || "default"}>
                  {extraction.overall_risk}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="付款条款" span={2}>
                <Text>{extraction.payment_terms || "-"}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="交付条款" span={2}>
                <Text>{extraction.delivery_terms || "-"}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="质保条款" span={2}>
                <Text>{extraction.warranty_terms || "-"}</Text>
              </Descriptions.Item>
            </Descriptions>

            <Card title="关键条款" size="small">
              <Table
                rowKey={(_, i) => String(i)}
                dataSource={extraction.key_terms}
                pagination={false}
                size="small"
                columns={[
                  { title: "条款", dataIndex: "clause", width: 120 },
                  { title: "内容", dataIndex: "content" },
                  {
                    title: "重要性", dataIndex: "importance", width: 80,
                    render: (v: string) => <Tag color={importanceColors[v] || "default"}>{v}</Tag>,
                  },
                  {
                    title: "风险标记", dataIndex: "risk_flag", width: 80,
                    render: (v: string) => <Tag color={riskFlagColors[v] || "default"}>{v}</Tag>,
                  },
                ]}
              />
            </Card>

            {extraction.missing_clauses && extraction.missing_clauses.length > 0 && (
              <Card title="缺失条款" size="small" style={{ borderColor: "#faad14" }}>
                <List
                  size="small"
                  dataSource={extraction.missing_clauses}
                  renderItem={(item: string) => (
                    <List.Item>
                      <Badge status="warning" />
                      <Text style={{ marginLeft: 8 }}>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </Space>
        ) : (
          <Spin />
        )}
      </Modal>

      {/* ================================================================ */}
      {/* Modal: 风险评估 (Risk Assessment)                                   */}
      {/* ================================================================ */}
      <Modal
        title={<span><SafetyCertificateOutlined /> 风险评估</span>}
        open={riskOpen}
        onCancel={() => setRiskOpen(false)}
        footer={null}
        width={900}
      >
        {risk ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Row gutter={24} align="middle">
              <Col>
                <Progress
                  type="circle"
                  percent={risk.risk_score}
                  size={80}
                  strokeColor={
                    risk.risk_score >= 70 ? "#ff4d4f" :
                    risk.risk_score >= 40 ? "#faad14" :
                    "#52c41a"
                  }
                />
              </Col>
              <Col>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="风险等级">
                    <Tag color={riskLevelColors[risk.risk_level] || "default"}>{risk.risk_level}</Tag>
                  </Descriptions.Item>
                </Descriptions>
              </Col>
            </Row>

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="财务风险">
                <Paragraph style={{ margin: 0 }}>{risk.financial_risk || "-"}</Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="法律风险">
                <Paragraph style={{ margin: 0 }}>{risk.legal_risk || "-"}</Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="运营风险">
                <Paragraph style={{ margin: 0 }}>{risk.operational_risk || "-"}</Paragraph>
              </Descriptions.Item>
            </Descriptions>

            <Card title="风险清单" size="small">
              <Table
                rowKey={(_, i) => String(i)}
                dataSource={risk.risk_items}
                pagination={false}
                size="small"
                columns={[
                  { title: "事项", dataIndex: "item", width: 120 },
                  { title: "风险", dataIndex: "risk", width: 80 },
                  { title: "影响", dataIndex: "impact" },
                  { title: "缓解措施", dataIndex: "mitigation" },
                ]}
              />
            </Card>

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="建议">
                <Paragraph style={{ margin: 0 }}>{risk.recommendation || "-"}</Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="谈判优先级">
                {risk.negotiation_priority?.length ? (
                  <List
                    size="small"
                    dataSource={risk.negotiation_priority}
                    renderItem={(item: string, i: number) => (
                      <List.Item style={{ padding: "4px 0" }}>
                        <Badge count={i + 1} style={{ backgroundColor: "#1677ff" }} />
                        <Text style={{ marginLeft: 16 }}>{item}</Text>
                      </List.Item>
                    )}
                  />
                ) : <Text type="secondary">-</Text>}
              </Descriptions.Item>
            </Descriptions>
          </Space>
        ) : (
          <Spin />
        )}
      </Modal>

      {/* ================================================================ */}
      {/* Modal: 到期预警 (Expiry Alerts)                                     */}
      {/* ================================================================ */}
      <Modal
        title={<span><AlertOutlined /> 到期预警</span>}
        open={expiryOpen}
        onCancel={() => setExpiryOpen(false)}
        footer={null}
        width={1000}
      >
        {expiry ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Row gutter={24}>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="即将到期合同"
                    value={expiry.expiring_soon?.length ?? 0}
                    suffix="份"
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="风险金额"
                    value={expiry.total_at_risk_amount}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#cf1322" }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="高风险到期"
                    value={expiry.high_risk_expiries?.length ?? 0}
                    suffix="项"
                    valueStyle={{ color: "#ff4d4f" }}
                  />
                </Card>
              </Col>
            </Row>

            <Card title="到期合同清单" size="small">
              <Table
                rowKey={(_, i) => String(i)}
                dataSource={expiry.expiring_soon}
                pagination={false}
                size="small"
                columns={[
                  { title: "合同号", dataIndex: "contract_no", width: 120 },
                  { title: "客户", dataIndex: "customer_name", width: 120 },
                  {
                    title: "金额", dataIndex: "amount", width: 120,
                    render: (v: number) => `¥${v.toFixed(2)}`,
                  },
                  { title: "到期日期", dataIndex: "expire_date", width: 110 },
                  {
                    title: "剩余天数", dataIndex: "days_left", width: 90,
                    render: (v: number) => (
                      <Tag color={v <= 30 ? "red" : v <= 60 ? "orange" : "blue"}>{v}天</Tag>
                    ),
                  },
                  {
                    title: "续约概率", dataIndex: "renewal_probability", width: 90,
                    render: (v: number) => <Progress percent={v} size="small" />,
                  },
                  { title: "建议行动", dataIndex: "action" },
                ]}
              />
            </Card>

            {expiry.high_risk_expiries?.length > 0 && (
              <Card title="高风险到期" size="small" style={{ borderColor: "#ff4d4f" }}>
                <List
                  size="small"
                  dataSource={expiry.high_risk_expiries}
                  renderItem={(item: string) => (
                    <List.Item>
                      <Badge status="error" />
                      <Text style={{ marginLeft: 8 }}>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {expiry.priority_actions?.length > 0 && (
              <Card title="优先行动" size="small">
                <List
                  size="small"
                  dataSource={expiry.priority_actions}
                  renderItem={(item: string, i: number) => (
                    <List.Item style={{ padding: "4px 0" }}>
                      <Badge count={i + 1} style={{ backgroundColor: "#1677ff" }} />
                      <Text style={{ marginLeft: 16 }}>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </Space>
        ) : (
          <Spin />
        )}
      </Modal>

      {/* ================================================================ */}
      {/* Modal: 返利跟踪 (Rebate Tracking)                                    */}
      {/* ================================================================ */}
      <Modal
        title={<span><DollarOutlined /> 返利跟踪</span>}
        open={rebateOpen}
        onCancel={() => setRebateOpen(false)}
        footer={null}
        width={800}
      >
        {rebate ? (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Row gutter={24}>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="已达成返利"
                    value={rebate.rebate_achieved}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#3f8600" }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="预计返利"
                    value={rebate.rebate_projected}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: "#1677ff" }}
                  />
                </Card>
              </Col>
            </Row>

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="层级进度">
                <Paragraph style={{ margin: 0 }}>{rebate.rebate_tier_progress || "-"}</Paragraph>
              </Descriptions.Item>
              <Descriptions.Item label="距下一层级">
                <Text style={{ color: "#faad14", fontWeight: "bold" }}>
                  ¥{rebate.gap_to_next_tier.toFixed(2)}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {rebate.upsell_opportunities?.length > 0 && (
              <Card title="增量销售机会" size="small">
                <List
                  size="small"
                  dataSource={rebate.upsell_opportunities}
                  renderItem={(item: string) => (
                    <List.Item>
                      <Badge status="success" />
                      <Text style={{ marginLeft: 8 }}>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {rebate.optimization_suggestions?.length > 0 && (
              <Card title="优化建议" size="small">
                <List
                  size="small"
                  dataSource={rebate.optimization_suggestions}
                  renderItem={(item: string, i: number) => (
                    <List.Item style={{ padding: "4px 0" }}>
                      <Badge count={i + 1} style={{ backgroundColor: "#1677ff" }} />
                      <Text style={{ marginLeft: 16 }}>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </Space>
        ) : (
          <Spin />
        )}
      </Modal>
    </div>
  );
}