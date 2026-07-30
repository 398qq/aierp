import { Card } from "antd";
import type { ProColumns } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { useApiQuery } from "@/lib/queries";

interface Account {
  id: number; code: string; name: string; type: string;
  parent_id: number | null; description: string; is_active: boolean;
}

const typeColors: Record<string, string> = { asset: "blue", liability: "orange", equity: "purple", income: "green", expense: "red" };
const typeLabels: Record<string, string> = { asset: "资产", liability: "负债", equity: "权益", income: "收入", expense: "费用" };

export default function AccountList() {
  const query = useApiQuery<Account[]>(
    ["finance-accounts"],
    "/finance/accounts",
    undefined,
    { staleTime: 5 * 60 * 1000 },
  );

  const columns: ProColumns<Account>[] = [
    { title: "编码", dataIndex: "code", width: 100 },
    { title: "名称", dataIndex: "name", width: 180 },
    {
      title: "类型", dataIndex: "type", width: 80,
      render: (_, r) => <StatusTag tone={typeColors[r.type]}>{typeLabels[r.type] || r.type}</StatusTag>,
    },
    { title: "说明", dataIndex: "description", ellipsis: true },
  ];

  return (
    <Card title="会计科目表">
      <ProTable<Account>
        rowKey="id"
        columns={columns}
        dataSource={query.data || []}
        loading={query.isLoading || query.isFetching}
        pagination={false}
        size="small"
        search={false}
        options={false}
      />
    </Card>
  );
}
