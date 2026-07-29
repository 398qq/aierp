import { useState } from "react";
import { Card, Descriptions, Typography, Tabs, Button, Form, Input, Space, message } from "antd";
import { useAuthStore } from "../../store/auth";
import { changePassword } from "../../api";
import AlertRulesTable from "./AlertRulesTable";
import AlertEventsTable from "./AlertEventsTable";
import LevelRulesTable from "./LevelRulesTable";

const { Title } = Typography;

export default function Settings() {
  const username = useAuthStore((s) => s.username);
  const [activeTab, setActiveTab] = useState("account");
  const [passwordForm] = Form.useForm();
  const [passwordSaving, setPasswordSaving] = useState(false);

  const handleChangePassword = async (values: {
    current_password: string;
    new_password: string;
  }) => {
    setPasswordSaving(true);
    try {
      await changePassword(values.current_password, values.new_password);
      message.success("密码已更新");
      passwordForm.resetFields();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.response?.data?.msg || "修改密码失败");
    } finally {
      setPasswordSaving(false);
    }
  };

  const tabItems = [
    {
      key: "account",
      label: "账户信息",
      children: (
        <Space direction="vertical" size={16} style={{ width: "100%", maxWidth: 720 }}>
          <Card>
            <Descriptions title="账户信息" column={1}>
              <Descriptions.Item label="用户名">{username}</Descriptions.Item>
              <Descriptions.Item label="角色">管理员</Descriptions.Item>
              <Descriptions.Item label="AI 分析模型">
                Qwen/Qwen2.5-7B-Instruct (RFM/流失/建议)
              </Descriptions.Item>
              <Descriptions.Item label="AI 助手模型">
                Qwen/Qwen2.5-7B-Instruct (Chat)
              </Descriptions.Item>
              <Descriptions.Item label="嵌入模型">BAAI/bge-large-zh-v1.5</Descriptions.Item>
              <Descriptions.Item label="数据库">PostgreSQL 16 + pgvector</Descriptions.Item>
              <Descriptions.Item label="后端框架">FastAPI + SQLAlchemy 2.0</Descriptions.Item>
              <Descriptions.Item label="前端框架">
                React 19 + TypeScript + Ant Design
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="修改当前密码">
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handleChangePassword}
              autoComplete="off"
              style={{ maxWidth: 420 }}
            >
              <Form.Item
                label="当前密码"
                name="current_password"
                rules={[{ required: true, message: "请输入当前密码" }]}
              >
                <Input.Password autoComplete="current-password" />
              </Form.Item>
              <Form.Item
                label="新密码"
                name="new_password"
                rules={[
                  { required: true, message: "请输入新密码" },
                  { min: 8, message: "新密码至少 8 位" },
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item
                label="确认新密码"
                name="confirm_password"
                dependencies={["new_password"]}
                rules={[
                  { required: true, message: "请再次输入新密码" },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue("new_password") === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error("两次输入的新密码不一致"));
                    },
                  }),
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={passwordSaving}>
                更新密码
              </Button>
            </Form>
          </Card>
        </Space>
      ),
    },
    {
      key: "alert-rules",
      label: "预警规则",
      children: <AlertRulesTable />,
    },
    {
      key: "alert-events",
      label: "预警事件",
      children: <AlertEventsTable />,
    },
    {
      key: "level-rules",
      label: "客户分级",
      children: <LevelRulesTable />,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        系统设置
      </Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
}
