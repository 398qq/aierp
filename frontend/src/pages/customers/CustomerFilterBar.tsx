// CustomerFilterBar — toolbar card with search, scene segmented control,
// advanced filters, summary strip, and active-filter chips.

import { Card, Col, Input, Row, Segmented, Select, Space, Typography, Button, Popover } from "antd";
import {
  DownOutlined,
  FilterOutlined,
  MoreOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { StatusTag } from "../../ui";
import {
  CREDIT_LEVELS,
  INDUSTRIES,
  LEVELS,
  REGIONS,
  SCENE_OPTIONS,
  SceneValue,
  SOURCES,
} from "./constants";

interface Props {
  q: string;
  scene: SceneValue;
  industry?: string;
  level?: string;
  region?: string;
  source?: string;
  creditLevel?: string;
  advancedOpen: boolean;
  activeAdvancedFilterCount: number;
  levelACount: number;
  alertCount: number;
  monthlyNewCount: number;
  topIndustry?: { name: string; value: number } | undefined;
  statsLoading: boolean;
  activeFilterItems: { key: string; label: string; clear: () => void }[];
  moreActionsContent: React.ReactNode;
  onSearchChange: (q: string) => void;
  onSceneChange: (scene: SceneValue) => void;
  onToggleAdvanced: () => void;
  onResetFilters: () => void;
  onIndustryChange: (v?: string) => void;
  onLevelChange: (v?: string) => void;
  onRegionChange: (v?: string) => void;
  onSourceChange: (v?: string) => void;
  onCreditLevelChange: (v?: string) => void;
  onClearFilter: (key: string) => void;
}

export default function CustomerFilterBar({
  q,
  scene,
  industry,
  level,
  region,
  source,
  creditLevel,
  advancedOpen,
  activeAdvancedFilterCount,
  levelACount,
  alertCount,
  monthlyNewCount,
  topIndustry,
  statsLoading,
  activeFilterItems,
  moreActionsContent,
  onSearchChange,
  onSceneChange,
  onToggleAdvanced,
  onResetFilters,
  onIndustryChange,
  onLevelChange,
  onRegionChange,
  onSourceChange,
  onCreditLevelChange,
  onClearFilter,
}: Props) {
  return (
    <Card size="small" className="customer-toolbar-card" style={{ marginBottom: 12 }}>
      <div className="customer-toolbar-main">
        <div>
          <Input
            placeholder="搜索客户名称/编码/联系人/电话"
            prefix={<SearchOutlined />}
            value={q}
            onChange={(e) => onSearchChange(e.target.value)}
            allowClear
          />
        </div>
        <div>
          <Segmented
            style={{ maxWidth: "100%" }}
            options={SCENE_OPTIONS}
            value={scene}
            onChange={(v) => onSceneChange(v as SceneValue)}
          />
        </div>
        <div>
          <Space wrap className="customer-toolbar-actions" style={{ width: "100%", justifyContent: "flex-end" }}>
            <Button
              icon={<FilterOutlined />}
              type={activeAdvancedFilterCount > 0 ? "primary" : "default"}
              onClick={onToggleAdvanced}
            >
              高级筛选{activeAdvancedFilterCount > 0 ? `(${activeAdvancedFilterCount})` : ""}
              <DownOutlined />
            </Button>
            <Button icon={<ReloadOutlined />} onClick={onResetFilters}>重置</Button>
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
              allowClear placeholder="行业" style={{ width: "100%" }}
              value={industry}
              options={INDUSTRIES.map((v) => ({ value: v, label: v }))}
              onChange={onIndustryChange}
            />
          </Col>
          <Col xs={12} md={6} xl={4}>
            <Select
              allowClear placeholder="等级" style={{ width: "100%" }}
              value={level}
              options={LEVELS.map((v) => ({ value: v, label: v }))}
              onChange={onLevelChange}
            />
          </Col>
          <Col xs={12} md={6} xl={4}>
            <Select
              allowClear placeholder="区域" style={{ width: "100%" }}
              value={region}
              options={REGIONS.map((v) => ({ value: v, label: v }))}
              onChange={onRegionChange}
            />
          </Col>
          <Col xs={12} md={6} xl={4}>
            <Select
              allowClear placeholder="来源" style={{ width: "100%" }}
              value={source}
              options={SOURCES.map((v) => ({ value: v, label: v }))}
              onChange={onSourceChange}
            />
          </Col>
          <Col xs={12} md={6} xl={4}>
            <Select
              allowClear placeholder="信用等级" style={{ width: "100%" }}
              value={creditLevel}
              options={CREDIT_LEVELS.map((v) => ({ value: v, label: v }))}
              onChange={onCreditLevelChange}
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
              <StatusTag
                key={item.key}
                closable
                onClose={(event) => {
                  event.preventDefault();
                  onClearFilter(item.key);
                }}
              >
                {item.label}
              </StatusTag>
            ))}
            <Button size="small" type="link" onClick={onResetFilters}>清除</Button>
          </div>
        )}
      </div>
    </Card>
  );
}
