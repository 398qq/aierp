// CustomerSemanticSearchModal — natural-language customer search using
// the AI semantic-search endpoint, with results as a small table.

import { useNavigate } from "react-router";
import { Button, Input, Modal, Space } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import type { SimilarCustomer } from "../../types";

interface Props {
  open: boolean;
  loading: boolean;
  query: string;
  results: SimilarCustomer[];
  onClose: () => void;
  onChangeQuery: (q: string) => void;
  onSearch: () => void;
}

export default function CustomerSemanticSearchModal({
  open,
  loading,
  query,
  results,
  onClose,
  onChangeQuery,
  onSearch,
}: Props) {
  const navigate = useNavigate();
  const columns: any = [
    {
      title: "客户名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, r: SimilarCustomer) => (
        <a
          onClick={() => {
            onClose();
            navigate(`/customers/${r.id}`);
          }}
        >
          {name}
        </a>
      ),
    },
    { title: "行业", dataIndex: "industry", key: "industry", render: (v: string) => <StatusTag>{v || "-"}</StatusTag> },
    { title: "区域", dataIndex: "region", key: "region", render: (v: string) => v || "-" },
    { title: "相似度", dataIndex: "similarity", key: "similarity", render: (v: number) => `${(v * 100).toFixed(1)}%` },
  ];

  return (
    <Modal title="语义搜索" open={open} onCancel={onClose} footer={null} width={620}>
      <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
        <Input
          placeholder="例如：华东地区做汽车电子的A级客户"
          value={query}
          onChange={(e) => onChangeQuery(e.target.value)}
          onPressEnter={onSearch}
        />
        <Button type="primary" loading={loading} onClick={onSearch}>搜索</Button>
      </Space.Compact>
      <ProTable
        dataSource={results}
        rowKey="id"
        size="small"
        pagination={false}
        search={false}
        options={false}
        locale={{ emptyText: query && !loading ? "未找到匹配客户" : "输入关键词后搜索" }}
        columns={columns}
      />
    </Modal>
  );
}
