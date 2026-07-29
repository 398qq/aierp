/**
 * 客户跟进记录表单页面（新建/编辑）
 * 路由: /customers/:customerId/follow-ups/new
 *      /customers/:customerId/follow-ups/:followupId/edit
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { App, Button, Card, Spin, Space } from "antd";
import {
  ProForm,
  ProFormSelect,
  ProFormDateTimePicker,
  ProFormText,
  ProFormTextArea,
} from "@ant-design/pro-components";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { createFollowUp, updateFollowUp, getFollowUps, getApiErrorMessage } from "../../api";
import type { FollowUp } from "../../types";
import { FOLLOW_UP_METHOD_OPTIONS, FOLLOW_UP_PRIORITY_OPTIONS, FOLLOW_UP_STATUS_OPTIONS } from "./customerUi";
import FollowUpAIRecognizer from "./FollowUpAIRecognizer";
import CustomerModuleShell from "./CustomerModuleShell";


export default function FollowUpForm() {
  const { message } = App.useApp();
  const { customerId, followupId } = useParams<{ customerId: string; followupId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [form] = ProForm.useForm();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);

  const custId = Number(customerId);
  const followupIdNum = followupId ? Number(followupId) : null;
  const isEdit = !!followupIdNum && !isNaN(followupIdNum);
  const opportunityId = Number(searchParams.get("opportunity_id")) || null;

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
  }, [isEdit, custId, followupIdNum, form, message]);

  // 提交表单
  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      if (values.status === "planned" && !values.planned_at) {
        message.warning("计划中的跟进必须填写计划时间");
        setLoading(false);
        return;
      }
      const submitData = {
        ...values,
        ...(opportunityId ? { opportunity_id: opportunityId } : {}),
        planned_at: values.planned_at ? (values.planned_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss") : null,
        completed_at: values.completed_at
          ? (values.completed_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : values.status === "completed"
            ? dayjs().format("YYYY-MM-DD HH:mm:ss")
            : null,
      };

      if (isEdit && followupIdNum) {
        await updateFollowUp(custId, followupIdNum, submitData);
        message.success("更新成功");
      } else {
        await createFollowUp(custId, submitData);
        message.success("创建成功");
      }
      navigate(opportunityId ? `/sales/opportunities/${opportunityId}` : `/customers/${custId}/follow-ups`);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "保存失败")); } finally {
      setLoading(false);
    }
  };

  // 返回列表
  const handleBack = () => {
    navigate(opportunityId ? `/sales/opportunities/${opportunityId}` : `/customers/${custId}/follow-ups`);
  };

  // 无效的客户ID
  if (!customerId || isNaN(custId)) {
    return (
      <Card>
        <Space direction="vertical" style={{ width: "100%", textAlign: "center" }}>
          <p>请先选择客户</p>
          <Button onClick={() => navigate("/customers")}>返回客户</Button>
        </Space>
      </Card>
    );
  }

  if (isEdit && initialLoading) {
    return <Spin style={{ display: "block", margin: "100px auto" }} />;
  }

  return (
    <CustomerModuleShell title={isEdit ? "编辑跟进" : "新增跟进"} subtitle="记录客户互动结果与下一步计划">
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
          返回列表
        </Button>
      </Space>

      <Card className="customer-surface customer-form-card"
        title={isEdit ? "编辑跟进记录" : "新建跟进记录"}
        extra={!isEdit && (
          <FollowUpAIRecognizer
            customerId={custId}
            form={form}
          />
        )}
      >
        <ProForm
          form={form}
          layout="vertical"
          onFinish={onFinish}
          onValuesChange={(changed) => {
            if (changed.status === "completed" && !form.getFieldValue("completed_at")) {
              form.setFieldValue("completed_at", dayjs());
            }
          }}
          initialValues={{
            status: "planned",
            priority: "medium",
          }}
          submitter={{
            render: () => [
              <Space key="actions">
                <Button
                  key="submit"
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={loading}
                >
                  保存
                </Button>
                <Button key="cancel" onClick={handleBack}>取消</Button>
              </Space>,
            ],
          }}
        >
          <ProFormSelect
            name="method"
            label="跟进方式"
            rules={[{ required: true, message: "请选择跟进方式" }]}
            options={FOLLOW_UP_METHOD_OPTIONS}
            placeholder="选择跟进方式"
          />

          <ProFormSelect
            name="status"
            label="状态"
            rules={[{ required: true, message: "请选择状态" }]}
            options={FOLLOW_UP_STATUS_OPTIONS}
            placeholder="选择状态"
          />

          <ProFormTextArea
            name="content"
            label="内容"
            fieldProps={{ rows: 4, placeholder: "请输入跟进内容" }}
          />

          <ProFormTextArea
            name="result"
            label="结果"
            fieldProps={{ rows: 3, placeholder: "请输入跟进结果" }}
          />

          <ProFormDateTimePicker
            name="planned_at"
            label="计划时间"
            fieldProps={{ format: "YYYY-MM-DD HH:mm", style: { width: "100%" } }}
          />

          <ProFormDateTimePicker
            name="completed_at"
            label="完成时间"
            fieldProps={{ format: "YYYY-MM-DD HH:mm", style: { width: "100%" } }}
          />

          <ProFormSelect
            name="priority"
            label="优先级"
            options={FOLLOW_UP_PRIORITY_OPTIONS}
            placeholder="选择优先级"
          />

          <ProFormText
            name="assigned_to"
            label="负责人"
            placeholder="请输入负责人"
          />
        </ProForm>
      </Card>
    </CustomerModuleShell>
  );
}
