import {
  AimOutlined,
  BellOutlined,
  CarOutlined,
  DashboardOutlined,
  DollarOutlined,
  FileDoneOutlined,
  FileTextOutlined,
  HeartOutlined,
  IssuesCloseOutlined,
  PieChartOutlined,
  ProfileOutlined,
  RobotOutlined,
  SettingOutlined,
  ShopOutlined,
  ShoppingCartOutlined,
  StockOutlined,
  SwapOutlined,
  TagOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  UploadOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import type { MenuDataItem } from "@ant-design/pro-components";

export const navigationMenuItems: MenuDataItem[] = [
  {
    key: "_domain_overview",
    icon: <DashboardOutlined />,
    name: "经营总览",
    children: [
      { key: "/", icon: <DashboardOutlined />, name: "经营总览" },
      { key: "/dashboard/global360", icon: <PieChartOutlined />, name: "全局360" },
      { key: "/dashboard/watchtower", icon: <WarningOutlined />, name: "全局监控" },
    ],
  },
  {
    key: "_domain_sales",
    icon: <ThunderboltOutlined />,
    name: "客户与销售",
    children: [
      { key: "/customers/stats", icon: <DashboardOutlined />, name: "客户工作台" },
      { key: "/customers", icon: <TeamOutlined />, name: "客户台账" },
      { key: "/customers/follow-ups", icon: <FileTextOutlined />, name: "跟进任务" },
      { key: "/customers/release-rules", icon: <WarningOutlined />, name: "释放规则" },
      {
        key: "/customers/assignment-rules",
        icon: <ThunderboltOutlined />,
        name: "自动分配规则",
      },
      {
        key: "/customers/transfer-requests",
        icon: <SwapOutlined />,
        name: "转移审批",
      },
      { key: "/sales/dashboard", icon: <DashboardOutlined />, name: "销售工作台" },
      { key: "/sales/inquiry", icon: <RobotOutlined />, name: "询价回复" },
      { key: "/sales/opportunities", icon: <ThunderboltOutlined />, name: "商机管理" },
      { key: "/sales/quotations", icon: <FileTextOutlined />, name: "报价管理" },
      { key: "/sales/orders", icon: <ShoppingCartOutlined />, name: "销售订单" },
      { key: "/sales/contracts", icon: <ProfileOutlined />, name: "合同管理" },
      { key: "/sales/delivery-notes", icon: <CarOutlined />, name: "发货管理" },
      { key: "/sales/invoices", icon: <FileDoneOutlined />, name: "发票管理" },
      { key: "/sales/payments", icon: <DollarOutlined />, name: "回款管理" },
      { key: "/sales/targets", icon: <AimOutlined />, name: "销售目标" },
    ],
  },
  {
    key: "_domain_procurement",
    icon: <ShoppingCartOutlined />,
    name: "采购与供应链",
    children: [
      {
        key: "/procurement/dashboard",
        icon: <DashboardOutlined />,
        name: "采购工作台",
      },
      {
        key: "/sales/purchase-orders",
        icon: <ShoppingCartOutlined />,
        name: "采购订单",
      },
      { key: "/suppliers/stats", icon: <DashboardOutlined />, name: "供应商总览" },
      { key: "/suppliers", icon: <TeamOutlined />, name: "供应商台账" },
      { key: "/suppliers/compare", icon: <SwapOutlined />, name: "供应商对比" },
    ],
  },
  {
    key: "_domain_inventory",
    icon: <StockOutlined />,
    name: "产品与库存",
    children: [
      { key: "/products", icon: <ShopOutlined />, name: "产品台账" },
      { key: "/products/price-import", icon: <UploadOutlined />, name: "价格导入" },
      { key: "/brands", icon: <TagOutlined />, name: "品牌管理" },
      { key: "/inventory", icon: <StockOutlined />, name: "库存总览" },
      { key: "/warehouse/warehouses", icon: <ShopOutlined />, name: "仓库管理" },
      {
        key: "/warehouse/inventory-ledger",
        icon: <FileTextOutlined />,
        name: "库存台账",
      },
      {
        key: "/warehouse/inventory-batches",
        icon: <FileTextOutlined />,
        name: "批次与 COGS",
      },
    ],
  },
  {
    key: "_domain_finance",
    icon: <DollarOutlined />,
    name: "财务管理",
    children: [
      { key: "/finance/accounts", icon: <FileTextOutlined />, name: "会计科目" },
      {
        key: "/finance/journal-entries",
        icon: <ProfileOutlined />,
        name: "记账凭证",
      },
      { key: "/finance/pnl", icon: <PieChartOutlined />, name: "损益表" },
      { key: "/reports/ar", icon: <DollarOutlined />, name: "应收账款" },
      { key: "/reports/ap", icon: <DollarOutlined />, name: "应付账款" },
      { key: "/finance/commissions", icon: <TrophyOutlined />, name: "佣金管理" },
      {
        key: "/finance/commission-schemes",
        icon: <SettingOutlined />,
        name: "提成方案",
      },
    ],
  },
  {
    key: "_domain_analytics",
    icon: <PieChartOutlined />,
    name: "报表与分析",
    children: [
      { key: "/reports/sales", icon: <PieChartOutlined />, name: "销售报表" },
      { key: "/reports/inventory", icon: <StockOutlined />, name: "库存报表" },
      {
        key: "/reports/procurement",
        icon: <ShoppingCartOutlined />,
        name: "采购报表",
      },
      { key: "/customers/intelligence", icon: <HeartOutlined />, name: "客户分析" },
    ],
  },
  {
    key: "_domain_collaboration",
    icon: <IssuesCloseOutlined />,
    name: "协作与审批",
    children: [
      { key: "/system/approvals", icon: <FileDoneOutlined />, name: "审批管理" },
      { key: "/system/approval-rules", icon: <ProfileOutlined />, name: "审批规则" },
      { key: "/tickets", icon: <IssuesCloseOutlined />, name: "工单管理" },
      { key: "/notifications", icon: <BellOutlined />, name: "通知中心" },
      { key: "/ai/chat", icon: <RobotOutlined />, name: "AI 助手" },
    ],
  },
  {
    key: "_domain_system",
    icon: <SettingOutlined />,
    name: "系统治理",
    children: [
      { key: "/system/users", icon: <TeamOutlined />, name: "用户管理" },
      { key: "/system/roles", icon: <TeamOutlined />, name: "角色权限" },
      { key: "/system/uoms", icon: <ShopOutlined />, name: "计量单位" },
      { key: "/system/audit-logs", icon: <FileTextOutlined />, name: "审计日志" },
      { key: "/data/import-export", icon: <SwapOutlined />, name: "导入与导出" },
      { key: "/settings", icon: <SettingOutlined />, name: "系统设置" },
    ],
  },
];

export interface SearchableNavigationItem {
  key: string;
  name: string;
}

function flattenNavigationItems(items: MenuDataItem[]): SearchableNavigationItem[] {
  return items.flatMap((item) => {
    const current =
      typeof item.key === "string" && item.key.startsWith("/")
        ? [{ key: item.key, name: String(item.name) }]
        : [];
    return [...current, ...flattenNavigationItems(item.children ?? [])];
  });
}

export const searchableNavigationItems = flattenNavigationItems(navigationMenuItems);

export function resolveSelectedNavigationKey(pathname: string) {
  return (
    searchableNavigationItems
      .map((item) => item.key)
      .filter((key) => pathname === key || pathname.startsWith(`${key}/`))
      .sort((left, right) => right.length - left.length)[0] ?? pathname
  );
}

export function findNavigationTarget(query: string) {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return undefined;
  }

  return searchableNavigationItems.find(
    (item) =>
      item.name.toLowerCase().includes(normalizedQuery) ||
      item.key.toLowerCase().includes(normalizedQuery),
  )?.key;
}

export function getMenuItemTarget(item: MenuDataItem) {
  return typeof item.key === "string" && item.key.startsWith("/") ? item.key : undefined;
}
