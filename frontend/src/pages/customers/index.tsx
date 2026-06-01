import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Divider,
  Dropdown,
  Drawer,
  Empty,
  DatePicker,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Popover,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  Upload,
} from "antd";
import {
  BellOutlined,
  BulbOutlined,
  DeleteOutlined,
  DownOutlined,
  DownloadOutlined,
  EyeOutlined,
  FilterOutlined,
  MergeCellsOutlined,
  MoreOutlined,
  PhoneOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  SendOutlined,
  ShoppingCartOutlined,
  SwapOutlined,
  TagsOutlined,
  UploadOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import {
  batchDeleteCustomers,
  batchTagCustomers,
  checkAlerts,
  createTag,
  createFollowUp,
  deleteCustomer,
  detectDuplicates,
  downloadImportTemplate,
  exportCustomers,
  generateDefaultCustomerTags,
  getAlertEvents,
  getCustomer,
  getCustomers,
  getCustomerStats,
  getDashboardStats,
  getFollowUpReminders,
  getGlobalFollowUps,
  getTags,
  importCustomers,
  markAllAlertsRead,
  mergeCustomers,
  recommendProductsForCustomer,
  searchSimilarCustomers,
  updateFollowUp,
} from "../../api";
import type {
  Customer,
  CustomerProductMatch,
  CustomerStats,
  DashboardStats,
  DuplicatePair,
  FollowUpReminder,
  GlobalFollowUp,
  OverdueFollowUp,
  SimilarCustomer,
  Tag as TagType,
} from "../../types";
import VendAsSupplierModal from "./VendAsSupplierModal";
import CustomerModuleShell from "./CustomerModuleShell";
import FollowUpAIRecognizer from "./FollowUpAIRecognizer";
import dayjs from "dayjs";
import {
  FOLLOW_UP_METHOD_OPTIONS,
  FOLLOW_UP_PRIORITY_OPTIONS,
  FOLLOW_UP_STATUS_OPTIONS,
  FollowUpMethodTag,
  FollowUpPriorityTag,
  FollowUpStatusTag,
} from "./customerUi";

const INDUSTRIES = ["汽车电子", "消费电子", "工业控制", "通信设备", "医疗设备", "安防监控", "其他"];
const LEVELS = ["A", "B", "C", "D"];
const REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"];
const SOURCES = ["展会", "转介绍", "线上推广", "陌生拜访", "公司资源"];
const CREDIT_LEVELS = ["AAA", "AA", "A", "B", "C"];
const TAG_COLOR_OPTIONS = [
  { value: "blue", label: "蓝色" },
  { value: "green", label: "绿色" },
  { value: "orange", label: "橙色" },
  { value: "red", label: "红色" },
  { value: "purple", label: "紫色" },
  { value: "cyan", label: "青色" },
  { value: "default", label: "默认" },
];

type SceneValue = "all" | "key_accounts" | "east_region" | "expo_leads" | "high_credit";
type SmartTaskKey = "today" | "overdue" | "high_risk" | "key_stale" | "new_customers" | "ai_suggested" | "all";
type CustomerWorkbenchTab = "customers" | "followups";
type CustomerViewMode = "table" | "board";
type CrmObjectKey = "companies" | "people" | "opportunities" | "quotations" | "orders";

const SCENE_OPTIONS: { label: string; value: SceneValue }[] = [
  { label: "全部客户", value: "all" },
  { label: "重点客户", value: "key_accounts" },
  { label: "华东区域", value: "east_region" },
  { label: "展会线索", value: "expo_leads" },
  { label: "高信用", value: "high_credit" },
];

const SCENE_FILTERS: Record<SceneValue, { level?: string; region?: string; source?: string; creditLevel?: string }> = {
  all: {},
  key_accounts: { level: "A" },
  east_region: { region: "华东" },
  expo_leads: { source: "展会" },
  high_credit: { creditLevel: "A" },
};

const COL_LABEL_MAP: Record<string, string> = {
  code: "编码",
  name: "名称",
  industry: "行业",
  level: "等级",
  region: "区域",
  credit_level: "信用",
  health: "健康度",
  next_followup: "下一次跟进",
  tags: "标签",
  owner: "负责人",
  contact_person: "联系人",
  phone: "电话",
  email: "邮箱",
  last_contacted_at: "最近联系",
  source: "来源",
  created_at: "创建时间",
  actions: "操作",
};

const DEFAULT_VISIBLE_COL_KEYS = ["name", "level", "region", "owner", "next_followup", "last_contacted_at", "tags", "actions"];
const PEOPLE_VISIBLE_COL_KEYS = ["name", "contact_person", "phone", "email", "owner", "last_contacted_at", "actions"];
type ReminderBucket = "all" | FollowUpReminder["due_bucket"];
type GlobalFollowUpBucket = "all" | GlobalFollowUp["due_bucket"];

const REMINDER_BUCKETS: { key: ReminderBucket; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "overdue", label: "逾期" },
  { key: "today", label: "今日" },
  { key: "upcoming", label: "未来" },
];

const GLOBAL_FOLLOW_UP_BUCKETS: { key: GlobalFollowUpBucket; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "overdue", label: "逾期" },
  { key: "today", label: "今日" },
  { key: "upcoming", label: "未来" },
  { key: "unscheduled", label: "未排期" },
  { key: "closed", label: "已完成" },
];

const SMART_TASK_LABELS: Record<SmartTaskKey, string> = {
  today: "今日必做",
  overdue: "逾期跟进",
  high_risk: "高风险客户",
  key_stale: "A类长期未联系",
  new_customers: "新客户首联",
  ai_suggested: "AI推荐动作",
  all: "全部客户",
};

const CRM_OBJECTS: Array<{ key: CrmObjectKey; label: string; title: string; path: string; icon: ReactNode }> = [
  { key: "companies", label: "Companies", title: "客户公司", path: "/customers", icon: <UserOutlined /> },
  { key: "people", label: "People", title: "联系人", path: "/customers?view=people", icon: <PhoneOutlined /> },
  { key: "opportunities", label: "Opportunities", title: "商机", path: "/sales/opportunities", icon: <BulbOutlined /> },
  { key: "quotations", label: "Quotes", title: "报价", path: "/sales/quotations", icon: <SendOutlined /> },
  { key: "orders", label: "Orders", title: "订单", path: "/sales/orders", icon: <ShoppingCartOutlined /> },
];

const CRM_VIEW_PRESETS = [
  { key: "all", label: "All companies", description: "全部公司对象", task: "all" as SmartTaskKey, view: "table" as CustomerViewMode },
  { key: "key", label: "Key accounts", description: "A级客户看板", task: "all" as SmartTaskKey, scene: "key_accounts" as SceneValue, view: "board" as CustomerViewMode },
  { key: "today", label: "Today follow-ups", description: "今日必须推进", task: "today" as SmartTaskKey, view: "table" as CustomerViewMode },
  { key: "risk", label: "At risk", description: "逾期或健康度低", task: "high_risk" as SmartTaskKey, view: "board" as CustomerViewMode },
  { key: "new", label: "New companies", description: "14天内新建", task: "new_customers" as SmartTaskKey, view: "table" as CustomerViewMode },
];

const DEFAULT_STATS: DashboardStats = {
  total: 0,
  by_industry: [],
  by_level: [],
  by_region: [],
  by_source: [],
  by_type: [],
  monthly: [],
};

const getLevelColor = (level?: string | null) => {
  if (!level) return "default";
  if (level === "A") return "red";
  if (level === "B") return "orange";
  if (level === "C") return "gold";
  return "default";
};

const getHealthColor = (value?: number | null) => {
  if (value == null) return "default";
  if (value >= 80) return "green";
  if (value >= 60) return "gold";
  return "red";
};

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  return value.slice(0, 10);
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "-";
  return value.slice(0, 16).replace("T", " ");
};

const formatReminderRefreshTime = (value: Date | null) => {
  if (!value) return "尚未刷新";
  const diffMs = Date.now() - value.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return "刚刚刷新";
  if (diffMinutes < 60) return `${diffMinutes}分钟前刷新`;
  return `${value.getHours().toString().padStart(2, "0")}:${value.getMinutes().toString().padStart(2, "0")} 刷新`;
};

const plusOneDayIso = (value?: string | null) => {
  const currentTime = value ? new Date(value).getTime() : Date.now();
  const baseTime = Number.isNaN(currentTime) ? Date.now() : Math.max(currentTime, Date.now());
  return new Date(baseTime + 24 * 60 * 60 * 1000).toISOString();
};

const getReminderDueMeta = (item: FollowUpReminder) => {
  if (item.due_bucket === "overdue") {
    return { text: `逾期 ${item.overdue_days} 天`, color: "red" };
  }
  if (item.due_bucket === "today") {
    return { text: "今日待跟进", color: "orange" };
  }
  return { text: `${item.days_until ?? "-"} 天后`, color: "blue" };
};

const getGlobalFollowUpDueMeta = (item: GlobalFollowUp) => {
  if (item.due_bucket === "overdue") return { text: `逾期 ${item.overdue_days} 天`, color: "red" };
  if (item.due_bucket === "today") return { text: "今日待跟进", color: "orange" };
  if (item.due_bucket === "upcoming") return { text: `${item.days_until ?? "-"} 天后`, color: "blue" };
  if (item.due_bucket === "closed") return { text: "已完成", color: "green" };
  return { text: "未排期", color: "default" };
};

const getDaysSince = (value?: string | null) => {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.floor((Date.now() - time) / (24 * 60 * 60 * 1000));
};

const getCustomerPriorityScore = (customer: Customer, next?: FollowUpReminder) => {
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

const getCustomerSuggestedAction = (customer: Customer, next?: FollowUpReminder) => {
  if (next?.due_bucket === "overdue") return "立即补跟进并更新结果";
  if (next?.due_bucket === "today") return "按计划完成今日跟进";
  if (customer.health_score != null && customer.health_score < 60) return "查看风险原因并安排挽回";
  if (customer.level === "A" && getDaysSince(customer.last_contacted_at) != null && getDaysSince(customer.last_contacted_at)! > 30) {
    return "联系关键客户并确认近期需求";
  }
  if (getDaysSince(customer.created_at) != null && getDaysSince(customer.created_at)! <= 14) return "完成新客户首联";
  return "补充客户画像并规划下一步";
};

const buildFollowUpTalkTrack = (customer: Customer, next?: FollowUpReminder) => {
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
    lines[1] = "近期客户健康度偏低，我想重点确认是否存在交付、价格、响应或备货方面的问题，我们这边及时调整。";
  }
  return lines;
};

const buildFollowUpPlanContent = (customer: Customer, next?: FollowUpReminder) => {
  const talkTrack = buildFollowUpTalkTrack(customer, next);
  return [
    `AI建议动作：${getCustomerSuggestedAction(customer, next)}`,
    `客户优先级：${getCustomerPriorityScore(customer, next)}`,
    "",
    "建议沟通话术：",
    ...talkTrack.map((line, index) => `${index + 1}. ${line}`),
  ].join("\n");
};

export default function CustomerList() {
  const { message, modal } = App.useApp();
  const [quickFollowUpForm] = Form.useForm();
  const [data, setData] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);
  const [stats, setStats] = useState<DashboardStats>(DEFAULT_STATS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [q, setQ] = useState(() => new URLSearchParams(window.location.search).get("q")?.trim() || "");
  const [scene, setScene] = useState<SceneValue>("all");
  const [industry, setIndustry] = useState<string | undefined>();
  const [level, setLevel] = useState<string | undefined>();
  const [region, setRegion] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [creditLevel, setCreditLevel] = useState<string | undefined>();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [sortBy, setSortBy] = useState<string>("id");
  const [sortOrder, setSortOrder] = useState<string>("desc");
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [tags, setTags] = useState<TagType[]>([]);
  const [batchTagIds, setBatchTagIds] = useState<number[]>([]);
  const [tagCreateName, setTagCreateName] = useState("");
  const [tagCreateColor, setTagCreateColor] = useState("blue");
  const [tagCreating, setTagCreating] = useState(false);
  const [tagGenerating, setTagGenerating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [overdueList, setOverdueList] = useState<OverdueFollowUp[]>([]);
  const [followUpReminders, setFollowUpReminders] = useState<FollowUpReminder[]>([]);
  const [reminderBucket, setReminderBucket] = useState<ReminderBucket>("all");
  const [reminderLoading, setReminderLoading] = useState(false);
  const [reminderActionKey, setReminderActionKey] = useState<string | null>(null);
  const [reminderRefreshedAt, setReminderRefreshedAt] = useState<Date | null>(null);
  const [reminderDrawerOpen, setReminderDrawerOpen] = useState(false);
  const [globalFollowUps, setGlobalFollowUps] = useState<GlobalFollowUp[]>([]);
  const [globalFollowUpTotal, setGlobalFollowUpTotal] = useState(0);
  const [globalFollowUpCounts, setGlobalFollowUpCounts] = useState<Record<string, number>>({});
  const [globalFollowUpBucket, setGlobalFollowUpBucket] = useState<GlobalFollowUpBucket>("all");
  const [globalFollowUpQ, setGlobalFollowUpQ] = useState("");
  const [globalFollowUpLoading, setGlobalFollowUpLoading] = useState(false);
  const [workbenchTab, setWorkbenchTab] = useState<CustomerWorkbenchTab>("customers");
  const [customerView, setCustomerView] = useState<CustomerViewMode>("table");
  const [activeCrmObject, setActiveCrmObject] = useState<CrmObjectKey>("companies");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [quickFollowUpCustomer, setQuickFollowUpCustomer] = useState<Customer | null>(null);
  const [quickFollowUpSaving, setQuickFollowUpSaving] = useState(false);
  const [duplicatePairs, setDuplicatePairs] = useState<DuplicatePair[]>([]);
  const [dupLoading, setDupLoading] = useState(false);
  const [dupModalOpen, setDupModalOpen] = useState(false);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [merging, setMerging] = useState(false);
  const [mergeSource, setMergeSource] = useState<DuplicatePair | null>(null);
  const [alertCount, setAlertCount] = useState(0);
  const [alertChecking, setAlertChecking] = useState(false);
  const [semanticOpen, setSemanticOpen] = useState(false);
  const [semanticQ, setSemanticQ] = useState("");
  const [semanticResults, setSemanticResults] = useState<SimilarCustomer[]>([]);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [vendCustomer, setVendCustomer] = useState<Customer | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailCustomer, setDetailCustomer] = useState<Customer | null>(null);
  const [detailStats, setDetailStats] = useState<CustomerStats | null>(null);
  const [smartTask, setSmartTask] = useState<SmartTaskKey>("today");
  const [activeViewPreset, setActiveViewPreset] = useState("today");
  const [contextCustomerId, setContextCustomerId] = useState<number | null>(null);
  const [productRecLoading, setProductRecLoading] = useState(false);
  const [productRecCustomerId, setProductRecCustomerId] = useState<number | null>(null);
  const [productRecResult, setProductRecResult] = useState<CustomerProductMatch | null>(null);

  const allColKeys = [
    "code",
    "name",
    "industry",
    "level",
    "region",
    "credit_level",
    "health",
    "next_followup",
    "tags",
    "owner",
    "contact_person",
    "phone",
    "email",
    "last_contacted_at",
    "source",
    "created_at",
    "actions",
  ];
  const [visibleCols, setVisibleCols] = useState<string[]>(DEFAULT_VISIBLE_COL_KEYS);
  const navigate = useNavigate();
  const location = useLocation();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const searchText = q.trim();
  const activeSmartTask: SmartTaskKey = searchText ? "all" : smartTask;

  const overdueCustomerIds = useMemo(() => new Set(overdueList.map((item) => item.customer_id)), [overdueList]);
  const selectedIdSet = useMemo(() => new Set(selectedRowKeys), [selectedRowKeys]);
  const selectedA = useMemo(
    () => data.filter((item) => selectedIdSet.has(item.id) && item.level === "A").length,
    [data, selectedIdSet],
  );
  const selectedOverdue = useMemo(
    () => overdueList.filter((item) => selectedIdSet.has(item.customer_id)).length,
    [overdueList, selectedIdSet],
  );
  const levelACount = useMemo(
    () => stats.by_level.find((row) => String(row.name).toUpperCase() === "A")?.value || 0,
    [stats],
  );
  const monthlyNewCount = useMemo(
    () => stats.monthly[stats.monthly.length - 1]?.count || 0,
    [stats],
  );
  const topIndustry = useMemo(() => stats.by_industry[0], [stats]);
  const topRegion = useMemo(() => stats.by_region[0], [stats]);
  const activeAdvancedFilterCount = useMemo(
    () => [industry, level, region, source, creditLevel].filter(Boolean).length,
    [industry, level, region, source, creditLevel],
  );
  const activeFilterItems = useMemo<Array<{ key: string; label: string; clear: () => void }>>(() => {
    const items: Array<{ key: string; label: string; clear: () => void }> = [];
    const selectedScene = SCENE_OPTIONS.find((item) => item.value === scene);
    if (searchText) items.push({ key: "q", label: `搜索：${searchText}`, clear: () => setQ("") });
    if (selectedScene && scene !== "all") {
      items.push({ key: "scene", label: `场景：${selectedScene.label}`, clear: () => setScene("all") });
    }
    if (industry) items.push({ key: "industry", label: `行业：${industry}`, clear: () => setIndustry(undefined) });
    if (level) items.push({ key: "level", label: `等级：${level}`, clear: () => setLevel(undefined) });
    if (region) items.push({ key: "region", label: `区域：${region}`, clear: () => setRegion(undefined) });
    if (source) items.push({ key: "source", label: `来源：${source}`, clear: () => setSource(undefined) });
    if (creditLevel) {
      items.push({ key: "creditLevel", label: `信用：${creditLevel}`, clear: () => setCreditLevel(undefined) });
    }
    if (overdueOnly) items.push({ key: "overdueOnly", label: "仅逾期客户", clear: () => setOverdueOnly(false) });
    return items.map((item) => ({
      ...item,
      clear: () => {
        item.clear();
        setPage(1);
      },
    }));
  }, [creditLevel, industry, level, overdueOnly, region, scene, searchText, source]);
  const reminderCounts = useMemo(
    () => ({
      all: followUpReminders.length,
      overdue: followUpReminders.filter((item) => item.due_bucket === "overdue").length,
      today: followUpReminders.filter((item) => item.due_bucket === "today").length,
      upcoming: followUpReminders.filter((item) => item.due_bucket === "upcoming").length,
    }),
    [followUpReminders],
  );
  const visibleReminders = useMemo(
    () => reminderBucket === "all"
      ? followUpReminders
      : followUpReminders.filter((item) => item.due_bucket === reminderBucket),
    [followUpReminders, reminderBucket],
  );
  const nextFollowUpByCustomer = useMemo(() => {
    const map = new Map<number, FollowUpReminder>();
    for (const item of followUpReminders) {
      const existing = map.get(item.customer_id);
      if (!existing || new Date(item.planned_at).getTime() < new Date(existing.planned_at).getTime()) {
        map.set(item.customer_id, item);
      }
    }
    return map;
  }, [followUpReminders]);
  const baseTableData = useMemo(
    () => overdueOnly ? data.filter((item) => overdueCustomerIds.has(item.id)) : data,
    [data, overdueOnly, overdueCustomerIds],
  );
  const customerMatchesSmartTask = (customer: Customer, task: SmartTaskKey) => {
    const next = nextFollowUpByCustomer.get(customer.id);
    const lastContactAge = getDaysSince(customer.last_contacted_at);
    const createdAge = getDaysSince(customer.created_at);
    if (task === "all") return true;
    if (task === "today") return next?.due_bucket === "today";
    if (task === "overdue") return overdueCustomerIds.has(customer.id);
    if (task === "high_risk") return overdueCustomerIds.has(customer.id) || (customer.health_score != null && customer.health_score < 60);
    if (task === "key_stale") return customer.level === "A" && (lastContactAge == null || lastContactAge > 30);
    if (task === "new_customers") return createdAge != null && createdAge <= 14;
    if (task === "ai_suggested") return getCustomerPriorityScore(customer, next) >= 65;
    return true;
  };
  const tableData = useMemo(
    () => baseTableData
      .filter((item) => customerMatchesSmartTask(item, activeSmartTask))
      .sort((a, b) => {
        const scoreA = getCustomerPriorityScore(a, nextFollowUpByCustomer.get(a.id));
        const scoreB = getCustomerPriorityScore(b, nextFollowUpByCustomer.get(b.id));
        return scoreB - scoreA;
      }),
    [activeSmartTask, baseTableData, nextFollowUpByCustomer, overdueCustomerIds],
  );
  const smartTaskItems = useMemo(() => {
    const items: Array<{ key: SmartTaskKey; label: string; count: number; color: string; note: string }> = [
      { key: "today", label: SMART_TASK_LABELS.today, count: data.filter((item) => customerMatchesSmartTask(item, "today")).length, color: "orange", note: "今天需要推进" },
      { key: "overdue", label: SMART_TASK_LABELS.overdue, count: data.filter((item) => customerMatchesSmartTask(item, "overdue")).length, color: "red", note: "已超过计划时间" },
      { key: "high_risk", label: SMART_TASK_LABELS.high_risk, count: data.filter((item) => customerMatchesSmartTask(item, "high_risk")).length, color: "red", note: "健康度低或逾期" },
      { key: "key_stale", label: SMART_TASK_LABELS.key_stale, count: data.filter((item) => customerMatchesSmartTask(item, "key_stale")).length, color: "gold", note: "重点客户需唤醒" },
      { key: "new_customers", label: SMART_TASK_LABELS.new_customers, count: data.filter((item) => customerMatchesSmartTask(item, "new_customers")).length, color: "blue", note: "14天内新建" },
      { key: "ai_suggested", label: SMART_TASK_LABELS.ai_suggested, count: data.filter((item) => customerMatchesSmartTask(item, "ai_suggested")).length, color: "purple", note: "综合优先级较高" },
      { key: "all", label: SMART_TASK_LABELS.all, count: data.length, color: "default", note: "回到普通列表" },
    ];
    return items;
  }, [data, nextFollowUpByCustomer, overdueCustomerIds]);
  const contextCustomer = useMemo(
    () => data.find((item) => item.id === contextCustomerId) || tableData[0] || null,
    [contextCustomerId, data, tableData],
  );
  const contextNextFollowUp = contextCustomer ? nextFollowUpByCustomer.get(contextCustomer.id) : undefined;
  const contextPriorityScore = contextCustomer ? getCustomerPriorityScore(contextCustomer, contextNextFollowUp) : 0;
  const contextSuggestedAction = contextCustomer ? getCustomerSuggestedAction(contextCustomer, contextNextFollowUp) : "";
  const contextTalkTrack = useMemo(
    () => contextCustomer ? buildFollowUpTalkTrack(contextCustomer, contextNextFollowUp) : [],
    [contextCustomer, contextNextFollowUp],
  );
  const customerBoardColumns = useMemo(() => {
    const stages = [...LEVELS, "未分级"];
    return stages.map((stage) => {
      const customers = tableData.filter((customer) => (customer.level || "未分级") === stage);
      const overdueCount = customers.filter((customer) => overdueCustomerIds.has(customer.id)).length;
      const avgPriority = customers.length
        ? Math.round(customers.reduce((sum, customer) => (
          sum + getCustomerPriorityScore(customer, nextFollowUpByCustomer.get(customer.id))
        ), 0) / customers.length)
        : 0;
      return { stage, customers, overdueCount, avgPriority };
    });
  }, [nextFollowUpByCustomer, overdueCustomerIds, tableData]);

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const resp = await getDashboardStats();
      setStats(resp.data.data || DEFAULT_STATS);
    } catch {
      // ignore
    } finally {
      setStatsLoading(false);
    }
  };

  const refreshAlertCount = async () => {
    try {
      const r = await getAlertEvents({ page: 1, page_size: 1, is_read: false });
      setAlertCount(r.data.data?.total || 0);
    } catch {
      // ignore
    }
  };

  const loadOverdue = async () => {
    setReminderLoading(true);
    try {
      const r = await getFollowUpReminders();
      const items = r.data.data?.items || [];
      setFollowUpReminders(items);
      setOverdueList(items.filter((item) => item.due_bucket === "overdue"));
      setReminderRefreshedAt(new Date());
    } catch {
      // ignore
    } finally {
      setReminderLoading(false);
    }
  };

  const loadGlobalFollowUps = async (
    bucket = globalFollowUpBucket,
    query = globalFollowUpQ,
  ) => {
    setGlobalFollowUpLoading(true);
    try {
      const params: Record<string, unknown> = { page: 1, page_size: 30 };
      if (bucket !== "all") params.due_bucket = bucket;
      if (query.trim()) params.q = query.trim();
      const resp = await getGlobalFollowUps(params);
      const payload = resp.data.data;
      setGlobalFollowUps(payload?.list || []);
      setGlobalFollowUpTotal(payload?.total || 0);
      setGlobalFollowUpCounts(payload?.counts || {});
    } catch {
      message.error("加载全局跟进集合失败");
    } finally {
      setGlobalFollowUpLoading(false);
    }
  };

  const fetch = async (p = page, ps = pageSize, search = q) => {
    setLoading(true);
    try {
      const sceneFilter = SCENE_FILTERS[scene];
      const resolvedLevel = level ?? sceneFilter.level;
      const resolvedRegion = region ?? sceneFilter.region;
      const resolvedSource = source ?? sceneFilter.source;
      const resolvedCreditLevel = creditLevel ?? sceneFilter.creditLevel;

      const params: Record<string, unknown> = {
        page: p,
        page_size: ps,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (search.trim()) {
        params.keyword = search.trim();
        params.q = search.trim();
      }
      if (industry) params.industry = industry;
      if (resolvedLevel) params.level = resolvedLevel;
      if (resolvedRegion) params.region = resolvedRegion;
      if (resolvedSource) params.source = resolvedSource;
      if (resolvedCreditLevel) params.credit_level = resolvedCreditLevel;

      const resp = await getCustomers(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch {
      message.error("加载客户列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      fetch(1, pageSize, q);
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [q]);

  // Sync external route query (`/customers?q=...`) into local search state.
  useEffect(() => {
    const urlQ = new URLSearchParams(location.search).get("q")?.trim() || "";
    setQ((current) => {
      if (urlQ === current) return current;
      setPage(1);
      return urlQ;
    });
  }, [location.search]);

  useEffect(() => {
    fetch();
  }, [page, pageSize, industry, level, region, source, creditLevel, sortBy, sortOrder, scene]);

  useEffect(() => {
    getTags().then((r) => setTags(r.data.data || [])).catch(() => {});
    loadStats();
    loadOverdue();
    loadGlobalFollowUps();
    refreshAlertCount();
  }, []);

  useEffect(() => {
    const refreshReminderState = () => {
      loadOverdue();
      loadGlobalFollowUps();
      refreshAlertCount();
    };
    const refreshWhenVisible = () => {
      if (!document.hidden) refreshReminderState();
    };

    window.addEventListener("focus", refreshReminderState);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refreshReminderState);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  const resetFilters = () => {
    setQ("");
    setScene("all");
    setIndustry(undefined);
    setLevel(undefined);
    setRegion(undefined);
    setSource(undefined);
    setCreditLevel(undefined);
    setOverdueOnly(false);
    setAdvancedOpen(false);
    setSortBy("id");
    setSortOrder("desc");
    setSmartTask("all");
    setActiveViewPreset("all");
    setActiveCrmObject("companies");
    setCustomerView("table");
    setVisibleCols(DEFAULT_VISIBLE_COL_KEYS);
    setPage(1);
  };

  const applyCrmViewPreset = (presetKey: string) => {
    const preset = CRM_VIEW_PRESETS.find((item) => item.key === presetKey);
    if (!preset) return;
    setActiveViewPreset(preset.key);
    setActiveCrmObject("companies");
    setSmartTask(preset.task);
    setCustomerView(preset.view);
    setVisibleCols(DEFAULT_VISIBLE_COL_KEYS);
    setScene(preset.scene || "all");
    setQ("");
    setIndustry(undefined);
    setLevel(undefined);
    setRegion(undefined);
    setSource(undefined);
    setCreditLevel(undefined);
    setOverdueOnly(preset.task === "overdue");
    setContextCustomerId(null);
    setPage(1);
  };

  const openCrmObject = (object: (typeof CRM_OBJECTS)[number]) => {
    if (object.key === "companies") {
      setActiveCrmObject("companies");
      setWorkbenchTab("customers");
      setCustomerView("table");
      setVisibleCols(DEFAULT_VISIBLE_COL_KEYS);
      return;
    }
    if (object.key === "people") {
      setActiveCrmObject("people");
      setWorkbenchTab("customers");
      setCustomerView("table");
      setSmartTask("all");
      setActiveViewPreset("all");
      setScene("all");
      setVisibleCols(PEOPLE_VISIBLE_COL_KEYS);
      setPage(1);
      return;
    }
    navigate(object.path);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteCustomer(id);
      message.success("已删除");
      await Promise.all([fetch(), loadStats(), loadOverdue()]);
    } catch {
      message.error("删除失败");
    }
  };

  const handleExport = async () => {
    try {
      const sceneFilter = SCENE_FILTERS[scene];
      const params: Record<string, unknown> = {};
      if (q.trim()) {
        params.keyword = q.trim();
        params.q = q.trim();
      }
      if (industry) params.industry = industry;
      if (level ?? sceneFilter.level) params.level = level ?? sceneFilter.level;
      if (region ?? sceneFilter.region) params.region = region ?? sceneFilter.region;
      if (source ?? sceneFilter.source) params.source = source ?? sceneFilter.source;
      if (creditLevel ?? sceneFilter.creditLevel) params.credit_level = creditLevel ?? sceneFilter.creditLevel;

      const resp = await exportCustomers(params);
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "customers.csv";
      a.click();
      URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch {
      message.error("导出失败");
    }
  };

  const handleTemplate = async () => {
    try {
      const resp = await downloadImportTemplate();
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "customer_template.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载模板失败");
    }
  };

  const handleImport = async (file: File) => {
    setImporting(true);
    try {
      const resp = await importCustomers(file);
      const result = resp.data.data as { created?: number; skipped?: number; imported?: number; updated?: number };
      const created = result.created ?? result.imported ?? 0;
      const skipped = result.skipped ?? 0;
      const updated = result.updated ?? 0;
      message.success(`导入成功：新建 ${created} 条，更新 ${updated} 条，跳过 ${skipped} 条`);
      await Promise.all([fetch(), loadStats(), loadOverdue()]);
    } catch (err: any) {
      message.error(err?.response?.data?.msg || err?.response?.data?.detail || "导入失败，请检查文件格式");
    } finally {
      setImporting(false);
    }
    return false;
  };

  const handleBatchDelete = async () => {
    try {
      await batchDeleteCustomers(selectedRowKeys);
      message.success(`已删除 ${selectedRowKeys.length} 条`);
      setSelectedRowKeys([]);
      await Promise.all([fetch(), loadStats(), loadOverdue()]);
    } catch {
      message.error("批量删除失败");
    }
  };

  const handleBatchTag = async () => {
    if (!batchTagIds.length) return;
    try {
      await batchTagCustomers(selectedRowKeys, batchTagIds);
      message.success(`已为 ${selectedRowKeys.length} 个客户添加标签`);
      setSelectedRowKeys([]);
      setTagModalOpen(false);
      setBatchTagIds([]);
      fetch();
    } catch {
      message.error("批量打标签失败");
    }
  };

  const handleCreateBatchTag = async () => {
    const name = tagCreateName.trim();
    if (!name) {
      message.warning("请输入标签名称");
      return;
    }
    setTagCreating(true);
    try {
      const resp = await createTag({ name, color: tagCreateColor });
      const created = resp.data.data as TagType;
      setTags((items) => [...items, created].sort((a, b) => a.name.localeCompare(b.name)));
      setBatchTagIds((ids) => Array.from(new Set([...ids, created.id])));
      setTagCreateName("");
      setTagCreateColor("blue");
      message.success("标签已创建");
    } catch {
      message.error("创建标签失败");
    } finally {
      setTagCreating(false);
    }
  };

  const handleGenerateDefaultTags = async () => {
    setTagGenerating(true);
    try {
      const resp = await generateDefaultCustomerTags();
      const data = resp.data.data;
      const tagsResp = await getTags();
      setTags((tagsResp.data.data || []).sort((a, b) => a.name.localeCompare(b.name)));
      message.success(data?.created ? `已生成 ${data.created} 个客户标签` : "默认客户标签已存在");
    } catch {
      message.error("生成默认标签失败");
    } finally {
      setTagGenerating(false);
    }
  };

  const handleDetectDups = async () => {
    setDupLoading(true);
    try {
      const resp = await detectDuplicates();
      const pairs = (resp.data.data?.pairs || []) as DuplicatePair[];
      setDuplicatePairs(pairs);
      setDupModalOpen(true);
      if (!pairs.length) message.info("未发现疑似重复客户");
    } catch {
      message.error("检测失败");
    } finally {
      setDupLoading(false);
    }
  };

  const openMergeModal = (pair: DuplicatePair) => {
    setMergeSource(pair);
    setMergeModalOpen(true);
  };

  const handleMerge = async () => {
    if (!mergeSource) return;
    setMerging(true);
    try {
      await mergeCustomers(mergeSource.customer_a.id, mergeSource.customer_b.id);
      message.success(`已合并至 ${mergeSource.customer_b.name}`);
      setMergeModalOpen(false);
      setMergeSource(null);
      setDupModalOpen(false);
      await Promise.all([fetch(), loadStats(), loadOverdue()]);
    } catch {
      message.error("合并失败");
    } finally {
      setMerging(false);
    }
  };

  const handleCheckAlerts = async () => {
    setAlertChecking(true);
    try {
      const resp = await checkAlerts();
      message.success(`预警检查完成，生成 ${resp.data.data.generated} 条`);
      await refreshAlertCount();
    } catch {
      message.error("预警检查失败");
    } finally {
      setAlertChecking(false);
    }
  };

  const handleMarkAllAlertsRead = async () => {
    try {
      await markAllAlertsRead();
      setAlertCount(0);
      message.success("已全部标记为已读");
    } catch {
      message.error("操作失败");
    }
  };

  const handleSemanticSearch = async () => {
    if (!semanticQ.trim()) return;
    setSemanticLoading(true);
    try {
      const resp = await searchSimilarCustomers(semanticQ);
      setSemanticResults((resp.data.data || []) as SimilarCustomer[]);
    } catch {
      message.error("语义搜索失败");
    } finally {
      setSemanticLoading(false);
    }
  };

  const handleTableChange = (
    pag: TablePaginationConfig,
    _filters: Record<string, unknown>,
    sorter: SorterResult<Customer> | SorterResult<Customer>[],
  ) => {
    if (pag.current) setPage(pag.current);
    if (pag.pageSize) {
      setPageSize(pag.pageSize);
      if (pag.pageSize !== pageSize) setPage(1);
    }
    const s = Array.isArray(sorter) ? sorter[0] : sorter;
    if (s.field && typeof s.field === "string") {
      setSortBy(s.field);
      if (s.order === "ascend") setSortOrder("asc");
      if (s.order === "descend") setSortOrder("desc");
      if (!s.order) setSortOrder("desc");
    }
  };

  const openDetailDrawer = async (customerId: number) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const [detailResp, statsResp] = await Promise.all([
        getCustomer(customerId),
        getCustomerStats(customerId),
      ]);
      setDetailCustomer(detailResp.data.data);
      setDetailStats(statsResp.data.data);
    } catch {
      message.error("加载客户详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const confirmDeleteCustomer = (customer: Customer) => {
    modal.confirm({
      title: "删除客户",
      content: `确定删除「${customer.name}」？此操作不可撤销。`,
      okText: "删除",
      cancelText: "取消",
      okButtonProps: { danger: true },
      onOk: () => handleDelete(customer.id),
    });
  };

  const handleCompleteReminder = async (item: FollowUpReminder) => {
    const actionKey = `complete-${item.id}`;
    setReminderActionKey(actionKey);
    try {
      await updateFollowUp(item.customer_id, item.id, {
        status: "completed",
        completed_at: new Date().toISOString(),
      });
      message.success("跟进已完成");
      await Promise.all([loadOverdue(), loadGlobalFollowUps(), fetch()]);
    } catch {
      message.error("完成跟进失败");
    } finally {
      setReminderActionKey(null);
    }
  };

  const handlePostponeReminder = async (item: FollowUpReminder) => {
    const actionKey = `postpone-${item.id}`;
    setReminderActionKey(actionKey);
    try {
      await updateFollowUp(item.customer_id, item.id, {
        planned_at: plusOneDayIso(item.planned_at),
        status: item.status || "planned",
      });
      message.success("已延期 1 天");
      await Promise.all([loadOverdue(), loadGlobalFollowUps(), fetch()]);
    } catch {
      message.error("延期失败");
    } finally {
      setReminderActionKey(null);
    }
  };

  const handleCompleteGlobalFollowUp = async (item: GlobalFollowUp) => {
    const actionKey = `global-complete-${item.id}`;
    setReminderActionKey(actionKey);
    try {
      await updateFollowUp(item.customer_id, item.id, {
        status: "completed",
        completed_at: new Date().toISOString(),
      });
      message.success("跟进已完成");
      await Promise.all([loadOverdue(), loadGlobalFollowUps(), fetch()]);
    } catch {
      message.error("完成跟进失败");
    } finally {
      setReminderActionKey(null);
    }
  };

  const openQuickFollowUp = (customer: Customer) => {
    setQuickFollowUpCustomer(customer);
    quickFollowUpForm.setFieldsValue({
      method: "phone",
      status: "planned",
      priority: "medium",
      planned_at: dayjs().add(1, "day"),
    });
  };

  const openAIPlannedFollowUp = (customer: Customer, next?: FollowUpReminder) => {
    setQuickFollowUpCustomer(customer);
    quickFollowUpForm.setFieldsValue({
      method: next?.method || "phone",
      status: "planned",
      priority: contextPriorityScore >= 75 ? "high" : "medium",
      planned_at: dayjs().add(next?.due_bucket === "overdue" || next?.due_bucket === "today" ? 2 : 24, "hour"),
      assigned_to: customer.owner || "",
      content: buildFollowUpPlanContent(customer, next),
    });
  };

  const handleLoadProductRecommendations = async (customer: Customer) => {
    setProductRecLoading(true);
    setProductRecCustomerId(customer.id);
    try {
      const resp = await recommendProductsForCustomer(customer.id);
      setProductRecResult(resp.data.data as CustomerProductMatch);
    } catch {
      message.error("AI产品推荐失败");
    } finally {
      setProductRecLoading(false);
    }
  };

  const handleQuickFollowUpSubmit = async () => {
    if (!quickFollowUpCustomer) return;
    const values = await quickFollowUpForm.validateFields();
    if (values.status === "planned" && !values.planned_at) {
      message.warning("计划中的跟进必须填写计划时间");
      return;
    }
    setQuickFollowUpSaving(true);
    try {
      await createFollowUp(quickFollowUpCustomer.id, {
        ...values,
        planned_at: values.planned_at ? values.planned_at.format("YYYY-MM-DD HH:mm:ss") : null,
        completed_at: values.completed_at
          ? values.completed_at.format("YYYY-MM-DD HH:mm:ss")
          : values.status === "completed"
            ? dayjs().format("YYYY-MM-DD HH:mm:ss")
            : null,
      });
      message.success("跟进已创建");
      setQuickFollowUpCustomer(null);
      quickFollowUpForm.resetFields();
      await Promise.all([loadOverdue(), loadGlobalFollowUps(), fetch()]);
    } catch {
      message.error("创建跟进失败");
    } finally {
      setQuickFollowUpSaving(false);
    }
  };

  const columns: ColumnsType<Customer> = [
    {
      title: "客户编码",
      dataIndex: "code",
      key: "code",
      width: 120,
      sorter: true,
      sortOrder: sortBy === "code" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => (
        <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{v || "-"}</span>
      ),
    },
    {
      title: "客户",
      dataIndex: "name",
      key: "name",
      width: 280,
      sorter: true,
      sortOrder: sortBy === "name" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (text: string, r: Customer) => (
        <Space direction="vertical" size={2}>
          <Space size={6} wrap>
            <Typography.Link strong onClick={() => navigate(`/customers/${r.id}`)}>{text}</Typography.Link>
            {r.level && <Tag color={getLevelColor(r.level)} style={{ marginInlineEnd: 0 }}>{r.level}</Tag>}
            {overdueCustomerIds.has(r.id) && <Tag color="red" style={{ marginInlineEnd: 0 }}>逾期</Tag>}
          </Space>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {[r.code, r.short_name].filter(Boolean).join(" / ") || "-"}
          </Typography.Text>
          {r.contact_person && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              联系人：{r.contact_person}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "行业",
      dataIndex: "industry",
      key: "industry",
      width: 120,
      sorter: true,
      sortOrder: sortBy === "industry" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => (v ? <Tag>{v}</Tag> : "-"),
    },
    {
      title: "等级",
      dataIndex: "level",
      key: "level",
      width: 76,
      align: "center",
      sorter: true,
      sortOrder: sortBy === "level" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => <Tag color={getLevelColor(v)} style={{ marginInlineEnd: 0 }}>{v || "-"}</Tag>,
    },
    {
      title: "区域",
      dataIndex: "region",
      key: "region",
      width: 100,
      sorter: true,
      sortOrder: sortBy === "region" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => v || "-",
    },
    {
      title: "信用",
      dataIndex: "credit_level",
      key: "credit_level",
      width: 90,
      sorter: true,
      sortOrder: sortBy === "credit_level" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => v ? <Tag>{v}</Tag> : "-",
    },
    {
      title: "健康/风险",
      key: "health",
      width: 130,
      render: (_: unknown, row: Customer) => (
        <Space size={4} wrap>
          <Tag color={getHealthColor(row.health_score)}>
            {row.health_score != null ? `${row.health_score}` : "-"}
          </Tag>
          {overdueCustomerIds.has(row.id) && <Tag color="red">逾期</Tag>}
        </Space>
      ),
    },
    {
      title: "下一次跟进",
      key: "next_followup",
      width: 170,
      render: (_: unknown, row: Customer) => {
        const next = nextFollowUpByCustomer.get(row.id);
        if (!next) return "-";
        const color = next.due_bucket === "overdue" ? "red" : next.due_bucket === "today" ? "orange" : "blue";
        const label = next.due_bucket === "overdue"
          ? `逾期${next.overdue_days}天`
          : next.due_bucket === "today"
            ? "今日"
            : `${next.days_until ?? "-"}天后`;
        return (
          <Space direction="vertical" size={0}>
            <Space size={4}>
              <Tag color={color}>{label}</Tag>
              <FollowUpMethodTag method={next.method} />
            </Space>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{formatDateTime(next.planned_at)}</Typography.Text>
          </Space>
        );
      },
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 180,
      render: (rowTags: TagType[] | undefined) => {
        const items = rowTags || [];
        if (!items.length) return "-";
        return (
          <Space size={[4, 4]} wrap>
            {items.slice(0, 2).map((t) => (
              <Tag key={t.id} color={t.color || "blue"}>{t.name}</Tag>
            ))}
            {items.length > 2 && <Tag>+{items.length - 2}</Tag>}
          </Space>
        );
      },
    },
    {
      title: "负责人",
      dataIndex: "owner",
      key: "owner",
      width: 100,
      render: (v: string | null) => v ? <Typography.Text>{v}</Typography.Text> : "-",
    },
    {
      title: "联系人",
      dataIndex: "contact_person",
      key: "contact_person",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "电话",
      dataIndex: "phone",
      key: "phone",
      width: 130,
      render: (v: string | null) => v || "-",
    },
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
      width: 180,
      render: (v: string | null) => v ? <Typography.Text copyable>{v}</Typography.Text> : "-",
    },
    {
      title: "最近联系",
      dataIndex: "last_contacted_at",
      key: "last_contacted_at",
      width: 110,
      render: (v: string | null) => formatDate(v),
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
      width: 100,
      sorter: true,
      sortOrder: sortBy === "source" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string | null) => v || "-",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 120,
      sorter: true,
      sortOrder: sortBy === "created_at" ? (sortOrder === "asc" ? "ascend" : "descend") : null,
      render: (v: string) => formatDate(v),
    },
    {
      title: "操作",
      key: "actions",
      width: 142,
      fixed: "right",
      render: (_: unknown, r: Customer) => (
        <Space size={2}>
          <Button size="small" type="link" onClick={() => openDetailDrawer(r.id)}>查看</Button>
          <Button size="small" type="link" onClick={() => openQuickFollowUp(r)}>跟进</Button>
          <Dropdown
            trigger={["click"]}
            menu={{
              items: [
                { key: "order", icon: <ShoppingCartOutlined />, label: "创建销售订单" },
                { key: "supplier", icon: <SwapOutlined />, label: "转为供应商" },
                { type: "divider" },
                { key: "delete", icon: <DeleteOutlined />, danger: true, label: "删除客户" },
              ],
              onClick: ({ key }) => {
                if (key === "order") navigate(`/sales/orders/new?customer_id=${r.id}`);
                if (key === "supplier") setVendCustomer(r);
                if (key === "delete") confirmDeleteCustomer(r);
              },
            }}
          >
            <Tooltip title="更多操作">
              <Button size="small" type="link" icon={<MoreOutlined />} aria-label="更多操作" />
            </Tooltip>
          </Dropdown>
        </Space>
      ),
    },
  ];

  const moreActionsContent = (
    <Space direction="vertical" size={8} style={{ width: 260 }}>
      <Upload accept=".csv" showUploadList={false} beforeUpload={handleImport} disabled={importing}>
        <Button style={{ width: 260 }} icon={<UploadOutlined />} loading={importing}>导入客户</Button>
      </Upload>
      <Button block onClick={handleTemplate}>下载导入模板</Button>
      <Button block icon={<DownloadOutlined />} onClick={handleExport}>导出当前筛选</Button>
      <Button block icon={<SafetyCertificateOutlined />} loading={dupLoading} onClick={handleDetectDups}>疑似重复检测</Button>
      <Button block icon={<SendOutlined />} onClick={() => setSemanticOpen(true)}>语义搜索</Button>
      <Button block danger={alertCount > 0} loading={alertChecking} onClick={handleCheckAlerts}>
        {alertCount > 0 ? `预警检查(${alertCount})` : "预警检查"}
      </Button>
      {alertCount > 0 && <Button block onClick={handleMarkAllAlertsRead}>全部预警标为已读</Button>}
      <Divider style={{ margin: "4px 0" }} />
      <Typography.Text type="secondary">显示列</Typography.Text>
      <Checkbox.Group
        options={allColKeys.map((k) => ({ label: COL_LABEL_MAP[k] || k, value: k }))}
        value={visibleCols}
        onChange={(vals) => setVisibleCols(vals as string[])}
        style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 4 }}
      />
    </Space>
  );

  return (
    <CustomerModuleShell
      title="客户工作台"
      subtitle="筛选客户、处理跟进提醒并完成批量运营"
      extra={(
        <>
          <Button icon={<RobotOutlined />} onClick={() => navigate("/customers/workbench")}>AI队列</Button>
          <Button icon={<BulbOutlined />} onClick={() => setSemanticOpen(true)}>AI搜索</Button>
        </>
      )}
    >
      <style>{`
        .customer-workbench-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin-bottom: 12px;
        }
        .customer-kpi-card {
          min-height: 86px;
          padding: 12px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-kpi-card.is-risk {
          border-color: #ffccc7;
          background: #fffafa;
        }
        .customer-kpi-card.is-warning {
          border-color: #ffe58f;
          background: #fffbe6;
        }
        .customer-kpi-title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 20px;
        }
        .customer-kpi-value {
          margin-top: 8px;
          color: #262626;
          font-size: 26px;
          font-weight: 650;
          line-height: 1;
        }
          .customer-kpi-note {
            margin-top: 7px;
            color: #8c8c8c;
            font-size: 12px;
            line-height: 18px;
          white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
        .crm-object-strip {
          display: grid;
          grid-template-columns: repeat(5, minmax(150px, 1fr));
          gap: 10px;
          margin-bottom: 12px;
        }
        .crm-object-button {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          min-height: 58px;
          padding: 10px 12px;
          color: #262626;
          text-align: left;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          cursor: pointer;
        }
        .crm-object-button:hover,
        .crm-object-button.is-active {
          border-color: #91caff;
          background: #f0f7ff;
        }
        .crm-object-main {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }
        .crm-object-title {
          display: block;
          font-weight: 600;
          line-height: 20px;
        }
        .crm-object-label {
          display: block;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .crm-view-strip {
          display: grid;
          grid-template-columns: repeat(5, minmax(150px, 1fr));
          gap: 8px;
          margin-bottom: 12px;
        }
        .crm-view-button {
          min-height: 64px;
          padding: 9px 10px;
          text-align: left;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          cursor: pointer;
        }
        .crm-view-button:hover,
        .crm-view-button.is-active {
          border-color: #91caff;
          background: #f0f7ff;
        }
        .crm-view-name {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          font-weight: 600;
          line-height: 20px;
        }
        .crm-view-desc {
          margin-top: 4px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-batch-bar {
          position: sticky;
          top: 8px;
          z-index: 5;
          margin-bottom: 12px;
          padding: 10px 12px;
          background: #f0f5ff;
          border: 1px solid #adc6ff;
          border-radius: 8px;
        }
        .customer-ai-layout {
          display: grid;
          grid-template-columns: 220px minmax(0, 1fr) 280px;
          gap: 12px;
          align-items: start;
        }
        .customer-ai-sidebar,
        .customer-ai-context {
          position: sticky;
          top: 8px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .customer-ai-panel {
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          overflow: hidden;
        }
        .customer-ai-panel-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          padding: 10px 12px;
          border-bottom: 1px solid #f0f0f0;
        }
        .customer-ai-task {
          display: block;
          width: 100%;
          padding: 9px 12px;
          text-align: left;
          background: transparent;
          border: 0;
          border-bottom: 1px solid #f5f5f5;
          cursor: pointer;
        }
        .customer-ai-task:hover,
        .customer-ai-task.is-active {
          background: #f0f5ff;
        }
        .customer-ai-task:last-child {
          border-bottom: 0;
        }
        .customer-ai-task-main {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .customer-ai-task-note,
        .customer-ai-context-note {
          margin-top: 4px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-ai-context-body {
          padding: 12px;
        }
        .customer-ai-score {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          margin: 10px 0;
          padding: 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-ai-score-value {
          color: #1677ff;
          font-size: 26px;
          font-weight: 650;
          line-height: 1;
        }
        .customer-ai-action-box {
          margin-top: 10px;
          padding: 10px;
          background: #fffbe6;
          border: 1px solid #ffe58f;
          border-radius: 8px;
        }
        .customer-ai-talk-track {
          margin-top: 10px;
          padding: 10px;
          background: #f6ffed;
          border: 1px solid #b7eb8f;
          border-radius: 8px;
        }
        .customer-ai-talk-track ol {
          margin: 8px 0 0;
          padding-left: 18px;
        }
        .customer-ai-talk-track li {
          margin-bottom: 6px;
          color: #595959;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-ai-products {
          margin-top: 10px;
          padding: 10px;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-ai-product-item {
          padding: 8px 0;
          border-top: 1px solid #f5f5f5;
        }
        .customer-ai-product-item:first-of-type {
          border-top: 0;
          padding-top: 0;
        }
        .customer-ai-context-actions {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-top: 10px;
        }
        .customer-ai-context-actions .ant-btn {
          min-width: 0;
        }
        .customer-ai-main {
          min-width: 0;
        }
        .customer-workbench-tabs {
          margin-bottom: 10px;
          padding: 0 4px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-workbench-tabs .ant-tabs-nav {
          margin: 0;
          padding: 0 8px;
        }
        .customer-table-card.customer-followup-card .ant-card-body {
          padding: 12px;
        }
        .customer-followup-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
          margin-bottom: 12px;
        }
        .customer-toolbar-card .ant-card-body {
          padding: 12px;
        }
        .customer-toolbar-main {
          display: grid;
          grid-template-columns: minmax(260px, 0.9fr) minmax(360px, 1.1fr) auto;
          gap: 10px;
          align-items: center;
        }
        .customer-advanced-grid {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid #f0f0f0;
        }
        .customer-summary-strip {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid #f0f0f0;
        }
        .customer-table-title {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .customer-stat-grid {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        .customer-stat-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-height: 34px;
          padding: 5px 10px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-stat-pill.is-risk {
          background: #fff2f0;
          border-color: #ffccc7;
        }
        .customer-stat-pill.is-warning {
          background: #fffbe6;
          border-color: #ffe58f;
        }
        .customer-stat-label {
          color: #8c8c8c;
          font-size: 12px;
        }
        .customer-stat-value {
          color: #262626;
          font-size: 14px;
          font-weight: 600;
          line-height: 1;
        }
        .customer-active-filters {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 6px;
          flex-wrap: wrap;
          max-width: min(100%, 560px);
        }
        .customer-summary-strip .ant-tag,
        .customer-filter-tags .ant-tag,
        .customer-reminder-strip .ant-tag {
          margin-inline-end: 0;
        }
        .customer-reminder-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
          margin-bottom: 12px;
          padding: 10px 12px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-left: 3px solid #1677ff;
          border-radius: 8px;
        }
        .customer-reminder-strip.is-risk {
          border-left-color: #ff4d4f;
          background: #fffafa;
        }
        .customer-reminder-title {
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .customer-table-card .ant-card-body {
          padding: 0;
        }
        .customer-table-card .ant-card-head {
          min-height: 44px;
          padding: 0 12px;
        }
        .customer-table-card .ant-card-head-title,
        .customer-table-card .ant-card-extra {
          padding: 10px 0;
        }
        .customer-table-card .ant-table-thead > tr > th {
          background: #fafafa;
        }
        .customer-table-card .ant-table-tbody > tr > td {
          padding-top: 10px;
          padding-bottom: 10px;
          vertical-align: top;
        }
        .customer-board {
          display: grid;
          grid-template-columns: repeat(5, minmax(220px, 1fr));
          gap: 10px;
          padding: 12px;
          overflow-x: auto;
        }
        .customer-board-column {
          min-width: 220px;
          background: #fafafa;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
        }
        .customer-board-column-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
          padding: 10px;
          border-bottom: 1px solid #f0f0f0;
        }
        .customer-board-column-meta {
          margin-top: 5px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-board-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          min-height: 180px;
          padding: 8px;
        }
        .customer-board-card {
          padding: 10px;
          background: #fff;
          border: 1px solid #f0f0f0;
          border-radius: 8px;
          cursor: pointer;
        }
        .customer-board-card:hover,
        .customer-board-card.is-active {
          border-color: #91caff;
          box-shadow: 0 2px 8px rgba(22, 119, 255, 0.12);
        }
        .customer-board-card.is-overdue {
          border-left: 3px solid #ff4d4f;
        }
        .customer-board-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 8px;
        }
        .customer-board-card-name {
          max-width: 150px;
        }
        .customer-board-card-meta {
          margin-top: 6px;
          color: #8c8c8c;
          font-size: 12px;
          line-height: 18px;
        }
        .customer-board-card-actions {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 6px;
          margin-top: 8px;
        }
        .customer-row-overdue td:first-child { border-left: 3px solid #ff4d4f; }
        .customer-row-key td:first-child { border-left: 3px solid #52c41a; }
        .customer-row-selected td {
          background: #f0f5ff !important;
        }
        @media (max-width: 1180px) {
          .customer-workbench-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .crm-object-strip,
          .crm-view-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .customer-ai-layout {
            grid-template-columns: 1fr;
          }
          .customer-ai-sidebar,
          .customer-ai-context {
            position: static;
          }
          .customer-ai-context-actions {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
          .customer-toolbar-main {
            grid-template-columns: 1fr;
          }
          .customer-board {
            grid-template-columns: repeat(5, minmax(220px, 240px));
          }
          .customer-toolbar-actions {
            justify-content: flex-start !important;
          }
        }
        @media (max-width: 768px) {
          .customer-workbench-grid {
            grid-template-columns: 1fr;
          }
          .crm-object-strip,
          .crm-view-strip {
            grid-template-columns: 1fr;
          }
          .customer-ai-context-actions {
            grid-template-columns: 1fr 1fr;
          }
          .customer-stat-grid,
          .customer-active-filters,
          .customer-reminder-strip > .ant-space {
            width: 100%;
          }
          .customer-stat-pill {
            flex: 1 1 calc(50% - 8px);
            justify-content: space-between;
          }
        }
      `}</style>

      <div className="customer-workbench-grid">
        <div className="customer-kpi-card">
          <div className="customer-kpi-title">
            <span>客户总数</span>
            <UserOutlined />
          </div>
          <div className="customer-kpi-value">{statsLoading ? "..." : stats.total}</div>
          <div className="customer-kpi-note">当前筛选显示 {overdueOnly ? tableData.length : total} 条</div>
        </div>
        <div className={`customer-kpi-card${reminderCounts.today > 0 ? " is-warning" : ""}`}>
          <div className="customer-kpi-title">
            <span>今日待跟进</span>
            <PhoneOutlined />
          </div>
          <div className="customer-kpi-value">{reminderCounts.today}</div>
          <div className="customer-kpi-note">{formatReminderRefreshTime(reminderRefreshedAt)}</div>
        </div>
        <div className={`customer-kpi-card${reminderCounts.overdue > 0 ? " is-risk" : ""}`}>
          <div className="customer-kpi-title">
            <span>超期未跟进</span>
            <BellOutlined />
          </div>
          <div className="customer-kpi-value">{reminderCounts.overdue}</div>
          <div className="customer-kpi-note">可一键完成或延期处理</div>
        </div>
        <div className="customer-kpi-card">
          <div className="customer-kpi-title">
            <span>高价值客户</span>
            <SafetyCertificateOutlined />
          </div>
          <div className="customer-kpi-value">{statsLoading ? "..." : levelACount}</div>
          <div className="customer-kpi-note">
            {topRegion ? `主力区域 ${topRegion.name} ${topRegion.value}` : `本月新增 ${monthlyNewCount}`}
          </div>
        </div>
      </div>

      <div className="crm-object-strip">
        {CRM_OBJECTS.map((object) => (
          <button
            key={object.key}
            type="button"
            className={`crm-object-button${activeCrmObject === object.key ? " is-active" : ""}`}
            onClick={() => openCrmObject(object)}
          >
            <span className="crm-object-main">
              {object.icon}
              <span>
                <span className="crm-object-title">{object.title}</span>
                <span className="crm-object-label">{object.label}</span>
              </span>
            </span>
            {activeCrmObject === object.key ? <Tag color="blue">当前</Tag> : <Tag>打开</Tag>}
          </button>
        ))}
      </div>

      <div className="crm-view-strip">
        {CRM_VIEW_PRESETS.map((preset) => (
          <button
            key={preset.key}
            type="button"
            className={`crm-view-button${activeViewPreset === preset.key ? " is-active" : ""}`}
            onClick={() => applyCrmViewPreset(preset.key)}
          >
            <span className="crm-view-name">
              <span>{preset.label}</span>
              <Tag color={activeViewPreset === preset.key ? "blue" : "default"}>
                {preset.view === "board" ? "Board" : "Table"}
              </Tag>
            </span>
            <span className="crm-view-desc">{preset.description}</span>
          </button>
        ))}
      </div>

      <div className="customer-ai-layout">
        <aside className="customer-ai-sidebar">
          <div className="customer-ai-panel">
            <div className="customer-ai-panel-head">
              <Space size={6}>
                <RobotOutlined />
                <Typography.Text strong>AI任务队列</Typography.Text>
              </Space>
              <Button size="small" type="link" onClick={() => navigate("/customers/workbench")}>完整队列</Button>
            </div>
            {smartTaskItems.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`customer-ai-task${smartTask === item.key ? " is-active" : ""}`}
                onClick={() => {
                  setSmartTask(item.key);
                  setPage(1);
                  setContextCustomerId(null);
                }}
              >
                <span className="customer-ai-task-main">
                  <Typography.Text strong={smartTask === item.key}>{item.label}</Typography.Text>
                  <Tag color={item.color}>{item.count}</Tag>
                </span>
                <span className="customer-ai-task-note">{item.note}</span>
              </button>
            ))}
          </div>

          <div className={`customer-ai-panel${reminderCounts.overdue > 0 ? " is-risk" : ""}`}>
            <div className="customer-ai-panel-head">
              <Space size={6}>
                <BellOutlined style={{ color: reminderCounts.overdue > 0 ? "#cf1322" : undefined }} />
                <Typography.Text strong>跟进提醒</Typography.Text>
              </Space>
              <Button size="small" type="link" onClick={() => setReminderDrawerOpen(true)}>明细</Button>
            </div>
            <div className="customer-ai-context-body">
              <Space size={[4, 6]} wrap>
                <Tag color={reminderCounts.overdue > 0 ? "red" : "default"}>逾期 {reminderCounts.overdue}</Tag>
                <Tag color={reminderCounts.today > 0 ? "orange" : "default"}>今日 {reminderCounts.today}</Tag>
                <Tag color={reminderCounts.upcoming > 0 ? "blue" : "default"}>未来 {reminderCounts.upcoming}</Tag>
              </Space>
              <div className="customer-ai-context-note">{formatReminderRefreshTime(reminderRefreshedAt)}</div>
              <Button size="small" icon={<ReloadOutlined />} loading={reminderLoading} onClick={loadOverdue} style={{ marginTop: 8 }}>
                刷新提醒
              </Button>
            </div>
          </div>

        </aside>

        <main className="customer-ai-main">
          <Tabs
            className="customer-workbench-tabs"
            activeKey={workbenchTab}
            onChange={(key) => {
              const next = key as CustomerWorkbenchTab;
              setWorkbenchTab(next);
              if (next === "followups") loadGlobalFollowUps();
            }}
            items={[
              {
                key: "customers",
                label: (
                  <Space size={6}>
                    <UserOutlined />
                    <span>客户列表</span>
                    <Tag>{overdueOnly ? tableData.length : total}</Tag>
                  </Space>
                ),
              },
              {
                key: "followups",
                label: (
                  <Space size={6}>
                    <PhoneOutlined />
                    <span>全局跟进</span>
                    <Tag color={(globalFollowUpCounts.overdue || 0) > 0 ? "red" : "blue"}>
                      {globalFollowUpCounts.all ?? globalFollowUpTotal}
                    </Tag>
                  </Space>
                ),
              },
            ]}
          />
          {workbenchTab === "customers" && (
            <>
      <Card size="small" className="customer-toolbar-card" style={{ marginBottom: 12 }}>
        <div className="customer-toolbar-main">
          <div>
            <Input
              placeholder="搜索客户名称/编码/联系人/电话"
              prefix={<SearchOutlined />}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setSmartTask("all");
                setActiveViewPreset("all");
                setOverdueOnly(false);
                setPage(1);
              }}
              allowClear
            />
          </div>
          <div>
            <Segmented
              style={{ maxWidth: "100%" }}
              options={SCENE_OPTIONS}
              value={scene}
              onChange={(v) => {
                setScene(v as SceneValue);
                setPage(1);
              }}
            />
          </div>
          <div>
            <Space wrap className="customer-toolbar-actions" style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button
                icon={<FilterOutlined />}
                type={activeAdvancedFilterCount > 0 ? "primary" : "default"}
                onClick={() => setAdvancedOpen((open) => !open)}
              >
                高级筛选{activeAdvancedFilterCount > 0 ? `(${activeAdvancedFilterCount})` : ""}
                <DownOutlined />
              </Button>
              <Button icon={<ReloadOutlined />} onClick={resetFilters}>重置</Button>
              <Popover content={moreActionsContent} title="更多操作" trigger="click" placement="bottomRight">
                <Button icon={<MoreOutlined />}>更多</Button>
              </Popover>
            </Space>
          </div>
        </div>

        {advancedOpen && (
          <Row gutter={[10, 10]} className="customer-advanced-grid">
            <Col xs={12} md={6} xl={4}>
              <Select
                allowClear
                placeholder="行业"
                style={{ width: "100%" }}
                value={industry}
                options={INDUSTRIES.map((v) => ({ value: v, label: v }))}
                onChange={(v) => {
                  setIndustry(v);
                  setPage(1);
                }}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Select
                allowClear
                placeholder="等级"
                style={{ width: "100%" }}
                value={level}
                options={LEVELS.map((v) => ({ value: v, label: v }))}
                onChange={(v) => {
                  setLevel(v);
                  setPage(1);
                }}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Select
                allowClear
                placeholder="区域"
                style={{ width: "100%" }}
                value={region}
                options={REGIONS.map((v) => ({ value: v, label: v }))}
                onChange={(v) => {
                  setRegion(v);
                  setPage(1);
                }}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Select
                allowClear
                placeholder="来源"
                style={{ width: "100%" }}
                value={source}
                options={SOURCES.map((v) => ({ value: v, label: v }))}
                onChange={(v) => {
                  setSource(v);
                  setPage(1);
                }}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Select
                allowClear
                placeholder="信用等级"
                style={{ width: "100%" }}
                value={creditLevel}
                options={CREDIT_LEVELS.map((v) => ({ value: v, label: v }))}
                onChange={(v) => {
                  setCreditLevel(v);
                  setPage(1);
                }}
              />
            </Col>
          </Row>
        )}

        <div className="customer-summary-strip">
          <div className="customer-stat-grid">
            <div className="customer-stat-pill">
              <span className="customer-stat-label">A级客户</span>
              <span className="customer-stat-value">{statsLoading ? "..." : levelACount}</span>
            </div>
            <div className={`customer-stat-pill${alertCount > 0 ? " is-warning" : ""}`}>
              <BellOutlined />
              <span className="customer-stat-label">未读预警</span>
              <span className="customer-stat-value">{alertCount}</span>
            </div>
            <div className="customer-stat-pill">
              <span className="customer-stat-label">本月新增</span>
              <span className="customer-stat-value">{statsLoading ? "..." : monthlyNewCount}</span>
            </div>
            {topIndustry && (
              <div className="customer-stat-pill">
                <span className="customer-stat-label">主力行业</span>
                <span className="customer-stat-value">{topIndustry.name} {topIndustry.value}</span>
              </div>
            )}
          </div>
          {activeFilterItems.length > 0 && (
            <div className="customer-active-filters">
              <Typography.Text type="secondary">筛选</Typography.Text>
              {activeFilterItems.map((item) => (
                <Tag
                  key={item.key}
                  closable
                  onClose={(event) => {
                    event.preventDefault();
                    item.clear();
                  }}
                >
                  {item.label}
                </Tag>
              ))}
              <Button size="small" type="link" onClick={resetFilters}>清除</Button>
            </div>
          )}
        </div>
      </Card>

      {selectedRowKeys.length > 0 && (
        <div className="customer-batch-bar">
          <Space wrap>
            <Tag color="blue">已选 {selectedRowKeys.length} 个客户</Tag>
            <Tag color="red">A级 {selectedA}</Tag>
            <Tag color="orange">逾期跟进 {selectedOverdue}</Tag>
            <Popconfirm title={`确定删除 ${selectedRowKeys.length} 个客户?`} onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>批量删除</Button>
            </Popconfirm>
            <Button icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>批量打标签</Button>
            <Button onClick={() => setSelectedRowKeys([])}>清空选择</Button>
          </Space>
        </div>
      )}

      <Card
        className="customer-table-card"
        size="small"
        title={(
          <div className="customer-table-title">
            <Typography.Text strong>智能客户列表</Typography.Text>
            <Typography.Text type="secondary">
              {overdueOnly ? tableData.length : total} 条
            </Typography.Text>
            <Tag color="purple">{SMART_TASK_LABELS[activeSmartTask]}</Tag>
            {activeFilterItems.length > 0 && <Tag color="blue">已筛选</Tag>}
            {overdueOnly && <Tag color="red">仅逾期</Tag>}
          </div>
        )}
        extra={(
          <Space size={8}>
            <Segmented
              size="small"
              value={customerView}
              options={[
                { label: "表格", value: "table" },
                { label: "看板", value: "board" },
              ]}
              onChange={(value) => setCustomerView(value as CustomerViewMode)}
            />
            <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={() => fetch()}>
              刷新列表
            </Button>
          </Space>
        )}
      >
        {customerView === "board" ? (
          <div className="customer-board">
            {customerBoardColumns.map((column) => (
              <section className="customer-board-column" key={column.stage}>
                <div className="customer-board-column-head">
                  <div>
                    <Space size={6}>
                      <Tag color={getLevelColor(column.stage === "未分级" ? null : column.stage)}>{column.stage}</Tag>
                      <Typography.Text strong>{column.customers.length}</Typography.Text>
                    </Space>
                    <div className="customer-board-column-meta">
                      逾期 {column.overdueCount} | 平均优先级 {column.avgPriority || "-"}
                    </div>
                  </div>
                  {column.overdueCount > 0 && <BellOutlined style={{ color: "#cf1322" }} />}
                </div>
                <div className="customer-board-list">
                  {column.customers.length === 0 ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无客户" />
                  ) : column.customers.map((customer) => {
                    const next = nextFollowUpByCustomer.get(customer.id);
                    const priority = getCustomerPriorityScore(customer, next);
                    const overdue = overdueCustomerIds.has(customer.id);
                    const active = contextCustomer?.id === customer.id;
                    return (
                      <div
                        key={customer.id}
                        className={`customer-board-card${overdue ? " is-overdue" : ""}${active ? " is-active" : ""}`}
                        onClick={() => setContextCustomerId(customer.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") setContextCustomerId(customer.id);
                        }}
                      >
                        <div className="customer-board-card-head">
                          <Typography.Link
                            strong
                            className="customer-board-card-name"
                            ellipsis
                            onClick={(event) => {
                              event.stopPropagation();
                              navigate(`/customers/${customer.id}`);
                            }}
                          >
                            {customer.name}
                          </Typography.Link>
                          <Tag color={priority >= 75 ? "red" : priority >= 60 ? "orange" : "blue"}>{priority}</Tag>
                        </div>
                        <div className="customer-board-card-meta">
                          {[customer.industry, customer.region, customer.owner].filter(Boolean).join(" / ") || "暂无画像信息"}
                        </div>
                        <Space size={[4, 6]} wrap style={{ marginTop: 7 }}>
                          {customer.health_score != null && <Tag color={getHealthColor(customer.health_score)}>健康 {customer.health_score}</Tag>}
                          {next && <Tag color={getReminderDueMeta(next).color}>{getReminderDueMeta(next).text}</Tag>}
                          {overdue && <Tag color="red">逾期</Tag>}
                        </Space>
                        <div className="customer-board-card-meta">
                          {getCustomerSuggestedAction(customer, next)}
                        </div>
                        <div className="customer-board-card-actions">
                          <Button
                            size="small"
                            icon={<PhoneOutlined />}
                            onClick={(event) => {
                              event.stopPropagation();
                              openQuickFollowUp(customer);
                            }}
                          >
                            跟进
                          </Button>
                          <Button
                            size="small"
                            icon={<EyeOutlined />}
                            onClick={(event) => {
                              event.stopPropagation();
                              navigate(`/customers/${customer.id}`);
                            }}
                          >
                            详情
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <Table
            rowKey="id"
            size="middle"
            sticky
            columns={columns.filter((c) => visibleCols.includes(String(c.key)))}
            dataSource={tableData}
            loading={loading}
            onChange={handleTableChange}
            rowSelection={{
              columnWidth: 44,
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys as number[]),
            }}
            rowClassName={(record) => {
              if (contextCustomer?.id === record.id) return "customer-row-selected";
              if (overdueCustomerIds.has(record.id)) return "customer-row-overdue";
              if (record.level === "A") return "customer-row-key";
              return "";
            }}
            onRow={(record) => ({
              onClick: () => setContextCustomerId(record.id),
            })}
            scroll={{ x: "max-content" }}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无客户数据" /> }}
            pagination={{
              current: page,
              total: activeSmartTask !== "all" || overdueOnly ? tableData.length : total,
              pageSize,
              pageSizeOptions: ["10", "20", "50", "100"],
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => {
                setPage(p);
                setPageSize(ps);
              },
            }}
          />
        )}
      </Card>
            </>
          )}

          {workbenchTab === "followups" && (
            <Card
              className="customer-followup-card customer-table-card"
              size="small"
              title={(
                <div className="customer-table-title">
                  <Typography.Text strong>客户跟进全局集合</Typography.Text>
                  <Tag>总计 {globalFollowUpCounts.all ?? globalFollowUpTotal}</Tag>
                  <Tag color="red">逾期 {globalFollowUpCounts.overdue || 0}</Tag>
                  <Tag color="orange">今日 {globalFollowUpCounts.today || 0}</Tag>
                  <Tag color="blue">未来 {globalFollowUpCounts.upcoming || 0}</Tag>
                  <Tag color="green">已完成 {globalFollowUpCounts.closed || 0}</Tag>
                </div>
              )}
              extra={(
                <Button size="small" icon={<ReloadOutlined />} loading={globalFollowUpLoading} onClick={() => loadGlobalFollowUps()}>
                  刷新集合
                </Button>
              )}
            >
              <div className="customer-followup-toolbar">
                <Input.Search
                  allowClear
                  placeholder="搜索客户 / 跟进内容 / 负责人"
                  value={globalFollowUpQ}
                  style={{ width: 320, maxWidth: "100%" }}
                  onChange={(event) => {
                    setGlobalFollowUpQ(event.target.value);
                    if (!event.target.value) loadGlobalFollowUps(globalFollowUpBucket, "");
                  }}
                  onSearch={(value) => loadGlobalFollowUps(globalFollowUpBucket, value)}
                />
                <Segmented
                  value={globalFollowUpBucket}
                  options={GLOBAL_FOLLOW_UP_BUCKETS.map((item) => ({
                    value: item.key,
                    label: `${item.label} ${item.key === "all" ? (globalFollowUpCounts.all ?? globalFollowUpTotal) : (globalFollowUpCounts[item.key] || 0)}`,
                  }))}
                  onChange={(value) => {
                    const next = value as GlobalFollowUpBucket;
                    setGlobalFollowUpBucket(next);
                    loadGlobalFollowUps(next, globalFollowUpQ);
                  }}
                />
              </div>
              <List
                loading={globalFollowUpLoading}
                dataSource={globalFollowUps}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" /> }}
                renderItem={(item) => {
                  const due = getGlobalFollowUpDueMeta(item);
                  const isClosed = item.due_bucket === "closed";
                  return (
                    <List.Item
                      actions={isClosed ? [
                        <Button key="customer" size="small" type="link" onClick={() => navigate(`/customers/${item.customer_id}`)}>
                          查看客户
                        </Button>,
                      ] : [
                        <Button
                          key="complete"
                          size="small"
                          type="link"
                          loading={reminderActionKey === `global-complete-${item.id}`}
                          onClick={() => handleCompleteGlobalFollowUp(item)}
                        >
                          完成
                        </Button>,
                        <Button key="customer" size="small" type="link" onClick={() => navigate(`/customers/${item.customer_id}`)}>
                          查看客户
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={(
                          <Space size={6} wrap>
                            <Typography.Link onClick={() => navigate(`/customers/${item.customer_id}`)}>
                              {item.customer_name}
                            </Typography.Link>
                            <Tag color={due.color}>{due.text}</Tag>
                            <FollowUpStatusTag status={item.status} />
                            <FollowUpMethodTag method={item.method} />
                            <FollowUpPriorityTag priority={item.priority} />
                            {(item.assigned_to || item.owner) && (
                              <Typography.Text type="secondary">{item.assigned_to || item.owner}</Typography.Text>
                            )}
                          </Space>
                        )}
                        description={(
                          <Space direction="vertical" size={2}>
                            <Typography.Text type="secondary">
                              计划 {formatDateTime(item.planned_at)} | 创建 {formatDateTime(item.created_at)}
                            </Typography.Text>
                            {item.content && <Typography.Text>{item.content}</Typography.Text>}
                            {item.result && <Typography.Text type="secondary">结果：{item.result}</Typography.Text>}
                          </Space>
                        )}
                      />
                    </List.Item>
                  );
                }}
              />
            </Card>
          )}
        </main>

        <aside className="customer-ai-context">
          <div className="customer-ai-panel">
            <div className="customer-ai-panel-head">
              <Space size={6}>
                <BulbOutlined />
                <Typography.Text strong>AI上下文</Typography.Text>
              </Space>
              {contextCustomer && <Tag color={getLevelColor(contextCustomer.level)}>{contextCustomer.level || "-"}</Tag>}
            </div>
            {!contextCustomer ? (
              <div className="customer-ai-context-body">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择客户查看AI上下文" />
              </div>
            ) : (
              <div className="customer-ai-context-body">
                <Typography.Link strong onClick={() => navigate(`/customers/${contextCustomer.id}`)}>
                  {contextCustomer.name}
                </Typography.Link>
                <div className="customer-ai-context-note">
                  {[contextCustomer.short_name, contextCustomer.industry, contextCustomer.region].filter(Boolean).join(" / ") || "暂无画像信息"}
                </div>
                <div className="customer-ai-score">
                  <div>
                    <Typography.Text type="secondary">AI优先级</Typography.Text>
                    <div className="customer-ai-context-note">按跟进、等级、健康度计算</div>
                  </div>
                  <div className="customer-ai-score-value">{contextPriorityScore}</div>
                </div>
                <Space size={[4, 6]} wrap>
                  {contextCustomer.health_score != null && <Tag color={getHealthColor(contextCustomer.health_score)}>健康 {contextCustomer.health_score}</Tag>}
                  {contextNextFollowUp && <Tag color={getReminderDueMeta(contextNextFollowUp).color}>{getReminderDueMeta(contextNextFollowUp).text}</Tag>}
                  {contextCustomer.owner && <Tag>负责人 {contextCustomer.owner}</Tag>}
                </Space>
                <div className="customer-ai-action-box">
                  <Typography.Text strong>推荐下一步</Typography.Text>
                  <div className="customer-ai-context-note">{contextSuggestedAction}</div>
                </div>
                <div className="customer-ai-talk-track">
                  <Space style={{ width: "100%", justifyContent: "space-between" }}>
                    <Typography.Text strong>建议话术</Typography.Text>
                    <Button
                      size="small"
                      type="link"
                      onClick={() => {
                        navigator.clipboard?.writeText(contextTalkTrack.join("\n"));
                        message.success("话术已复制");
                      }}
                    >
                      复制
                    </Button>
                  </Space>
                  <ol>
                    {contextTalkTrack.map((line) => <li key={line}>{line}</li>)}
                  </ol>
                </div>
                <Descriptions column={1} size="small" style={{ marginTop: 10 }}>
                  <Descriptions.Item label="联系人">{contextCustomer.contact_person || "-"}</Descriptions.Item>
                  <Descriptions.Item label="电话">{contextCustomer.phone || "-"}</Descriptions.Item>
                  <Descriptions.Item label="最近联系">{formatDate(contextCustomer.last_contacted_at)}</Descriptions.Item>
                  <Descriptions.Item label="计划跟进">{formatDateTime(contextNextFollowUp?.planned_at)}</Descriptions.Item>
                </Descriptions>
                <div className="customer-ai-context-actions">
                  <Button size="small" type="primary" icon={<PhoneOutlined />} onClick={() => openAIPlannedFollowUp(contextCustomer, contextNextFollowUp)}>转跟进</Button>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/customers/${contextCustomer.id}`)}>详情</Button>
                  <Button size="small" icon={<ShoppingCartOutlined />} onClick={() => navigate(`/sales/orders/new?customer_id=${contextCustomer.id}`)}>订单</Button>
                  <Button size="small" icon={<RobotOutlined />} onClick={() => navigate(`/customers/${contextCustomer.id}/360`)}>AI 360</Button>
                </div>
                {contextNextFollowUp && (
                  <div className="customer-ai-context-actions">
                    <Button
                      size="small"
                      loading={reminderActionKey === `complete-${contextNextFollowUp.id}`}
                      onClick={() => handleCompleteReminder(contextNextFollowUp)}
                    >
                      完成提醒
                    </Button>
                    <Button
                      size="small"
                      loading={reminderActionKey === `postpone-${contextNextFollowUp.id}`}
                      onClick={() => handlePostponeReminder(contextNextFollowUp)}
                    >
                      延期1天
                    </Button>
                  </div>
                )}
                <div className="customer-ai-products">
                  <Space style={{ width: "100%", justifyContent: "space-between" }}>
                    <Typography.Text strong>推荐产品/机会</Typography.Text>
                    <Button
                      size="small"
                      loading={productRecLoading && productRecCustomerId === contextCustomer.id}
                      onClick={() => handleLoadProductRecommendations(contextCustomer)}
                    >
                      生成
                    </Button>
                  </Space>
                  {productRecResult && productRecCustomerId === contextCustomer.id ? (
                    <>
                      {productRecResult.summary && (
                        <div className="customer-ai-context-note">{productRecResult.summary}</div>
                      )}
                      {productRecResult.recommendations.slice(0, 3).map((item) => (
                        <div className="customer-ai-product-item" key={`${item.product_name}-${item.brand}`}>
                          <Space size={4} wrap>
                            <Typography.Text strong>{item.product_name}</Typography.Text>
                            {item.brand && <Tag>{item.brand}</Tag>}
                            {item.priority && <Tag color={item.priority === "高" ? "red" : item.priority === "中" ? "orange" : "blue"}>{item.priority}</Tag>}
                          </Space>
                          <div className="customer-ai-context-note">{item.reason || item.estimated_potential || "-"}</div>
                        </div>
                      ))}
                    </>
                  ) : (
                    <div className="customer-ai-context-note">基于客户画像生成交叉销售建议</div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="customer-ai-panel">
            <div className="customer-ai-panel-head">
              <Typography.Text strong>辅助能力</Typography.Text>
            </div>
            <div className="customer-ai-context-body">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button block size="small" icon={<SendOutlined />} onClick={() => setSemanticOpen(true)}>AI语义搜索</Button>
                <Button block size="small" icon={<SafetyCertificateOutlined />} loading={dupLoading} onClick={handleDetectDups}>重复检测</Button>
                <Button block size="small" icon={<TagsOutlined />} disabled={!selectedRowKeys.length} onClick={() => setTagModalOpen(true)}>批量标签</Button>
              </Space>
            </div>
          </div>
        </aside>
      </div>

      <Drawer
        title="跟进提醒"
        width={620}
        open={reminderDrawerOpen}
        onClose={() => setReminderDrawerOpen(false)}
        extra={(
          <Space>
            <Button size="small" icon={<ReloadOutlined />} loading={reminderLoading} onClick={loadOverdue}>
              刷新
            </Button>
            <Button
              size="small"
              type={overdueOnly ? "primary" : "default"}
              onClick={() => setOverdueOnly((value) => !value)}
            >
              {overdueOnly ? "取消逾期筛选" : "只看逾期客户"}
            </Button>
          </Space>
        )}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Segmented
            value={reminderBucket}
            options={REMINDER_BUCKETS.map((item) => ({
              value: item.key,
              label: `${item.label} ${reminderCounts[item.key]}`,
            }))}
            onChange={(value) => setReminderBucket(value as ReminderBucket)}
          />
          <Typography.Text type="secondary">{formatReminderRefreshTime(reminderRefreshedAt)}</Typography.Text>
          {visibleReminders.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待处理跟进提醒" />
          ) : (
            <List
              loading={reminderLoading}
              dataSource={visibleReminders}
              renderItem={(item) => {
                const due = getReminderDueMeta(item);
                return (
                  <List.Item
                    actions={[
                      <Button
                        key="complete"
                        size="small"
                        type="link"
                        loading={reminderActionKey === `complete-${item.id}`}
                        onClick={() => handleCompleteReminder(item)}
                      >
                        完成
                      </Button>,
                      <Button
                        key="postpone"
                        size="small"
                        type="link"
                        loading={reminderActionKey === `postpone-${item.id}`}
                        onClick={() => handlePostponeReminder(item)}
                      >
                        延期1天
                      </Button>,
                      <Button
                        key="customer"
                        size="small"
                        type="link"
                        onClick={() => navigate(`/customers/${item.customer_id}`)}
                      >
                        查看客户
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={(
                        <Space size={6} wrap>
                          <Typography.Link onClick={() => navigate(`/customers/${item.customer_id}`)}>
                            {item.customer_name}
                          </Typography.Link>
                          <Tag color={due.color}>{due.text}</Tag>
                          {item.priority && <Tag>{item.priority}</Tag>}
                          {item.owner && <Typography.Text type="secondary">{item.owner}</Typography.Text>}
                        </Space>
                      )}
                      description={`${item.method || "跟进"} | 计划 ${formatDateTime(item.planned_at)}${item.content ? ` | ${item.content}` : ""}`}
                    />
                  </List.Item>
                );
              }}
            />
          )}
        </Space>
      </Drawer>

      <Modal
        title="添加标签"
        open={tagModalOpen}
        onCancel={() => setTagModalOpen(false)}
        onOk={handleBatchTag}
        okText="添加到已选客户"
        okButtonProps={{ disabled: !batchTagIds.length || !selectedRowKeys.length }}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <Typography.Text type="secondary">可用标签</Typography.Text>
            <Button size="small" icon={<TagsOutlined />} loading={tagGenerating} onClick={handleGenerateDefaultTags}>
              生成5个默认标签
            </Button>
          </Space>
          <Select
            mode="multiple"
            style={{ width: "100%" }}
            placeholder="选择要添加的标签"
            value={batchTagIds}
            onChange={(v) => setBatchTagIds(v)}
            options={tags.map((t) => ({ value: t.id, label: t.name }))}
          />
          <Divider style={{ margin: 0 }} />
          <Typography.Text type="secondary">新建标签</Typography.Text>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="标签名称"
              value={tagCreateName}
              onChange={(event) => setTagCreateName(event.target.value)}
              onPressEnter={handleCreateBatchTag}
            />
            <Select
              style={{ width: 110 }}
              value={tagCreateColor}
              options={TAG_COLOR_OPTIONS}
              onChange={setTagCreateColor}
            />
            <Button loading={tagCreating} onClick={handleCreateBatchTag}>创建</Button>
          </Space.Compact>
        </Space>
      </Modal>

      <Modal title="疑似重复客户" open={dupModalOpen} onCancel={() => setDupModalOpen(false)} footer={null} width={720}>
        {duplicatePairs.length === 0 ? (
          <Empty description="未发现疑似重复客户" />
        ) : (
          <List
            dataSource={duplicatePairs}
            renderItem={(pair) => (
              <List.Item
                actions={[
                  <Button key="merge" icon={<MergeCellsOutlined />} onClick={() => openMergeModal(pair)}>合并</Button>,
                ]}
              >
                <List.Item.Meta
                  title={(
                    <Space>
                      <Typography.Text>{pair.customer_a.name}</Typography.Text>
                      <Tag color="orange">相似 {(pair.similarity * 100).toFixed(0)}%</Tag>
                      <Typography.Text>{pair.customer_b.name}</Typography.Text>
                    </Space>
                  )}
                  description={(
                    <Space size={16} wrap>
                      {pair.reasons?.length ? (
                        <span>依据: {pair.reasons.join("、")}</span>
                      ) : null}
                      <span>电话A: {pair.customer_a.phone || "-"}</span>
                      <span>电话B: {pair.customer_b.phone || "-"}</span>
                      <span>负责人A: {pair.customer_a.owner || "-"}</span>
                      <span>负责人B: {pair.customer_b.owner || "-"}</span>
                    </Space>
                  )}
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

      <Modal title="语义搜索" open={semanticOpen} onCancel={() => setSemanticOpen(false)} footer={null} width={620}>
        <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
          <Input
            placeholder="例如：华东地区做汽车电子的A级客户"
            value={semanticQ}
            onChange={(e) => setSemanticQ(e.target.value)}
            onPressEnter={handleSemanticSearch}
          />
          <Button type="primary" loading={semanticLoading} onClick={handleSemanticSearch}>搜索</Button>
        </Space.Compact>
        <Table
          dataSource={semanticResults}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: semanticQ && !semanticLoading ? "未找到匹配客户" : "输入关键词后搜索" }}
          columns={[
            {
              title: "客户名称",
              dataIndex: "name",
              key: "name",
              render: (name: string, r: SimilarCustomer) => (
                <a
                  onClick={() => {
                    setSemanticOpen(false);
                    navigate(`/customers/${r.id}`);
                  }}
                >
                  {name}
                </a>
              ),
            },
            { title: "行业", dataIndex: "industry", key: "industry", render: (v: string) => <Tag>{v || "-"}</Tag> },
            { title: "区域", dataIndex: "region", key: "region", render: (v: string) => v || "-" },
            { title: "相似度", dataIndex: "similarity", key: "similarity", render: (v: number) => `${(v * 100).toFixed(1)}%` },
          ]}
        />
      </Modal>

      <Modal
        title="合并客户"
        open={mergeModalOpen}
        onCancel={() => {
          setMergeModalOpen(false);
          setMergeSource(null);
        }}
        onOk={handleMerge}
        confirmLoading={merging}
        okText="确认合并"
        okButtonProps={{ danger: true }}
      >
        {mergeSource && (
          <div>
            <p>确认将以下客户合并？</p>
            <Card size="small" style={{ marginBottom: 12, backgroundColor: "#fff2f0" }}>
              <Typography.Text strong delete>源客户: {mergeSource.customer_a.name}</Typography.Text>
              <div style={{ fontSize: 12, color: "#888" }}>
                电话: {mergeSource.customer_a.phone || "无"} | 负责人: {mergeSource.customer_a.owner || "无"}
              </div>
            </Card>
            <Card size="small" style={{ backgroundColor: "#f6ffed" }}>
              <Typography.Text strong>目标客户: {mergeSource.customer_b.name}</Typography.Text>
              <div style={{ fontSize: 12, color: "#888" }}>
                电话: {mergeSource.customer_b.phone || "无"} | 负责人: {mergeSource.customer_b.owner || "无"}
              </div>
            </Card>
            <p style={{ marginTop: 12, color: "#ff4d4f" }}>
              合并后，源客户的联系人、跟进记录、标签、附件和订单将转移到目标客户，源客户将被删除。
            </p>
          </div>
        )}
      </Modal>

      <Drawer
        title={detailCustomer ? `客户详情 - ${detailCustomer.name}` : "客户详情"}
        width={700}
        placement="right"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {detailLoading ? (
          <Card loading />
        ) : !detailCustomer ? (
          <Empty description="暂无详情" />
        ) : (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Space wrap>
              <Tag color={getLevelColor(detailCustomer.level)}>等级 {detailCustomer.level || "-"}</Tag>
              <Tag>行业 {detailCustomer.industry || "-"}</Tag>
              <Tag>区域 {detailCustomer.region || "-"}</Tag>
              <Tag color={getHealthColor(detailCustomer.health_score)}>健康度 {detailCustomer.health_score ?? "-"}</Tag>
            </Space>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="客户编码">{detailCustomer.code || "-"}</Descriptions.Item>
              <Descriptions.Item label="客户简称">{detailCustomer.short_name || "-"}</Descriptions.Item>
              <Descriptions.Item label="负责人">{detailCustomer.owner || "-"}</Descriptions.Item>
              <Descriptions.Item label="联系人">{detailCustomer.contact_person || "-"}</Descriptions.Item>
              <Descriptions.Item label="电话">{detailCustomer.phone || "-"}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{detailCustomer.email || "-"}</Descriptions.Item>
              <Descriptions.Item label="来源">{detailCustomer.source || "-"}</Descriptions.Item>
              <Descriptions.Item label="信用等级">{detailCustomer.credit_level || "-"}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDate(detailCustomer.created_at)}</Descriptions.Item>
              <Descriptions.Item label="最近联系">{formatDate(detailCustomer.last_contacted_at)}</Descriptions.Item>
              <Descriptions.Item label="地址" span={2}>{detailCustomer.address || "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{detailCustomer.notes || "-"}</Descriptions.Item>
            </Descriptions>

            <Divider style={{ margin: "4px 0" }}>经营指标</Divider>
            {!detailStats ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无指标数据" />
            ) : (
              <Row gutter={[10, 10]}>
                <Col span={8}><Card size="small"><Statistic title="订单数" value={detailStats.order_count} /></Card></Col>
                <Col span={8}><Card size="small"><Statistic title="总营收" value={detailStats.total_revenue} precision={2} /></Card></Col>
                <Col span={8}><Card size="small"><Statistic title="信用占用%" value={detailStats.credit_usage_pct} precision={1} /></Card></Col>
              </Row>
            )}

            <Divider style={{ margin: "4px 0" }}>快速动作</Divider>
            <Space wrap>
              <Button icon={<EyeOutlined />} onClick={() => navigate(`/customers/${detailCustomer.id}`)}>完整详情</Button>
              <Button icon={<ShoppingCartOutlined />} onClick={() => navigate(`/sales/orders/new?customer_id=${detailCustomer.id}`)}>建订单</Button>
              <Button icon={<PhoneOutlined />} onClick={() => navigate(`/customers/${detailCustomer.id}?tab=followups`)}>建跟进</Button>
              <Button icon={<SwapOutlined />} onClick={() => setVendCustomer(detailCustomer)}>转供应商</Button>
            </Space>
          </Space>
        )}
      </Drawer>

      <Drawer
        title={quickFollowUpCustomer ? `新增跟进 - ${quickFollowUpCustomer.name}` : "新增跟进"}
        width={520}
        open={!!quickFollowUpCustomer}
        onClose={() => setQuickFollowUpCustomer(null)}
        extra={(
          <Space>
            <Button onClick={() => setQuickFollowUpCustomer(null)}>取消</Button>
            <Button type="primary" loading={quickFollowUpSaving} onClick={handleQuickFollowUpSubmit}>保存</Button>
          </Space>
        )}
      >
        <Form
          form={quickFollowUpForm}
          layout="vertical"
          initialValues={{ method: "phone", status: "planned", priority: "medium" }}
          onValuesChange={(changed) => {
            if (changed.status === "completed" && !quickFollowUpForm.getFieldValue("completed_at")) {
              quickFollowUpForm.setFieldValue("completed_at", dayjs());
            }
          }}
        >
          {quickFollowUpCustomer && (
            <Form.Item>
              <FollowUpAIRecognizer
                customerId={quickFollowUpCustomer.id}
                form={quickFollowUpForm}
                getSeedText={() => {
                  const values = quickFollowUpForm.getFieldsValue(["content", "result"]) as { content?: string; result?: string };
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

      {vendCustomer && (
        <VendAsSupplierModal
          customer={vendCustomer}
          open={!!vendCustomer}
          onCancel={() => setVendCustomer(null)}
          onSuccess={() => {
            setVendCustomer(null);
            fetch();
          }}
        />
      )}
    </CustomerModuleShell>
  );
}
