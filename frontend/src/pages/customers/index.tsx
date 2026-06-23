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
import { StatusTag } from "../../ui";
import { useCustomersFilter } from "../../hooks/useCustomersFilter";
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
  getApiErrorMessage,
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
import "./index.css";
import dayjs from "dayjs";
import {
  FOLLOW_UP_METHOD_OPTIONS,
  FOLLOW_UP_PRIORITY_OPTIONS,
  FOLLOW_UP_STATUS_OPTIONS,
  FollowUpMethodTag,
  FollowUpPriorityTag,
  FollowUpStatusTag,
} from "./customerUi";
import {
  buildFollowUpPlanContent,
  buildFollowUpTalkTrack,
  COL_LABEL_MAP,
  CREDIT_LEVELS,
  CRM_OBJECTS,
  CRM_VIEW_PRESETS,
  CustomerViewMode,
  CustomerWorkbenchTab,
  CrmObjectKey,
  DEFAULT_STATS,
  DEFAULT_VISIBLE_COL_KEYS,
  formatDate,
  formatDateTime,
  formatReminderRefreshTime,
  GLOBAL_FOLLOW_UP_BUCKETS,
  GlobalFollowUpBucket,
  getCustomerPriorityScore,
  getCustomerSuggestedAction,
  getDaysSince,
  getGlobalFollowUpDueMeta,
  getHealthColor,
  getLevelColor,
  getReminderDueMeta,
  INDUSTRIES,
  LEVELS,
  PEOPLE_VISIBLE_COL_KEYS,
  plusOneDayIso,
  REGIONS,
  ReminderBucket,
  REMINDER_BUCKETS,
  SCENE_FILTERS,
  SCENE_OPTIONS,
  SceneValue,
  SMART_TASK_LABELS,
  SmartTaskKey,
  SOURCES,
  TAG_COLOR_OPTIONS,
} from "./constants";
import { useCustomerTableColumns } from "./useCustomerTableColumns";
import CustomerStatsCards from "./CustomerStatsCards";
import CustomerCrmToolbar from "./CustomerCrmToolbar";
import CustomerFilterBar from "./CustomerFilterBar";
import CustomerDetailDrawer from "./CustomerDetailDrawer";
import CustomerReminderDrawer from "./CustomerReminderDrawer";
import CustomerSemanticSearchModal from "./CustomerSemanticSearchModal";
import { CustomerDuplicateListModal, CustomerMergeModal } from "./CustomerDuplicateModals";
import CustomerTagModal from "./CustomerTagModal";
import CustomerQuickFollowUpDrawer from "./CustomerQuickFollowUpDrawer";

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
  // 8 filter / sort states extracted to useCustomersFilter (Stage 3 Day 1)
  const filter = useCustomersFilter();
  const {
    q,
    scene,
    industry,
    level,
    region,
    source,
    creditLevel,
    sortBy,
    sortOrder,
    setQ,
    setScene,
    setIndustry,
    setLevel,
    setRegion,
    setSource,
    setCreditLevel,
    setSort,
  } = filter;

  const [advancedOpen, setAdvancedOpen] = useState(false);
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
  const [smartTask, setSmartTask] = useState<SmartTaskKey>("all");
  const [activeViewPreset, setActiveViewPreset] = useState("today");
  const [contextCustomerId, setContextCustomerId] = useState<number | null>(null);
  const [productRecLoading, setProductRecLoading] = useState(false);
  const [productRecCustomerId, setProductRecCustomerId] = useState<number | null>(null);
  const [productRecResult, setProductRecResult] = useState<CustomerProductMatch | null>(null);

  const allColKeys = [
    "code",
    "name",
    "short_name",
    "industry",
    "level",
    "region",
    "credit_level",
    "credit_limit",
    "payment_terms",
    "currency",
    "tax_id",
    "delivery_address",
    "health",
    "next_followup",
    "tags",
    "owner",
    "contact_person",
    "phone",
    "email",
    "last_contacted_at",
    "source",
    "customer_type",
    "created_at",
    "actions",
  ];
  const [visibleCols, setVisibleCols] = useState<string[]>(DEFAULT_VISIBLE_COL_KEYS);
  const navigate = useNavigate();
  const location = useLocation();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const searchText = q.trim();
  const activeSmartTask: SmartTaskKey = searchText ? "all" : smartTask;

  const overdueCustomerIds = useMemo(
    () => new Set(overdueList.map((item) => item.customer_id)),
    [overdueList],
  );
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
  const activeFilterItems = useMemo<
    Array<{ key: string; label: string; clear: () => void }>
  >(() => {
    const items: Array<{ key: string; label: string; clear: () => void }> = [];
    const selectedScene = SCENE_OPTIONS.find((item) => item.value === scene);
    if (searchText) items.push({ key: "q", label: `搜索：${searchText}`, clear: () => setQ("") });
    if (selectedScene && scene !== "all") {
      items.push({
        key: "scene",
        label: `场景：${selectedScene.label}`,
        clear: () => setScene("all"),
      });
    }
    if (industry)
      items.push({
        key: "industry",
        label: `行业：${industry}`,
        clear: () => setIndustry(undefined),
      });
    if (level)
      items.push({ key: "level", label: `等级：${level}`, clear: () => setLevel(undefined) });
    if (region)
      items.push({ key: "region", label: `区域：${region}`, clear: () => setRegion(undefined) });
    if (source)
      items.push({ key: "source", label: `来源：${source}`, clear: () => setSource(undefined) });
    if (creditLevel) {
      items.push({
        key: "creditLevel",
        label: `信用：${creditLevel}`,
        clear: () => setCreditLevel(undefined),
      });
    }
    if (overdueOnly)
      items.push({ key: "overdueOnly", label: "仅逾期客户", clear: () => setOverdueOnly(false) });
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
    () =>
      reminderBucket === "all"
        ? followUpReminders
        : followUpReminders.filter((item) => item.due_bucket === reminderBucket),
    [followUpReminders, reminderBucket],
  );
  const nextFollowUpByCustomer = useMemo(() => {
    const map = new Map<number, FollowUpReminder>();
    for (const item of followUpReminders) {
      const existing = map.get(item.customer_id);
      if (
        !existing ||
        new Date(item.planned_at).getTime() < new Date(existing.planned_at).getTime()
      ) {
        map.set(item.customer_id, item);
      }
    }
    return map;
  }, [followUpReminders]);
  const baseTableData = useMemo(
    () => (overdueOnly ? data.filter((item) => overdueCustomerIds.has(item.id)) : data),
    [data, overdueOnly, overdueCustomerIds],
  );
  const customerMatchesSmartTask = (customer: Customer, task: SmartTaskKey) => {
    const next = nextFollowUpByCustomer.get(customer.id);
    const lastContactAge = getDaysSince(customer.last_contacted_at);
    const createdAge = getDaysSince(customer.created_at);
    if (task === "all") return true;
    if (task === "today") return next?.due_bucket === "today";
    if (task === "overdue") return overdueCustomerIds.has(customer.id);
    if (task === "high_risk")
      return (
        overdueCustomerIds.has(customer.id) ||
        (customer.health_score != null && customer.health_score < 60)
      );
    if (task === "key_stale")
      return customer.level === "A" && (lastContactAge == null || lastContactAge > 30);
    if (task === "new_customers") return createdAge != null && createdAge <= 14;
    if (task === "ai_suggested") return getCustomerPriorityScore(customer, next) >= 65;
    return true;
  };
  const tableData = useMemo(
    () =>
      baseTableData
        .filter((item) => customerMatchesSmartTask(item, activeSmartTask))
        .sort((a, b) => {
          const scoreA = getCustomerPriorityScore(a, nextFollowUpByCustomer.get(a.id));
          const scoreB = getCustomerPriorityScore(b, nextFollowUpByCustomer.get(b.id));
          return scoreB - scoreA;
        }),
    [activeSmartTask, baseTableData, nextFollowUpByCustomer, overdueCustomerIds],
  );
  const smartTaskItems = useMemo(() => {
    const items: Array<{
      key: SmartTaskKey;
      label: string;
      count: number;
      color: string;
      note: string;
    }> = [
      {
        key: "today",
        label: SMART_TASK_LABELS.today,
        count: data.filter((item) => customerMatchesSmartTask(item, "today")).length,
        color: "orange",
        note: "今天需要推进",
      },
      {
        key: "overdue",
        label: SMART_TASK_LABELS.overdue,
        count: data.filter((item) => customerMatchesSmartTask(item, "overdue")).length,
        color: "red",
        note: "已超过计划时间",
      },
      {
        key: "high_risk",
        label: SMART_TASK_LABELS.high_risk,
        count: data.filter((item) => customerMatchesSmartTask(item, "high_risk")).length,
        color: "red",
        note: "健康度低或逾期",
      },
      {
        key: "key_stale",
        label: SMART_TASK_LABELS.key_stale,
        count: data.filter((item) => customerMatchesSmartTask(item, "key_stale")).length,
        color: "gold",
        note: "重点客户需唤醒",
      },
      {
        key: "new_customers",
        label: SMART_TASK_LABELS.new_customers,
        count: data.filter((item) => customerMatchesSmartTask(item, "new_customers")).length,
        color: "blue",
        note: "14天内新建",
      },
      {
        key: "ai_suggested",
        label: SMART_TASK_LABELS.ai_suggested,
        count: data.filter((item) => customerMatchesSmartTask(item, "ai_suggested")).length,
        color: "purple",
        note: "综合优先级较高",
      },
      {
        key: "all",
        label: SMART_TASK_LABELS.all,
        count: data.length,
        color: "default",
        note: "回到普通列表",
      },
    ];
    return items;
  }, [data, nextFollowUpByCustomer, overdueCustomerIds]);
  const contextCustomer = useMemo(
    () => data.find((item) => item.id === contextCustomerId) || tableData[0] || null,
    [contextCustomerId, data, tableData],
  );
  const contextNextFollowUp = contextCustomer
    ? nextFollowUpByCustomer.get(contextCustomer.id)
    : undefined;
  const contextPriorityScore = contextCustomer
    ? getCustomerPriorityScore(contextCustomer, contextNextFollowUp)
    : 0;
  const contextSuggestedAction = contextCustomer
    ? getCustomerSuggestedAction(contextCustomer, contextNextFollowUp)
    : "";
  const contextTalkTrack = useMemo(
    () => (contextCustomer ? buildFollowUpTalkTrack(contextCustomer, contextNextFollowUp) : []),
    [contextCustomer, contextNextFollowUp],
  );
  const customerBoardColumns = useMemo(() => {
    const stages = [...LEVELS, "未分级"];
    return stages.map((stage) => {
      const customers = tableData.filter((customer) => (customer.level || "未分级") === stage);
      const overdueCount = customers.filter((customer) =>
        overdueCustomerIds.has(customer.id),
      ).length;
      const avgPriority = customers.length
        ? Math.round(
            customers.reduce(
              (sum, customer) =>
                sum + getCustomerPriorityScore(customer, nextFollowUpByCustomer.get(customer.id)),
              0,
            ) / customers.length,
          )
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

  const loadGlobalFollowUps = async (bucket = globalFollowUpBucket, query = globalFollowUpQ) => {
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载全局跟进集合失败"));
    } finally {
      setGlobalFollowUpLoading(false);
    }
  };

  const fetch = async (p = page, ps = pageSize, search = q) => {
    setLoading(true);
    try {
      const sceneFilter = SCENE_FILTERS[scene];
      const resolvedLevel = level ?? (sceneFilter as any).level;
      const resolvedRegion = region ?? (sceneFilter as any).region;
      const resolvedSource = source ?? (sceneFilter as any).source;
      const resolvedCreditLevel = creditLevel ?? (sceneFilter as any).creditLevel;

      const params: Record<string, unknown> = {
        page: p,
        page_size: ps,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (scene === "pending_erp") params.missing_erp = "1";

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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载客户列表失败"));
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
    getTags()
      .then((r) => setTags(r.data.data || []))
      .catch(() => {});
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
    setSort("id", "desc");
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
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
      if (creditLevel ?? sceneFilter.creditLevel)
        params.credit_level = creditLevel ?? sceneFilter.creditLevel;

      const resp = await exportCustomers(params);
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "customers.csv";
      a.click();
      URL.revokeObjectURL(url);
      message.success("导出成功");
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "导出失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "下载模板失败"));
    }
  };

  const handleImport = async (file: File) => {
    setImporting(true);
    try {
      const resp = await importCustomers(file);
      const result = resp.data.data as {
        created?: number;
        skipped?: number;
        imported?: number;
        updated?: number;
      };
      const created = result.created ?? result.imported ?? 0;
      const skipped = result.skipped ?? 0;
      const updated = result.updated ?? 0;
      message.success(`导入成功：新建 ${created} 条，更新 ${updated} 条，跳过 ${skipped} 条`);
      await Promise.all([fetch(), loadStats(), loadOverdue()]);
    } catch (err: any) {
      message.error(
        err?.response?.data?.msg || err?.response?.data?.detail || "导入失败，请检查文件格式",
      );
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量删除失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量打标签失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "创建标签失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "生成默认标签失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "检测失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "合并失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "预警检查失败"));
    } finally {
      setAlertChecking(false);
    }
  };

  const handleMarkAllAlertsRead = async () => {
    try {
      await markAllAlertsRead();
      setAlertCount(0);
      message.success("已全部标记为已读");
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const handleSemanticSearch = async () => {
    if (!semanticQ.trim()) return;
    setSemanticLoading(true);
    try {
      const resp = await searchSimilarCustomers(semanticQ);
      setSemanticResults((resp.data.data || []) as SimilarCustomer[]);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "语义搜索失败"));
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
      if (s.order === "ascend") setSort(s.field, "asc");
      else setSort(s.field, "desc"); // covers "descend" + null + undefined
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载客户详情失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "完成跟进失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "延期失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "完成跟进失败"));
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
      planned_at: dayjs().add(
        next?.due_bucket === "overdue" || next?.due_bucket === "today" ? 2 : 24,
        "hour",
      ),
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "AI产品推荐失败"));
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
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "创建跟进失败"));
    } finally {
      setQuickFollowUpSaving(false);
    }
  };

  const columns: ColumnsType<Customer> = useCustomerTableColumns({
    sortBy,
    sortOrder,
    overdueCustomerIds,
    nextFollowUpByCustomer,
    onOpenDetail: openDetailDrawer,
    onOpenQuickFollowUp: openQuickFollowUp,
    onConfirmDelete: confirmDeleteCustomer,
    onVendAsSupplier: setVendCustomer,
  });

  const moreActionsContent = (
    <Space direction="vertical" size={8} style={{ width: 260 }}>
      <Upload accept=".csv" showUploadList={false} beforeUpload={handleImport} disabled={importing}>
        <Button style={{ width: 260 }} icon={<UploadOutlined />} loading={importing}>
          导入客户
        </Button>
      </Upload>
      <Button block onClick={handleTemplate}>
        下载导入模板
      </Button>
      <Button block icon={<DownloadOutlined />} onClick={handleExport}>
        导出当前筛选
      </Button>
      <Button
        block
        icon={<SafetyCertificateOutlined />}
        loading={dupLoading}
        onClick={handleDetectDups}
      >
        疑似重复检测
      </Button>
      <Button block icon={<SendOutlined />} onClick={() => setSemanticOpen(true)}>
        语义搜索
      </Button>
      <Button block danger={alertCount > 0} loading={alertChecking} onClick={handleCheckAlerts}>
        {alertCount > 0 ? `预警检查(${alertCount})` : "预警检查"}
      </Button>
      {alertCount > 0 && (
        <Button block onClick={handleMarkAllAlertsRead}>
          全部预警标为已读
        </Button>
      )}
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
      extra={
        <>
          <Button icon={<RobotOutlined />} onClick={() => navigate("/customers/workbench")}>
            AI队列
          </Button>
          <Button icon={<BulbOutlined />} onClick={() => setSemanticOpen(true)}>
            AI搜索
          </Button>
        </>
      }
    >
      {/* inline styles (CustomerList.css removed Stage 5 Day 2 — see CUSTOMER_CSS_AUDIT.md) */}

      <div className="customer-workbench-grid">
        <CustomerStatsCards
          total={stats.total}
          statsLoading={statsLoading}
          filteredCount={overdueOnly ? tableData.length : total}
          todayReminders={reminderCounts.today}
          overdueReminders={reminderCounts.overdue}
          lastRefreshedAt={reminderRefreshedAt}
          levelACount={levelACount}
          topRegion={topRegion}
          monthlyNewCount={monthlyNewCount}
          formatRefreshTime={formatReminderRefreshTime}
        />
      </div>

      <div className="crm-compact-bar">
        <CustomerCrmToolbar
          activeCrmObject={activeCrmObject}
          activeViewPreset={activeViewPreset}
          customerView={customerView}
          reminderTotal={reminderCounts.today + reminderCounts.overdue}
          onOpenCrmObject={(key) => {
            const object = CRM_OBJECTS.find((item) => item.key === key);
            if (object) openCrmObject(object);
          }}
          onApplyCrmViewPreset={applyCrmViewPreset}
          onSetCustomerView={setCustomerView}
          onOpenReminderDrawer={() => setReminderDrawerOpen(true)}
        />
      </div>

      <div className="customer-ai-layout">
        <aside className="customer-ai-sidebar">
          <div className="customer-ai-panel">
            <div className="customer-ai-panel-head">
              <Space size={6}>
                <RobotOutlined />
                <Typography.Text strong>AI任务队列</Typography.Text>
              </Space>
              <Button size="small" type="link" onClick={() => navigate("/customers/workbench")}>
                完整队列
              </Button>
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
                  <StatusTag tone={item.color}>{item.count}</StatusTag>
                </span>
                <span className="customer-ai-task-note">{item.note}</span>
              </button>
            ))}
          </div>

          <div className={`customer-ai-panel${reminderCounts.overdue > 0 ? " is-risk" : ""}`}>
            <div className="customer-ai-panel-head">
              <Space size={6}>
                <BellOutlined
                  style={{ color: reminderCounts.overdue > 0 ? "#cf1322" : undefined }}
                />
                <Typography.Text strong>跟进提醒</Typography.Text>
              </Space>
              <Button size="small" type="link" onClick={() => setReminderDrawerOpen(true)}>
                明细
              </Button>
            </div>
            <div className="customer-ai-context-body">
              <Space size={[4, 6]} wrap>
                <StatusTag tone={reminderCounts.overdue > 0 ? "danger" : "neutral"}>
                  逾期 {reminderCounts.overdue}
                </StatusTag>
                <StatusTag tone={reminderCounts.today > 0 ? "warning" : "neutral"}>
                  今日 {reminderCounts.today}
                </StatusTag>
                <StatusTag tone={reminderCounts.upcoming > 0 ? "info" : "neutral"}>
                  未来 {reminderCounts.upcoming}
                </StatusTag>
              </Space>
              <div className="customer-ai-context-note">
                {formatReminderRefreshTime(reminderRefreshedAt)}
              </div>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={reminderLoading}
                onClick={loadOverdue}
                style={{ marginTop: 8 }}
              >
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
                    <StatusTag>{overdueOnly ? tableData.length : total}</StatusTag>
                  </Space>
                ),
              },
              {
                key: "followups",
                label: (
                  <Space size={6}>
                    <PhoneOutlined />
                    <span>全局跟进</span>
                    <StatusTag tone={(globalFollowUpCounts.overdue || 0) > 0 ? "danger" : "info"}>
                      {globalFollowUpCounts.all ?? globalFollowUpTotal}
                    </StatusTag>
                  </Space>
                ),
              },
            ]}
          />
          {workbenchTab === "customers" && (
            <>
              <Card size="small" className="customer-toolbar-card" style={{ marginBottom: 12 }}>
                <CustomerFilterBar
                  q={q}
                  scene={scene}
                  industry={industry}
                  level={level}
                  region={region}
                  source={source}
                  creditLevel={creditLevel}
                  advancedOpen={advancedOpen}
                  activeAdvancedFilterCount={activeAdvancedFilterCount}
                  levelACount={levelACount}
                  alertCount={alertCount}
                  monthlyNewCount={monthlyNewCount}
                  topIndustry={topIndustry}
                  statsLoading={statsLoading}
                  activeFilterItems={activeFilterItems}
                  moreActionsContent={moreActionsContent}
                  onSearchChange={(value) => {
                    setQ(value);
                    setSmartTask("all");
                    setActiveViewPreset("all");
                    setOverdueOnly(false);
                    setPage(1);
                  }}
                  onSceneChange={(v) => {
                    setScene(v);
                    setPage(1);
                  }}
                  onToggleAdvanced={() => setAdvancedOpen((open) => !open)}
                  onResetFilters={resetFilters}
                  onIndustryChange={(v) => {
                    setIndustry(v);
                    setPage(1);
                  }}
                  onLevelChange={(v) => {
                    setLevel(v);
                    setPage(1);
                  }}
                  onRegionChange={(v) => {
                    setRegion(v);
                    setPage(1);
                  }}
                  onSourceChange={(v) => {
                    setSource(v);
                    setPage(1);
                  }}
                  onCreditLevelChange={(v) => {
                    setCreditLevel(v);
                    setPage(1);
                  }}
                  onClearFilter={(key) => {
                    const item = activeFilterItems.find((i) => i.key === key);
                    item?.clear();
                  }}
                />
              </Card>

              {selectedRowKeys.length > 0 && (
                <div className="customer-batch-bar">
                  <Space wrap>
                    <StatusTag tone="info">已选 {selectedRowKeys.length} 个客户</StatusTag>
                    <StatusTag tone="danger">A级 {selectedA}</StatusTag>
                    <StatusTag tone="warning">逾期跟进 {selectedOverdue}</StatusTag>
                    <Popconfirm
                      title={`确定删除 ${selectedRowKeys.length} 个客户?`}
                      onConfirm={handleBatchDelete}
                    >
                      <Button danger icon={<DeleteOutlined />}>
                        批量删除
                      </Button>
                    </Popconfirm>
                    <Button icon={<TagsOutlined />} onClick={() => setTagModalOpen(true)}>
                      批量打标签
                    </Button>
                    <Button onClick={() => setSelectedRowKeys([])}>清空选择</Button>
                  </Space>
                </div>
              )}

              <Card
                className="customer-table-card erp-table"
                size="small"
                title={
                  <div className="customer-table-title">
                    <Typography.Text strong>智能客户列表</Typography.Text>
                    <Typography.Text type="secondary">
                      {overdueOnly ? tableData.length : total} 条
                    </Typography.Text>
                    <StatusTag tone="info">{SMART_TASK_LABELS[activeSmartTask]}</StatusTag>
                    {activeFilterItems.length > 0 && <StatusTag tone="info">已筛选</StatusTag>}
                    {overdueOnly && <StatusTag tone="danger">仅逾期</StatusTag>}
                  </div>
                }
                extra={
                  <Space size={8}>
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={loading}
                      onClick={() => fetch()}
                    >
                      刷新列表
                    </Button>
                  </Space>
                }
              >
                {customerView === "board" ? (
                  <div className="customer-board">
                    {customerBoardColumns.map((column) => (
                      <section className="customer-board-column" key={column.stage}>
                        <div className="customer-board-column-head">
                          <div>
                            <Space size={6}>
                              <StatusTag
                                tone={getLevelColor(
                                  column.stage === "未分级" ? null : column.stage,
                                )}
                              >
                                {column.stage}
                              </StatusTag>
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
                          ) : (
                            column.customers.map((customer) => {
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
                                    if (event.key === "Enter" || event.key === " ")
                                      setContextCustomerId(customer.id);
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
                                    <StatusTag
                                      tone={
                                        priority >= 75
                                          ? "danger"
                                          : priority >= 60
                                            ? "warning"
                                            : "info"
                                      }
                                    >
                                      {priority}
                                    </StatusTag>
                                  </div>
                                  <div className="customer-board-card-meta">
                                    {[customer.industry, customer.region, customer.owner]
                                      .filter(Boolean)
                                      .join(" / ") || "暂无画像信息"}
                                  </div>
                                  <Space size={[4, 6]} wrap style={{ marginTop: 7 }}>
                                    {customer.health_score != null && (
                                      <StatusTag tone={getHealthColor(customer.health_score)}>
                                        健康 {customer.health_score}
                                      </StatusTag>
                                    )}
                                    {next && (
                                      <StatusTag tone={getReminderDueMeta(next).color}>
                                        {getReminderDueMeta(next).text}
                                      </StatusTag>
                                    )}
                                    {overdue && <StatusTag tone="danger">逾期</StatusTag>}
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
                            })
                          )}
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
                    scroll={{ x: 1600 }}
                    locale={{
                      emptyText: (
                        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无客户数据" />
                      ),
                    }}
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
              title={
                <div className="customer-table-title">
                  <Typography.Text strong>客户跟进全局集合</Typography.Text>
                  <StatusTag>总计 {globalFollowUpCounts.all ?? globalFollowUpTotal}</StatusTag>
                  <StatusTag tone="danger">逾期 {globalFollowUpCounts.overdue || 0}</StatusTag>
                  <StatusTag tone="warning">今日 {globalFollowUpCounts.today || 0}</StatusTag>
                  <StatusTag tone="info">未来 {globalFollowUpCounts.upcoming || 0}</StatusTag>
                  <StatusTag tone="success">已完成 {globalFollowUpCounts.closed || 0}</StatusTag>
                </div>
              }
              extra={
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  loading={globalFollowUpLoading}
                  onClick={() => loadGlobalFollowUps()}
                >
                  刷新集合
                </Button>
              }
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
                    label: `${item.label} ${item.key === "all" ? (globalFollowUpCounts.all ?? globalFollowUpTotal) : globalFollowUpCounts[item.key] || 0}`,
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
                locale={{
                  emptyText: (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无跟进记录" />
                  ),
                }}
                renderItem={(item) => {
                  const due = getGlobalFollowUpDueMeta(item);
                  const isClosed = item.due_bucket === "closed";
                  return (
                    <List.Item
                      actions={
                        isClosed
                          ? [
                              <Button
                                key="customer"
                                size="small"
                                type="link"
                                onClick={() => navigate(`/customers/${item.customer_id}`)}
                              >
                                查看客户
                              </Button>,
                            ]
                          : [
                              <Button
                                key="complete"
                                size="small"
                                type="link"
                                loading={reminderActionKey === `global-complete-${item.id}`}
                                onClick={() => handleCompleteGlobalFollowUp(item)}
                              >
                                完成
                              </Button>,
                              <Button
                                key="customer"
                                size="small"
                                type="link"
                                onClick={() => navigate(`/customers/${item.customer_id}`)}
                              >
                                查看客户
                              </Button>,
                            ]
                      }
                    >
                      <List.Item.Meta
                        title={
                          <Space size={6} wrap>
                            <Typography.Link
                              onClick={() => navigate(`/customers/${item.customer_id}`)}
                            >
                              {item.customer_name}
                            </Typography.Link>
                            <StatusTag tone={due.color}>{due.text}</StatusTag>
                            <FollowUpStatusTag status={item.status} />
                            <FollowUpMethodTag method={item.method} />
                            <FollowUpPriorityTag priority={item.priority} />
                            {(item.assigned_to || item.owner) && (
                              <Typography.Text type="secondary">
                                {item.assigned_to || item.owner}
                              </Typography.Text>
                            )}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={2}>
                            <Typography.Text type="secondary">
                              计划 {formatDateTime(item.planned_at)} | 创建{" "}
                              {formatDateTime(item.created_at)}
                            </Typography.Text>
                            {item.content && <Typography.Text>{item.content}</Typography.Text>}
                            {item.result && (
                              <Typography.Text type="secondary">
                                结果：{item.result}
                              </Typography.Text>
                            )}
                          </Space>
                        }
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
              {contextCustomer && (
                <StatusTag tone={getLevelColor(contextCustomer.level)}>
                  {contextCustomer.level || "-"}
                </StatusTag>
              )}
            </div>
            {!contextCustomer ? (
              <div className="customer-ai-context-body">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择客户查看AI上下文" />
              </div>
            ) : (
              <div className="customer-ai-context-body">
                <Typography.Link
                  strong
                  onClick={() => navigate(`/customers/${contextCustomer.id}`)}
                >
                  {contextCustomer.name}
                </Typography.Link>
                <div className="customer-ai-context-note">
                  {[contextCustomer.short_name, contextCustomer.industry, contextCustomer.region]
                    .filter(Boolean)
                    .join(" / ") || "暂无画像信息"}
                </div>
                <div className="customer-ai-score">
                  <div>
                    <Typography.Text type="secondary">AI优先级</Typography.Text>
                    <div className="customer-ai-context-note">按跟进、等级、健康度计算</div>
                  </div>
                  <div className="customer-ai-score-value">{contextPriorityScore}</div>
                </div>
                <Space size={[4, 6]} wrap>
                  {contextCustomer.health_score != null && (
                    <StatusTag tone={getHealthColor(contextCustomer.health_score)}>
                      健康 {contextCustomer.health_score}
                    </StatusTag>
                  )}
                  {contextNextFollowUp && (
                    <StatusTag tone={getReminderDueMeta(contextNextFollowUp).color}>
                      {getReminderDueMeta(contextNextFollowUp).text}
                    </StatusTag>
                  )}
                  {contextCustomer.owner && <StatusTag>负责人 {contextCustomer.owner}</StatusTag>}
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
                    {contextTalkTrack.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ol>
                </div>
                <Descriptions column={1} size="small" style={{ marginTop: 10 }}>
                  <Descriptions.Item label="联系人">
                    {contextCustomer.contact_person || "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label="电话">{contextCustomer.phone || "-"}</Descriptions.Item>
                  <Descriptions.Item label="最近联系">
                    {formatDate(contextCustomer.last_contacted_at)}
                  </Descriptions.Item>
                  <Descriptions.Item label="计划跟进">
                    {formatDateTime(contextNextFollowUp?.planned_at)}
                  </Descriptions.Item>
                </Descriptions>
                <div className="customer-ai-context-actions">
                  <Button
                    size="small"
                    type="primary"
                    icon={<PhoneOutlined />}
                    onClick={() => openAIPlannedFollowUp(contextCustomer, contextNextFollowUp)}
                  >
                    转跟进
                  </Button>
                  <Button
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => navigate(`/customers/${contextCustomer.id}`)}
                  >
                    详情
                  </Button>
                  <Button
                    size="small"
                    icon={<ShoppingCartOutlined />}
                    onClick={() => navigate(`/sales/orders/new?customer_id=${contextCustomer.id}`)}
                  >
                    订单
                  </Button>
                  <Button
                    size="small"
                    icon={<RobotOutlined />}
                    onClick={() => navigate(`/customers/${contextCustomer.id}/360`)}
                  >
                    AI 360
                  </Button>
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
                        <div
                          className="customer-ai-product-item"
                          key={`${item.product_name}-${item.brand}`}
                        >
                          <Space size={4} wrap>
                            <Typography.Text strong>{item.product_name}</Typography.Text>
                            {item.brand && <StatusTag>{item.brand}</StatusTag>}
                            {item.priority && (
                              <StatusTag
                                tone={
                                  item.priority === "高"
                                    ? "danger"
                                    : item.priority === "中"
                                      ? "warning"
                                      : "info"
                                }
                              >
                                {item.priority}
                              </StatusTag>
                            )}
                          </Space>
                          <div className="customer-ai-context-note">
                            {item.reason || item.estimated_potential || "-"}
                          </div>
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
                <Button
                  block
                  size="small"
                  icon={<SendOutlined />}
                  onClick={() => setSemanticOpen(true)}
                >
                  AI语义搜索
                </Button>
                <Button
                  block
                  size="small"
                  icon={<SafetyCertificateOutlined />}
                  loading={dupLoading}
                  onClick={handleDetectDups}
                >
                  重复检测
                </Button>
                <Button
                  block
                  size="small"
                  icon={<TagsOutlined />}
                  disabled={!selectedRowKeys.length}
                  onClick={() => setTagModalOpen(true)}
                >
                  批量标签
                </Button>
              </Space>
            </div>
          </div>
        </aside>
      </div>

      <CustomerReminderDrawer
        open={reminderDrawerOpen}
        loading={reminderLoading}
        bucket={reminderBucket}
        reminderCounts={reminderCounts}
        visibleReminders={visibleReminders}
        refreshedAt={reminderRefreshedAt}
        overdueOnly={overdueOnly}
        actionKey={reminderActionKey}
        onClose={() => setReminderDrawerOpen(false)}
        onReload={loadOverdue}
        onToggleOverdueOnly={() => setOverdueOnly((value) => !value)}
        onChangeBucket={setReminderBucket}
        onComplete={handleCompleteReminder}
        onPostpone={handlePostponeReminder}
      />

      <CustomerTagModal
        open={tagModalOpen}
        tags={tags}
        selectedTagIds={batchTagIds}
        createName={tagCreateName}
        createColor={tagCreateColor}
        creating={tagCreating}
        generating={tagGenerating}
        selectedRowCount={selectedRowKeys.length}
        onCancel={() => setTagModalOpen(false)}
        onOk={handleBatchTag}
        onChangeSelectedTagIds={setBatchTagIds}
        onChangeCreateName={setTagCreateName}
        onChangeCreateColor={setTagCreateColor}
        onCreate={handleCreateBatchTag}
        onGenerateDefault={handleGenerateDefaultTags}
      />

      <CustomerDuplicateListModal
        open={dupModalOpen}
        pairs={duplicatePairs}
        onClose={() => setDupModalOpen(false)}
        onMerge={openMergeModal}
      />

      <CustomerSemanticSearchModal
        open={semanticOpen}
        loading={semanticLoading}
        query={semanticQ}
        results={semanticResults}
        onClose={() => setSemanticOpen(false)}
        onChangeQuery={setSemanticQ}
        onSearch={handleSemanticSearch}
      />

      <CustomerMergeModal
        open={mergeModalOpen}
        loading={merging}
        pair={mergeSource}
        onCancel={() => {
          setMergeModalOpen(false);
          setMergeSource(null);
        }}
        onConfirm={handleMerge}
      />

      <CustomerDetailDrawer
        open={detailOpen}
        loading={detailLoading}
        customer={detailCustomer}
        stats={detailStats}
        onClose={() => setDetailOpen(false)}
        onVendAsSupplier={setVendCustomer}
      />

      <CustomerQuickFollowUpDrawer
        open={!!quickFollowUpCustomer}
        saving={quickFollowUpSaving}
        customer={quickFollowUpCustomer}
        form={quickFollowUpForm}
        onClose={() => setQuickFollowUpCustomer(null)}
        onSubmit={handleQuickFollowUpSubmit}
      />

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
