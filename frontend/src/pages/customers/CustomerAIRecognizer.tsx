import { ThunderboltOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, App, Button, Descriptions, Input, Modal, Space, Typography, Upload } from "antd";
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
  const [pendingRecognition, setPendingRecognition] = useState<CustomerRecognition | null>(null);

  const openModal = () => {
    const values = form.getFieldsValue(["name", "contact_person", "phone", "email", "notes"]) as Record<string, string | undefined>;
    const seededText = [values.name, values.contact_person, values.phone, values.email, values.notes].filter(Boolean).join("\n");
    setText(seededText.trim());
    setPendingRecognition(null);
    setOpen(true);
  };

  const applyRecognizedCustomer = (recognized: CustomerRecognition, fallbackText: string) => {
    form.setFieldsValue(buildCustomerFormValues(recognized, fallbackText));
    setOpen(false);
    message.success(recognized.summary || "AI识别完成，请确认后保存");
  };

  const handleRecognize = async () => {
    if (pendingRecognition) {
      applyRecognizedCustomer(pendingRecognition, pendingRecognition.raw_text || text.trim());
      return;
    }

    const rawText = text.trim();
    if (!rawText) {
      message.warning("请先输入需要识别的客户资料");
      return;
    }
    setRecognizing(true);
    try {
      const resp = await recognizeCustomer(rawText);
      const recognized = resp.data?.data as CustomerRecognition | null | undefined;
      if (!recognized) {
        throw new Error(resp.data?.msg || "AI识别失败");
      }
      applyRecognizedCustomer(recognized, rawText);
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
      const recognized = resp.data?.data as CustomerRecognition | null | undefined;
      if (!recognized) {
        throw new Error(resp.data?.msg || "名片识别失败");
      }
      if (recognized.raw_text) setText(recognized.raw_text);
      setPendingRecognition(recognized);
      message.success("名片识别完成，请确认字段后填充");
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
            onChange={(event) => {
              setText(event.target.value);
              setPendingRecognition(null);
            }}
            placeholder={"例如：深圳市星河电子有限公司，汽车电子OEM，华南区域，联系人张工 13800001111 zhang@example.com，展会线索，负责人王明，授信20万。"}
          />
          {pendingRecognition && (
            <>
              <Alert
                showIcon
                type="info"
                message="名片识别预览"
                description={`OCR引擎: ${pendingRecognition.ocr_engine || "unknown"}；置信度: ${
                  pendingRecognition.ocr_confidence != null ? Math.round(pendingRecognition.ocr_confidence * 100) + "%" : "未知"
                }；候选: ${pendingRecognition.ocr_candidates?.length || 1}；评分: ${pendingRecognition.ocr_score != null ? pendingRecognition.ocr_score.toFixed(2) : "未知"}${
                  pendingRecognition.image_quality
                    ? `；图片: ${pendingRecognition.image_quality.width}x${pendingRecognition.image_quality.height}，清晰度 ${pendingRecognition.image_quality.sharpness}`
                    : ""
                }`}
              />
              {!!pendingRecognition.recognition_warnings?.length && (
                <Alert showIcon type="warning" message="请重点核对" description={pendingRecognition.recognition_warnings.join("；")} />
              )}
              <Descriptions
                bordered
                size="small"
                column={2}
                items={[
                  { key: "name", label: "客户名称", children: pendingRecognition.name || "-" },
                  { key: "contact", label: "联系人", children: pendingRecognition.contact_person || "-" },
                  { key: "phone", label: "电话", children: pendingRecognition.phone || "-" },
                  { key: "email", label: "邮箱", children: pendingRecognition.email || "-" },
                  { key: "industry", label: "行业", children: pendingRecognition.industry || "-" },
                  { key: "region", label: "区域", children: pendingRecognition.region || "-" },
                ]}
              />
              <Input.TextArea rows={4} value={pendingRecognition.raw_text || ""} readOnly />
            </>
          )}
        </Space>
      </Modal>
    </>
  );
}
