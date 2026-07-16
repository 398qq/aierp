// CustomerDuplicateModals — pair of modals for the duplicate detection
// flow: list of suspected duplicate customer pairs, and a confirm modal
// for merging one pair.

import { Button, Card, Empty, List, Modal, Space, Typography } from "antd";
import { MergeCellsOutlined } from "@ant-design/icons";
import { StatusTag } from "../../ui";
import type { DuplicatePair } from "../../types";

interface ListModalProps {
  open: boolean;
  pairs: DuplicatePair[];
  onClose: () => void;
  onMerge: (pair: DuplicatePair) => void;
}

export function CustomerDuplicateListModal({ open, pairs, onClose, onMerge }: ListModalProps) {
  return (
    <Modal title="疑似重复客户" open={open} onCancel={onClose} footer={null} width={720}>
      {pairs.length === 0 ? (
        <Empty description="未发现疑似重复客户" />
      ) : (
        <List
          dataSource={pairs}
          renderItem={(pair) => (
            <List.Item
              actions={[
                <Button key="merge" icon={<MergeCellsOutlined />} onClick={() => onMerge(pair)}>合并</Button>,
              ]}
            >
              <List.Item.Meta
                title={(
                  <Space>
                    <Typography.Text>{pair.customer_a.name}</Typography.Text>
                    <StatusTag tone="warning">相似 {(pair.similarity * 100).toFixed(0)}%</StatusTag>
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
  );
}

interface MergeModalProps {
  open: boolean;
  loading: boolean;
  pair: DuplicatePair | null;
  onCancel: () => void;
  onConfirm: () => void;
  onSwap: () => void;
}

export function CustomerMergeModal({ open, loading, pair, onCancel, onConfirm, onSwap }: MergeModalProps) {
  return (
    <Modal
      title="合并客户"
      open={open}
      onCancel={onCancel}
      onOk={onConfirm}
      confirmLoading={loading}
      okText="确认合并"
      okButtonProps={{ danger: true }}
    >
      {pair && (
        <div>
          <p>确认将以下客户合并？</p>
          <Card size="small" style={{ marginBottom: 12, backgroundColor: "#fff2f0" }}>
            <Typography.Text strong delete>源客户: {pair.customer_a.name}</Typography.Text>
            <div style={{ fontSize: 12, color: "#888" }}>
              电话: {pair.customer_a.phone || "无"} | 负责人: {pair.customer_a.owner || "无"}
            </div>
          </Card>
          <Card size="small" style={{ backgroundColor: "#f6ffed" }}>
            <Typography.Text strong>目标客户: {pair.customer_b.name}</Typography.Text>
            <div style={{ fontSize: 12, color: "#888" }}>
              电话: {pair.customer_b.phone || "无"} | 负责人: {pair.customer_b.owner || "无"}
            </div>
          </Card>
          <Button style={{ marginTop: 12 }} onClick={onSwap} disabled={loading}>
            交换保留对象
          </Button>
          <p style={{ marginTop: 12, color: "#ff4d4f" }}>
            合并后，源客户的联系人、跟进记录、标签、附件和订单将转移到目标客户，源客户将被删除。
          </p>
        </div>
      )}
    </Modal>
  );
}
