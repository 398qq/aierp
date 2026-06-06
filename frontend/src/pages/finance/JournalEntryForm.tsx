import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Form, Input, DatePicker, Button, Space, InputNumber, Select, message, Table, Tag } from "antd";
import { StatusTag } from "../../ui";
import { PlusOutlined, DeleteOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import client from "../../api/client";
import dayjs from "dayjs";

interface Account { id: number; code: string; name: string; type: string; }

export default function JournalEntryForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const isEdit = !!id;

  useEffect(() => {
    client.get("/finance/accounts").then(r => setAccounts(r.data.data || []));
    if (id) {
      client.get(`/finance/journal-entries/${id}`).then(r => {
        const e = r.data.data;
        form.setFieldsValue({
          entry_date: dayjs(e.entry_date),
          description: e.description,
          lines: e.lines.map((l: { account_id: number; description: string; debit: number; credit: number }) => ({
            account_id: l.account_id, description: l.description, debit: l.debit, credit: l.credit,
          })),
        });
      });
    }
  }, [id]);

  const handleSubmit = async () => {
    const vals = await form.validateFields();
    setSaving(true);
    try {
      await client.post("/finance/journal-entries", {
        entry_date: vals.entry_date.format("YYYY-MM-DD"),
        description: vals.description,
        lines: vals.lines.map((l: { account_id: number; description: string; debit: number; credit: number }) => ({
          account_id: l.account_id, description: l.description || "",
          debit: l.debit || 0, credit: l.credit || 0,
        })),
      });
      message.success("凭证创建成功");
      navigate("/finance/journal-entries");
    } catch { message.error("保存失败"); }
    finally { setSaving(false); }
  };

  const columns = [
    {
      title: "科目", width: 200,
      render: (_: unknown, __: unknown, i: number) => (
        <Form.Item name={[i, "account_id"]} rules={[{ required: true }]} style={{ margin: 0 }}>
          <Select showSearch placeholder="选择科目" optionFilterProp="label"
            options={accounts.map(a => ({ value: a.id, label: `${a.code} ${a.name}` }))} />
        </Form.Item>
      ),
    },
    {
      title: "摘要", width: 120,
      render: (_: unknown, __: unknown, i: number) => (
        <Form.Item name={[i, "description"]} style={{ margin: 0 }}><Input /></Form.Item>
      ),
    },
    {
      title: "借方金额", width: 120,
      render: (_: unknown, __: unknown, i: number) => (
        <Form.Item name={[i, "debit"]} style={{ margin: 0 }}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
      ),
    },
    {
      title: "贷方金额", width: 120,
      render: (_: unknown, __: unknown, i: number) => (
        <Form.Item name={[i, "credit"]} style={{ margin: 0 }}><InputNumber min={0} precision={2} style={{ width: "100%" }} /></Form.Item>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/finance/journal-entries")}>返回</Button>
      </Space>
      <Card title={isEdit ? "凭证详情" : "新建凭证"}>
        <Form form={form} layout="vertical" initialValues={{ lines: [{}, {}] }}>
          <Space>
            <Form.Item name="entry_date" label="日期" rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
            <Form.Item name="description" label="摘要">
              <Input style={{ width: 300 }} />
            </Form.Item>
          </Space>
          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <>
                <Table rowKey="name" dataSource={fields.map(f => ({ ...f, name: f.name }))} columns={[
                  ...columns,
                  {
                    title: "", width: 60,
                    render: (_: unknown, __: unknown, i: number) => (
                      <Button size="small" danger icon={<DeleteOutlined />} onClick={() => remove(i)} />
                    ),
                  },
                ]} pagination={false} size="small" />
                <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ debit: 0, credit: 0 })} block style={{ marginTop: 12 }}>
                  添加行
                </Button>
              </>
            )}
          </Form.List>
          <div style={{ marginTop: 16, fontSize: 13 }}>
            {(() => {
              const lines = form.getFieldValue("lines") || [];
              const totalDebit = lines.reduce((s: number, l: { debit?: number }) => s + (l.debit || 0), 0);
              const totalCredit = lines.reduce((s: number, l: { credit?: number }) => s + (l.credit || 0), 0);
              const diff = totalDebit - totalCredit;
              return (
                <Space>
                  <span>借方合计: <strong>¥{totalDebit.toLocaleString()}</strong></span>
                  <span>贷方合计: <strong>¥{totalCredit.toLocaleString()}</strong></span>
                  <StatusTag tone={Math.abs(diff) < 0.01 ? "success" : "danger"}>
                    {Math.abs(diff) < 0.01 ? "借贷平衡" : `差额: ¥${diff.toLocaleString()}`}
                  </StatusTag>
                </Space>
              );
            })()}
          </div>
          {!isEdit && (
            <Button type="primary" onClick={handleSubmit} loading={saving} style={{ marginTop: 16 }}>
              保存凭证
            </Button>
          )}
        </Form>
      </Card>
    </div>
  );
}
