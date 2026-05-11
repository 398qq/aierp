import { useEffect, useState } from "react";
import { Table, Card, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import client from "../../api/client";

interface Account {
  id: number; code: string; name: string; type: string;
  parent_id: number | null; description: string; is_active: boolean;
}

const typeColors: Record<string, string> = { asset: "blue", liability: "orange", equity: "purple", income: "green", expense: "red" };
const typeLabels: Record<string, string> = { asset: "资产", liability: "负债", equity: "权益", income: "收入", expense: "费用" };

export default function AccountList() {
  const [data, setData] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const resp = await client.get("/finance/accounts");
        setData(resp.data.data || []);
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, []);

  const columns: ColumnsType<Account> = [
    { title: "编码", dataIndex: "code", width: 100 },
    { title: "名称", dataIndex: "name", width: 180 },
    {
      title: "类型", dataIndex: "type", width: 80,
      render: (v: string) => <Tag color={typeColors[v]}>{typeLabels[v] || v}</Tag>,
    },
    { title: "说明", dataIndex: "description", ellipsis: true },
  ];

  return (
    <Card title="会计科目表">
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={false} size="small" />
    </Card>
  );
}
