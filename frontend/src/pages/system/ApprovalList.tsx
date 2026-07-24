import { useState, useRef } from "react";
import { Button, Space, Modal, Input, message, Card, Tabs, Typography, Timeline, Descriptions } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { CheckOutlined, CloseOutlined, EyeOutlined } from "@ant-design/icons";
import client from "../../api/client";
import { getApiErrorMessage } from "../../api";

interface ApprovalReq {
  id: number; doc_type: string; doc_id: number;
  submitter_id: number; submitter_name: string;
  status: string; current_level: number;
  created_at: string;
}

interface ApprovalDetail extends ApprovalReq {
  flow_snapshot: { level: number; approver_role?: string; approver_id?: number }[];
  doc_summary: Record<string, unknown>;
  actions: { id: number; approver_name: string; action: string; comment: string; level: number; created_at: string }[];
}

const docTypeLabels: Record<string, string> = { quotation: "报价单", purchase_order: "采购订单" };
const statusColors: Record<string, string> = { pending: "processing", approved: "success", rejected: "error" };
const statusLabels: Record<string, string> = { pending: "待审批", approved: "已通过", rejected: "已驳回" };

export default function ApprovalList() {
  const actionRef = useRef<ActionType>(null);
  const [tab, setTab] = useState("all");
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [acting, setActing] = useState(false);

  const viewDetail = async (id: number) => {
    try {
      const resp = await client.get(`/approvals/requests/${id}`);
      setDetail(resp.data.data);
      setDetailOpen(true);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载详情失败")); }
  };

  const handleAction = async (id: number, action: string) => {
    setActing(true);
    try {
      await client.post(`/approvals/requests/${id}/${action}`, { comment });
      message.success(action === "approve" ? "已通过" : "已驳回");
      setDetailOpen(false);
      setComment("");
      actionRef.current?.reload();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
    finally { setActing(false); }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60, responsive: ["lg"] as unknown as ("xxl" | "xl" | "lg" | "md" | "sm" | "xs")[] },
    { title: "单据类型", dataIndex: "doc_type", width: 100, render: (v: string) => docTypeLabels[v] || v },
    { title: "单据ID", dataIndex: "doc_id", width: 80, responsive: ["md"] as unknown as ("xxl" | "xl" | "lg" | "md" | "sm" | "xs")[] },
    { title: "提交人", dataIndex: "submitter_name", width: 100 },
    {
      title: "状态", dataIndex: "status", width: 80,
      render: (v: string) => <StatusTag status={v} color={statusColors[v]} label={statusLabels[v] || v} />,
    },
    { title: "当前级别", dataIndex: "current_level", width: 80, responsive: ["md"] as unknown as ("xxl" | "xl" | "lg" | "md" | "sm" | "xs")[] },
    { title: "提交时间", dataIndex: "created_at", width: 160, render: (v: string) => v?.slice(0, 19).replace("T", " "), responsive: ["lg"] as unknown as ("xxl" | "xl" | "lg" | "md" | "sm" | "xs")[] },
    {
      title: "操作", key: "op", width: 80,
      render: (_: any, r: any) => <Button size="small" icon={<EyeOutlined />} onClick={() => viewDetail(r.id)}>详情</Button>,
    },
  ];

  return (
    <Card title="审批管理">
      <Tabs activeKey={tab} onChange={(v) => { setTab(v); actionRef.current?.reload(); }} items={[
        { key: "all", label: "全部" },
        { key: "pending", label: "待审批" },
        { key: "approved", label: "已通过" },
        { key: "rejected", label: "已驳回" },
      ]} />
      <ProTable rowKey="id" actionRef={actionRef} search={false} options={{ reload: true }}
        columns={columns as any}
        request={async (params) => {
          const queryParams: Record<string, unknown> = {};
          if (tab && tab !== "all") queryParams.status = tab;
          queryParams.page = params.current;
          queryParams.page_size = params.pageSize;
          const resp = await client.get("/approvals/requests", { params: queryParams });
          const d = resp.data.data;
          return { data: d?.list || [], success: true, total: d?.total || 0 };
        }} />

      <Modal title="审批详情" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={600}>
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="单据类型">{docTypeLabels[detail.doc_type]}</Descriptions.Item>
              <Descriptions.Item label="单据ID">{detail.doc_id}</Descriptions.Item>
              <Descriptions.Item label="提交人">{detail.submitter_name}</Descriptions.Item>
              <Descriptions.Item label="状态"><StatusTag status={detail.status} color={statusColors[detail.status]} label={statusLabels[detail.status]} /></Descriptions.Item>
            </Descriptions>
            {detail.doc_summary && (
              <Descriptions column={1} size="small" bordered>
                {Object.entries(detail.doc_summary).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
                ))}
              </Descriptions>
            )}
            <Typography.Title level={5}>审批历史</Typography.Title>
            <Timeline items={(detail.actions || []).map((a) => ({
              color: a.action === "approve" ? "green" : "red",
              children: `${a.approver_name} — ${a.action === "approve" ? "通过" : "驳回"}${a.comment ? ` (${a.comment})` : ""} — ${a.created_at?.slice(0, 19)}`,
            }))} />
            {detail.status === "pending" && (
              <Space direction="vertical" style={{ width: "100%" }}>
                <Input.TextArea rows={2} placeholder="审批意见（可选）" value={comment} onChange={(e) => setComment(e.target.value)} />
                <Space>
                  <Button type="primary" icon={<CheckOutlined />} loading={acting} onClick={() => handleAction(detail.id, "approve")}>通过</Button>
                  <Button danger icon={<CloseOutlined />} loading={acting} onClick={() => handleAction(detail.id, "reject")}>驳回</Button>
                </Space>
              </Space>
            )}
          </Space>
        )}
      </Modal>
    </Card>
  );
}
