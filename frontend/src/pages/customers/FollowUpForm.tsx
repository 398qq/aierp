/**
 * 客户跟进记录表单页面（新建/编辑）
 * 路由: /customers/:customerId/follow-ups/new
 *      /customers/:customerId/follow-ups/:followupId/edit
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Form, Input, Select, DatePicker, Button, Card, Spin, message, Space } from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { createFollowUp, updateFollowUp, getFollowUps } from "../../api";
import type { FollowUp } from "../../types";

const { TextArea } = Input;

// 跟进方式选项
const METHOD_OPTIONS = [
  { value: "phone", label: "电话拜访" },
  { value: "visit", label: "上门拜访" },
  { value: "video", label: "视频会议" },
  { value: "email", label: "邮件" },
  { value: "other", label: "其他" },
];

// 状态选项
const STATUS_OPTIONS = [
  { value: "planned", label: "计划中" },
  { value: "in_progress", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "cancelled", label: "已取消" },
];

// 优先级选项
const PRIORITY_OPTIONS = [
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

export default function FollowUpForm() {
  const { customerId, followupId } = useParams<{ customerId: string; followupId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);

  const custId = Number(customerId);
  const followupIdNum = followupId ? Number(followupId) : null;
  const isEdit = !!followupIdNum && !isNaN(followupIdNum);

  // 加载编辑数据
  useEffect(() => {
    if (isEdit && custId && followupIdNum) {
      setInitialLoading(true);
      getFollowUps(custId)
        .then((resp) => {
          const result = resp.data;
          let items: FollowUp[] = [];
          if (Array.isArray(result.data)) {
            items = result.data;
          } else if (result.data && typeof result.data === "object") {
            const d = result.data as { list?: FollowUp[]; items?: FollowUp[] };
            items = d.list || d.items || [];
          }
          const found = items.find((item) => item.id === followupIdNum);
          if (found) {
            // 设置表单值
            form.setFieldsValue({
              ...found,
              planned_at: found.planned_at ? dayjs(found.planned_at) : null,
              completed_at: found.completed_at ? dayjs(found.completed_at) : null,
            });
          }
        })
        .catch(() => {
          message.error("加载跟进记录失败");
        })
        .finally(() => {
          setInitialLoading(false);
        });
    }
  }, [isEdit, custId, followupIdNum, form]);

  // 提交表单
  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const submitData = {
        ...values,
        planned_at: values.planned_at ? (values.planned_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss") : null,
        completed_at: values.completed_at ? (values.completed_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss") : null,
      };

      if (isEdit && followupIdNum) {
        await updateFollowUp(custId, followupIdNum, submitData);
        message.success("更新成功");
      } else {
        await createFollowUp(custId, submitData);
        message.success("创建成功");
      }
      navigate(`/customers/${custId}/follow-ups`);
    } catch {
      message.error("保存失败");
    } finally {
      setLoading(false);
    }
  };

  // 返回列表
  const handleBack = () => {
    navigate(`/customers/${custId}/follow-ups`);
  };

  // 无效的客户ID
  if (!customerId || isNaN(custId)) {
    return (
      <Card>
        <Space direction="vertical" style={{ width: "100%", textAlign: "center" }}>
          <p>请先选择客户</p>
          <Button onClick={() => navigate("/customers")}>返回客户列表</Button>
        </Space>
      </Card>
    );
  }

  if (isEdit && initialLoading) {
    return <Spin style={{ display: "block", margin: "100px auto" }} />;
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
          返回列表
        </Button>
      </Space>

      <Card title={isEdit ? "编辑跟进记录" : "新建跟进记录"}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            status: "planned",
            priority: "medium",
          }}
        >
          <Form.Item name="method" label="跟进方式" rules={[{ required: true, message: "请选择跟进方式" }]}>
            <Select options={METHOD_OPTIONS} placeholder="选择跟进方式" />
          </Form.Item>

          <Form.Item name="status" label="状态" rules={[{ required: true, message: "请选择状态" }]}>
            <Select options={STATUS_OPTIONS} placeholder="选择状态" />
          </Form.Item>

          <Form.Item name="content" label="内容">
            <TextArea rows={4} placeholder="请输入跟进内容" />
          </Form.Item>

          <Form.Item name="result" label="结果">
            <TextArea rows={3} placeholder="请输入跟进结果" />
          </Form.Item>

          <Form.Item name="planned_at" label="计划时间">
            <DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="priority" label="优先级">
            <Select options={PRIORITY_OPTIONS} placeholder="选择优先级" />
          </Form.Item>

          <Form.Item name="assigned_to" label="负责人">
            <Input placeholder="请输入负责人" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
                保存
              </Button>
              <Button onClick={handleBack}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
