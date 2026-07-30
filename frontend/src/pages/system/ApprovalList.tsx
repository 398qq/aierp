import { useState } from "react";
import {
  App,
  Button,
  Card,
  Descriptions,
  Input,
  Modal,
  Space,
  Tabs,
  Timeline,
  Typography,
} from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { CheckOutlined, CloseOutlined, EyeOutlined } from "@ant-design/icons";
import { StatusTag } from "../../ui";
import { getApiErrorMessage } from "../../api";
import type { PageData } from "@/types";
import { useApiMutation, useApiQuery, useQueryClient } from "@/lib/queries";

interface ApprovalReq {
  id: number;
  doc_type: string;
  doc_id: number;
  submitter_id: number;
  submitter_name: string;
  status: string;
  current_level: number;
  created_at: string;
}

interface ApprovalDetail extends ApprovalReq {
  flow_snapshot: { level: number; approver_role?: string; approver_id?: number }[];
  doc_summary: Record<string, unknown>;
  actions: {
    id: number;
    approver_name: string;
    action: string;
    comment: string;
    level: number;
    created_at: string;
  }[];
}

const docTypeLabels: Record<string, string> = { quotation: "报价单", purchase_order: "采购订单" };
const statusColors: Record<string, string> = {
  pending: "processing",
  approved: "success",
  rejected: "error",
};
const statusLabels: Record<string, string> = {
  pending: "待审批",
  approved: "已通过",
  rejected: "已驳回",
};

export default function ApprovalList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("all");
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [comment, setComment] = useState("");
  const [acting, setActing] = useState(false);

  const params: Record<string, unknown> = {};
  if (tab && tab !== "all") params.status = tab;

  const query = useApiQuery<PageData<ApprovalReq>>(
    ["approvals", tab],
    "/approvals/requests",
    params,
    { staleTime: 30 * 1000 },
  );

  const detailQuery = useApiQuery<ApprovalDetail>(
    ["approval-detail", detailId],
    `/approvals/requests/${detailId}`,
    undefined,
    { enabled: detailId !== null, staleTime: 30 * 1000 },
  );

  const actionMut = useApiMutation<unknown, { id: number; action: string; comment: string }>(
    "post",
    (vars) => `/approvals/requests/${vars.id}/${vars.action}`,
    {
      invalidateKeys: [["approvals"], ["approval-detail"]],
      onSuccess: (_, vars) => {
        message.success(vars.action === "approve" ? "已通过" : "已驳回");
        setDetailOpen(false);
        setComment("");
        setDetailId(null);
      },
      onError: (err) => message.error(getApiErrorMessage(err, "操作失败")),
    },
  );

  const viewDetail = (id: number) => {
    setDetailId(id);
    setDetailOpen(true);
  };

  const handleAction = (id: number, action: string) => {
    setActing(true);
    actionMut.mutate(
      { id, action, comment },
      {
        onSettled: () => setActing(false),
      },
    );
  };

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["approvals", tab] });
  };

  const detail = detailQuery.data;

  const columns: ProColumns<ApprovalReq>[] = [
    { title: "ID", dataIndex: "id", width: 60, responsive: ["lg"] },
    {
      title: "单据类型",
      dataIndex: "doc_type",
      width: 100,
      render: (_, r) => docTypeLabels[r.doc_type] || r.doc_type,
    },
    { title: "单据ID", dataIndex: "doc_id", width: 80, responsive: ["md"] },
    { title: "提交人", dataIndex: "submitter_name", width: 100 },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (_, r) => (
        <StatusTag
          status={r.status}
          color={statusColors[r.status]}
          label={statusLabels[r.status] || r.status}
        />
      ),
    },
    { title: "当前级别", dataIndex: "current_level", width: 80, responsive: ["md"] },
    {
      title: "提交时间",
      dataIndex: "created_at",
      width: 160,
      render: (_, r) => r.created_at?.slice(0, 19).replace("T", " "),
      responsive: ["lg"],
    },
    {
      title: "操作",
      key: "op",
      width: 80,
      render: (_, r) => (
        <Button size="small" icon={<EyeOutlined />} onClick={() => viewDetail(r.id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <Card title="审批管理">
      <Tabs
        activeKey={tab}
        onChange={setTab}
        items={[
          { key: "all", label: "全部" },
          { key: "pending", label: "待审批" },
          { key: "approved", label: "已通过" },
          { key: "rejected", label: "已驳回" },
        ]}
      />
      <ProTable<ApprovalReq>
        rowKey="id"
        columns={columns}
        dataSource={query.data?.list || []}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: handleSearch, density: true, setting: true }}
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => query.refetch(),
        }}
      />

      <Modal
        title="审批详情"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false);
          setDetailId(null);
        }}
        footer={null}
        width={600}
      >
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="单据类型">
                {docTypeLabels[detail.doc_type]}
              </Descriptions.Item>
              <Descriptions.Item label="单据ID">{detail.doc_id}</Descriptions.Item>
              <Descriptions.Item label="提交人">{detail.submitter_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <StatusTag
                  status={detail.status}
                  color={statusColors[detail.status]}
                  label={statusLabels[detail.status]}
                />
              </Descriptions.Item>
            </Descriptions>
            {detail.doc_summary && (
              <Descriptions column={1} size="small" bordered>
                {Object.entries(detail.doc_summary).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {String(v)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            )}
            <Typography.Title level={5}>审批历史</Typography.Title>
            <Timeline
              items={(detail.actions || []).map((a) => ({
                color: a.action === "approve" ? "green" : "red",
                children: `${a.approver_name} — ${a.action === "approve" ? "通过" : "驳回"}${a.comment ? ` (${a.comment})` : ""} — ${a.created_at?.slice(0, 19)}`,
              }))}
            />
            {detail.status === "pending" && (
              <Space direction="vertical" style={{ width: "100%" }}>
                <Input.TextArea
                  rows={2}
                  placeholder="审批意见（可选）"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
                <Space>
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    loading={acting}
                    onClick={() => handleAction(detail.id, "approve")}
                  >
                    通过
                  </Button>
                  <Button
                    danger
                    icon={<CloseOutlined />}
                    loading={acting}
                    onClick={() => handleAction(detail.id, "reject")}
                  >
                    驳回
                  </Button>
                </Space>
              </Space>
            )}
          </Space>
        )}
      </Modal>
    </Card>
  );
}
