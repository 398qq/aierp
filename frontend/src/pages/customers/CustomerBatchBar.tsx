/**
 * CustomerBatchBar — 批量操作浮动工具栏
 *
 * 选中行后出现，提供：批量打标签、批量删除、批量导出、批量状态变更
 * 权限：仅主管（batch 操作）+ 管理员可见
 */

import React, { useCallback, useState } from "react";
import { Button, message, Modal, Select, Space, Tag } from "antd";
import {
  DeleteOutlined,
  ExportOutlined,
  PushpinOutlined,
  TagsOutlined,
  UserSwitchOutlined,
  UsergroupAddOutlined,
} from "@ant-design/icons";
import {
  assignCustomers,
  batchDeleteCustomers,
  batchSetOwner,
  batchTagCustomers,
  exportCustomers,
  getActiveUsers,
  getApiErrorMessage,
  getTags,
} from "@/api";

// ── 类型 ──

interface CustomerBatchBarProps {
  selectedIds: number[];
  selectedCount: number;
  onClear: () => void;
  onBatchComplete: () => void;
}

// ── 组件 ──

export const CustomerBatchBar: React.FC<CustomerBatchBarProps> = ({
  selectedIds,
  selectedCount,
  onClear,
  onBatchComplete,
}) => {
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [tagging, setTagging] = useState(false);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [tagOptions, setTagOptions] = useState<Array<{ value: number; label: string }>>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignTarget, setAssignTarget] = useState<string | null>(null);
  const [userOptions, setUserOptions] = useState<Array<{ value: string; label: string }>>([]);

  // ── 批量删除 ──
  const handleBatchDelete = useCallback(() => {
    Modal.confirm({
      title: `确认删除 ${selectedCount} 个客户？`,
      content: "此操作为软删除，客户将不再出现在正常列表中。",
      okText: "确认删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        setDeleting(true);
        try {
          await batchDeleteCustomers(selectedIds);
          message.success(`已删除 ${selectedCount} 个客户`);
          onBatchComplete();
          onClear();
        } catch (e: unknown) {
          message.error(getApiErrorMessage(e, "批量删除失败"));
        } finally {
          setDeleting(false);
        }
      },
    });
  }, [selectedIds, selectedCount, onBatchComplete, onClear]);

  // ── 批量导出 ──
  const handleBatchExport = useCallback(async () => {
    setExporting(true);
    try {
      const res = await exportCustomers({ ids: selectedIds.join(",") });
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `customers_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${selectedCount} 个客户`);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "导出失败"));
    } finally {
      setExporting(false);
    }
  }, [selectedIds, selectedCount]);

  // ── 批量打标签 ──
  const handleBatchTag = useCallback(async () => {
    try {
      const res = await getTags();
      const tags = (res.data?.data || res.data) as
        | Array<{ id: number; name: string; color?: string }>
        | { list: Array<{ id: number; name: string }> };
      const tagList = Array.isArray(tags)
        ? tags
        : (tags as { list: Array<{ id: number; name: string }> }).list || [];
      setTagOptions(tagList.map((t) => ({ value: t.id, label: t.name })));
      setSelectedTagIds([]);
      setTagModalOpen(true);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载标签失败"));
    }
  }, [selectedCount]);

  const handleBatchTagSubmit = useCallback(async () => {
    if (!selectedTagIds.length) {
      message.warning("请选择至少一个标签");
      return;
    }
    setTagging(true);
    try {
      await batchTagCustomers(selectedIds, selectedTagIds);
      message.success(`已为 ${selectedCount} 个客户添加标签`);
      setTagModalOpen(false);
      setSelectedTagIds([]);
      onBatchComplete();
      onClear();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量打标签失败"));
    } finally {
      setTagging(false);
    }
  }, [selectedIds, selectedTagIds, selectedCount, onBatchComplete, onClear]);

  // ── 批量分配 ──
  const handleBatchAssign = useCallback(async () => {
    try {
      const res = await getActiveUsers();
      const users = (res.data?.data || res.data) as
        | Array<{ username: string; role: string }>
        | { list: Array<{ username: string; role: string }> };
      const userList = Array.isArray(users)
        ? users
        : (users as { list: Array<{ username: string; role: string }> }).list || [];
      setUserOptions(userList.map((u) => ({ value: u.username, label: `${u.username} (${u.role || "销售"})` })));
      setAssignTarget(null);
      setAssignModalOpen(true);
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "加载用户列表失败"));
    }
  }, []);

  const handleBatchAssignSubmit = useCallback(async () => {
    if (!assignTarget) {
      message.warning("请选择目标负责人");
      return;
    }
    setAssigning(true);
    try {
      await assignCustomers(selectedIds, assignTarget);
      message.success(`已分配 ${selectedCount} 个客户给 ${assignTarget}`);
      setAssignModalOpen(false);
      setAssignTarget(null);
      onBatchComplete();
      onClear();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "批量分配失败"));
    } finally {
      setAssigning(false);
    }
  }, [selectedIds, assignTarget, selectedCount, onBatchComplete, onClear]);

  if (selectedCount === 0) return null;

  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "8px 16px",
          background: "#e6f4ff",
          border: "1px solid #91caff",
          borderRadius: 6,
          margin: "0 16px 8px",
        }}
      >
        <Tag color="blue" style={{ marginRight: 12 }}>
          已选 {selectedCount} 项
        </Tag>
        <Space>
          <Button size="small" icon={<TagsOutlined />} onClick={handleBatchTag}>
            批量打标签
          </Button>
          <Button
            size="small"
            icon={<ExportOutlined />}
            loading={exporting}
            onClick={handleBatchExport}
          >
            导出
          </Button>
          <Button
            size="small"
            icon={<PushpinOutlined />}
            onClick={async () => {
              try {
                await batchSetOwner(selectedIds, "claim");
                message.success(`已认领 ${selectedCount} 个客户`);
                onBatchComplete();
                onClear();
              } catch (e: unknown) {
                message.error(getApiErrorMessage(e, "认领失败"));
              }
            }}
          >
            认领
          </Button>
          <Button
            size="small"
            icon={<UsergroupAddOutlined />}
            onClick={handleBatchAssign}
          >
            分配
          </Button>
          <Button
            size="small"
            icon={<UserSwitchOutlined />}
            onClick={async () => {
              try {
                await batchSetOwner(selectedIds, "release");
                message.success(`已释放 ${selectedCount} 个客户到公海`);
                onBatchComplete();
                onClear();
              } catch (e: unknown) {
                message.error(getApiErrorMessage(e, "释放失败"));
              }
            }}
          >
            释放
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={deleting}
            onClick={handleBatchDelete}
          >
            删除
          </Button>
          <Button size="small" onClick={onClear}>
            取消选择
          </Button>
        </Space>
      </div>
      <Modal
        title={`为 ${selectedCount} 个客户添加标签`}
        open={tagModalOpen}
        okText="确认"
        cancelText="取消"
        confirmLoading={tagging}
        onOk={handleBatchTagSubmit}
        onCancel={() => setTagModalOpen(false)}
      >
        <Select
          mode="multiple"
          style={{ width: "100%", marginTop: 12 }}
          placeholder="选择标签"
          options={tagOptions}
          value={selectedTagIds}
          onChange={setSelectedTagIds}
        />
      </Modal>
      <Modal
        title={`分配 ${selectedCount} 个客户给负责人`}
        open={assignModalOpen}
        okText="确认分配"
        cancelText="取消"
        confirmLoading={assigning}
        onOk={handleBatchAssignSubmit}
        onCancel={() => setAssignModalOpen(false)}
      >
        <Select
          showSearch
          style={{ width: "100%", marginTop: 12 }}
          placeholder="选择目标负责人"
          options={userOptions}
          value={assignTarget}
          onChange={setAssignTarget}
          filterOption={(input, option) =>
            (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
          }
        />
      </Modal>
    </>
  );
};

export default CustomerBatchBar;
