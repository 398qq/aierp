// CustomerDetailDrawer — 钉钉风格客户详情抽屉
// 卡片式信息 + 快捷操作栏 + 经营数据
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Row,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  EditOutlined,
  EyeOutlined,
  MailOutlined,
  PhoneOutlined,
  ShoppingCartOutlined,
  SwapOutlined,
  EnvironmentOutlined,
  BankOutlined,
  CreditCardOutlined,
  FileTextOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { Customer, CustomerStats } from "../../types";
import { formatDate, getHealthColor, getLevelColor } from "./constants";

const { Text, Link } = Typography;

interface Props {
  open: boolean;
  loading: boolean;
  customer: Customer | null;
  stats: CustomerStats | null;
  onClose: () => void;
  onVendAsSupplier: (customer: Customer) => void;
}

export default function CustomerDetailDrawer({
  open,
  loading,
  customer,
  stats,
  onClose,
  onVendAsSupplier,
}: Props) {
  const navigate = useNavigate();
  return (
    <Drawer
      title={customer?.name || "客户详情"}
      width={680}
      placement="right"
      open={open}
      onClose={onClose}
      footer={
        customer ? (
          <Space style={{ width: "100%", justifyContent: "flex-end" }}>
            <Button
              icon={<EditOutlined />}
              onClick={() => navigate(`/customers/${customer.id}/edit`)}
            >
              编辑
            </Button>
            <Button
              icon={<ShoppingCartOutlined />}
              type="primary"
              onClick={() => navigate(`/sales/orders/new?customer_id=${customer.id}`)}
            >
              建订单
            </Button>
            <Button
              icon={<PhoneOutlined />}
              onClick={() => navigate(`/customers/${customer.id}?tab=followups`)}
            >
              建跟进
            </Button>
            <Button icon={<SwapOutlined />} onClick={() => onVendAsSupplier(customer)}>
              转供应商
            </Button>
          </Space>
        ) : null
      }
    >
      {loading ? (
        <Card loading />
      ) : !customer ? (
        <Empty description="暂无详情" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* ── 客户身份卡 ── */}
          <Card
            size="small"
            style={{
              background: "linear-gradient(135deg, #f0f5ff 0%, #e6f4ff 100%)",
              border: "1px solid #91caff",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 12,
              }}
            >
              <div style={{ flex: 1 }}>
                <Space size={8} style={{ marginBottom: 4 }}>
                  <Link
                    strong
                    style={{ fontSize: 15 }}
                    onClick={() => navigate(`/customers/${customer.id}`)}
                  >
                    {customer.name}
                  </Link>
                  {customer.level && (
                    <StatusTag tone={getLevelColor(customer.level)}>{customer.level}级</StatusTag>
                  )}
                  {customer.health_score != null && (
                    <StatusTag tone={getHealthColor(customer.health_score)}>
                      健康{customer.health_score}
                    </StatusTag>
                  )}
                </Space>
                <div style={{ color: "#595959", fontSize: 12, marginTop: 2 }}>
                  {[customer.short_name, customer.industry, customer.region]
                    .filter(Boolean)
                    .join(" · ") || "暂无分类信息"}
                </div>
                <Space size={[4, 6]} wrap style={{ marginTop: 6 }}>
                  {customer.contact_person && (
                    <Tag icon={<UserOutlined />} color="blue">
                      {customer.contact_person}
                    </Tag>
                  )}
                  {customer.phone && (
                    <Tag icon={<PhoneOutlined />} color="green">
                      {customer.phone}
                    </Tag>
                  )}
                  {customer.email && (
                    <Tag icon={<MailOutlined />} color="orange">
                      {customer.email}
                    </Tag>
                  )}
                </Space>
              </div>
              <Button
                size="small"
                type="link"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/customers/${customer.id}`)}
              >
                完整详情
              </Button>
            </div>
          </Card>

          {/* ── 商务概况 ── */}
          <Card size="small" title="商务概况" styles={{ body: { padding: "8px 12px" } }}>
            <Row gutter={[8, 6]}>
              <Col span={8}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  付款条件
                </Text>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{customer.payment_terms || "-"}</div>
              </Col>
              <Col span={8}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  币种
                </Text>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{customer.currency || "CNY"}</div>
              </Col>
              <Col span={8}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  价格等级
                </Text>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{customer.price_tier || "-"}</div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  信用等级
                </Text>
                <div>
                  {customer.credit_level || "-"}
                  {customer.credit_limit ? (
                    <span style={{ color: "#1677ff", marginLeft: 6 }}>
                      ¥{customer.credit_limit.toLocaleString()}
                    </span>
                  ) : (
                    ""
                  )}
                </div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  贸易条款
                </Text>
                <div style={{ fontSize: 13, fontWeight: 500 }}>
                  {customer.default_incoterm || "-"}
                </div>
              </Col>
            </Row>
          </Card>

          {/* ── 税务银行 ── */}
          <Card
            size="small"
            title={
              <Space size={4}>
                <BankOutlined />
                税务与银行
              </Space>
            }
            styles={{ body: { padding: "8px 12px" } }}
          >
            <Row gutter={[8, 4]}>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  税号
                </Text>
                <div style={{ fontSize: 13 }}>{customer.tax_id || "-"}</div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  发票抬头
                </Text>
                <div style={{ fontSize: 13 }}>{customer.invoice_title || "-"}</div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  开户行
                </Text>
                <div style={{ fontSize: 13 }}>{customer.bank_name || "-"}</div>
              </Col>
              <Col span={12}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  银行账号
                </Text>
                <div style={{ fontSize: 13 }}>{customer.bank_account || "-"}</div>
              </Col>
            </Row>
          </Card>

          {/* ── 地址 ── */}
          {(customer.address || customer.delivery_address) && (
            <Card
              size="small"
              title={
                <Space size={4}>
                  <EnvironmentOutlined />
                  地址
                </Space>
              }
              styles={{ body: { padding: "8px 12px" } }}
            >
              {customer.address && (
                <div style={{ fontSize: 12, marginBottom: 4 }}>注册：{customer.address}</div>
              )}
              {customer.delivery_address && (
                <div style={{ fontSize: 12 }}>收货：{customer.delivery_address}</div>
              )}
            </Card>
          )}

          {/* ── 经营指标 ── */}
          {stats && (
            <Card size="small" title="经营指标" styles={{ body: { padding: "8px 12px" } }}>
              <Row gutter={[8, 8]}>
                <Col span={8}>
                  <Statistic
                    title="订单数"
                    value={stats.order_count}
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="总营收"
                    value={stats.total_revenue}
                    precision={0}
                    prefix="¥"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="信用占用"
                    value={stats.credit_usage_pct}
                    precision={1}
                    suffix="%"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
              </Row>
            </Card>
          )}

          {/* ── 备注 ── */}
          {customer.notes && (
            <Card
              size="small"
              title={
                <Space size={4}>
                  <FileTextOutlined />
                  备注
                </Space>
              }
              styles={{ body: { padding: "8px 12px" } }}
            >
              <Text style={{ fontSize: 12 }}>{customer.notes}</Text>
            </Card>
          )}
        </div>
      )}
    </Drawer>
  );
}
