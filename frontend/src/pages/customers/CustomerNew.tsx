import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Card, Button, Form, Space } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { createCustomer } from "../../api";
import { useAuthStore } from "../../store/auth";
import CustomerAIRecognizer from "./CustomerAIRecognizer";
import CustomerFormFields from "./CustomerForm";

export function getDefaultCustomerOwner(username?: string | null) {
  return username?.trim() || "";
}

export default function CustomerNew() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const username = useAuthStore((state) => state.username);

  useEffect(() => {
    const defaultOwner = getDefaultCustomerOwner(username);
    const currentOwner = form.getFieldValue("owner");
    if (defaultOwner && !currentOwner) {
      form.setFieldValue("owner", defaultOwner);
    }
  }, [form, username]);

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
      <Card title="新建客户" extra={<CustomerAIRecognizer form={form} />} style={{ maxWidth: 800 }}>
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
