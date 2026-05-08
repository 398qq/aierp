import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Tag, Select, message, Popconfirm } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getContracts, deleteContract } from "../../api";
import type { Contract } from "../../types";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" }, signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" }, expired: { color: "orange", label: "已到期" }, terminated: { color: "red", label: "已终止" },
};

export default function ContractList() {
  const [data, setData] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (status) params.status = status;
      const resp = await getContracts(params);
      setData(resp.data.data.list || []);
      setTotal(resp.data.data.total || 0);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page, status]);

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/sales/contracts/new")}>新增合同</Button>
        <Select placeholder="状态筛选" allowClear style={{ width: 120 }} value={status} onChange={setStatus} options={[
          { value: "draft", label: "草稿" }, { value: "signed", label: "已签署" }, { value: "active", label: "履行中" },
        ]} />
      </Space>
      <Table
        rowKey="id" loading={loading} dataSource={data}
        columns={[
          { title: "合同号", dataIndex: "contract_no", width: 140, render: (v: string, r: Contract) => <a onClick={() => navigate(`/sales/contracts/${r.id}`)}>{v || `#${r.id}`}</a> },
          { title: "标题", dataIndex: "title", ellipsis: true },
          { title: "金额", dataIndex: "amount", width: 120, render: (v: number) => `¥${v.toLocaleString()}` },
          { title: "状态", dataIndex: "status", width: 80, render: (v: string) => <Tag color={STATUS[v]?.color}>{STATUS[v]?.label || v}</Tag> },
          { title: "签署日期", dataIndex: "signed_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          { title: "到期日期", dataIndex: "expire_date", width: 110, render: (v: string) => v?.slice(0, 10) || "-" },
          {
            title: "操作", width: 120,
            render: (_: unknown, r: Contract) => (
              <Space size="small">
                <Button size="small" onClick={() => navigate(`/sales/contracts/${r.id}`)}>详情</Button>
                <Popconfirm title="确定删除?" onConfirm={async () => {
                  try { await deleteContract(r.id); message.success("已删除"); load(); } catch { message.error("删除失败"); }
                }}><Button size="small" danger>删除</Button></Popconfirm>
              </Space>
            ),
          },
        ]}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 条` }}
      />
    </div>
  );
}
