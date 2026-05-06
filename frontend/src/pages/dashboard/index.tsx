import { useEffect, useState } from "react";
import { Row, Col, Card, Statistic, Typography } from "antd";
import {
  TeamOutlined, DollarOutlined, ShoppingCartOutlined, AlertOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../store/auth";
import { getCustomers, getSalesOrders } from "../../api";

const { Title } = Typography;

export default function Dashboard() {
  const username = useAuthStore((s) => s.username);
  const [customerCount, setCustomerCount] = useState(0);
  const [orderCount, setOrderCount] = useState(0);

  useEffect(() => {
    Promise.all([
      getCustomers({ page: 1, page_size: 1 }),
      getSalesOrders({ page: 1, page_size: 1 }),
    ]).then(([custResp, orderResp]) => {
      setCustomerCount(custResp.data.data.total || 0);
      setOrderCount(orderResp.data.data.total || 0);
    }).catch(() => {});
  }, []);

  return (
    <div>
      <Title level={4}>欢迎回来，{username}</Title>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="客户总数" value={customerCount} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="销售订单" value={orderCount} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="本月销售(CNY)" value={0} prefix={<DollarOutlined />} precision={2} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="库存预警" value={0} prefix={<AlertOutlined />} valueStyle={{ color: "#cf1322" }} />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Title level={5}>AI 系统状态</Title>
        <p>AI 分析/助手: Qwen2.5-7B · 嵌入: bge-large-zh</p>
      </Card>
    </div>
  );
}
