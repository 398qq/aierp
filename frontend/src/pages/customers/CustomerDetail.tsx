import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { App, Tabs, Descriptions, Button, Space, Spin, Alert, Tag, Card, Form, Input, Modal, Popconfirm, Timeline, Select, Empty, Progress, Col, Row, Statistic, Upload, List, Typography, Tooltip, Table, DatePicker, InputNumber, Divider } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, ClockCircleOutlined, UserOutlined, PhoneOutlined, ShoppingCartOutlined, TagsOutlined, RiseOutlined, WalletOutlined, WarningOutlined, UploadOutlined, PaperClipOutlined, DownloadOutlined, HeartOutlined, FileTextOutlined, ApartmentOutlined, FileSearchOutlined, CalendarOutlined, LinkOutlined, DisconnectOutlined, BulbOutlined, PieChartOutlined, SwapOutlined } from "@ant-design/icons";
import { getCustomer, getContacts, createContact, updateContact, deleteContact, getFollowUps, createFollowUp, updateFollowUp, deleteFollowUp, updateCustomer, getTimeline, getTags, createTag, getCustomerTags, linkTag, unlinkTag, getCustomerStats, getCustomerLogs, getChildren, getGroupStats, linkParent, unlinkParent, getCustomerVisits, createCustomerVisit, updateCustomerVisit, deleteCustomerVisit, recommendProductsForCustomer, getSimilarCustomers } from "../../api";
import AttachmentPanel from "../../components/AttachmentPanel";
import type { CustomerProductMatch, SimilarCustomer } from "../../types";
import AIInsight from "../../components/ai/AIInsight";
import CustomerFormFields from "./CustomerForm";
import FollowUpAIRecognizer from "./FollowUpAIRecognizer";
import VendAsSupplierModal from "./VendAsSupplierModal";
import QuotationHistoryPanel from "./QuotationHistoryPanel";
import dayjs from "dayjs";
import type { Attachment, Customer, Contact, FollowUp, Tag as TagType, TimelineEvent, CustomerStats, CustomerLog, GroupStats, Visit } from "../../types";
import {
  CustomerHealthBadge,
  FOLLOW_UP_METHOD_OPTIONS,
  FOLLOW_UP_PRIORITY_OPTIONS,
  FOLLOW_UP_STATUS_OPTIONS,
  FollowUpMethodTag,
  FollowUpPriorityTag,
  FollowUpStatusTag,
  getLevelColor,
} from "./customerUi";

const formatShortDateTime = (value?: string | null) => value ? value.slice(0, 16).replace("T", " ") : "-";
const isOpenFollowUp = (item: FollowUp) => item.status !== "completed" && item.status !== "cancelled";
const getFollowUpDueMeta = (item?: FollowUp | null) => {
  if (!item) return { text: "无计划", color: "default" };
  if (item.status === "completed") return { text: "已完成", color: "green" };
  if (item.status === "cancelled") return { text: "已取消", color: "default" };
  if (!item.planned_at) return { text: "未排期", color: "default" };
  const due = dayjs(item.planned_at);
  const today = dayjs().startOf("day");
  const diff = due.startOf("day").diff(today, "day");
  if (diff < 0) return { text: `逾期 ${Math.abs(diff)} 天`, color: "red" };
  if (diff === 0) return { text: "今日待跟进", color: "orange" };
  return { text: `${diff} 天后`, color: "blue" };
};
const TAG_COLOR_OPTIONS = [
  { value: "blue", label: "蓝色" },
  { value: "green", label: "绿色" },
  { value: "orange", label: "橙色" },
  { value: "red", label: "红色" },
  { value: "purple", label: "紫色" },
  { value: "cyan", label: "青色" },
  { value: "default", label: "默认" },
];

export default function CustomerDetail() {
  const { message } = App.useApp();
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
  const [recModalOpen, setRecModalOpen] = useState(false);
  const [recResult, setRecResult] = useState<CustomerProductMatch | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const [vendModalOpen, setVendModalOpen] = useState(false);

  const customerId = Number(id);
  const nextOpenFollowUp = useMemo(
    () => followUps
      .filter((item) => isOpenFollowUp(item))
      .sort((a, b) => new Date(a.planned_at || a.created_at).getTime() - new Date(b.planned_at || b.created_at).getTime())[0],
    [followUps],
  );

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

  const handleCreateAndLinkTag = async (name: string, color: string) => {
    const resp = await createTag({ name, color });
    const created = resp.data.data as TagType;
    await linkTag(customerId, created.id);
    await loadTags();
    message.success("标签已创建并添加");
  };

  const handleProductRecs = async () => {
    setRecLoading(true);
    try {
      const resp = await recommendProductsForCustomer(customerId);
      if (resp.data.code === 0) { setRecResult(resp.data.data as CustomerProductMatch); setRecModalOpen(true); }
    } catch { message.error("AI 推荐失败"); }
    finally { setRecLoading(false); }
  };


  return (
    <div>
      {loading && <Spin style={{ display: "block", margin: "100px auto" }} />}
      {error && <Alert type="error" message={error} />}
      {!loading && !error && !customer && <Empty description="未找到客户" />}
      {!loading && !error && customer && (
          <>
            <style>{`
              .customer-detail-hero .ant-card-body {
                padding: 14px;
              }
              .customer-detail-title {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
              }
              .customer-detail-layout {
                display: grid;
                grid-template-columns: minmax(240px, 0.86fr) minmax(360px, 1.34fr) minmax(220px, 0.8fr);
                gap: 12px;
                align-items: stretch;
              }
              .customer-detail-panel {
                padding: 12px;
                background: #fafafa;
                border: 1px solid #f0f0f0;
                border-radius: 8px;
              }
              .customer-detail-panel.is-action {
                background: #fff;
              }
              .customer-detail-panel-title {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                margin-bottom: 10px;
              }
              .customer-detail-tag-row {
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                margin-top: 8px;
              }
              .customer-detail-tag-row .ant-tag {
                margin-inline-end: 0;
              }
              .customer-detail-next {
                padding: 10px;
                background: #fff;
                border: 1px solid #f0f0f0;
                border-radius: 8px;
                margin-bottom: 10px;
              }
              .customer-detail-follow-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
              }
              .customer-detail-follow-item {
                padding: 8px 10px;
                background: #fff;
                border: 1px solid #f0f0f0;
                border-radius: 8px;
              }
              .customer-detail-action-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 8px;
              }
              .customer-detail-action-grid .ant-btn {
                justify-content: flex-start;
              }
              @media (max-width: 1180px) {
                .customer-detail-layout {
                  grid-template-columns: 1fr 1fr;
                }
                .customer-detail-panel.is-action {
                  grid-column: 1 / -1;
                }
                .customer-detail-action-grid {
                  grid-template-columns: repeat(3, minmax(0, 1fr));
                }
              }
              @media (max-width: 768px) {
                .customer-detail-layout,
                .customer-detail-action-grid {
                  grid-template-columns: 1fr;
                }
              }
            `}</style>
            <Card
              className="customer-detail-hero"
              style={{ marginBottom: 16 }}
              title={(
                <div className="customer-detail-title">
                  <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/customers")}>返回列表</Button>
                  <Typography.Title level={4} style={{ margin: 0 }}>{customer.name}</Typography.Title>
                  <Tag color={getLevelColor(customer.level)}>等级 {customer.level || "-"}</Tag>
                  <CustomerHealthBadge value={customer.health_score} />
                </div>
              )}
              extra={(
                <Space wrap>
                  <Button icon={<EditOutlined />} onClick={() => setEditModalOpen(true)}>编辑</Button>
                  <Button type="primary" icon={<PhoneOutlined />} onClick={() => { setEditingFollowUp(null); setFollowupModalOpen(true); }}>新增跟进</Button>
                </Space>
              )}
            >
              <div className="customer-detail-layout">
                <section className="customer-detail-panel">
                  <div className="customer-detail-panel-title">
                    <Typography.Text strong>客户信息</Typography.Text>
                    <Button size="small" icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>标签</Button>
                  </div>
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="编码">{customer.code || "-"}</Descriptions.Item>
                    <Descriptions.Item label="简称">{customer.short_name || "-"}</Descriptions.Item>
                    <Descriptions.Item label="行业">{customer.industry || "-"}</Descriptions.Item>
                    <Descriptions.Item label="区域">{customer.region || "-"}</Descriptions.Item>
                    <Descriptions.Item label="负责人">{customer.owner || "-"}</Descriptions.Item>
                    <Descriptions.Item label="来源">{customer.source || "-"}</Descriptions.Item>
                    <Descriptions.Item label="信用">{customer.credit_level || "-"}</Descriptions.Item>
                    <Descriptions.Item label="最近联系">{formatShortDateTime(customer.last_contacted_at)}</Descriptions.Item>
                  </Descriptions>
                  <div className="customer-detail-tag-row">
                    {customerTags.length === 0 ? (
                      <Typography.Text type="secondary">暂无标签</Typography.Text>
                    ) : customerTags.map((t) => (
                      <Tag key={t.id} color={t.color || "blue"} closable onClose={() => handleUnlinkTag(t.id)}>{t.name}</Tag>
                    ))}
                  </div>
                </section>

                <section className="customer-detail-panel">
                  <div className="customer-detail-panel-title">
                    <Typography.Text strong>推进状态</Typography.Text>
                    <Button size="small" onClick={() => navigate(`/customers/${customerId}/follow-ups`)}>全部跟进</Button>
                  </div>
                  <div className="customer-detail-next">
                    {nextOpenFollowUp ? (
                      <Space direction="vertical" size={5} style={{ width: "100%" }}>
                        <Space wrap>
                          <Tag color={getFollowUpDueMeta(nextOpenFollowUp).color}>{getFollowUpDueMeta(nextOpenFollowUp).text}</Tag>
                          <FollowUpStatusTag status={nextOpenFollowUp.status} />
                          <FollowUpMethodTag method={nextOpenFollowUp.method} />
                          <FollowUpPriorityTag priority={nextOpenFollowUp.priority} />
                        </Space>
                        <Typography.Text strong>{formatShortDateTime(nextOpenFollowUp.planned_at)}</Typography.Text>
                        <Typography.Text type="secondary">{nextOpenFollowUp.content || "暂无跟进内容"}</Typography.Text>
                      </Space>
                    ) : (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待处理跟进" />
                    )}
                  </div>
                  <div className="customer-detail-follow-list">
                    {followUps.slice(0, 3).map((item) => {
                      const due = getFollowUpDueMeta(item);
                      return (
                        <div className="customer-detail-follow-item" key={item.id}>
                          <Space wrap size={6}>
                            <Tag color={due.color}>{due.text}</Tag>
                            <FollowUpMethodTag method={item.method} />
                            <Typography.Text type="secondary">{formatShortDateTime(item.planned_at)}</Typography.Text>
                          </Space>
                          <Typography.Paragraph type="secondary" style={{ margin: "4px 0 0" }} ellipsis={{ rows: 2 }}>
                            {item.content || item.result || "-"}
                          </Typography.Paragraph>
                        </div>
                      );
                    })}
                    {followUps.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" />}
                  </div>
                </section>

                <aside className="customer-detail-panel is-action">
                  <div className="customer-detail-panel-title">
                    <Typography.Text strong>行动区</Typography.Text>
                    <Tag color={getFollowUpDueMeta(nextOpenFollowUp).color}>{getFollowUpDueMeta(nextOpenFollowUp).text}</Tag>
                  </div>
                  <div className="customer-detail-action-grid">
                    <Button type="primary" icon={<PhoneOutlined />} onClick={() => { setEditingFollowUp(null); setFollowupModalOpen(true); }}>新增跟进</Button>
                    <Button icon={<ShoppingCartOutlined />} onClick={() => navigate(`/sales/orders/new?customer_id=${customerId}`)}>创建订单</Button>
                    <Button icon={<BulbOutlined />} loading={recLoading} onClick={handleProductRecs}>AI 产品推荐</Button>
                    <Button icon={<PieChartOutlined />} onClick={() => navigate(`/customers/${customerId}/360`)}>AI 360 洞察</Button>
                    <Button icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>管理标签</Button>
                    <Button icon={<SwapOutlined />} onClick={() => setVendModalOpen(true)}>转为供应商</Button>
                  </div>
                  <Divider style={{ margin: "12px 0" }} />
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="联系人">{customer.contact_person || "-"}</Descriptions.Item>
                    <Descriptions.Item label="电话">{customer.phone || "-"}</Descriptions.Item>
                    <Descriptions.Item label="邮箱">{customer.email || "-"}</Descriptions.Item>
                  </Descriptions>
                </aside>
              </div>
            </Card>

            <Tabs
              defaultActiveKey="overview"
              items={[
                {
                  key: "overview",
                  label: "概览",
                  children: (
                    <CustomerOverview
                      customerId={customerId}
                      contacts={contacts}
                      followUps={followUps}
                      nextOpenFollowUp={nextOpenFollowUp}
                      onNewFollowUp={() => { setEditingFollowUp(null); setFollowupModalOpen(true); }}
                      onOpenAllFollowUps={() => navigate(`/customers/${customerId}/follow-ups`)}
                    />
                  ),
                },
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
                      <Space style={{ marginBottom: 16 }}>
                        <Button type="primary" onClick={() => { setEditingFollowUp(null); setFollowupModalOpen(true); }}>
                          新增跟进
                        </Button>
                        <Button onClick={() => navigate(`/customers/${customerId}/follow-ups`)}>
                          查看全部
                        </Button>
                      </Space>
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
                            <Descriptions.Item label="提醒状态">
                              <Tag color={getFollowUpDueMeta(f).color}>{getFollowUpDueMeta(f).text}</Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="方式"><FollowUpMethodTag method={f.method} /></Descriptions.Item>
                            <Descriptions.Item label="状态"><FollowUpStatusTag status={f.status} /></Descriptions.Item>
                            <Descriptions.Item label="优先级"><FollowUpPriorityTag priority={f.priority} /></Descriptions.Item>
                            <Descriptions.Item label="计划时间">{formatShortDateTime(f.planned_at)}</Descriptions.Item>
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
                  children: <AttachmentPanel entityType="customer" entityId={customerId} />,
                },
                {
                  key: "logs",
                  label: "变更日志",
                  children: <ChangeLogPanel customerId={customerId} />,
                },
                {
                  key: "group",
                  label: "集团关系",
                  children: <GroupPanel customerId={customerId} customerName={customer.name} />,
                },
                {
                  key: "quotations",
                  label: "报价历史",
                  children: <QuotationHistoryPanel customerId={customerId} />,
                },
                {
                  key: "visits",
                  label: "拜访计划",
                  children: <VisitPanel customerId={customerId} />,
                },
                {
                  key: "similar",
                  label: "相似客户",
                  children: <SimilarCustomersPanel customerId={customerId} />,
                },
              ]}
            />

            <EditCustomerModal open={editModalOpen} customer={customer} onClose={() => setEditModalOpen(false)} onUpdated={() => { setEditModalOpen(false); load(); }} />
            <ContactFormModal open={contactModalOpen} customerId={customerId} contact={editingContact} onClose={() => { setContactModalOpen(false); setEditingContact(null); }} onSaved={() => { setContactModalOpen(false); setEditingContact(null); load(); }} />
            <FollowUpFormModal open={followupModalOpen} customerId={customerId} followUp={editingFollowUp} onClose={() => { setFollowupModalOpen(false); setEditingFollowUp(null); }} onSaved={() => { setFollowupModalOpen(false); setEditingFollowUp(null); load(); }} />
            <TagManageModal
              open={tagModalOpen}
              allTags={allTags}
              customerTags={customerTags}
              onLink={handleLinkTag}
              onCreate={handleCreateAndLinkTag}
              onClose={() => setTagModalOpen(false)}
            />

            {/* AI Product Recommendations Modal */}
            <Modal title={<><BulbOutlined /> AI 产品推荐</>} open={recModalOpen} onCancel={() => setRecModalOpen(false)} width={700}
              footer={<Button onClick={() => setRecModalOpen(false)}>关闭</Button>}>
              {recResult && (
                <div>
                  <Card size="small" style={{ marginBottom: 12, background: "#f6ffed" }}>
                    <Typography.Text>{recResult.summary}</Typography.Text>
                  </Card>
                  <Table size="small" dataSource={recResult.recommendations} rowKey="product_name" pagination={false}
                    columns={[
                      { title: "产品", dataIndex: "product_name", width: 180 },
                      { title: "品牌", dataIndex: "brand", width: 120, render: (v: string) => <Tag>{v}</Tag> },
                      { title: "推荐原因", dataIndex: "reason" },
                      { title: "预计价值", dataIndex: "estimated_potential", width: 180 },
                      { title: "优先级", dataIndex: "priority", width: 80, render: (v: string) => <Tag color={v === "高" ? "red" : v === "中" ? "blue" : "default"}>{v}</Tag> },
                    ]}
                  />
                  <Card size="small" type="inner" style={{ marginTop: 12, background: "#fffbe6" }}>
                    <Typography.Text strong>推荐策略：</Typography.Text><Typography.Text>{recResult.approach_strategy}</Typography.Text>
                  </Card>
                </div>
              )}
            </Modal>

            <VendAsSupplierModal
              customer={customer}
              open={vendModalOpen}
              onCancel={() => setVendModalOpen(false)}
              onSuccess={() => setVendModalOpen(false)}
            />
          </>
        )}
    </div>
  );
}

function CustomerOverview({
  customerId,
  contacts,
  followUps,
  nextOpenFollowUp,
  onNewFollowUp,
  onOpenAllFollowUps,
}: {
  customerId: number;
  contacts: Contact[];
  followUps: FollowUp[];
  nextOpenFollowUp?: FollowUp;
  onNewFollowUp: () => void;
  onOpenAllFollowUps: () => void;
}) {
  const recentFollowUps = followUps.slice(0, 5);
  const openFollowUps = followUps.filter(isOpenFollowUp);
  const primaryContact = contacts.find((item) => item.is_primary) || contacts[0];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={16}>
        <CustomerProfile customerId={customerId} />
      </Col>
      <Col xs={24} lg={8}>
        <Card size="small" title="下一步动作">
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            {nextOpenFollowUp ? (
              <div style={{ border: "1px solid #f0f0f0", borderRadius: 6, padding: 10 }}>
                <Space direction="vertical" size={4}>
                  <Space wrap>
                    <Tag color={getFollowUpDueMeta(nextOpenFollowUp).color}>{getFollowUpDueMeta(nextOpenFollowUp).text}</Tag>
                    <FollowUpStatusTag status={nextOpenFollowUp.status} />
                    <FollowUpMethodTag method={nextOpenFollowUp.method} />
                    <FollowUpPriorityTag priority={nextOpenFollowUp.priority} />
                  </Space>
                  <Typography.Text strong>{formatShortDateTime(nextOpenFollowUp.planned_at)}</Typography.Text>
                  <Typography.Text type="secondary">{nextOpenFollowUp.content || "暂无跟进内容"}</Typography.Text>
                </Space>
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待处理跟进" />
            )}
            <Space wrap>
              <Button type="primary" icon={<PhoneOutlined />} onClick={onNewFollowUp}>建跟进</Button>
              <Button onClick={onOpenAllFollowUps}>查看全部跟进</Button>
            </Space>
          </Space>
        </Card>
        <Card size="small" title="联系人" style={{ marginTop: 16 }}>
          {primaryContact ? (
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="姓名">{primaryContact.name}</Descriptions.Item>
              <Descriptions.Item label="职位">{primaryContact.title || "-"}</Descriptions.Item>
              <Descriptions.Item label="电话">{primaryContact.phone || "-"}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{primaryContact.email || "-"}</Descriptions.Item>
            </Descriptions>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无联系人" />
          )}
        </Card>
      </Col>
      <Col xs={24}>
        <Card size="small" title={`最近跟进 (${openFollowUps.length} 未完成)`}>
          {recentFollowUps.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" />
          ) : (
            <List
              size="small"
              dataSource={recentFollowUps}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={(
                      <Space wrap>
                        <Tag color={getFollowUpDueMeta(item).color}>{getFollowUpDueMeta(item).text}</Tag>
                        <FollowUpStatusTag status={item.status} />
                        <FollowUpMethodTag method={item.method} />
                        <span>{formatShortDateTime(item.planned_at)}</span>
                      </Space>
                    )}
                    description={item.content || item.result || "-"}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </Col>
    </Row>
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
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && customer) form.setFieldsValue(customer);
  }, [open, customer, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      await updateCustomer(customer.id, values);
      message.success("客户信息更新成功");
      onUpdated();
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || "更新失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="编辑客户" open={open} onCancel={onClose} onOk={() => form.submit()} confirmLoading={loading} width={720}>
      <Form form={form} layout="vertical" onFinish={onFinish}><CustomerFormFields /></Form>
    </Modal>
  );
}

// --- Contact Form Modal (create + edit) ---

function ContactFormModal({ open, customerId, contact, onClose, onSaved }: { open: boolean; customerId: number; contact: Contact | null; onClose: () => void; onSaved: () => void }) {
  const { message } = App.useApp();
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
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (followUp) {
        form.setFieldsValue({
          ...followUp,
          planned_at: followUp.planned_at ? dayjs(followUp.planned_at) : null,
          completed_at: followUp.completed_at ? dayjs(followUp.completed_at) : null,
        });
      }
      else form.resetFields();
    }
  }, [open, followUp, form]);

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
        planned_at: values.planned_at ? (values.planned_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss") : null,
        completed_at: values.completed_at
          ? (values.completed_at as dayjs.Dayjs).format("YYYY-MM-DD HH:mm:ss")
          : values.status === "completed"
            ? dayjs().format("YYYY-MM-DD HH:mm:ss")
            : null,
      };
      if (followUp) {
        await updateFollowUp(customerId, followUp.id, submitData);
        message.success("跟进记录更新成功");
      } else {
        await createFollowUp(customerId, submitData);
        message.success("跟进记录新增成功");
      }
      form.resetFields();
      onSaved();
    } catch { message.error("保存失败"); } finally { setLoading(false); }
  };

  return (
    <Modal title={followUp ? "编辑跟进记录" : "新增跟进记录"} open={open} onCancel={onClose} onOk={() => form.submit()} confirmLoading={loading}>
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ status: "planned", priority: "medium" }}
        onValuesChange={(changed) => {
          if (changed.status === "completed" && !form.getFieldValue("completed_at")) {
            form.setFieldValue("completed_at", dayjs());
          }
        }}
      >
        {!followUp && (
          <Form.Item>
            <FollowUpAIRecognizer
              customerId={customerId}
              form={form}
              getSeedText={() => {
                const values = form.getFieldsValue(["content", "result"]) as { content?: string; result?: string };
                return [values.content, values.result].filter(Boolean).join("\n");
              }}
              block
            />
          </Form.Item>
        )}
        <Form.Item name="method" label="跟进方式">
          <Select allowClear placeholder="选择方式" options={FOLLOW_UP_METHOD_OPTIONS} />
        </Form.Item>
        <Form.Item name="content" label="跟进内容"><Input.TextArea rows={4} /></Form.Item>
        <Form.Item name="result" label="跟进结果"><Input.TextArea rows={2} /></Form.Item>
        <Form.Item name="status" label="状态">
          <Select allowClear placeholder="选择状态" options={FOLLOW_UP_STATUS_OPTIONS} />
        </Form.Item>
        <Form.Item name="priority" label="优先级">
          <Select allowClear placeholder="选择优先级" options={FOLLOW_UP_PRIORITY_OPTIONS} />
        </Form.Item>
        <Form.Item name="planned_at" label="计划时间"><DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} /></Form.Item>
        <Form.Item name="completed_at" label="完成时间"><DatePicker showTime format="YYYY-MM-DD HH:mm" style={{ width: "100%" }} /></Form.Item>
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
  const healthColor = HEALTH_COLORS[stats.health_label] || "#1677ff";

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="健康度" value={stats.health_score} suffix="分"
              prefix={<HeartOutlined style={{ color: healthColor }} />}
              valueStyle={{ color: healthColor }}
            />
            <Progress percent={stats.health_score} size="small"
              strokeColor={stats.health_score >= 80 ? "#52c41a" : stats.health_score >= 60 ? "#1677ff" : stats.health_score >= 40 ? "#faad14" : "#ff4d4f"}
              style={{ marginTop: 4 }} />
            <div style={{ marginTop: 4, color: "#888", fontSize: 12 }}>{stats.health_label}</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="生命周期" value={stats.lifecycle}
              prefix={<Tag color={LIFECYCLE_COLORS[stats.lifecycle] || "default"} style={{ fontSize: 16 }}>{stats.lifecycle}</Tag>} />
            <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>创建 {stats.created_days} 天</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="订单总数" value={stats.order_count} prefix={<ShoppingCartOutlined />} />
            <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>累计: ¥{stats.total_revenue.toLocaleString()}</div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="信用额度" value={stats.credit_limit} prefix="¥" precision={0} />
            <div style={{ marginTop: 8, color: "#888", fontSize: 12 }}>
              已用 {stats.credit_usage_pct}% | 未付 ¥{stats.outstanding.toLocaleString()}
            </div>
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
        <div style={{ marginTop: 12, color: "#888", fontSize: 12 }}>
          最近订单: {stats.last_order_date?.slice(0, 10)} | 已付金额: ¥{stats.paid_total.toLocaleString()}
        </div>
      )}
    </div>
  );
}

// --- Tag Manage Modal ---

function TagManageModal({
  open,
  allTags,
  customerTags,
  onLink,
  onCreate,
  onClose,
}: {
  open: boolean;
  allTags: TagType[];
  customerTags: TagType[];
  onLink: (id: number) => void;
  onCreate: (name: string, color: string) => Promise<void>;
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("blue");
  const [creating, setCreating] = useState(false);
  const linkedIds = new Set(customerTags.map((t) => t.id));
  const available = allTags.filter((t) => !linkedIds.has(t.id));

  const handleCreate = async () => {
    const name = newTagName.trim();
    if (!name) {
      message.warning("请输入标签名称");
      return;
    }
    setCreating(true);
    try {
      await onCreate(name, newTagColor);
      setNewTagName("");
      setNewTagColor("blue");
    } catch {
      message.error("创建标签失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Modal title="管理标签" open={open} onCancel={onClose} footer={null}>
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        {customerTags.length > 0 && (
          <div>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>当前标签</div>
            {customerTags.map((t) => <Tag key={t.id} color={t.color || "blue"}>{t.name}</Tag>)}
          </div>
        )}
        <div>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>添加已有标签</div>
          {available.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有更多可用的标签" />}
          <Space wrap>
            {available.map((t) => (
              <Tag key={t.id} color={t.color || "default"} style={{ cursor: "pointer" }} onClick={() => onLink(t.id)}>
                + {t.name}
              </Tag>
            ))}
          </Space>
        </div>
        <div>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>新建并添加</div>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="标签名称"
              value={newTagName}
              onChange={(event) => setNewTagName(event.target.value)}
              onPressEnter={handleCreate}
            />
            <Select
              style={{ width: 110 }}
              value={newTagColor}
              options={TAG_COLOR_OPTIONS}
              onChange={setNewTagColor}
            />
            <Button loading={creating} onClick={handleCreate}>创建</Button>
          </Space.Compact>
        </div>
      </Space>
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

// --- Group Panel ---

function GroupPanel({ customerId, customerName }: { customerId: number; customerName: string }) {
  const { message } = App.useApp();
  const [children, setChildren] = useState<Customer[]>([]);
  const [stats, setStats] = useState<GroupStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [linkOpen, setLinkOpen] = useState(false);
  const [parentId, setParentId] = useState<number>(0);

  const load = async () => {
    try {
      const [cResp, sResp] = await Promise.all([getChildren(customerId), getGroupStats(customerId)]);
      setChildren((cResp.data.data as Customer[]) || []);
      setStats(sResp.data.data as GroupStats);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [customerId]);

  const handleLink = async () => {
    if (!parentId) return;
    try { await linkParent(customerId, parentId); message.success("关联成功"); setLinkOpen(false); load(); } catch { message.error("关联失败"); }
  };

  const handleUnlink = async () => {
    try { await unlinkParent(customerId); message.success("已解除关联"); load(); } catch { message.error("解除失败"); }
  };

  if (loading) return <Spin />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<LinkOutlined />} onClick={() => setLinkOpen(true)}>关联母公司</Button>
        <Button icon={<DisconnectOutlined />} onClick={handleUnlink}>解除关联</Button>
      </Space>

      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="集团客户数" value={stats.members} /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="集团订单数" value={stats.agg_orders} /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="集团营收" value={stats.agg_revenue} prefix="¥" /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="集团信用额" value={stats.agg_credit} prefix="¥" /></Card></Col>
        </Row>
      )}

      <Card size="small" title={`子公司 (${children.length})`}>
        {children.length === 0 ? <Empty description="暂无子公司" /> : (
          <List dataSource={children} renderItem={(c) => (
            <List.Item extra={<Tag color={c.level === "A" ? "red" : "default"}>{c.level}</Tag>}>
              <List.Item.Meta
                title={<a onClick={() => window.open(`/customers/${c.id}`, '_self')}>{c.name}</a>}
                description={`${c.industry || "-"} · ${c.region || "-"} · ${c.contact_person || "无联系人"}`}
              />
            </List.Item>
          )} />
        )}
      </Card>

      <Modal title="关联母客户" open={linkOpen} onCancel={() => setLinkOpen(false)} onOk={handleLink}>
        <Form.Item label="母客户ID">
          <Input value={parentId || ""} onChange={(e) => setParentId(Number(e.target.value) || 0)} placeholder="请输入母客户ID" />
        </Form.Item>
      </Modal>
    </div>
  );
}

// --- Similar Customers Panel ---

function SimilarCustomersPanel({ customerId }: { customerId: number }) {
  const [similar, setSimilar] = useState<SimilarCustomer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSimilarCustomers(customerId)
      .then((r) => setSimilar((r.data.data as SimilarCustomer[]) || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [customerId]);

  if (loading) return <Spin />;
  if (similar.length === 0) return <Empty description="暂无相似客户（需先生成嵌入向量）" />;

  return (
    <Table<SimilarCustomer>
      dataSource={similar}
      rowKey="id"
      size="small"
      pagination={false}
      columns={[
        {
          title: "客户名称", dataIndex: "name", key: "name",
          render: (name: string, r: SimilarCustomer) => (
            <a href={`/customers/${r.id}`}>{name}</a>
          ),
        },
        { title: "行业", dataIndex: "industry", key: "industry", render: (v: string) => <Tag>{v || "-"}</Tag> },
        { title: "区域", dataIndex: "region", key: "region" },
        {
          title: "相似度", dataIndex: "similarity", key: "similarity",
          render: (v: number) => `${(v * 100).toFixed(1)}%`,
          sorter: (a: SimilarCustomer, b: SimilarCustomer) => a.similarity - b.similarity,
        },
      ]}
    />
  );
}


// --- Visit Panel ---

function VisitPanel({ customerId }: { customerId: number }) {
  const { message } = App.useApp();
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingVisit, setEditingVisit] = useState<Visit | null>(null);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const resp = await getCustomerVisits(customerId);
      setVisits((resp.data.data as unknown as Visit[]) || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [customerId]);

  const openForm = (v?: Visit) => {
    setEditingVisit(v || null);
    if (v) form.setFieldsValue({ ...v, visit_date: v.visit_date?.slice(0, 10), followup_date: v.followup_date?.slice(0, 10) });
    else form.resetFields();
    setModalOpen(true);
  };

  const onFinish = async (values: Record<string, unknown>) => {
    try {
      if (editingVisit) {
        await updateCustomerVisit(customerId, editingVisit.id, values as Record<string, unknown>);
        message.success("更新成功");
      } else {
        await createCustomerVisit(customerId, values as Record<string, unknown>);
        message.success("创建成功");
      }
      setModalOpen(false);
      load();
    } catch { message.error("保存失败"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteCustomerVisit(customerId, id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
  };

  const TYPE: Record<string, string> = { visit: "拜访", call: "电话", online: "线上" };
  const STATUS: Record<string, { color: string; label: string }> = {
    planned: { color: "default", label: "计划中" }, completed: { color: "green", label: "已完成" },
    cancelled: { color: "red", label: "已取消" },
  };

  return (
    <div>
      <Button type="primary" onClick={() => openForm()} style={{ marginBottom: 16 }}>新增拜访</Button>
      {loading ? <Spin /> : visits.length === 0 ? <Empty description="暂无拜访记录" /> : (
        <List dataSource={visits} renderItem={(v) => (
          <Card size="small" style={{ marginBottom: 8 }}
            actions={[
              <EditOutlined key="edit" onClick={() => openForm(v)} />,
              <Popconfirm key="del" title="确定删除?" onConfirm={() => handleDelete(v.id)}><DeleteOutlined /></Popconfirm>,
            ]}
          >
            <Row gutter={8}>
              <Col span={6}><Typography.Text strong>{v.title || "无标题"}</Typography.Text></Col>
              <Col span={4}><Tag>{TYPE[v.type as string] || v.type}</Tag></Col>
              <Col span={4}><Tag color={STATUS[v.status as string]?.color}>{STATUS[v.status as string]?.label || v.status}</Tag></Col>
              <Col span={4}>{v.visit_date?.slice(0, 10) || "-"}</Col>
              <Col span={6}>{v.stage && <Tag color="blue">{v.stage}</Tag>}</Col>
            </Row>
            {v.content && <Typography.Paragraph ellipsis={{ rows: 2 }} style={{ marginTop: 8, fontSize: 13 }}>{v.content}</Typography.Paragraph>}
          </Card>
        )} />
      )}

      <Modal title={editingVisit ? "编辑拜访" : "新增拜访"} open={modalOpen}
        onCancel={() => setModalOpen(false)} onOk={() => form.submit()} width={600}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="title" label="标题"><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="type" label="方式"><Select options={[{ value: "visit", label: "拜访" }, { value: "call", label: "电话" }, { value: "online", label: "线上" }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态"><Select options={[{ value: "planned", label: "计划中" }, { value: "completed", label: "已完成" }, { value: "cancelled", label: "已取消" }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="visit_date" label="日期"><Input placeholder="YYYY-MM-DD" /></Form.Item></Col>
          </Row>
          <Form.Item name="purpose" label="拜访目的"><Input /></Form.Item>
          <Form.Item name="content" label="拜访内容"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="result" label="拜访结果"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="next_plan" label="下一步计划"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
