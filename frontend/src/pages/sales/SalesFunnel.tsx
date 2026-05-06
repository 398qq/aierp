import { useEffect, useState } from "react";
import { Card, Spin, Alert, Empty, Select, Typography } from "antd";
import { getSalesFunnel, getCustomers } from "../../api";
import type { FunnelStage, Customer } from "../../types";

const { Title } = Typography;

const stageColors: Record<string, string> = {
  lead: "#bfbfbf",
  qualified: "#1677ff",
  proposal: "#fa8c16",
  negotiation: "#722ed1",
  won: "#52c41a",
  lost: "#ff4d4f",
};

const stageLabels: Record<string, string> = {
  lead: "线索",
  qualified: "资格",
  proposal: "方案",
  negotiation: "谈判",
  won: "成交",
  lost: "失败",
};

export default function SalesFunnel() {
  const [data, setData] = useState<FunnelStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [customers, setCustomers] = useState<Customer[]>([]);

  const fetch = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (customerId) params.customer_id = customerId;
      const resp = await getSalesFunnel(params);
      setData(resp.data.data || []);
    } catch (e) {
      setError((e as Error).message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = async (q?: string) => {
    try {
      const resp = await getCustomers({ page: 1, page_size: 100, q });
      setCustomers(resp.data.data.list || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetch(); }, [customerId]);
  useEffect(() => { loadCustomers(); }, []);

  if (loading) return <Spin style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Alert type="error" message={error} />;
  if (!data.length) return <Empty description="暂无销售漏斗数据" />;

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>销售漏斗</Title>
        <Select
          allowClear
          showSearch
          placeholder="筛选客户"
          style={{ width: 240 }}
          value={customerId}
          onChange={(v) => setCustomerId(v)}
          onSearch={loadCustomers}
          filterOption={false}
          options={customers.map((c) => ({ value: c.id, label: c.name }))}
        />
      </div>
      <Card>
        {data.map((item) => (
          <div key={item.stage} style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontWeight: 500, color: stageColors[item.stage] || "#666" }}>
                {stageLabels[item.stage] || item.stage}
              </span>
              <span>
                {item.count} 个 · ¥{(item.amount || 0).toLocaleString()}
              </span>
            </div>
            <div style={{
              height: 36,
              width: `${Math.max((item.count / maxCount) * 100, 5)}%`,
              backgroundColor: stageColors[item.stage] || "#ccc",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 600,
              fontSize: 14,
              minWidth: 60,
              transition: "width 0.3s ease",
            }}>
              {item.count}
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
