// CustomerDetailDrawer — right-side drawer showing customer profile,
// basic fields, business metrics, and quick action buttons.

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
} from "antd";
import { EyeOutlined, PhoneOutlined, ShoppingCartOutlined, SwapOutlined } from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { Customer, CustomerStats } from "../../types";
import { formatDate, getHealthColor, getLevelColor } from "./constants";

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
      title={customer ? `客户详情 - ${customer.name}` : "客户详情"}
      width={700}
      placement="right"
      open={open}
      onClose={onClose}
    >
      {loading ? (
        <Card loading />
      ) : !customer ? (
        <Empty description="暂无详情" />
      ) : (
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space wrap>
            <StatusTag tone={getLevelColor(customer.level)}>等级 {customer.level || "-"}</StatusTag>
            <StatusTag>行业 {customer.industry || "-"}</StatusTag>
            <StatusTag>区域 {customer.region || "-"}</StatusTag>
            <StatusTag tone={getHealthColor(customer.health_score)}>
              健康度 {customer.health_score ?? "-"}
            </StatusTag>
          </Space>

          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="客户编码">{customer.code || "-"}</Descriptions.Item>
            <Descriptions.Item label="客户简称">{customer.short_name || "-"}</Descriptions.Item>
            <Descriptions.Item label="负责人">{customer.owner || "-"}</Descriptions.Item>
            <Descriptions.Item label="联系人">{customer.contact_person || "-"}</Descriptions.Item>
            <Descriptions.Item label="电话">{customer.phone || "-"}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{customer.email || "-"}</Descriptions.Item>
            <Descriptions.Item label="来源">{customer.source || "-"}</Descriptions.Item>
            <Descriptions.Item label="信用等级">
              {customer.credit_level || "-"}
              {customer.credit_limit ? ` / ¥${customer.credit_limit.toLocaleString()}` : ""}
            </Descriptions.Item>
            <Descriptions.Item label="税号">{customer.tax_id || "-"}</Descriptions.Item>
            <Descriptions.Item label="付款">{customer.payment_terms || "-"}</Descriptions.Item>
            <Descriptions.Item label="币种">{customer.currency || "CNY"}</Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {formatDate(customer.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="最近联系">
              {formatDate(customer.last_contacted_at)}
            </Descriptions.Item>
            <Descriptions.Item label="地址" span={2}>
              {customer.address || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="收货地址" span={2}>
              {customer.delivery_address || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>
              {customer.notes || "-"}
            </Descriptions.Item>
          </Descriptions>

          <Divider style={{ margin: "4px 0" }}>经营指标</Divider>
          {!stats ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无指标数据" />
          ) : (
            <Row gutter={[10, 10]}>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="订单数" value={stats.order_count} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="总营收" value={stats.total_revenue} precision={2} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="信用占用%" value={stats.credit_usage_pct} precision={1} />
                </Card>
              </Col>
            </Row>
          )}

          <Divider style={{ margin: "4px 0" }}>快速动作</Divider>
          <Space wrap>
            <Button icon={<EyeOutlined />} onClick={() => navigate(`/customers/${customer.id}`)}>
              完整详情
            </Button>
            <Button
              icon={<ShoppingCartOutlined />}
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
        </Space>
      )}
    </Drawer>
  );
}
