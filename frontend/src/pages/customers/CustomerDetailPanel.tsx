/**
 * CustomerDetailPanel — 三 Tab 右侧详情面板
 *
 * Tab 1: 基本信息 — 标题、指标、联系信息、快捷操作
 * Tab 2: 360 视图 — 交易历史、标签、联系人、机会、警告、文档
 * Tab 3: AI 洞察 — 客户洞察 + 智能推荐
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Descriptions,
  Drawer,
  Empty,
  List,
  message,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  Grid,
} from "antd";
import {
  EditOutlined,
  MailOutlined,
  PhoneOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import { getCustomer360, getCustomerQuotationHistory, getCustomerLogs, getContacts, getCustomerTags, getApiErrorMessage } from "@/api";
import type { CustomerLog, CustomerQuotationHistory } from "@/types";
import { StatusTag } from "@/ui";
import { CustomerAIPanel } from "./CustomerAIPanel";
import { CustomerBusinessInsight } from "./CustomerBusinessInsight";
import { CREDIT_COLORS, STATUS_CONFIG } from "./constants";

const { Text, Title } = Typography;

// ── 类型 ──

interface DetailPanelProps {
  customerId: number;
  customerName: string;
  customer: Record<string, unknown>;
  open: boolean;
  onClose: () => void;
  onEdit?: () => void;
}

interface QuotationRecord {
  id: number;
  quotation_no: string;
  total_amount: number;
  status: string;
  created_at: string;
}

interface ActivityLog {
  id: number;
  action: string;
  summary: string | null;
  created_at: string;
}

interface Customer360Data {
  transactions?: Array<{ id: number; order_no: string; total_amount: number; status: string }>;
  opportunities?: Array<{ id: number; title: string; stage: string; amount: number }>;
  alerts?: Array<{ id: number; rule_name: string; message: string }>;
  rfm?: { r_score: number; f_score: number; m_score: number; segment: string };
}

// ── 常量 ──

function relativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (diff === 0) return "今天";
  if (diff === 1) return "昨天";
  if (diff < 30) return `${diff}天前`;
  if (diff < 365) return `${Math.floor(diff / 30)}月前`;
  return `${Math.floor(diff / 365)}年前`;
}

const ORDER_COLUMNS: ColumnsType<QuotationRecord> = [
  { title: "编号", dataIndex: "quotation_no", width: 130 },
  {
    title: "金额", dataIndex: "total_amount", width: 120, align: "right",
    render: (v: number) => `¥${v.toLocaleString("zh-CN")}`,
  },
  {
    title: "状态", dataIndex: "status", width: 80,
    render: (s: string) => {
      const tone = s === "won" ? "success" : s === "lost" ? "danger" : "default";
      return <StatusTag tone={tone}>{s}</StatusTag>;
    },
  },
  {
    title: "日期", dataIndex: "created_at", width: 110,
    render: (d: string) => d?.slice(0, 10) || "-",
  },
];

const LOG_COLUMNS: ColumnsType<ActivityLog> = [
  { title: "操作", dataIndex: "action", width: 100 },
  { title: "详情", dataIndex: "summary", ellipsis: true, render: (value: string | null) => value || "-" },
  {
    title: "时间", dataIndex: "created_at", width: 160,
    render: (d: string) => d && new Date(d).toLocaleString("zh-CN"),
  },
];

// ── 组件 ──

export const CustomerDetailPanel: React.FC<DetailPanelProps> = ({
  customerId,
  customerName,
  customer,
  open,
  onClose,
  onEdit,
}) => {
  const navigate = useNavigate();
  const screens = Grid.useBreakpoint();
  const [activeTab, setActiveTab] = useState("basic");
  const [loading360, setLoading360] = useState(false);
  const [loaded360, setLoaded360] = useState(false);
  const [data360, setData360] = useState<Customer360Data | null>(null);
  const [quotations, setQuotations] = useState<QuotationRecord[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [contacts, setContacts] = useState<Array<{ id: number; name: string; phone?: string; email?: string; role?: string }>>([]);
  const [tags, setTags] = useState<Array<{ id: number; name: string; color?: string }>>([]);

  const loadBasic = useCallback(async () => {
    if (!customerId || !open) return;
    try {
      const response = await getContacts(customerId);
      const payload = (response.data as { data?: Array<typeof contacts[0]> })?.data;
      setContacts(payload || []);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载联系人失败"));
    }
  }, [customerId, open]);

  const load360 = useCallback(async () => {
    if (!customerId || !open || loaded360) return;
    setLoading360(true);
    try {
      const [res360, resQuotes, resLogs, resTags] = await Promise.allSettled([
        getCustomer360(customerId),
        getCustomerQuotationHistory(customerId),
        getCustomerLogs(customerId),
        getCustomerTags(customerId),
      ]);

      if (res360.status === "fulfilled") {
        const payload = (res360.value.data as { data?: Customer360Data })?.data;
        setData360(payload || null);
      }
      if (resQuotes.status === "fulfilled") {
        const payload = resQuotes.value.data.data as CustomerQuotationHistory | undefined;
        setQuotations((payload?.quotations || []).slice(0, 5) as QuotationRecord[]);
      }
      if (resLogs.status === "fulfilled") {
        const payload = resLogs.value.data.data as CustomerLog[] | undefined;
        setLogs((payload || []).slice(0, 20));
      }
      if (resTags.status === "fulfilled") {
        const payload = (resTags.value.data as { data?: Array<typeof tags[0]> })?.data;
        setTags(payload || []);
      }
      setLoaded360(true);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载客户 360 失败")); } finally {
      setLoading360(false);
    }
  }, [customerId, loaded360, open]);

  useEffect(() => {
    if (open) {
      setActiveTab("basic");
      setLoaded360(false);
      loadBasic();
    }
  }, [loadBasic, open]);

  useEffect(() => {
    if (activeTab === "360") load360();
  }, [activeTab, load360]);

  const statusVal = (customer.status as string) || "new_lead";
  const statusCfg = STATUS_CONFIG[statusVal] || { label: statusVal, color: "default" };

  // ── Tab 1：基本信息 ──
  const tabBasic = (
    <div style={{ padding: "8px 0" }}>
      {/* 关键指标 */}
      <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="行业">
          {(customer.industry as string) || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="地区">
          {(customer.region as string) || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <StatusTag tone={statusCfg.color as "green" | "blue" | "gold" | "orange" | "red" | "cyan"}>
            {statusCfg.label}
          </StatusTag>
        </Descriptions.Item>
        <Descriptions.Item label="信用等级">
          <Tag color={CREDIT_COLORS[(customer.credit_level as string) || ""]}>
            {(customer.credit_level as string) || "-"}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="信用额度">
          ¥{((customer.credit_limit as number) || 0).toLocaleString("zh-CN")}
        </Descriptions.Item>
        <Descriptions.Item label="付款条款">
          {(customer.payment_terms as string) || "-"}
        </Descriptions.Item>
        <Descriptions.Item label="最后互动">
          {(customer.last_contacted_at as string) ? relativeTime(customer.last_contacted_at as string) : "-"}
        </Descriptions.Item>
        <Descriptions.Item label="累计交易">
          ¥{((customer.total_amount as number) || 0).toLocaleString("zh-CN")}
        </Descriptions.Item>
      </Descriptions>

      {/* 联系方式 */}
      <Title level={5}>联系方式</Title>
      {((): React.ReactNode => {
        const phone = customer.phone as string | undefined;
        const email = customer.email as string | undefined;
        if (!phone && !email) return <Text type="secondary">暂无电话/邮箱</Text>;
        return (
          <Space direction="vertical" size={4} style={{ width: "100%" }}>
            {phone && <Text copyable><PhoneOutlined /> {phone}</Text>}
            {email && <Text copyable><MailOutlined /> {email}</Text>}
          </Space>
        );
      })()}

      {contacts.length > 0 && (
        <>
          <Title level={5} style={{ marginTop: 16 }}>主联系人</Title>
          <List
            size="small"
            dataSource={contacts.slice(0, 3)}
            renderItem={(c) => (
              <List.Item>
                <Space>
                  <Text strong>{c.name}</Text>
                  {c.role && <Text type="secondary">({c.role as string})</Text>}
                  {c.phone && <Text copyable><PhoneOutlined /> {c.phone as string}</Text>}
                  {c.email && <Text copyable><MailOutlined /> {c.email as string}</Text>}
                </Space>
              </List.Item>
            )}
          />
        </>
      )}

      {/* 快捷操作 */}
      <div style={{ marginTop: 16 }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(`/sales/opportunities/new?customer_id=${customerId}`)}>新增机会</Button>
          <Button onClick={() => navigate(`/customers/${customerId}/follow-ups/new`)}>跟进任务</Button>
          <Button icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
        </Space>
      </div>
    </div>
  );

  // ── Tab 2：360 视图 ──
  const tab360 = (
    <div style={{ padding: "8px 0" }}>
      {loading360 ? (
        <Spin />
      ) : (
        <>
          {/* 交易历史 */}
          <Title level={5}>📊 交易历史</Title>
          <Table<QuotationRecord>
            rowKey="id"
            columns={ORDER_COLUMNS}
            dataSource={quotations}
            size="small"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无交易记录" /> }}
            style={{ marginBottom: 16 }}
          />

          {/* 标签 */}
          <Title level={5}>🏷️ 标签</Title>
          {tags.length > 0 ? (
            <Space wrap style={{ marginBottom: 16 }}>
              {tags.map((t) => (
                <Tag key={t.id} color={t.color as string | undefined}>{t.name}</Tag>
              ))}
            </Space>
          ) : (
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>暂无标签</Text>
          )}

          {/* 机会进度 */}
          {data360?.opportunities && data360.opportunities.length > 0 && (
            <>
              <Title level={5}>🎯 机会进度</Title>
              <List
                size="small"
                dataSource={data360.opportunities.slice(0, 3)}
                renderItem={(opp) => (
                  <List.Item>
                    <Space>
                      <Text>{opp.title}</Text>
                      <Tag>{opp.stage}</Tag>
                      <Text type="secondary">¥{opp.amount?.toLocaleString("zh-CN") || "0"}</Text>
                    </Space>
                  </List.Item>
                )}
                style={{ marginBottom: 16 }}
              />
            </>
          )}

          {/* RFM */}
          {data360?.rfm && (
            <>
              <Title level={5}>📈 RFM 分析</Title>
              <Descriptions column={4} size="small">
                <Descriptions.Item label="R">R{data360.rfm.r_score}</Descriptions.Item>
                <Descriptions.Item label="F">F{data360.rfm.f_score}</Descriptions.Item>
                <Descriptions.Item label="M">M{data360.rfm.m_score}</Descriptions.Item>
                <Descriptions.Item label="分类">
                  <Tag>{data360.rfm.segment}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </>
          )}

          {/* 审计日志 */}
          {logs.length > 0 && (
            <>
              <Title level={5} style={{ marginTop: 16 }}>📄 操作记录</Title>
              <Table<ActivityLog>
                rowKey="id"
                columns={LOG_COLUMNS}
                dataSource={logs.slice(0, 10)}
                size="small"
                pagination={false}
              />
            </>
          )}
        </>
      )}
    </div>
  );

  // ── Tab 3：AI 洞察 (RFM + 流失预警 + 产品推荐 + 语义搜索) ──
  const tabAI = (
    <CustomerAIPanel customerId={customerId} customerName={customerName} />
  );

  // ── Tab 4：商业洞察 (健康度 + 营收 + 回款 + 增长 + 对标) ──
  const tabBusiness = (
    <CustomerBusinessInsight customerId={customerId} customerName={customerName} />
  );

  return (
    <Drawer
      title={
        <Space>
          <Text strong style={{ fontSize: 16 }}>{customerName}</Text>
          <StatusTag tone={statusCfg.color as "green" | "blue" | "gold" | "orange" | "red" | "cyan"}>
            {statusCfg.label}
          </StatusTag>
        </Space>
      }
      open={open}
      onClose={onClose}
      width={screens.xl ? 720 : screens.md ? 620 : "100%"}
      className="customer-detail-drawer"
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        destroyOnHidden
        items={[
          { key: "basic", label: "基本信息", children: tabBasic },
          { key: "360", label: "360 视图", children: tab360 },
          { key: "ai", label: "AI 洞察", children: tabAI },
          { key: "business", label: "商业洞察", children: tabBusiness },
        ]}
      />
    </Drawer>
  );
};

export default CustomerDetailPanel;
