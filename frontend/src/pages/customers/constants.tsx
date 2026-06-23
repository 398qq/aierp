// Customer list constants, enums, and shared formatters.
//
// Single source of truth for filter dropdown values, CRM view presets,
// tag color palette, due-bucket metadata, and small pure helpers
// used across the customer workbench.
//
// Mutating these does not require a code change; they are static
// declarations read at module load.

import {
  BulbOutlined,
  PhoneOutlined,
  SendOutlined,
  ShoppingCartOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { ReactNode } from "react";
import type { Customer, DashboardStats, FollowUpReminder, GlobalFollowUp } from "../../types";

export const INDUSTRIES = [
  "汽车电子",
  "消费电子",
  "工业控制",
  "通信设备",
  "医疗设备",
  "安防监控",
  "其他",
];
export const LEVELS = ["A", "B", "C", "D"];
export const REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
export const SOURCES = ["展会", "转介绍", "线上推广", "陌生拜访", "公司资源"];
export const CREDIT_LEVELS = ["AAA", "AA", "A", "B", "C"];

export const TAG_COLOR_OPTIONS: { value: string; label: string }[] = [
  { value: "blue", label: "蓝色" },
  { value: "green", label: "绿色" },
  { value: "orange", label: "橙色" },
  { value: "red", label: "红色" },
  { value: "purple", label: "紫色" },
  { value: "cyan", label: "青色" },
  { value: "default", label: "默认" },
];

export type SceneValue =
  | "all"
  | "key_accounts"
  | "east_region"
  | "expo_leads"
  | "high_credit"
  | "pending_erp";

export type SmartTaskKey =
  | "today"
  | "overdue"
  | "high_risk"
  | "key_stale"
  | "new_customers"
  | "ai_suggested"
  | "all";

export type CustomerWorkbenchTab = "customers" | "followups";
export type CustomerViewMode = "table" | "board";
export type CrmObjectKey = "companies" | "people" | "opportunities" | "quotations" | "orders";

export const SCENE_OPTIONS: { label: string; value: SceneValue }[] = [
  { label: "全部客户", value: "all" },
  { label: "重点客户", value: "key_accounts" },
  { label: "华东区域", value: "east_region" },
  { label: "展会线索", value: "expo_leads" },
  { label: "高信用", value: "high_credit" },
  { label: "待补ERP资料", value: "pending_erp" },
];

export const SCENE_FILTERS: Record<
  SceneValue,
  { level?: string; region?: string; source?: string; creditLevel?: string }
> = {
  all: {},
  key_accounts: { level: "A" },
  east_region: { region: "华东" },
  expo_leads: { source: "展会" },
  high_credit: { creditLevel: "A" },
  pending_erp: {},
};

// Customer lifecycle status — mirrors backend state machine
export const CUSTOMER_STATUSES = ["new_lead", "active", "converted", "vip", "inactive", "churned"];

export const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  new_lead: { label: "新潜客", color: "blue" },
  active: { label: "活跃", color: "green" },
  converted: { label: "已成交", color: "cyan" },
  vip: { label: "VIP", color: "gold" },
  inactive: { label: "不活跃", color: "orange" },
  churned: { label: "流失", color: "red" },
};

// Customer group presets
export type GroupValue = "all" | "new" | "vip_active" | "at_risk" | "dormant";
export const GROUP_OPTIONS: { label: string; value: GroupValue }[] = [
  { label: "全部", value: "all" },
  { label: "新潜客", value: "new" },
  { label: "VIP/活跃", value: "vip_active" },
  { label: "风险客户", value: "at_risk" },
  { label: "沉默客户", value: "dormant" },
];

export const GROUP_FILTERS: Record<GroupValue, { status?: string[] }> = {
  all: {},
  new: { status: ["new_lead"] },
  vip_active: { status: ["vip", "active"] },
  at_risk: { status: ["inactive", "churned"] },
  dormant: { status: ["inactive"] },
};

export const COL_LABEL_MAP: Record<string, string> = {
  code: "客户编码",
  name: "客户名称",
  short_name: "简称",
  industry: "行业",
  level: "等级",
  region: "区域",
  credit_level: "信用等级",
  credit_limit: "信用额度",
  payment_terms: "付款条件",
  currency: "币种",
  tax_id: "税号",
  delivery_address: "收货地址",
  status: "生命周期",
  health: "健康度",
  next_followup: "下次跟进",
  tags: "标签",
  owner: "负责人",
  contact_person: "联系人",
  phone: "电话",
  email: "邮箱",
  last_contacted_at: "最近联系",
  source: "来源",
  customer_type: "客户类型",
  created_at: "创建时间",
  actions: "操作",
};

export const DEFAULT_VISIBLE_COL_KEYS = [
  "code",
  "name",
  "status",
  "level",
  "region",
  "credit_level",
  "payment_terms",
  "owner",
  "next_followup",
  "last_contacted_at",
  "tags",
  "actions",
];
export const PEOPLE_VISIBLE_COL_KEYS = [
  "name",
  "contact_person",
  "phone",
  "email",
  "owner",
  "last_contacted_at",
  "actions",
];

export type ReminderBucket = "all" | FollowUpReminder["due_bucket"];
export type GlobalFollowUpBucket = "all" | GlobalFollowUp["due_bucket"];

export const REMINDER_BUCKETS: { key: ReminderBucket; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "overdue", label: "逾期" },
  { key: "today", label: "今日" },
  { key: "upcoming", label: "未来" },
];

export const GLOBAL_FOLLOW_UP_BUCKETS: { key: GlobalFollowUpBucket; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "overdue", label: "逾期" },
  { key: "today", label: "今日" },
  { key: "upcoming", label: "未来" },
  { key: "unscheduled", label: "未排期" },
  { key: "closed", label: "已完成" },
];

export const SMART_TASK_LABELS: Record<SmartTaskKey, string> = {
  today: "今日必做",
  overdue: "逾期跟进",
  high_risk: "高风险客户",
  key_stale: "A类长期未联系",
  new_customers: "新客户首联",
  ai_suggested: "AI推荐动作",
  all: "全部客户",
};

export const CRM_OBJECTS: Array<{
  key: CrmObjectKey;
  label: string;
  title: string;
  path: string;
  icon: ReactNode;
}> = [
  {
    key: "companies",
    label: "Companies",
    title: "客户公司",
    path: "/customers",
    icon: <UserOutlined />,
  },
  {
    key: "people",
    label: "People",
    title: "联系人",
    path: "/customers?view=people",
    icon: <PhoneOutlined />,
  },
  {
    key: "opportunities",
    label: "Opportunities",
    title: "商机",
    path: "/sales/opportunities",
    icon: <BulbOutlined />,
  },
  {
    key: "quotations",
    label: "Quotes",
    title: "报价",
    path: "/sales/quotations",
    icon: <SendOutlined />,
  },
  {
    key: "orders",
    label: "Orders",
    title: "订单",
    path: "/sales/orders",
    icon: <ShoppingCartOutlined />,
  },
];

export const CRM_VIEW_PRESETS = [
  {
    key: "all",
    label: "All companies",
    description: "全部公司对象",
    task: "all" as SmartTaskKey,
    view: "table" as CustomerViewMode,
  },
  {
    key: "key",
    label: "Key accounts",
    description: "A级客户看板",
    task: "all" as SmartTaskKey,
    scene: "key_accounts" as SceneValue,
    view: "board" as CustomerViewMode,
  },
  {
    key: "today",
    label: "Today follow-ups",
    description: "今日必须推进",
    task: "today" as SmartTaskKey,
    view: "table" as CustomerViewMode,
  },
  {
    key: "risk",
    label: "At risk",
    description: "逾期或健康度低",
    task: "high_risk" as SmartTaskKey,
    view: "board" as CustomerViewMode,
  },
  {
    key: "new",
    label: "New companies",
    description: "14天内新建",
    task: "new_customers" as SmartTaskKey,
    view: "table" as CustomerViewMode,
  },
];

export const DEFAULT_STATS: DashboardStats = {
  total: 0,
  by_industry: [],
  by_level: [],
  by_region: [],
  by_source: [],
  by_type: [],
  monthly: [],
};

// === small pure helpers (no JSX, no React imports) ========================

export const getLevelColor = (level?: string | null): string => {
  if (!level) return "default";
  if (level === "A") return "red";
  if (level === "B") return "orange";
  if (level === "C") return "gold";
  return "default";
};

export const getHealthColor = (value?: number | null): string => {
  if (value == null) return "default";
  if (value >= 80) return "green";
  if (value >= 60) return "gold";
  return "red";
};

export const formatDate = (value?: string | null): string => {
  if (!value) return "-";
  return value.slice(0, 10);
};

export const formatDateTime = (value?: string | null): string => {
  if (!value) return "-";
  return value.slice(0, 16).replace("T", " ");
};

export const formatReminderRefreshTime = (value: Date | null): string => {
  if (!value) return "尚未刷新";
  const diffMs = Date.now() - value.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return "刚刚刷新";
  if (diffMinutes < 60) return `${diffMinutes}分钟前刷新`;
  return `${value.getHours().toString().padStart(2, "0")}:${value.getMinutes().toString().padStart(2, "0")} 刷新`;
};

export const plusOneDayIso = (value?: string | null): string => {
  const currentTime = value ? new Date(value).getTime() : Date.now();
  const baseTime = Number.isNaN(currentTime) ? Date.now() : Math.max(currentTime, Date.now());
  return new Date(baseTime + 24 * 60 * 60 * 1000).toISOString();
};

export const getReminderDueMeta = (item: FollowUpReminder) => {
  if (item.due_bucket === "overdue") return { text: `逾期 ${item.overdue_days} 天`, color: "red" };
  if (item.due_bucket === "today") return { text: "今日待跟进", color: "orange" };
  return { text: `${item.days_until ?? "-"} 天后`, color: "blue" };
};

export const getGlobalFollowUpDueMeta = (item: GlobalFollowUp) => {
  if (item.due_bucket === "overdue") return { text: `逾期 ${item.overdue_days} 天`, color: "red" };
  if (item.due_bucket === "today") return { text: "今日待跟进", color: "orange" };
  if (item.due_bucket === "upcoming")
    return { text: `${item.days_until ?? "-"} 天后`, color: "blue" };
  if (item.due_bucket === "closed") return { text: "已完成", color: "green" };
  return { text: "未排期", color: "default" };
};

export const getDaysSince = (value?: string | null): number | null => {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.floor((Date.now() - time) / (24 * 60 * 60 * 1000));
};

export const getCustomerPriorityScore = (customer: Customer, next?: FollowUpReminder): number => {
  let score = 35;
  if (customer.level === "A") score += 18;
  if (customer.level === "B") score += 10;
  if (next?.due_bucket === "overdue") score += 28;
  if (next?.due_bucket === "today") score += 20;
  if (customer.health_score != null && customer.health_score < 60) score += 18;
  const contactAge = getDaysSince(customer.last_contacted_at);
  if (contactAge == null) score += 10;
  else if (contactAge > 60) score += 16;
  else if (contactAge > 30) score += 8;
  return Math.min(100, score);
};

export const getCustomerSuggestedAction = (customer: Customer, next?: FollowUpReminder): string => {
  if (next?.due_bucket === "overdue") return "立即补跟进并更新结果";
  if (next?.due_bucket === "today") return "按计划完成今日跟进";
  if (customer.health_score != null && customer.health_score < 60) return "查看风险原因并安排挽回";
  const contactAge = getDaysSince(customer.last_contacted_at);
  if (customer.level === "A" && contactAge != null && contactAge > 30) {
    return "联系关键客户并确认近期需求";
  }
  const createdAge = getDaysSince(customer.created_at);
  if (createdAge != null && createdAge <= 14) return "完成新客户首联";
  return "补充客户画像并规划下一步";
};

export const buildFollowUpTalkTrack = (customer: Customer, next?: FollowUpReminder): string[] => {
  const name = customer.contact_person || "客户";
  const action = getCustomerSuggestedAction(customer, next);
  const lines = [
    `${name}您好，我这边想同步一下${customer.name}近期项目和物料需求，看看有没有需要我们提前配合的地方。`,
    `我注意到当前建议动作是「${action}」，所以这次主要想确认需求进度、交付时间和后续采购计划。`,
    "如果方便，我可以先整理一版适配产品/报价建议，您确认方向后我们再推进下一步。",
  ];
  if (next?.due_bucket === "overdue") {
    lines[0] = `${name}您好，之前计划的跟进已逾期，我先补充确认一下当前项目状态和需要我们处理的事项。`;
  }
  if (customer.health_score != null && customer.health_score < 60) {
    lines[1] =
      "近期客户健康度偏低，我想重点确认是否存在交付、价格、响应或备货方面的问题，我们这边及时调整。";
  }
  return lines;
};

export const buildFollowUpPlanContent = (customer: Customer, next?: FollowUpReminder): string => {
  const talkTrack = buildFollowUpTalkTrack(customer, next);
  return [
    `AI建议动作：${getCustomerSuggestedAction(customer, next)}`,
    `客户优先级：${getCustomerPriorityScore(customer, next)}`,
    "",
    "建议沟通话术：",
    ...talkTrack.map((line, index) => `${index + 1}. ${line}`),
  ].join("\n");
};
