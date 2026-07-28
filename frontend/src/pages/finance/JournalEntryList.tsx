import { useRef } from "react";
import { Button, Card, Typography, Modal, Descriptions } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ActionType } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { PlusOutlined, EyeOutlined } from "@ant-design/icons";

import { useNavigate } from "react-router-dom";
import client from "../../api/client";

interface Entry {
  id: number; entry_no: string; entry_date: string; description: string; status: string; created_at: string;
}

const statusColors: Record<string, string> = { draft: "default", posted: "green", reversed: "red" };
const statusLabels: Record<string, string> = { draft: "草稿", posted: "已过账", reversed: "已冲销" };

export default function JournalEntryList() {
  const actionRef = useRef<ActionType>(null);
  const navigate = useNavigate();

  const columns: any = [
    { title: "凭证号", dataIndex: "entry_no", width: 160 },
    { title: "日期", dataIndex: "entry_date", width: 100 },
    { title: "摘要", dataIndex: "description", ellipsis: true },
    {
      title: "状态", dataIndex: "status", width: 80,
      render: (v: string) => <StatusTag status={v} color={statusColors[v]} label={statusLabels[v] || v} />,
    },
    { title: "创建时间", dataIndex: "created_at", width: 160, render: (v: string) => v?.slice(0, 19).replace("T", " ") },
    {
      title: "操作", key: "op", width: 80,
      render: (_: any, r: any) => <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/finance/journal-entries/${r.id}`)}>详情</Button>,
    },
  ];

  return (
    <Card title="记账凭证" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/finance/journal-entries/new")}>新建凭证</Button>}>
      <ProTable actionRef={actionRef} rowKey="id" columns={columns}
        request={async (params) => {
          const resp = await client.get("/finance/journal-entries", { params: { page: params.current, page_size: params.pageSize } });
          return { data: resp.data.data?.list || [], success: true, total: resp.data.data?.total || 0 };
        }}
        search={false} options={{ reload: true, density: true, setting: true }} size="small" />
    </Card>
  );
}
