// CustomerQuickFollowUpDrawer — right-side drawer with a single follow-up
// form: method, status, priority, planned/completed time, owner, content,
// and result. Includes the AI recognizer helper and auto-stamps
// completed_at when status flips to "completed".

import { Button, DatePicker, Drawer, Form, Input, Select, Space } from "antd";
import type { FormInstance } from "antd";
import dayjs from "dayjs";
import FollowUpAIRecognizer from "./FollowUpAIRecognizer";
import {
  FOLLOW_UP_METHOD_OPTIONS,
  FOLLOW_UP_PRIORITY_OPTIONS,
  FOLLOW_UP_STATUS_OPTIONS,
} from "./customerUi";
import type { Customer } from "../../types";

interface Props {
  open: boolean;
  saving: boolean;
  customer: Customer | null;
  form: FormInstance;
  onClose: () => void;
  onSubmit: () => void;
}

export default function CustomerQuickFollowUpDrawer({
  open,
  saving,
  customer,
  form,
  onClose,
  onSubmit,
}: Props) {
  return (
    <Drawer
      title={customer ? `新增跟进 - ${customer.name}` : "新增跟进"}
      width={520}
      open={open}
      onClose={onClose}
      extra={(
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={saving} onClick={onSubmit}>保存</Button>
        </Space>
      )}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ method: "phone", status: "planned", priority: "medium" }}
        onValuesChange={(changed) => {
          if (changed.status === "completed" && !form.getFieldValue("completed_at")) {
            form.setFieldValue("completed_at", dayjs());
          }
        }}
      >
        {customer && (
          <Form.Item>
            <FollowUpAIRecognizer
              customerId={customer.id}
              form={form}
              getSeedText={() => {
                const values = form.getFieldsValue(["content", "result"]) as {
                  content?: string;
                  result?: string;
                };
                return [values.content, values.result].filter(Boolean).join("\n");
              }}
              block
            />
          </Form.Item>
        )}
        <Form.Item name="method" label="跟进方式" rules={[{ required: true, message: "请选择跟进方式" }]}>
          <Select options={FOLLOW_UP_METHOD_OPTIONS} />
        </Form.Item>
        <Form.Item name="status" label="状态" rules={[{ required: true, message: "请选择状态" }]}>
          <Select options={FOLLOW_UP_STATUS_OPTIONS} />
        </Form.Item>
        <Form.Item name="priority" label="优先级">
          <Select options={FOLLOW_UP_PRIORITY_OPTIONS} />
        </Form.Item>
        <Form.Item name="planned_at" label="计划时间">
          <DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="completed_at" label="完成时间">
          <DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="assigned_to" label="负责人">
          <Input placeholder="客户负责人或跟进人" />
        </Form.Item>
        <Form.Item name="content" label="跟进内容">
          <Input.TextArea rows={4} placeholder="记录计划、沟通重点或客户需求" />
        </Form.Item>
        <Form.Item name="result" label="跟进结果">
          <Input.TextArea rows={3} placeholder="已完成时填写结果" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
