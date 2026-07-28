import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App, Button, Space } from "antd";
import { ProForm } from "@ant-design/pro-components";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { createCustomer } from "../../api";
import { useAuthStore } from "../../store/auth";
import CustomerAIRecognizer from "./CustomerAIRecognizer";
import CustomerFormFields from "./CustomerForm";
import CustomerModuleShell from "./CustomerModuleShell";

export function getDefaultCustomerOwner(username?: string | null) {
  return username?.trim() || "";
}

export default function CustomerNew() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [form] = ProForm.useForm();
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
      setLoading(false);
      navigate(`/customers/${newId}`);
    } catch (err: any) {
      message.error(
        err?.response?.data?.msg || err?.response?.data?.detail || "创建失败，请检查字段",
      );
      setLoading(false);
    }
  };

  return (
    <CustomerModuleShell
      title="新建客户"
      subtitle="客户主数据录入"
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/customers")}>
          返回列表
        </Button>
      }
    >
      <ProForm
        form={form}
        layout="vertical"
        onFinish={onFinish}
        submitter={{
          render: (_, defaultSubmitter) => (
            <div style={{ marginTop: 24, textAlign: "right" }}>
              <Space>
                <Button onClick={() => navigate("/customers")}>取消</Button>
                {defaultSubmitter}
              </Space>
            </div>
          ),
        }}
      >
        <CustomerAIRecognizer form={form} />
        <CustomerFormFields />
      </ProForm>
    </CustomerModuleShell>
  );
}
