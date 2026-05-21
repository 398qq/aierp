import type { Brand } from "../../types";

export type BrandAiPriority = "high" | "medium" | "low";

export interface BrandAiTask {
  key: string;
  title: string;
  reason: string;
  priority: BrandAiPriority;
  actionLabel: string;
  statusText: string;
}

export interface BrandOperationTask {
  key: string;
  label: string;
  count: number;
  color: string;
  path: string;
  reason: string;
}

export interface BrandStatsLike {
  total: number;
  recent_30d: number;
  eol_nrnd_count: number;
  automotive_count: number;
  high_risk_count: number;
  pending_completion_count?: number;
  no_product_count?: number;
}

export interface BrandAction {
  label: string;
  color: string;
  priority: BrandAiPriority;
}

const hasProducts = (brand: Brand) => Boolean(brand.has_products ?? ((brand.product_count ?? 0) > 0));
const completion = (brand: Brand) => brand.completion_score ?? 0;
const riskScore = (brand: Brand) => brand.risk_score ?? 0;
const isLifecycleRisk = (brand: Brand) => brand.lifecycle_stage === "eol" || brand.lifecycle_stage === "nrnd";
const isHighRisk = (brand: Brand) => brand.risk_level === "high" || brand.risk_level === "critical" || riskScore(brand) >= 70;

export const getBrandNextAction = (brand: Brand): BrandAction => {
  if (!hasProducts(brand)) return { label: "补产品", color: "orange", priority: "high" };
  if (completion(brand) < 70) return { label: "补资料", color: "gold", priority: "medium" };
  if (isLifecycleRisk(brand)) return { label: "替代评估", color: "red", priority: "high" };
  if (brand.authorization_status === "unauthorized") return { label: "授权核验", color: "volcano", priority: "high" };
  if (isHighRisk(brand)) return { label: "风险复核", color: "red", priority: "high" };
  return { label: "正常维护", color: "green", priority: "low" };
};

export const getBrandAiTasks = (brand: Brand): BrandAiTask[] => {
  const tasks: BrandAiTask[] = [];
  const missingCount = brand.missing_fields?.length ?? 0;

  if (completion(brand) < 80 || missingCount > 0) {
    tasks.push({
      key: "auto_complete",
      title: "AI 资料补全",
      reason: missingCount > 0 ? `仍缺 ${missingCount} 个字段，建议先补齐主数据。` : "资料完整度偏低，建议自动识别可补字段。",
      priority: completion(brand) < 60 ? "high" : "medium",
      actionLabel: "补全资料",
      statusText: `${Math.round(completion(brand))}% 完整`,
    });
  }

  if (isHighRisk(brand)) {
    tasks.push({
      key: "risk",
      title: "风险评估",
      reason: `风险评分 ${Math.round(riskScore(brand))}，需要复核供应、生命周期和集中度风险。`,
      priority: "high",
      actionLabel: "评估风险",
      statusText: "高风险",
    });
  }

  if (isLifecycleRisk(brand)) {
    tasks.push({
      key: "lifecycle",
      title: "生命周期预测",
      reason: `${brand.lifecycle_stage?.toUpperCase()} 品牌需要判断替代、库存和客户影响。`,
      priority: "high",
      actionLabel: "预测周期",
      statusText: brand.lifecycle_stage?.toUpperCase() || "生命周期风险",
    });
    tasks.push({
      key: "recommendations",
      title: "替代品牌推荐",
      reason: "生命周期异常时应优先建立替代品牌和客户迁移方案。",
      priority: "high",
      actionLabel: "生成推荐",
      statusText: "替代评估",
    });
  }

  if (brand.authorization_status === "unauthorized") {
    tasks.push({
      key: "supplier",
      title: "供应商矩阵",
      reason: "当前未授权，建议核验渠道覆盖和价格稳定性。",
      priority: "high",
      actionLabel: "分析供应",
      statusText: "未授权",
    });
  }

  if (!hasProducts(brand)) {
    tasks.push({
      key: "portfolio",
      title: "产品线分析",
      reason: "当前未铺货，需要识别优先引入的产品线。",
      priority: "high",
      actionLabel: "分析产品线",
      statusText: "未铺货",
    });
  }

  tasks.push(
    {
      key: "profile",
      title: "品牌画像",
      reason: "沉淀市场定位、技术优势、应用场景和采购建议。",
      priority: "medium",
      actionLabel: "生成画像",
      statusText: "基础画像",
    },
    {
      key: "performance",
      title: "产品绩效",
      reason: "查看销售、库存和利润表现，辅助品牌分层维护。",
      priority: "medium",
      actionLabel: "分析绩效",
      statusText: "经营分析",
    },
    {
      key: "penetration",
      title: "客户渗透",
      reason: "识别客户覆盖、复购机会和交叉销售空间。",
      priority: "low",
      actionLabel: "分析客户",
      statusText: "增长机会",
    },
  );

  return tasks.sort((a, b) => {
    const score: Record<BrandAiPriority, number> = { high: 3, medium: 2, low: 1 };
    return score[b.priority] - score[a.priority];
  });
};

export const getBrandOperationTasks = (stats: BrandStatsLike, eolAlertCount = 0): BrandOperationTask[] => [
  {
    key: "high_risk",
    label: "高风险复核",
    count: stats.high_risk_count,
    color: "red",
    path: "/brands?scene=high_risk",
    reason: "优先复核风险评分超过阈值的品牌。",
  },
  {
    key: "eol",
    label: "生命周期处理",
    count: stats.eol_nrnd_count,
    color: "orange",
    path: "/brands?scene=eol_nrnd",
    reason: "处理 EOL/NRND 品牌的替代、库存和客户影响。",
  },
  {
    key: "missing",
    label: "资料补全",
    count: stats.pending_completion_count ?? 0,
    color: "gold",
    path: "/brands?scene=pending_completion",
    reason: "补齐官网、产品线、授权、风险等主数据字段。",
  },
  {
    key: "no_products",
    label: "铺货规划",
    count: stats.no_product_count ?? 0,
    color: "blue",
    path: "/brands?scene=no_products",
    reason: "为无产品覆盖品牌建立产品线引入计划。",
  },
  {
    key: "alerts",
    label: "EOL 预警跟进",
    count: eolAlertCount,
    color: "volcano",
    path: "/brands?scene=eol_nrnd",
    reason: "跟进 AI 识别的生命周期预警。",
  },
];

export const getBatchAiSummary = (brands: Brand[]) => {
  const summary = {
    total: brands.length,
    highRisk: 0,
    lifecycleRisk: 0,
    missingData: 0,
    noProducts: 0,
    unauthorized: 0,
  };

  brands.forEach((brand) => {
    if (isHighRisk(brand)) summary.highRisk += 1;
    if (isLifecycleRisk(brand)) summary.lifecycleRisk += 1;
    if (completion(brand) < 70) summary.missingData += 1;
    if (!hasProducts(brand)) summary.noProducts += 1;
    if (brand.authorization_status === "unauthorized") summary.unauthorized += 1;
  });

  return summary;
};
