// CustomerTagModal — modal for batch-applying tags to selected customers
// and creating new tags inline.

import { Button, Divider, Input, Modal, Select, Space, Typography } from "antd";
import { TagsOutlined } from "@ant-design/icons";
import { TAG_COLOR_OPTIONS } from "./constants";
import type { Tag as TagType } from "../../types";

interface Props {
  open: boolean;
  tags: TagType[];
  selectedTagIds: number[];
  createName: string;
  createColor: string;
  creating: boolean;
  generating: boolean;
  selectedRowCount: number;
  onCancel: () => void;
  onOk: () => void;
  onChangeSelectedTagIds: (ids: number[]) => void;
  onChangeCreateName: (name: string) => void;
  onChangeCreateColor: (color: string) => void;
  onCreate: () => void;
  onGenerateDefault: () => void;
}

export default function CustomerTagModal({
  open,
  tags,
  selectedTagIds,
  createName,
  createColor,
  creating,
  generating,
  selectedRowCount,
  onCancel,
  onOk,
  onChangeSelectedTagIds,
  onChangeCreateName,
  onChangeCreateColor,
  onCreate,
  onGenerateDefault,
}: Props) {
  return (
    <Modal
      title="添加标签"
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      okText="添加到已选客户"
      okButtonProps={{ disabled: !selectedTagIds.length || !selectedRowCount }}
    >
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Space style={{ width: "100%", justifyContent: "space-between" }}>
          <Typography.Text type="secondary">可用标签</Typography.Text>
          <Button size="small" icon={<TagsOutlined />} loading={generating} onClick={onGenerateDefault}>
            生成5个默认标签
          </Button>
        </Space>
        <Select
          mode="multiple"
          style={{ width: "100%" }}
          placeholder="选择要添加的标签"
          value={selectedTagIds}
          onChange={onChangeSelectedTagIds}
          options={tags.map((t) => ({ value: t.id, label: t.name }))}
        />
        <Divider style={{ margin: 0 }} />
        <Typography.Text type="secondary">新建标签</Typography.Text>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            placeholder="标签名称"
            value={createName}
            onChange={(e) => onChangeCreateName(e.target.value)}
            onPressEnter={onCreate}
          />
          <Select
            style={{ width: 110 }}
            value={createColor}
            options={TAG_COLOR_OPTIONS}
            onChange={onChangeCreateColor}
          />
          <Button loading={creating} onClick={onCreate}>创建</Button>
        </Space.Compact>
      </Space>
    </Modal>
  );
}
