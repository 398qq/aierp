import { useRef, useState } from "react";
import { App, Button, Modal, Form, Input, Tag, Space, Popconfirm, Descriptions } from "antd";
import { PlusOutlined, CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import type { ProColumns, ActionType } from "@ant-design/pro-components";
import { ProForm, ProFormText, ProFormTextArea, ProTable } from "@ant-design/pro-components";
import { getApiErrorMessage } from "@/api/client";
import client from "@/api/client";
import type { APIResponse } from "@/types";

interface TransferRequest {
  id: number; customer_id: number; from_owner: string | null; to_owner: string;
  requested_by: string; status: string; reason: string | null;
  reviewed_by: string | null; review_comment: string | null;
  reviewed_at: string | null; created_at: string | null;
}

const STATUS_LABELS: Record<string, string> = { pending: "待审批", approved: "已通过", rejected: "已驳回", cancelled: "已撤销" };
const STATUS_COLORS: Record<string, string> = { pending: "gold", approved: "green", rejected: "red", cancelled: "default" };

export default function OwnerTransferRequestsPage() {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState<TransferRequest | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [form] = ProForm.useForm();
  const [reviewForm] = ProForm.useForm();

  const handleCreate = () => { form.resetFields(); setModalOpen(true); };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await client.post("/customers/transfer-requests", values);
      message.success("转移申请已提交，等待审批");
      setModalOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "提交失败"));
    } finally {
      setSaving(false);
    }
  };

  const handleDetail = (req: TransferRequest) => {
    setSelectedReq(req);
    reviewForm.resetFields();
    setDetailOpen(true);
  };

  const handleApprove = async (comment: string | null) => {
    if (!selectedReq) return;
    try {
      await client.post(`/customers/transfer-requests/${selectedReq.id}/approve`, { comment: comment || null });
      message.success("已审批通过，负责人已转移");
      setDetailOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "审批失败"));
    }
  };

  const handleReject = async (comment: string | null) => {
    if (!selectedReq) return;
    try {
      await client.post(`/customers/transfer-requests/${selectedReq.id}/reject`, { comment: comment || null });
      message.success("已驳回");
      setDetailOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "驳回失败"));
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await client.post(`/customers/transfer-requests/${id}/cancel`);
      message.success("申请已撤销");
      actionRef.current?.reload();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "撤销失败"));
    }
  };

  const columns: ProColumns<TransferRequest>[] = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "客户 ID", dataIndex: "customer_id", width: 80 },
    { title: "原负责人", dataIndex: "from_owner", width: 100, render: (_, r) => r.from_owner || "（公海）" },
    { title: "目标负责人", dataIndex: "to_owner", width: 100 },
    { title: "申请人", dataIndex: "requested_by", width: 100 },
    { title: "原因", dataIndex: "reason", ellipsis: true },
    { title: "状态", dataIndex: "status", width: 90, render: (_, r) => <Tag color={STATUS_COLORS[r.status]}>{STATUS_LABELS[r.status]}</Tag> },
    {
      title: "操作", key: "actions", width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => handleDetail(r)}>详情</Button>
          {r.status === "pending" && (
            <Popconfirm title="确认撤销此申请？" onConfirm={() => handleCancel(r.id)}>
              <Button size="small" danger>撤销</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <ProTable<TransferRequest>
        actionRef={actionRef}
        rowKey="id"
        headerTitle="负责人转移审批"
        columns={columns}
        request={async () => {
          const url = statusFilter ? `/customers/transfer-requests?status=${statusFilter}` : "/customers/transfer-requests";
          const res = await client.get<APIResponse<TransferRequest[]>>(url);
          return { data: (res.data?.data as TransferRequest[]) || [], success: true };
        }}
        toolBarRender={() => [
          <Select key="filter" allowClear placeholder="筛选状态" style={{ width: 120 }} value={statusFilter}
            onChange={(v) => { setStatusFilter(v); actionRef.current?.reload(); }}
            options={[
              { label: "待审批", value: "pending" }, { label: "已通过", value: "approved" },
              { label: "已驳回", value: "rejected" }, { label: "已撤销", value: "cancelled" },
            ]} />,
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            提交转移申请
          </Button>,
        ]}
        search={false}
        pagination={false}
      />

      <Modal title="提交转移申请" open={modalOpen} okText="提交" cancelText="取消"
        confirmLoading={saving} onOk={handleSave} onCancel={() => setModalOpen(false)}>
        <ProForm form={form} layout="vertical" submitter={false} style={{ marginTop: 16 }}>
          <ProFormText
            name="customer_id"
            label="客户 ID"
            rules={[{ required: true, message: "请输入客户 ID" }]}
            fieldProps={{ type: "number", min: 1, placeholder: "输入客户编号" }}
          />
          <ProFormText
            name="to_owner"
            label="目标负责人"
            rules={[{ required: true, message: "请输入目标负责人用户名" }]}
            placeholder="输入用户名"
          />
          <ProFormTextArea
            name="reason"
            label="转移原因"
            placeholder="请说明转移原因"
            fieldProps={{ rows: 3, maxLength: 500, showCount: true }}
          />
        </ProForm>
      </Modal>

      <Modal title="转移申请详情" open={detailOpen} footer={null} onCancel={() => setDetailOpen(false)} width={560}>
        {selectedReq && (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="客户 ID">{selectedReq.customer_id}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={STATUS_COLORS[selectedReq.status]}>{STATUS_LABELS[selectedReq.status]}</Tag></Descriptions.Item>
              <Descriptions.Item label="原负责人">{selectedReq.from_owner || "（公海）"}</Descriptions.Item>
              <Descriptions.Item label="目标负责人">{selectedReq.to_owner}</Descriptions.Item>
              <Descriptions.Item label="申请人">{selectedReq.requested_by}</Descriptions.Item>
              <Descriptions.Item label="申请时间">{selectedReq.created_at}</Descriptions.Item>
              <Descriptions.Item label="转移原因" span={2}>{selectedReq.reason || "无"}</Descriptions.Item>
              {selectedReq.reviewed_by && (
                <>
                  <Descriptions.Item label="审批人">{selectedReq.reviewed_by}</Descriptions.Item>
                  <Descriptions.Item label="审批时间">{selectedReq.reviewed_at}</Descriptions.Item>
                  <Descriptions.Item label="审批意见" span={2}>{selectedReq.review_comment || "无"}</Descriptions.Item>
                </>
              )}
            </Descriptions>
            {selectedReq.status === "pending" && (
              <ProForm form={reviewForm} layout="vertical" submitter={false}>
                <ProFormTextArea
                  name="comment"
                  label="审批意见"
                  fieldProps={{ rows: 2, placeholder: "可选，输入审批意见", maxLength: 500, showCount: true }}
                />
                <Space>
                  <Button type="primary" icon={<CheckCircleOutlined />}
                    onClick={async () => { const v = await reviewForm.validateFields(); handleApprove(v.comment || null); }}>
                    审批通过
                  </Button>
                  <Button danger icon={<CloseCircleOutlined />}
                    onClick={async () => { const v = await reviewForm.validateFields(); handleReject(v.comment || null); }}>
                    驳回
                  </Button>
                </Space>
              </ProForm>
            )}
          </>
        )}
      </Modal>
    </>
  );
}
