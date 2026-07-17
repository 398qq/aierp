import { Button } from "antd";
import {
  AppstoreOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  InboxOutlined,
  PlusOutlined,
  StopOutlined,
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
      <div className="product-health-toolbar">
        <div className="product-health-title">
          <InboxOutlined />
          <div>
            <span>产品主数据台账</span>
            <small>统一维护产品标识、库存控制、价格成本与供应关系</small>
          </div>
          {statsLoading && <StatusTag>刷新中</StatusTag>}
        </div>
        <div className="product-health-actions">
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>
            新建产品
          </Button>
          <Button icon={<UploadOutlined />} onClick={onImport}>
            批量导入
          </Button>
          <Button icon={<ThunderboltOutlined />} onClick={onOpenAiParse}>
            AI 解析
          </Button>
          <Button icon={<FileTextOutlined />} onClick={onOpenBomImport}>
            BOM 导入
          </Button>
        </div>
      </div>
      <div className="product-health-kpis">
        <button type="button" className="product-health-metric" onClick={onResetFilters}>
          <span className="product-health-icon is-primary"><AppstoreOutlined /></span>
          <span className="product-health-copy"><span className="product-health-label">SKU 总数</span><small>在库率 {metrics.inStockRate}%</small></span>
          <strong className="product-health-value">{(stats.total ?? 0).toLocaleString()}</strong>
        </button>
        <button type="button" className="product-health-metric is-success" onClick={() => onTaskClick("all", "in_stock")}>
          <span className="product-health-icon is-success"><InboxOutlined /></span>
          <span className="product-health-copy"><span className="product-health-label">正常在库</span><small>可正常销售</small></span>
          <strong className="product-health-value">{(stats.in_stock_count ?? 0).toLocaleString()}</strong>
        </button>
        <button type="button" className="product-health-metric is-warning" onClick={() => onTaskClick("replenish", "low_stock")}>
          <span className="product-health-icon is-warning"><ExclamationCircleOutlined /></span>
          <span className="product-health-copy"><span className="product-health-label">低库存</span><small>占比 {metrics.lowStockRate}%</small></span>
          <strong className="product-health-value">{(stats.low_stock_count ?? 0).toLocaleString()}</strong>
        </button>
        <button type="button" className="product-health-metric is-danger" onClick={() => onTaskClick("out", "out_of_stock")}>
          <span className="product-health-icon is-danger"><StopOutlined /></span>
          <span className="product-health-copy"><span className="product-health-label">缺货</span><small>占比 {metrics.outOfStockRate}%</small></span>
          <strong className="product-health-value">{(stats.out_of_stock_count ?? 0).toLocaleString()}</strong>
        </button>
        <button type="button" className="product-health-metric is-info" onClick={() => onTaskClick("complete", "pending_completion")}>
          <span className="product-health-icon is-info"><FileTextOutlined /></span>
          <span className="product-health-copy"><span className="product-health-label">待完善</span><small>缺口率 {metrics.completionGapRate}%</small></span>
          <strong className="product-health-value">{(stats.pending_completion_count ?? 0).toLocaleString()}</strong>
        </button>
      </div>
    </div>
  );
}
