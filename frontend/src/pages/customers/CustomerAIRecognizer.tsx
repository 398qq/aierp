import { ThunderboltOutlined, UploadOutlined } from "@ant-design/icons";
import { App, Button, Input, Modal, Space, Typography, Upload } from "antd";
import type { FormInstance } from "antd/es/form";
import type { UploadProps } from "antd";
import { useState } from "react";
import { recognizeBusinessCard, recognizeCustomer } from "../../api";
import type { CustomerRecognition } from "../../types";
import { generateCustomerShortName } from "./CustomerForm";

interface CustomerAIRecognizerProps {
  form: FormInstance;
}

const buildCustomerFormValues = (recognized: CustomerRecognition, fallbackText: string) => {
  const values: Record<string, unknown> = {};
  const textFields: Array<keyof CustomerRecognition> = [
    "name",
    "short_name",
    "customer_type",
    "industry",
    "level",
    "region",
    "source",
    "contact_person",
    "phone",
    "email",
    "owner",
    "credit_level",
    "address",
    "notes",
  ];

  for (const key of textFields) {
    const value = recognized[key];
    if (typeof value === "string" && value.trim()) values[key] = value.trim();
  }

  if (!values.short_name && typeof values.name === "string") {
    values.short_name = generateCustomerShortName(values.name);
  }
  if (recognized.credit_limit != null) values.credit_limit = recognized.credit_limit;
  if (!values.notes) values.notes = fallbackText;

  return values;
};

export default function CustomerAIRecognizer({ form }: CustomerAIRecognizerProps) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [recognizing, setRecognizing] = useState(false);
  const [cardRecognizing, setCardRecognizing] = useState(false);

  const openModal = () => {
    const values = form.getFieldsValue(["name", "contact_person", "phone", "email", "notes"]) as Record<string, string | undefined>;
    const seededText = [values.name, values.contact_person, values.phone, values.email, values.notes].filter(Boolean).join("\n");
    setText(seededText.trim());
    setOpen(true);
  };

  const applyRecognizedCustomer = (recognized: CustomerRecognition, fallbackText: string) => {
    form.setFieldsValue(buildCustomerFormValues(recognized, fallbackText));
    setOpen(false);
    message.success(recognized.summary || "AI识别完成，请确认后保存");
  };

  const handleRecognize = async () => {
    const rawText = text.trim();
    if (!rawText) {
      message.warning("请先输入需要识别的客户资料");
      return;
    }
    setRecognizing(true);
    try {
      const resp = await recognizeCustomer(rawText);
      applyRecognizedCustomer(resp.data.data, rawText);
    } catch {
      message.error("AI识别失败");
    } finally {
      setRecognizing(false);
    }
  };

  const handleCardUpload: UploadProps["beforeUpload"] = async (file) => {
    if (!file.type.startsWith("image/")) {
      message.warning("请上传名片图片");
      return Upload.LIST_IGNORE;
    }

    setCardRecognizing(true);
    try {
      const resp = await recognizeBusinessCard(file);
      const recognized = resp.data.data;
      applyRecognizedCustomer(recognized, recognized.raw_text || text.trim());
      if (recognized.raw_text) setText(recognized.raw_text);
    } catch (error: any) {
      const backendMsg = error?.response?.data?.msg || error?.message;
      message.error(backendMsg || "名片识别失败，请换一张更清晰的图片或改用文本识别");
    } finally {
      setCardRecognizing(false);
    }
    return false;
  };

  return (
    <>
      <Button icon={<ThunderboltOutlined />} onClick={openModal}>
        AI识别
      </Button>
      <Modal
        title="AI识别客户资料"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={handleRecognize}
        confirmLoading={recognizing}
        okText="识别并填充"
        cancelText="取消"
        footer={(_, { OkBtn, CancelBtn }) => (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Upload accept="image/*" beforeUpload={handleCardUpload} disabled={cardRecognizing} maxCount={1} showUploadList={false}>
              <Button icon={<UploadOutlined />} loading={cardRecognizing}>
                上传名片识别
              </Button>
            </Upload>
            <Space>
              <CancelBtn />
              <OkBtn />
            </Space>
          </div>
        )}
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          粘贴名片、展会线索、聊天记录或邮件签名，系统会识别客户名称、联系人、电话、邮箱、行业、区域和负责人。
        </Typography.Paragraph>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Input.TextArea
            rows={8}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={"例如：深圳市星河电子有限公司，汽车电子OEM，华南区域，联系人张工 13800001111 zhang@example.com，展会线索，负责人王明，授信20万。"}
          />
        </Space>
      </Modal>
    </>
  );
}
