import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Tabs, Descriptions, Button, Space, Spin, Alert, Tag, Card, Form, Input, Modal, message, Popconfirm, Timeline, Select, Empty, Progress, Col, Row, Statistic, Upload, List, Typography, Tooltip } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, ClockCircleOutlined, UserOutlined, PhoneOutlined, ShoppingCartOutlined, TagsOutlined, RiseOutlined, WalletOutlined, WarningOutlined, UploadOutlined, PaperClipOutlined, DownloadOutlined, HeartOutlined, FileTextOutlined } from "@ant-design/icons";
import { getCustomer, getContacts, createContact, updateContact, deleteContact, getFollowUps, createFollowUp, updateFollowUp, deleteFollowUp, updateCustomer, getTimeline, getTags, getCustomerTags, linkTag, unlinkTag, getCustomerStats, getAttachments, uploadAttachment, deleteAttachment, getCustomerLogs } from "../../api";
import AIInsight from "../../components/ai/AIInsight";
import LoadingGuard from "../../components/shared/LoadingGuard";
import CustomerFormFields from "./CustomerForm";
import type { Attachment, Customer, Contact, FollowUp, Tag as TagType, TimelineEvent, CustomerStats, CustomerLog } from "../../types";

export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contactModalOpen, setContactModalOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [followupModalOpen, setFollowupModalOpen] = useState(false);
  const [editingFollowUp, setEditingFollowUp] = useState<FollowUp | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [allTags, setAllTags] = useState<TagType[]>([]);
  const [customerTags, setCustomerTags] = useState<TagType[]>([]);
  const [tagModalOpen, setTagModalOpen] = useState(false);

  const customerId = Number(id);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [custResp, contactsResp, followUpsResp, tagsResp] = await Promise.all([
        getCustomer(customerId),
        getContacts(customerId),
        getFollowUps(customerId),
        getCustomerTags(customerId),
      ]);
      setCustomer(custResp.data.data as Customer);
      setContacts((contactsResp.data.data as Contact[]) || []);
      setFollowUps((followUpsResp.data.data as FollowUp[]) || []);
      setCustomerTags((tagsResp.data.data as TagType[]) || []);
    } catch (e: unknown) {
      setError((e as Error).message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadTags = async () => {
    try {
      const [allResp, custTagsResp] = await Promise.all([getTags(), getCustomerTags(customerId)]);
      setAllTags((allResp.data.data as TagType[]) || []);
      setCustomerTags((custTagsResp.data.data as TagType[]) || []);
    } catch {}
  };

  useEffect(() => { load(); }, [customerId]);
  useEffect(() => { loadTags(); }, [customerId]);

  const handleUnlinkTag = async (tagId: number) => {
    try { await unlinkTag(customerId, tagId); loadTags(); } catch { message.error("移除标签失败"); }
  };

  const handleLinkTag = async (tagId: number) => {
    try { await linkTag(customerId, tagId); loadTags(); message.success("标签已添加"); } catch { message.error("添加标签失败"); }
  };

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/customers")} style={{ marginBottom: 16 }}>
        返回列表
      </Button>

      <LoadingGuard loading={loading} error={error} data={customer}>
        {customer && (
          <>
            <Card
              style={{ marginBottom: 16 }}
              title={customer.name}
              extra={
                <Space>
                  {customerTags.map((t) => (
                    <Tag key={t.id} color={t.color || "blue"} closable onClose={() => handleUnlinkTag(t.id)}>{t.name}</Tag>
                  ))}
                  <Button size="small" icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>标签</Button>
                  <Button icon={<EditOutlined />} onClick={() => setEditModalOpen(true)}>编辑</Button>
                </Space>
              }
            >
              <Descriptions column={3} size="small">
                <Descriptions.Item label="编码">{customer.code || "-"}</Descriptions.Item>
                <Descriptions.Item label="行业">{customer.industry || "-"}</Descriptions.Item>
                <Descriptions.Item label="等级"><Tag color={customer.level === "A" ? "red" : customer.level === "B" ? "orange" : "default"}>{customer.level}</Tag></Descriptions.Item>
                <Descriptions.Item label="区域">{customer.region || "-"}</Descriptions.Item>
                <Descriptions.Item label="来源">{customer.source || "-"}</Descriptions.Item>
                <Descriptions.Item label="类型">{customer.customer_type || "-"}</Descriptions.Item>
                <Descriptions.Item label="联系人">{customer.contact_person || "-"}</Descriptions.Item>
                <Descriptions.Item label="电话">{customer.phone || "-"}</Descriptions.Item>
                <Descriptions.Item label="邮箱">{customer.email || "-"}</Descriptions.Item>
                <Descriptions.Item label="信用等级">{customer.credit_level || "-"}</Descriptions.Item>
                <Descriptions.Item label="最近联系">{customer.last_contacted_at || "-"}</Descriptions.Item>
                <Descriptions.Item label="地址" span={3}>{customer.address || "-"}</Descriptions.Item>
                <Descriptions.Item label="备注" span={3}>{customer.notes || "-"}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Tabs
              defaultActiveKey="ai"
              items={[
                {
                  key: "profile",
                  label: "客户画像",
                  children: <CustomerProfile customerId={customerId} />,
                },
                {
                  key: "ai",
                  label: "AI 洞察",
                  children: <AIInsight customerId={customerId} />,
                },
                {
                  key: "timeline",
                  label: "活动时间线",
                  children: <CustomerTimeline customerId={customerId} />,
                },
                {
                  key: "contacts",
                  label: `联系人 (${contacts.length})`,
                  children: (
                    <div>
                      <Button type="primary" onClick={() => { setEditingContact(null); setContactModalOpen(true); }} style={{ marginBottom: 16 }}>
                        新增联系人
                      </Button>
                      {contacts.length === 0 && <Empty description="暂无联系人" />}
                      {contacts.map((c) => (
                        <Card key={c.id} size="small" style={{ marginBottom: 8 }}
                          actions={[
                            <EditOutlined key="edit" onClick={() => { setEditingContact(c); setContactModalOpen(true); }} />,
                            <Popconfirm key="del" title="确定删除?" onConfirm={async () => {
                              try { await deleteContact(customerId, c.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                            }}><DeleteOutlined /></Popconfirm>,
                          ]}
                        >
                          <Descriptions column={3} size="small">
                            <Descriptions.Item label="姓名">{c.name}{c.is_primary && <Tag color="gold" style={{ marginLeft: 4 }}>主要</Tag>}</Descriptions.Item>
                            <Descriptions.Item label="职位">{c.title || "-"}</Descriptions.Item>
                            <Descriptions.Item label="角色">{c.role || "-"}</Descriptions.Item>
                            <Descriptions.Item label="邮箱">{c.email || "-"}</Descriptions.Item>
                            <Descriptions.Item label="电话">{c.phone || "-"}</Descriptions.Item>
                            <Descriptions.Item label="微信">{c.wechat || "-"}</Descriptions.Item>
                          </Descriptions>
                        </Card>
                      ))}
                    </div>
                  ),
                },
                {
                  key: "followups",
                  label: `跟进记录 (${followUps.length})`,
                  children: (
                    <div>
                      <Button type="primary" onClick={() => { setEditingFollowUp(null); setFollowupModalOpen(true); }} style={{ marginBottom: 16 }}>
                        新增跟进
                      </Button>
                      {followUps.length === 0 && <Empty description="暂无跟进记录" />}
                      {followUps.map((f) => (
                        <Card key={f.id} size="small" style={{ marginBottom: 8 }}
                          actions={[
                            <EditOutlined key="edit" onClick={() => { setEditingFollowUp(f); setFollowupModalOpen(true); }} />,
                            <Popconfirm key="del" title="确定删除?" onConfirm={async () => {
                              try { await deleteFollowUp(customerId, f.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                            }}><DeleteOutlined /></Popconfirm>,
                          ]}
                        >
                          <Descriptions column={3} size="small">
                            <Descriptions.Item label="方式"><Tag>{f.method}</Tag></Descriptions.Item>
                            <Descriptions.Item label="状态"><Tag color={f.status === "completed" ? "green" : "processing"}>{f.status}</Tag></Descriptions.Item>
                            <Descriptions.Item label="优先级">{f.priority && <Tag color={f.priority === "high" ? "red" : f.priority === "medium" ? "orange" : "default"}>{f.priority}</Tag>}</Descriptions.Item>
                            <Descriptions.Item label="计划时间">{f.planned_at || "-"}</Descriptions.Item>
                            <Descriptions.Item label="负责人">{f.assigned_to || "-"}</Descriptions.Item>
                          </Descriptions>
                          {f.content && <p style={{ marginTop: 8 }}>{f.content}</p>}
                          {f.result && <p style={{ marginTop: 4, color: "#666" }}>结果：{f.result}</p>}
                        </Card>
                      ))}
                    </div>
                  ),
                },
                {
                  key: "attachments",
                  label: "附件",
                  children: <AttachmentPanel customerId={customerId} />,
                },
                {
                  key: "logs",
                  label: "变更日志",
                  children: <ChangeLogPanel customerId={customerId} />,
                },
              ]}
            />

            <EditCustomerModal open={editModalOpen} customer={customer} onClose={() => setEditModalOpen(false)} onUpdated={() => { setEditModalOpen(false); load(); }} />
            <ContactFormModal open={contactModalOpen} customerId={customerId} contact={editingContact} onClose={() => { setContactModalOpen(false); setEditingContact(null); }} onSaved={() => { setContactModalOpen(false); setEditingContact(null); load(); }} />
            <FollowUpFormModal open={followupModalOpen} customerId={customerId} followUp={editingFollowUp} onClose={() => { setFollowupModalOpen(false); setEditingFollowUp(null); }} onSaved={() => { setFollowupModalOpen(false); setEditingFollowUp(null); load(); }} />
            <TagManageModal open={tagModalOpen} allTags={allTags} customerTags={customerTags} onLink={handleLinkTag} onClose={() => setTagModalOpen(false)} />
          </>
        )}
      </LoadingGuard>
    </div>
  );
}

// --- Timeline component ---

function CustomerTimeline({ customerId }: { customerId: number }) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTimeline(customerId).then((r) => {
      setEvents((r.data.data as TimelineEvent[]) || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <Spin />;
  if (events.length === 0) return <Empty description="暂无活动记录" />;

  const iconMap = { contact: <UserOutlined />, followup: <PhoneOutlined />, order: <ShoppingCartOutlined /> };
  const colorMap = { contact: "blue", followup: "green", order: "red" };

  return (
    <Timeline
      items={events.map((e) => ({
        color: (colorMap[e.type] as "blue" | "green" | "red") || "gray",
        dot: iconMap[e.type],
        children: (
          <div>
            <div style={{ fontWeight: 500 }}>{e.title}</div>
            <div style={{ color: "#888", fontSize: 12 }}>{e.detail}</div>
            <div style={{ color: "#aaa", fontSize: 11, marginTop: 2 }}>{new Date(e.time).toLocaleString("zh-CN")}</div>
          </div>
        ),
      }))}
    />
  );
}

// --- Edit Customer Modal ---

function EditCustomerModal({ open, customer, onClose, onUpdated }: { open: boolean; customer: Customer; onClose: () => void; onUpdated: () => void }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && customer) form.setFieldsValue(customer);
  }, [open, customer, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try { await updateCustomer(customer.id, values); message.success("客户信息更新成功"); onUpdated(); } catch { message.error("更新失败"); } finally { setLoading(false); }
  };

  return (
    <Modal title="编辑客户" open={open} onCancel={onClose} onOk={() => form.submit()} confirmLoading={loading} width={720}>
      <Form form={form} layout="vertical" onFinish={onFinish}><CustomerFormFields /></Form>
    </Modal>
  );
}

// --- Contact Form Modal (create + edit) ---

function ContactFormModal({ open, customerId, contact, onClose, onSaved }: { open: boolean; customerId: number; contact: Contact | null; onClose: () => void; onSaved: () => void }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (contact) form.setFieldsValue(contact);
      else form.resetFields();
    }
  }, [open, contact, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      if (contact) {
        await updateContact(customerId, contact.id, values);
        message.success("联系人更新成功");
      } else {
        await createContact(customerId, values);
        message.success("联系人新增成功");
      }
      form.resetFields();
      onSaved();
    } catch { message.error("保存失败"); } finally { setLoading(false); }
  };

  return (
    <Modal title={contact ? "编辑联系人" : "新增联系人"} open={open} onCancel={onClose} onOk={() => form.submit()} confirmLoading={loading}>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="title" label="职位"><Input /></Form.Item>
        <Form.Item name="role" label="角色"><Input /></Form.Item>
        <Form.Item name="email" label="邮箱"><Input /></Form.Item>
        <Form.Item name="phone" label="电话"><Input /></Form.Item>
        <Form.Item name="wechat" label="微信"><Input /></Form.Item>
        <Form.Item name="is_primary" label="主要联系人" valuePropName="checked">
          <Select options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// --- FollowUp Form Modal (create + edit) ---

function FollowUpFormModal({ open, customerId, followUp, onClose, onSaved }: { open: boolean; customerId: number; followUp: FollowUp | null; onClose: () => void; onSaved: () => void }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (followUp) form.setFieldsValue(followUp);
      else form.resetFields();
    }
  }, [open, followUp, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      if (followUp) {
        await updateFollowUp(customerId, followUp.id, values);
        message.success("跟进记录更新成功");
      } else {
        await createFollowUp(customerId, values);
        message.success("跟进记录新增成功");
      }
      form.resetFields();
      onSaved();
    } catch { message.error("保存失败"); } finally { setLoading(false); }
  };

  return (
    <Modal title={followUp ? "编辑跟进记录" : "新增跟进记录"} open={open} onCancel={onClose} onOk={() => form.submit()} confirmLoading={loading}>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item name="method" label="跟进方式">
          <Select allowClear placeholder="选择方式" options={[
            { value: "call", label: "电话" }, { value: "email", label: "邮件" },
            { value: "visit", label: "拜访" }, { value: "wechat", label: "微信" },
          ]} />
        </Form.Item>
        <Form.Item name="content" label="跟进内容"><Input.TextArea rows={4} /></Form.Item>
        <Form.Item name="result" label="跟进结果"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select allowClear placeholder="选择状态" options={[
            { value: "pending", label: "待跟进" }, { value: "in_progress", label: "进行中" }, { value: "completed", label: "已完成" },
          ]} />
        </Form.Item>
        <Form.Item name="priority" label="优先级">
          <Select allowClear placeholder="选择优先级" options={[
            { value: "high", label: "高" }, { value: "medium", label: "中" }, { value: "low", label: "低" },
          ]} />
        </Form.Item>
        <Form.Item name="assigned_to" label="负责人"><Input /></Form.Item>
      </Form>
    </Modal>
  );
}

// --- Customer Profile ---

const LIFECYCLE_COLORS: Record<string, string> = { "活跃": "green", "新客户": "blue", "衰退": "orange", "沉默客户": "default", "流失": "red" };
const HEALTH_COLORS: Record<string, string> = { "优秀": "#52c41a", "良好": "#1677ff", "一般": "#faad14", "差": "#ff4d4f" };

function CustomerProfile({ customerId }: { customerId: number }) {
  const [stats, setStats] = useState<CustomerStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCustomerStats(customerId).then((r) => {
      setStats(r.data.data as CustomerStats);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <Spin />;
  if (!stats) return <Empty description="暂无数据" />;

  const agingEntries = Object.entries(stats.aging).filter(([, v]) => v > 0);

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="健康度" value={stats.health_score} suffix="分"
              prefix={<HeartOutlined style={{ color: HEALTH_COLORS[stats.health_label] || "#1677ff" }} />}
              valueStyle={{ color: HEALTH_COLORS[stats.health_label] || "#1677ff" }}
            />
            <Progress percent={stats.health_score} size="small"
              strokeColor={stats.health_score >= 80 ? "#52c41a" : stats.health_score >= 60 ? "#1677ff" : stats.health_score >= 40 ? "#faad14" : "#ff4d4f"}
              style={{ marginTop: 4 }}
            />
            <div style={{ marginTop: 4, color: "#888", fontSize: 12 }}>{stats.health_label}</div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="生命周期" value={stats.lifecycle}
              prefix={<Tag color={LIFECYCLE_COLORS[stats.lifecycle] || "default"} style={{ fontSize: 16 }}>{stats.lifecycle}</Tag>}
            />
            <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>创建 {stats.created_days} 天</div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="订单总数" value={stats.order_count} prefix={<ShoppingCartOutlined />} />
            <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
              累计: ¥{stats.total_revenue.toLocaleString()}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="信用使用" value={stats.credit_usage_pct} suffix="%" prefix={<WalletOutlined />} />
            <Progress percent={stats.credit_usage_pct} size="small"
              status={stats.credit_usage_pct > 80 ? "exception" : stats.credit_usage_pct > 50 ? "active" : "normal"}
              style={{ marginTop: 4 }}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="应收账款账龄" style={{ marginTop: 16 }}>
        {agingEntries.length === 0 ? (
          <Empty description="无未结清应收账款" />
        ) : (
          <Row gutter={[16, 16]}>
            {agingEntries.map(([bucket, amt]) => (
              <Col xs={12} sm={6} key={bucket}>
                <Statistic
                  title={bucket + " 天"}
                  value={amt}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: bucket === "90+" ? "#cf1322" : bucket === "60-90" ? "#fa8c16" : "#333" }}
                />
              </Col>
            ))}
          </Row>
        )}
      </Card>

      {stats.last_order_date && (
        <div style={{ marginTop: 12, color: "#888", fontSize: 12 }}>最近订单: {stats.last_order_date?.slice(0, 10)} | 已付金额: ¥{stats.paid_total.toLocaleString()}</div>
      )}
    </div>
  );
}

// --- Attachment Panel ---

function AttachmentPanel({ customerId }: { customerId: number }) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getAttachments(customerId);
      setAttachments((resp.data.data as Attachment[]) || []);
    } catch {} finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [customerId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadAttachment(customerId, file);
      message.success("上传成功");
      load();
    } catch { message.error("上传失败"); }
    finally { setUploading(false); }
    return false;
  };

  const handleDelete = async (id: number) => {
    try { await deleteAttachment(customerId, id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Upload accept="*" showUploadList={false} beforeUpload={handleUpload} disabled={uploading}>
          <Button icon={<UploadOutlined />} loading={uploading}>上传文件</Button>
        </Upload>
      </Space>

      {loading ? <Spin /> :
        attachments.length === 0 ? <Empty description="暂无附件" /> :
        <List
          dataSource={attachments}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button key="dl" size="small" icon={<DownloadOutlined />}
                  onClick={() => window.open(`/api/v1/customers/${customerId}/attachments/${item.id}/download`, "_blank")}
                />,
                <Popconfirm key="del" title="确定删除?" onConfirm={() => handleDelete(item.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<PaperClipOutlined style={{ fontSize: 20 }} />}
                title={item.original_name}
                description={`${formatSize(item.file_size)} · ${item.category || "其他"} · ${item.created_at?.slice(0, 10)}`}
              />
            </List.Item>
          )}
        />
      }
    </div>
  );
}

// --- Tag Manage Modal ---

function TagManageModal({ open, allTags, customerTags, onLink, onClose }: { open: boolean; allTags: TagType[]; customerTags: TagType[]; onLink: (id: number) => void; onClose: () => void }) {
  const linkedIds = new Set(customerTags.map((t) => t.id));
  const available = allTags.filter((t) => !linkedIds.has(t.id));

  return (
    <Modal title="管理标签" open={open} onCancel={onClose} footer={null}>
      {customerTags.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>当前标签</div>
          {customerTags.map((t) => <Tag key={t.id} color={t.color || "blue"}>{t.name}</Tag>)}
        </div>
      )}
      <div>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>添加标签</div>
        {available.length === 0 && <Empty description="没有更多可用的标签" />}
        <Space wrap>
          {available.map((t) => (
            <Tag key={t.id} color={t.color || "default"} style={{ cursor: "pointer" }} onClick={() => onLink(t.id)}>
              + {t.name}
            </Tag>
          ))}
        </Space>
      </div>
    </Modal>
  );
}

// --- Change Log Panel ---

const ACTION_LABELS: Record<string, string> = {
  create: "创建", update: "更新", delete: "删除", merge: "合并", tag: "标签", import: "导入",
};
const ACTION_COLORS: Record<string, string> = {
  create: "green", update: "blue", delete: "red", merge: "purple", tag: "orange", import: "cyan",
};

function ChangeLogPanel({ customerId }: { customerId: number }) {
  const [logs, setLogs] = useState<CustomerLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCustomerLogs(customerId).then((r) => {
      setLogs((r.data.data as CustomerLog[]) || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <Spin />;
  if (logs.length === 0) return <Empty description="暂无变更记录" />;

  return (
    <Timeline
      items={logs.map((l) => ({
        color: ACTION_COLORS[l.action] || "gray",
        children: (
          <div>
            <Space size={4}>
              <Tag color={ACTION_COLORS[l.action]}>{ACTION_LABELS[l.action] || l.action}</Tag>
              {l.field_name && <Typography.Text strong>{l.field_name}</Typography.Text>}
            </Space>
            {l.summary && <div style={{ marginTop: 2, fontSize: 13 }}>{l.summary}</div>}
            {l.old_value !== null && l.new_value !== null && l.action === "update" && (
              <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
                <Typography.Text delete>{l.old_value}</Typography.Text> → {l.new_value}
              </div>
            )}
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>
              {l.created_at?.slice(0, 19)} {l.operator && `· ${l.operator}`}
            </div>
          </div>
        ),
      }))}
    />
  );
}
