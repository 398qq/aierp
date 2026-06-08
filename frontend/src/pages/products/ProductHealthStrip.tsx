// ProductHealthStrip — top-of-page 5-up metric strip showing total SKUs,
// low stock, out of stock, and pending-completion counts. Clicking a
// metric card sets the appropriate filter / task.

import { Button } from "antd";
import {
  FileTextOutlined,
  InboxOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { ProductStats, ProductTaskKey, SceneValue } from "./constants";

interface HealthMetrics {
  inStockRate: number;
  lowStockRate: number;
  outOfStockRate: number;
  completionGapRate: number;
}

interface Props {
  stats: ProductStats;
  statsLoading: boolean;
  metrics: HealthMetrics;
  onCreate: () => void;
  onImport: () => void;
  onOpenAiParse: () => void;
  onOpenBomImport: () => void;
  onResetFilters: () => void;
  onTaskClick: (task: ProductTaskKey, scene: SceneValue) => void;
}

export default function ProductHealthStrip({
  stats,
  statsLoading,
  metrics,
  onCreate,
  onImport,
  onOpenAiParse,
  onOpenBomImport,
  onResetFilters,
  onTaskClick,
}: Props) {
  return (
    <div className="product-health-strip">
      <div className="product-health-main">
        <div>
          <div className="product-health-title">
            <InboxOutlined />
            <span>产品管理工作台</span>
            {statsLoading && <StatusTag>刷新中</StatusTag>}
          </div>
          <div className="product-health-note">
            统一处理产品主数据、库存、供应商、价格和 AI 选型动作，优先消除缺货、低库存与资料缺口。
          </div>
        </div>
        <div className="product-health-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>新建产品</Button>
          <Button icon={<UploadOutlined />} onClick={onImport}>批量导入</Button>
          <Button icon={<ThunderboltOutlined />} onClick={onOpenAiParse}>AI 解析</Button>
          <Button icon={<FileTextOutlined />} onClick={onOpenBomImport}>BOM 导入</Button>
        </div>
      </div>
      <div className="product-health-metric" onClick={onResetFilters}>
        <span className="product-health-label">SKU 总数</span>
        <span className="product-health-value">{stats.total}<small>个</small></span>
        <div className="product-health-sub">在库率 {metrics.inStockRate}%</div>
      </div>
      <div
        className="product-health-metric"
        onClick={() => onTaskClick("replenish", "low_stock")}
      >
        <span className="product-health-label">低库存</span>
        <span className="product-health-value">{stats.low_stock_count}<small>个</small></span>
        <div className="product-health-sub">占比 {metrics.lowStockRate}%</div>
      </div>
      <div
        className="product-health-metric"
        onClick={() => onTaskClick("out", "out_of_stock")}
      >
        <span className="product-health-label">缺货</span>
        <span className="product-health-value">{stats.out_of_stock_count}<small>个</small></span>
        <div className="product-health-sub">占比 {metrics.outOfStockRate}%</div>
      </div>
      <div
        className="product-health-metric"
        onClick={() => onTaskClick("complete", "pending_completion")}
      >
        <span className="product-health-label">待完善</span>
        <span className="product-health-value">{stats.pending_completion_count}<small>个</small></span>
        <div className="product-health-sub">缺口率 {metrics.completionGapRate}%</div>
      </div>
    </div>
  );
}
