import { useState } from "react";
import { App, Card, Input, Select, Space, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { SearchOutlined } from "@ant-design/icons";
import type { PageData } from "@/types";
import { StatusTag } from "@/ui";
import { useApiQuery, useQueryClient } from "@/lib/queries";

interface AuditLog {
  id: number;
  user_id: number;
  username: string;
  action: string;
  resource_type: string;
  resource_id: number;
  summary: string;
  ip_address: string;
  created_at: string;
}

const actionColors: Record<string, string> = {
  create: "green",
  update: "blue",
  delete: "red",
  submit_approval: "orange",
  approve: "cyan",
  reject: "magenta",
};
const resourceLabels: Record<string, string> = {
  customer: "客户",
  product: "产品",
  supplier: "供应商",
  brand: "品牌",
  quotation: "报价单",
  sales_order: "销售订单",
  purchase_order: "采购订单",
  invoice: "发票",
  payment: "回款",
  contract: "合同",
  user: "用户",
  role: "角色",
  approval_rule: "审批规则",
  approval_request: "审批请求",
  report_template: "报表模板",
  opportunity: "商机",
  warehouse: "仓库",
};

export default function AuditLogList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [resourceType, setResourceType] = useState<string | undefined>();
  const [userId, setUserId] = useState<string>("");

  const query = useApiQuery<PageData<AuditLog>>(
    ["audit-logs", resourceType ?? "", userId],
    "/permissions/audit-logs",
    { resource_type: resourceType, user_id: userId ? Number(userId) : undefined },
    { staleTime: 30 * 1000, keepPreviousData: true },
  );

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
  };

  const columns: ProColumns<AuditLog>[] = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户", dataIndex: "username", width: 100 },
    {
      title: "操作",
      dataIndex: "action",
      width: 100,
      render: (_, r) => (
        <StatusTag tone={actionColors[r.action] || "neutral"}>{r.action}</StatusTag>
      ),
    },
    {
      title: "资源类型",
      dataIndex: "resource_type",
      width: 100,
      render: (_, r) => resourceLabels[r.resource_type] || r.resource_type,
    },
    { title: "资源ID", dataIndex: "resource_id", width: 80 },
    { title: "摘要", dataIndex: "summary", ellipsis: true },
    { title: "IP", dataIndex: "ip_address", width: 130 },
    {
      title: "时间",
      dataIndex: "created_at",
      width: 160,
      render: (_, r) => r.created_at?.slice(0, 19).replace("T", " "),
    },
  ];

  return (
    <Card title="审计日志">
      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="资源类型"
          style={{ width: 140 }}
          value={resourceType}
          onChange={setResourceType}
          options={Object.entries(resourceLabels).map(([k, v]) => ({ value: k, label: v }))}
        />
        <Input
          placeholder="用户ID"
          style={{ width: 120 }}
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <Typography.Link onClick={handleSearch}>
          <SearchOutlined /> 搜索
        </Typography.Link>
      </Space>
      <ProTable<AuditLog>
        rowKey="id"
        columns={columns}
        params={{ resource_type: resourceType, user_id: userId ? Number(userId) : undefined }}
        request={async () => {
          return {
            data: query.data?.list || [],
            success: true,
            total: query.data?.total || 0,
          };
        }}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: handleSearch, density: true, setting: true }}
        size="small"
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
        }}
      />
    </Card>
  );
}
