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
      <div className="product-health-main">
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

      <div className="product-health-metric" onClick={onResetFilters}>
        <span className="product-health-icon is-primary">
          <AppstoreOutlined />
        </span>
        <span className="product-health-label">SKU 总数</span>
        <span className="product-health-value">{(stats.total ?? 0).toLocaleString()}</span>
        <div className="product-health-sub">
          在库率 <strong>{metrics.inStockRate}%</strong>
        </div>
      </div>
      <div
        className="product-health-metric is-warning"
        onClick={() => onTaskClick("replenish", "low_stock")}
      >
        <span className="product-health-icon is-warning">
          <ExclamationCircleOutlined />
        </span>
        <span className="product-health-label">低库存</span>
        <span className="product-health-value">
          {(stats.low_stock_count ?? 0).toLocaleString()}
        </span>
        <div className="product-health-sub">
          占全部 SKU <strong>{metrics.lowStockRate}%</strong>
        </div>
      </div>
      <div
        className="product-health-metric is-danger"
        onClick={() => onTaskClick("out", "out_of_stock")}
      >
        <span className="product-health-icon is-danger">
          <StopOutlined />
        </span>
        <span className="product-health-label">缺货</span>
        <span className="product-health-value">
          {(stats.out_of_stock_count ?? 0).toLocaleString()}
        </span>
        <div className="product-health-sub">
          占全部 SKU <strong>{metrics.outOfStockRate}%</strong>
        </div>
      </div>
      <div
        className="product-health-metric is-info"
        onClick={() => onTaskClick("complete", "pending_completion")}
      >
        <span className="product-health-icon is-info">
          <FileTextOutlined />
        </span>
        <span className="product-health-label">资料待完善</span>
        <span className="product-health-value">
          {(stats.pending_completion_count ?? 0).toLocaleString()}
        </span>
        <div className="product-health-sub">
          资料缺口率 <strong>{metrics.completionGapRate}%</strong>
        </div>
      </div>
    </div>
  );
}
