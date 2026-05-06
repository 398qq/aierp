import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Button, Form, message, Space } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { createCustomer } from "../../api";
import CustomerFormFields from "./CustomerForm";

export default function CustomerNew() {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const resp = await createCustomer(values);
      const newId = (resp.data.data as { id: number }).id;
      message.success("客户创建成功");
      navigate(`/customers/${newId}`);
    } catch {
      message.error("创建失败，请检查字段");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/customers")}>返回列表</Button>
      </Space>
      <Card title="新建客户" style={{ maxWidth: 800 }}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <CustomerFormFields />
          <Form.Item style={{ marginTop: 24, textAlign: "right" }}>
            <Space>
              <Button onClick={() => navigate("/customers")}>取消</Button>
              <Button type="primary" htmlType="submit" loading={loading}>保存</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
