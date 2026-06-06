import { useEffect, useState } from "react";
import { Table, Card, Tag, Select, Input, Space, Typography } from "antd";
import { StatusTag } from "../../ui";
import { SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

interface AuditLog {
  id: number; user_id: number; username: string;
  action: string; resource_type: string; resource_id: number;
  summary: string; ip_address: string; created_at: string;
}

const actionColors: Record<string, string> = { create: "green", update: "blue", delete: "red", submit_approval: "orange", approve: "cyan", reject: "magenta" };
const resourceLabels: Record<string, string> = {
  customer: "客户", product: "产品", supplier: "供应商", brand: "品牌",
  quotation: "报价单", sales_order: "销售订单", purchase_order: "采购订单",
  invoice: "发票", payment: "回款", contract: "合同",
  user: "用户", role: "角色", approval_rule: "审批规则", approval_request: "审批请求",
  report_template: "报表模板", opportunity: "商机", warehouse: "仓库",
};

export default function AuditLogList() {
  const [data, setData] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [resourceType, setResourceType] = useState<string | undefined>();
  const [userId, setUserId] = useState<string>("");

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 };
      if (resourceType) params.resource_type = resourceType;
      if (userId) params.user_id = Number(userId);
      const resp = await client.get("/permissions/audit-logs", { params });
      setData(resp.data.data?.list || []);
      setTotal(resp.data.data?.total || 0);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [resourceType]);

  const handleSearch = () => { setPage(1); fetch(1); };

  const columns: ColumnsType<AuditLog> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "用户", dataIndex: "username", width: 100 },
    {
      title: "操作", dataIndex: "action", width: 100,
      render: (v: string) => <StatusTag tone={actionColors[v] || "neutral"}>{v}</StatusTag>,
    },
    {
      title: "资源类型", dataIndex: "resource_type", width: 100,
      render: (v: string) => resourceLabels[v] || v,
    },
    { title: "资源ID", dataIndex: "resource_id", width: 80 },
    { title: "摘要", dataIndex: "summary", ellipsis: true },
    { title: "IP", dataIndex: "ip_address", width: 130 },
    { title: "时间", dataIndex: "created_at", width: 160, render: (v: string) => v?.slice(0, 19).replace("T", " ") },
  ];

  return (
    <Card title="审计日志">
      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear placeholder="资源类型" style={{ width: 140 }}
          value={resourceType} onChange={(v) => setResourceType(v)}
          options={Object.entries(resourceLabels).map(([k, v]) => ({ value: k, label: v }))}
        />
        <Input
          placeholder="用户ID" style={{ width: 120 }}
          value={userId} onChange={(e) => setUserId(e.target.value)}
          onPressEnter={handleSearch}
        />
        <Typography.Link onClick={handleSearch}><SearchOutlined /> 搜索</Typography.Link>
      </Space>
      <Table
        rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => { setPage(p); fetch(p); } }}
        size="small"
      />
    </Card>
  );
}
