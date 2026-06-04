import { useEffect, useState } from "react";
import { Table, Button, Card, Typography, Modal, Descriptions } from "antd";
import { PlusOutlined, EyeOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useNavigate } from "react-router-dom";
import client from "../../api/client";
import { StatusTag } from "../../ui";

interface Entry {
  id: number; entry_no: string; entry_date: string; description: string; status: string; created_at: string;
}

const statusColors: Record<string, string> = { draft: "default", posted: "green", reversed: "red" };
const statusLabels: Record<string, string> = { draft: "草稿", posted: "已过账", reversed: "已冲销" };

export default function JournalEntryList() {
  const [data, setData] = useState<Entry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  const fetch = async (p = page) => {
    setLoading(true);
    try {
      const resp = await client.get("/finance/journal-entries", { params: { page: p, page_size: 20 } });
      setData(resp.data.data?.list || []);
      setTotal(resp.data.data?.total || 0);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page]);

  const columns: ColumnsType<Entry> = [
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
      render: (_, r) => <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/finance/journal-entries/${r.id}`)}>详情</Button>,
    },
  ];

  return (
    <Card title="记账凭证" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/finance/journal-entries/new")}>新建凭证</Button>}>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => { setPage(p); fetch(p); } }} size="small" />
    </Card>
  );
}
