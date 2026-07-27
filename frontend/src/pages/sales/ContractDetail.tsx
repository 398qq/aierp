import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { Alert, Button, Card, Descriptions, Divider, Empty, Progress, Space, Spin, Tag, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, AuditOutlined, EditOutlined, PrinterOutlined } from "@ant-design/icons";
import { getContract, getCustomer, getSalesOrder, getSalesOrderBusinessChain } from "../../api";
import type { Contract, SalesOrder, SalesOrderBusinessChain } from "../../types";
import { CustomerLink, ErpStatusTimeline, MetricBand, SalesModuleShell, SalesStatusTag, money, shortDate } from "./salesUi";
import { SalesContractPrint } from "./SalesContractPrint";

const STATUS: Record<string, { color: string; label: string }> = {
  draft: { color: "default", label: "草稿" },
  signed: { color: "blue", label: "已签署" },
  active: { color: "green", label: "履行中" },
  expired: { color: "orange", label: "已到期" },
  terminated: { color: "red", label: "已终止" },
};

const STATUS_STEPS = [
  { key: "draft", label: "草稿" },
  { key: "signed", label: "已签署" },
  { key: "active", label: "履行中" },
  { key: "expired", label: "已到期" },
];

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ct, setCt] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<SalesOrder | null>(null);
  const [chain, setChain] = useState<SalesOrderBusinessChain | null>(null);
  const [customerName, setCustomerName] = useState("");

  useEffect(() => {
    setLoading(true);
    setError(null);
    getContract(Number(id))
      .then(async (r) => {
        const contract = r.data.data;
        if (!contract) {
          setCt(null);
          return;
        }
        setCt(contract);
        getCustomer(contract.customer_id)
          .then((customerResult) => setCustomerName(customerResult.data.data?.name || ""))
          .catch(() => setCustomerName(""));
        if (contract.sales_order_id) {
          const [orderResult, chainResult] = await Promise.allSettled([
            getSalesOrder(contract.sales_order_id),
            getSalesOrderBusinessChain(contract.sales_order_id),
          ]);
          if (orderResult.status === "fulfilled") setOrder(orderResult.value.data.data);
          if (chainResult.status === "fulfilled") setChain(chainResult.value.data.data);
        }
      })
      .catch((e) => setError(e.message || "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <SalesModuleShell title="合同详情" activeKey="contracts">
        <Spin style={{ display: "block", margin: "100px auto" }} />
      </SalesModuleShell>
    );
  }

  if (error) {
    return (
      <SalesModuleShell title="合同详情" activeKey="contracts">
        <Alert type="error" message={error} />
      </SalesModuleShell>
    );
  }

  if (!ct) {
    return (
      <SalesModuleShell title="合同详情" activeKey="contracts">
        <Empty description="合同不存在" />
      </SalesModuleShell>
    );
  }

  return (
    <SalesModuleShell
      title={ct.contract_no || `合同 #${ct.id}`}
      subtitle={ct.notes ? `备注: ${ct.notes}` : "销售合同详情，含签署信息、履行状态和到期跟踪"}
      activeKey="contracts"
      extra={(
        <>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/contracts")}>返回</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/contracts/${ct.id}/edit`)}>编辑</Button>
        </>
      )}
    >
      <SalesContractPrint contract={ct} order={order} customerName={customerName} />
      <MetricBand
        items={[
          { title: "合同金额", value: ct.amount || 0, prefix: "¥", precision: 2 },
          { title: "已开票金额", value: chain?.progress.invoiced_amount || 0, prefix: "¥", precision: 2 },
          { title: "已回款金额", value: chain?.progress.paid_amount || 0, prefix: "¥", precision: 2 },
          { title: "状态", value: STATUS[ct.status]?.label || ct.status },
          { title: "到期日", value: ct.expire_date ? shortDate(ct.expire_date) : "-" },
        ]}
      />

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/contracts")}>返回列表</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/sales/contracts/${ct.id}/edit`)}>编辑合同</Button>
          <Button icon={<PrinterOutlined />} onClick={() => window.print()}>打印销售合同</Button>
        </Space>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 12, alignItems: "start" }}>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Card
            title="合同信息"
            size="small"
            extra={<StatusTag tone={STATUS[ct.status]?.color}>{STATUS[ct.status]?.label || ct.status}</StatusTag>}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="合同号">{ct.contract_no || `#${ct.id}`}</Descriptions.Item>
              <Descriptions.Item label="客户"><CustomerLink id={ct.customer_id} /></Descriptions.Item>
              <Descriptions.Item label="标题">{ct.title}</Descriptions.Item>
              <Descriptions.Item label="金额">{money(ct.amount)}</Descriptions.Item>
              <Descriptions.Item label="签署日期">{shortDate(ct.signed_date)}</Descriptions.Item>
              <Descriptions.Item label="到期日期">{shortDate(ct.expire_date)}</Descriptions.Item>
              <Descriptions.Item label="关联订单">{ct.sales_order_id ? `订单 #${ct.sales_order_id}` : "-"}</Descriptions.Item>
              <Descriptions.Item label="币种">{ct.currency || "CNY"}</Descriptions.Item>
              <Descriptions.Item label="发票类型">{ct.invoice_type || "-"}</Descriptions.Item>
              <Descriptions.Item label="交货地址" span={2}>{ct.delivery_address || order?.shipping_address || "-"}</Descriptions.Item>
              <Descriptions.Item label="文件">{ct.file_url ? <Typography.Link href={ct.file_url} target="_blank">查看文件</Typography.Link> : "-"}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{ct.notes || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="合同产品明细" size="small">
            {order ? <ProTable
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={order.items}
              columns={[
                { title: "产品", dataIndex: "product_name", ellipsis: true },
                { title: "数量", dataIndex: "quantity", align: "right" as const },
                { title: "单位", dataIndex: "unit", render: (value: string | null) => value || "-" },
                { title: "单价", dataIndex: "unit_price", align: "right" as const, render: (value: number | null) => value == null ? "-" : money(value) },
                { title: "金额", dataIndex: "total_price", align: "right" as const, render: (value: number | null) => value == null ? "-" : money(value) },
              ] as any}
              search={false}
              options={false}
              summary={() => <ProTable.Summary.Row><ProTable.Summary.Cell index={0}><Typography.Text strong>合计</Typography.Text></ProTable.Summary.Cell><ProTable.Summary.Cell index={1}><Typography.Text strong>{order.items.reduce((sum, item) => sum + Number(item.quantity || 0), 0)}</Typography.Text></ProTable.Summary.Cell><ProTable.Summary.Cell index={2} /><ProTable.Summary.Cell index={3} /><ProTable.Summary.Cell index={4}><Typography.Text strong>{money(order.total_amount)}</Typography.Text></ProTable.Summary.Cell></ProTable.Summary.Row>}
            /> : <Typography.Text type="secondary">未关联合同订单，暂无产品明细</Typography.Text>}
          </Card>

          <Card title="合同商务条款" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="付款条款">{ct.payment_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="交付条款">{ct.delivery_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="验收条款">{ct.acceptance_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="质保与售后">{ct.warranty_terms || "-"}</Descriptions.Item>
              <Descriptions.Item label="违约与争议解决">{ct.dispute_terms || "-"}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="签署确认" size="small">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="甲方（客户）">{order?.customer_name || "客户"}</Descriptions.Item>
              <Descriptions.Item label="乙方（供方）">本公司</Descriptions.Item>
              <Descriptions.Item label="签署日期">{shortDate(ct.signed_date)}</Descriptions.Item>
              <Descriptions.Item label="合同文件">{ct.file_url ? <Typography.Link href={ct.file_url} target="_blank">查看已上传文件</Typography.Link> : "待上传"}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Space>

        <Space direction="vertical" size={12} style={{ width: "100%", position: "sticky", top: 8 }}>
          <Card size="small" title={<><AuditOutlined /> 合同摘要</>}>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">合同金额</Typography.Text>
                <Typography.Text strong>{money(ct.amount)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">未开票</Typography.Text>
                <Typography.Text type={chain?.progress.uninvoiced_amount ? "warning" : undefined}>{money(chain?.progress.uninvoiced_amount || 0)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">未回款</Typography.Text>
                <Typography.Text type={chain?.progress.outstanding_amount ? "danger" : undefined}>{money(chain?.progress.outstanding_amount || 0)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">合同标题</Typography.Text>
                <Typography.Text>{ct.title}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">合同号</Typography.Text>
                <Typography.Text>{ct.contract_no || `#${ct.id}`}</Typography.Text>
              </div>
              <Divider style={{ margin: "6px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">状态</Typography.Text>
                <SalesStatusTag value={ct.status} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">签署日期</Typography.Text>
                <Typography.Text>{shortDate(ct.signed_date)}</Typography.Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <Typography.Text type="secondary">到期日期</Typography.Text>
                <Typography.Text>{shortDate(ct.expire_date)}</Typography.Text>
              </div>
            </Space>
          </Card>

          <Card size="small" title="合同执行进度">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              <Typography.Text type="secondary">交付</Typography.Text>
              <Progress size="small" percent={chain?.progress.delivery_percent || 0} />
              <Typography.Text type="secondary">开票</Typography.Text>
              <Progress size="small" percent={chain?.progress.invoice_percent || 0} />
              <Typography.Text type="secondary">回款</Typography.Text>
              <Progress size="small" percent={chain?.progress.payment_percent || 0} />
            </Space>
          </Card>

          <Card size="small" title="关联单据">
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <Typography.Link onClick={() => ct.sales_order_id && navigate(`/sales/orders/${ct.sales_order_id}`)}>销售订单：{order?.order_no || (ct.sales_order_id ? `#${ct.sales_order_id}` : "未关联")}</Typography.Link>
              <Typography.Text>发货单：{chain?.deliveries.length || 0} 张</Typography.Text>
              <Typography.Text>发票：{chain?.invoices.length || 0} 张</Typography.Text>
              <Typography.Text>回款：{chain?.payments.length || 0} 笔</Typography.Text>
            </Space>
          </Card>

          <Card size="small" title="状态流转">
            <ErpStatusTimeline
              currentStatus={ct.status}
              steps={STATUS_STEPS}
              createdAt={ct.created_at}
              lostStatus="terminated"
            />
          </Card>

          <Card size="small" title="下一步动作">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              {ct.status === "draft" ? (
                <Alert showIcon type="info" message="合同为草稿状态，完善信息后可签署。" />
              ) : ct.status === "signed" ? (
                <Alert showIcon type="success" message="合同已签署，进入履行阶段。" />
              ) : ct.status === "active" ? (
                <Alert showIcon type="info" message="合同履行中，关注到期日和交付进度。" />
              ) : ct.status === "expired" ? (
                <Alert showIcon type="warning" message="合同已到期，如需续签请及时处理。" />
              ) : ct.status === "terminated" ? (
                <Alert showIcon type="error" message="合同已终止。" />
              ) : null}
              <Button block icon={<EditOutlined />} onClick={() => navigate(`/sales/contracts/${ct.id}/edit`)}>编辑合同</Button>
              {ct.customer_id ? (
                <Button block onClick={() => navigate(`/customers/${ct.customer_id}`)}>查看客户</Button>
              ) : null}
            </Space>
          </Card>
        </Space>
      </div>
    </SalesModuleShell>
  );
}
