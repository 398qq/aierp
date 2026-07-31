import { useNavigate } from "react-router-dom";
import { Button, Card } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { PlusOutlined, EyeOutlined } from "@ant-design/icons";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import type { PageData, JournalEntry } from "@/types";

const statusColors: Record<string, string> = { draft: "default", posted: "green", reversed: "red" };
const statusLabels: Record<string, string> = {
  draft: "草稿",
  posted: "已过账",
  reversed: "已冲销",
};

export default function JournalEntryList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const query = useApiQuery<PageData<JournalEntry>>(
    ["journal-entries"],
    "/finance/journal-entries",
    {},
    { staleTime: 30 * 1000 },
  );

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
  };

  const columns: ProColumns<JournalEntry>[] = [
    { title: "凭证号", dataIndex: "entry_no", width: 160 },
    { title: "日期", dataIndex: "entry_date", width: 100 },
    { title: "摘要", dataIndex: "description", ellipsis: true },
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
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 160,
      render: (_, r) => (r.created_at ? r.created_at.slice(0, 19).replace("T", " ") : "-"),
    },
    {
      title: "操作",
      key: "op",
      width: 80,
      render: (_, r) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/finance/journal-entries/${r.id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <Card
      title="记账凭证"
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate("/finance/journal-entries/new")}
        >
          新建凭证
        </Button>
      }
    >
      <ProTable<JournalEntry>
        rowKey="id"
        columns={columns}
        dataSource={query.data?.list || []}
        loading={query.isLoading || query.isFetching}
        search={false}
        options={{ reload: handleSearch, density: true, setting: true }}
        pagination={{
          total: query.data?.total || 0,
          showSizeChanger: true,
          onChange: () => queryClient.invalidateQueries({ queryKey: ["journal-entries"] }),
        }}
      />
    </Card>
  );
}
