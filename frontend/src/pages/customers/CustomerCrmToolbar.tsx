// CustomerCrmToolbar — top-of-page compact bar with CRM object picker,
// view preset selector, table/board toggle, and quick-action buttons.

import { useNavigate } from "react-router-dom";
import { Button, Segmented, Select, Space, Typography } from "antd";
import { BellOutlined, RobotOutlined } from "@ant-design/icons";
import type {
  CrmObjectKey,
  CustomerViewMode,
  SceneValue,
  SmartTaskKey,
} from "./constants";
import { CRM_OBJECTS, CRM_VIEW_PRESETS } from "./constants";

interface Props {
  activeCrmObject: CrmObjectKey;
  activeViewPreset: string;
  customerView: CustomerViewMode;
  reminderTotal: number;
  onOpenCrmObject: (key: CrmObjectKey) => void;
  onApplyCrmViewPreset: (presetKey: string) => void;
  onSetCustomerView: (view: CustomerViewMode) => void;
  onOpenReminderDrawer: () => void;
}

export default function CustomerCrmToolbar({
  activeCrmObject,
  activeViewPreset,
  customerView,
  reminderTotal,
  onOpenCrmObject,
  onApplyCrmViewPreset,
  onSetCustomerView,
  onOpenReminderDrawer,
}: Props) {
  const navigate = useNavigate();
  return (
    <div className="crm-compact-bar">
      <Space size={8} wrap>
        <Typography.Text strong>CRM</Typography.Text>
        <Select
          size="small"
          style={{ width: 148 }}
          value={activeCrmObject}
          options={CRM_OBJECTS.map((object) => ({
            value: object.key,
            label: object.title,
          }))}
          onChange={(key) => onOpenCrmObject(key as CrmObjectKey)}
        />
        <Select
          size="small"
          style={{ width: 180 }}
          value={activeViewPreset}
          options={CRM_VIEW_PRESETS.map((preset) => ({
            value: preset.key,
            label: preset.description,
          }))}
          onChange={onApplyCrmViewPreset}
        />
      </Space>
      <div className="crm-compact-controls">
        <Segmented
          size="small"
          value={customerView}
          options={[
            { label: "表格", value: "table" },
            { label: "看板", value: "board" },
          ]}
          onChange={(value) => onSetCustomerView(value as CustomerViewMode)}
        />
        <Button size="small" icon={<BellOutlined />} onClick={onOpenReminderDrawer}>
          跟进 {reminderTotal}
        </Button>
        <Button size="small" icon={<RobotOutlined />} onClick={() => navigate("/customers/workbench")}>
          AI队列
        </Button>
      </div>
    </div>
  );
}

// Re-export types so consumers don't have to import them separately
export type { CrmObjectKey, CustomerViewMode, SceneValue, SmartTaskKey };
