import { ThunderboltOutlined } from "@ant-design/icons";
import { App, Button, Input, Modal, Typography } from "antd";
import type { FormInstance } from "antd/es/form";
import dayjs from "dayjs";
import { useState } from "react";
import { recognizeFollowUp } from "../../api";
import type { FollowUpRecognition } from "../../types";

interface FollowUpAIRecognizerProps {
  customerId: number;
  form: FormInstance;
  getSeedText?: () => string;
  block?: boolean;
  size?: "small" | "middle" | "large";
}

const toDayjs = (value?: string | null) => {
  if (!value) return undefined;
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed : undefined;
};

const buildFormValues = (recognized: FollowUpRecognition, fallbackText: string) => {
  const values: Record<string, unknown> = {
    content: recognized.content || fallbackText,
  };

  if (recognized.method) values.method = recognized.method;
  if (recognized.status) values.status = recognized.status;
  if (recognized.priority) values.priority = recognized.priority;
  if (recognized.result) values.result = recognized.result;
  if (recognized.assigned_to) values.assigned_to = recognized.assigned_to;

  const plannedAt = toDayjs(recognized.planned_at);
  const completedAt = toDayjs(recognized.completed_at);
  if (plannedAt) values.planned_at = plannedAt;
  if (completedAt) values.completed_at = completedAt;

  return values;
};

export default function FollowUpAIRecognizer({
  customerId,
  form,
  getSeedText,
  block = false,
  size = "middle",
}: FollowUpAIRecognizerProps) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [recognizing, setRecognizing] = useState(false);

  const openModal = () => {
    const fields = form.getFieldsValue(["content", "result"]) as { content?: string; result?: string };
    const seededText = getSeedText?.() || [fields.content, fields.result].filter(Boolean).join("\n");
    setText(seededText.trim());
    setOpen(true);
  };

  const handleRecognize = async () => {
    const rawText = text.trim();
    if (!rawText) {
      message.warning("请先输入需要识别的跟进内容");
      return;
    }
    setRecognizing(true);
    try {
      const resp = await recognizeFollowUp(customerId, rawText);
      const recognized = resp.data.data;
      form.setFieldsValue(buildFormValues(recognized, rawText));
      setOpen(false);
      message.success(recognized.summary || "AI识别完成，请确认后保存");
    } catch {
      message.error("AI识别失败");
    } finally {
      setRecognizing(false);
    }
  };

  return (
    <>
      <Button
        block={block}
        size={size}
        icon={<ThunderboltOutlined />}
        onClick={openModal}
      >
        AI识别
      </Button>
      <Modal
        title="AI识别跟进内容"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={handleRecognize}
        confirmLoading={recognizing}
        okText="识别并填充"
        cancelText="取消"
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          粘贴销售沟通记录、待办或语音转写文本，系统会识别方式、状态、优先级、时间、负责人和结果。
        </Typography.Paragraph>
        <Input.TextArea
          rows={7}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={"例如：今天上午和张工电话沟通，客户确认需要重新评估BOM价格，明天下午3点再电话确认，优先级高，负责人王明。"}
        />
      </Modal>
    </>
  );
}
