import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Card,
  Dropdown,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { StatusTag, type StatusTone } from "../../ui";
import type { ProColumns } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import type { MenuProps } from "antd";
import {
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EllipsisOutlined,
  FileDoneOutlined,
  PlusOutlined,
  ReloadOutlined,
  SendOutlined,
  ShoppingCartOutlined,
} from "@ant-design/icons";
import {
  batchDeleteQuotations,
  convertQuotationToOrder,
  deleteQuotation,
  downloadQuotationPDF,
  duplicateQuotation,
  getQuotationStats,
  sendQuotation,
  getApiErrorMessage,
} from "../../api";
import AIInlineBadge from "../../components/sales/AIInlineBadge";
import type { PageData, Quotation, QuotationStats } from "../../types";
import {
  CustomerLink,
  CustomerSelect,
  MetricBand,
  SalesModuleShell,
  SalesQuickActions,
  SalesStatusTag,
  erpRowClass,
  money,
  shortDate,
  statusDot,
  ERP_STATUS_DOT,
} from "./salesUi";
import { useApiQuery, useApiMutation, useQueryClient } from "@/lib/queries";

type QuoteScene = "all" | "draft" | "sent" | "expiring" | "expired" | "won" | "lost";

const SCENE_LABELS: Record<QuoteScene, string> = {
  all: "全部报价",
  draft: "待发送",
  sent: "已发送待跟进",
  expiring: "即将过期",
  expired: "已过期",
  won: "已成交",
  lost: "已丢失",
};

const getDueMeta = (validUntil?: string | null, status?: string) => {
  if (!validUntil || status === "won" || status === "lost")
    return { text: "-", tone: "neutral" as StatusTone, scene: "normal" };
  const due = new Date(validUntil).getTime();
  if (Number.isNaN(due))
    return { text: shortDate(validUntil), tone: "neutral" as StatusTone, scene: "normal" };
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((due - today.getTime()) / (24 * 60 * 60 * 1000));
  if (diffDays < 0)
    return {
      text: `已过期 ${Math.abs(diffDays)} 天`,
      tone: "danger" as StatusTone,
      scene: "expired",
    };
  if (diffDays === 0) return { text: "今日到期", tone: "danger" as StatusTone, scene: "expiring" };
  if (diffDays <= 7)
    return { text: `${diffDays} 天后到期`, tone: "warning" as StatusTone, scene: "expiring" };
  return { text: shortDate(validUntil), tone: "info" as StatusTone, scene: "normal" };
};

export default function QuotationList() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [stats, setStats] = useState<QuotationStats | null>(null);
  const [scene, setScene] = useState<QuoteScene>("all");
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState("");
  const [q, setQ] = useState("");
  const [includeAi, setIncludeAi] = useState(false);
  const [aiMap, setAiMap] = useState<Record<number, { pricing_health?: string; flag?: string }>>(
    {},
  );
  const [selected, setSelected] = useState<number[]>([]);
  const [pageStats, setPageStats] = useState({ amount: 0, total: 0 });

  const status = ["draft", "sent", "won", "lost"].includes(scene) ? scene : undefined;

  const tableParams = useMemo(() => {
    const p: Record<string, unknown> = { scene };
    if (customerId) p.customer_id = customerId;
    if (q) p.q = q;
    if (includeAi) p.include_ai = true;
    return p;
  }, [scene, customerId, q, includeAi]);

  const loadStats = async () => {
    try {
      const resp = await getQuotationStats();
      setStats(resp.data.data);
    } catch {
      // 页面主列表加载即可，统计失败不阻塞操作。
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const apiStatus = ["draft", "sent", "won", "lost"].includes(scene) ? scene : undefined;
  const queryParams: Record<string, unknown> = {
    scene,
    page: 1,
    page_size: 20,
    sort_by: "updated_at",
    sort_order: "desc",
  };
  if (apiStatus) queryParams.status = apiStatus;
  if (customerId) queryParams.customer_id = customerId;
  if (q) queryParams.q = q;
  if (includeAi) queryParams.include_ai = true;

  const query = useApiQuery<
    PageData<Quotation> & { ai?: Record<number, { pricing_health?: string; flag?: string }> }
  >(["quotations", scene, customerId, q, includeAi], "/quotations", queryParams, {
    staleTime: 30 * 1000,
    keepPreviousData: true,
  });

  // Update aiMap when query data changes
  useEffect(() => {
    if (query.data?.ai) {
      setAiMap(query.data.ai as Record<number, { pricing_health?: string; flag?: string }>);
    }
  }, [query.data?.ai]);

  // Update pageStats when list changes
  useEffect(() => {
    const list = query.data?.list || [];
    if (scene === "expiring" || scene === "expired") {
      const filtered = list.filter(
        (item) => getDueMeta(item.valid_until, item.status).scene === scene,
      );
      setPageStats({
        amount: filtered.reduce((sum, item) => sum + Number(item.total_amount || 0), 0),
        total: filtered.length,
      });
    } else {
      setPageStats({
        amount: list.reduce((sum, item) => sum + Number(item.total_amount || 0), 0),
        total: query.data?.total || 0,
      });
    }
  }, [query.data?.list, query.data?.total, scene]);

  const batchDeleteMut = useApiMutation("post", () => "/quotations/batch-delete", {
    invalidateKeys: [["quotations"]],
    onSuccess: () => {
      message.success("已批量删除");
      setSelected([]);
    },
    onError: (e) => message.error(getApiErrorMessage(e, "删除失败")),
  });

  const handleBatchDelete = () => {
    batchDeleteMut.mutate({ ids: selected } as never);
  };

  const duplicateMut = useApiMutation<{ id: number }, number>(
    "post",
    (id) => `/quotations/${id}/duplicate`,
    {
      invalidateKeys: [["quotations"]],
      onSuccess: (data) => {
        message.success("已复制为新报价");
        navigate(`/sales/quotations/${(data as unknown as { id: number }).id}/edit`);
      },
      onError: (e) => message.error(getApiErrorMessage(e, "复制失败")),
    },
  );

  const handleDuplicate = (record: Quotation) => {
    duplicateMut.mutate(record.id);
  };

  const sendMut = useApiMutation("put", (id: number) => `/quotations/${id}/send`, {
    invalidateKeys: [["quotations"]],
    onSuccess: () => message.success("已标记为已发送"),
    onError: (e) => message.error(getApiErrorMessage(e, "发送失败")),
  });

  const handleSend = (record: Quotation) => {
    sendMut.mutate(record.id);
  };

  const convertMut = useApiMutation("post", (id: number) => `/quotations/${id}/convert-to-order`, {
    invalidateKeys: [["quotations"]],
    onSuccess: () => message.success("已转为订单"),
    onError: (e) => message.error(getApiErrorMessage(e, "转换失败")),
  });

  const handleConvert = (record: Quotation) => {
    convertMut.mutate(record.id);
  };

  const deleteMut = useApiMutation("delete", (id: number) => `/quotations/${id}`, {
    invalidateKeys: [["quotations"]],
    onSuccess: () => message.success("已删除"),
    onError: (e) => message.error(getApiErrorMessage(e, "删除失败")),
  });

  const handleDelete = (record: Quotation) => {
    deleteMut.mutate(record.id);
  };

  const handleSearch = () => {
    queryClient.invalidateQueries({ queryKey: ["quotations"] });
    loadStats();
  };

  const sceneCount = (key: QuoteScene) => {
    if (!stats) return undefined;
    if (key === "all") return stats.total;
    if (key === "expiring") return stats.expiring_soon;
    if (key === "expired") return stats.expired;
    return stats[key];
  };

  const columns: ProColumns<Quotation>[] = [
    {
      title: "#",
      width: 45,
      fixed: "left",
      render: (_: unknown, __: Quotation, index: number) => index + 1,
    },
    {
      title: "报价单号",
      dataIndex: "quotation_no",
      fixed: "left",
      width: 160,
      render: (_: unknown, r: Quotation) => (
        <Typography.Link strong onClick={() => navigate(`/sales/quotations/${r.id}`)}>
          {r.quotation_no || r.title || `#${r.id}`}
        </Typography.Link>
      ),
    },
    {
      title: "客户名称",
      dataIndex: "customer_name",
      width: 160,
      render: (_: unknown, r: Quotation) =>
        r.customer_name ? (
          <Typography.Link onClick={() => navigate(`/customers/${r.customer_id}`)}>
            {r.customer_name}
          </Typography.Link>
        ) : (
          <CustomerLink id={r.customer_id} />
        ),
    },
    {
      title: "金额",
      dataIndex: "total_amount",
      width: 120,
      sorter: (a: unknown, b: unknown) =>
        Number((a as Quotation).total_amount || 0) - Number((b as Quotation).total_amount || 0),
      render: (_: unknown, r: Quotation) => money(r.total_amount),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      sorter: (a: unknown, b: unknown) =>
        ((a as Quotation).status || "").localeCompare((b as Quotation).status || ""),
      render: (_: unknown, r: Quotation) => (
        <>
          {statusDot(ERP_STATUS_DOT[r.status] || "#d9d9d9")}
          <SalesStatusTag value={r.status} />
        </>
      ),
    },
    {
      title: "有效期",
      dataIndex: "valid_until",
      width: 130,
      sorter: (a: unknown, b: unknown) =>
        ((a as Quotation).valid_until || "").localeCompare((b as Quotation).valid_until || ""),
      render: (_: unknown, r: Quotation) => {
        const due = getDueMeta(r.valid_until, r.status);
        return <StatusTag status={due.text} tone={due.tone} />;
      },
    },
    {
      title: "AI",
      width: 90,
      render: (_: unknown, record: Quotation) => (
        <AIInlineBadge
          riskLevel={
            aiMap[record.id]?.pricing_health === "poor"
              ? "high"
              : aiMap[record.id]?.pricing_health === "fair"
                ? "medium"
                : "low"
          }
          flag={aiMap[record.id]?.flag}
        />
      ),
    },
    {
      title: "下一步",
      width: 100,
      render: (_: unknown, record: Quotation) => {
        const due = getDueMeta(record.valid_until, record.status);
        if (record.status === "draft")
          return <StatusTag status="发送报价" tone="info" icon={<SendOutlined />} />;
        if (record.status === "sent" && due.scene === "expired")
          return <StatusTag status="重新报价" tone="danger" />;
        if (record.status === "sent")
          return <StatusTag status="跟进转单" tone="success" icon={<FileDoneOutlined />} />;
        if (record.status === "won") return <StatusTag status="订单执行" tone="success" />;
        return <Tag>复盘原因</Tag>;
      },
    },
    {
      title: "操作",
      width: 60,
      fixed: "right",
      render: (_: unknown, record: Quotation) => {
        const items: MenuProps["items"] = [
          {
            key: "view",
            icon: <FileDoneOutlined />,
            label: "查看详情",
            onClick: () => navigate(`/sales/quotations/${record.id}`),
          },
          ...(record.status === "draft"
            ? [
                {
                  key: "send",
                  icon: <SendOutlined />,
                  label: "标记发送",
                  onClick: () => handleSend(record),
                },
              ]
            : []),
          {
            key: "pdf",
            icon: <DownloadOutlined />,
            label: "智能 PDF",
            onClick: () =>
              downloadQuotationPDF(
                record.id,
                `QUOTATION_${record.quotation_no || record.id}.pdf`,
              ).catch(() => message.error("下载失败")),
          },
          {
            key: "copy",
            icon: <CopyOutlined />,
            label: "复制",
            onClick: () => handleDuplicate(record),
          },
          ...(record.status !== "won"
            ? [
                {
                  key: "convert",
                  icon: <ShoppingCartOutlined />,
                  label: "转订单",
                  onClick: () => {
                    Modal.confirm({
                      title: "转为销售订单?",
                      content: `将报价 ${record.quotation_no || `#${record.id}`} 转为销售订单`,
                      onOk: () => handleConvert(record),
                    });
                  },
                },
              ]
            : []),
          { type: "divider" as const },
          {
            key: "delete",
            icon: <DeleteOutlined />,
            label: "删除",
            danger: true,
            onClick: () => {
              Modal.confirm({
                title: "确定删除?",
                content: `删除报价 ${record.quotation_no || `#${record.id}`}`,
                onOk: () => handleDelete(record),
              });
            },
          },
        ];
        return (
          <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
            <Button size="small" icon={<EllipsisOutlined />} type="text" />
          </Dropdown>
        );
      },
    },
  ];

  return (
    <SalesModuleShell
      title="报价工作台"
      subtitle="处理待发送、临期、已发送待跟进报价，并推动报价转订单"
      activeKey="quotations"
      extra={<SalesQuickActions />}
    >
      <MetricBand
        items={[
          { title: "报价总数", value: stats?.total ?? pageStats.total, suffix: "张" },
          {
            title: "报价总额",
            value: stats?.total_amount ?? pageStats.amount,
            prefix: "¥",
            precision: 0,
          },
          { title: "即将过期", value: stats?.expiring_soon ?? 0, suffix: "张" },
          { title: "已过期", value: stats?.expired ?? 0, suffix: "张" },
          { title: "成交金额", value: stats?.won_amount ?? 0, prefix: "¥", precision: 0 },
          { title: "转订单率", value: stats?.quote_to_order_rate ?? 0, suffix: "%", precision: 1 },
        ]}
      />

      <Card size="small" className="sales-erp-toolbar" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/sales/quotations/new")}
          >
            新建报价
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleSearch}>
            刷新
          </Button>
          <Input.Search
            allowClear
            placeholder="搜索客户 / 报价单 / 产品"
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              if (!event.target.value) {
                setQ("");
              }
            }}
            onSearch={(value) => {
              setQ(value);
            }}
            style={{ width: 280 }}
          />
          <div style={{ width: 280 }}>
            <CustomerSelect value={customerId} onChange={setCustomerId} />
          </div>
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 128 }}
            value={status}
            onChange={(next) => {
              setScene((next as QuoteScene) || "all");
            }}
            options={[
              { value: "draft", label: "草稿" },
              { value: "sent", label: "已发送" },
              { value: "won", label: "成交" },
              { value: "lost", label: "丢失" },
            ]}
          />
          {selected.length > 0 ? (
            <Popconfirm title="确定批量删除选中的报价?" onConfirm={handleBatchDelete}>
              <Button danger icon={<DeleteOutlined />}>
                删除 {selected.length}
              </Button>
            </Popconfirm>
          ) : null}
          <Space>
            <Switch checked={includeAi} onChange={setIncludeAi} size="small" />
            <span style={{ fontSize: 13 }}>AI</span>
          </Space>
        </Space>
      </Card>

      <Card
        size="small"
        className="sales-erp-table-card"
        title={
          <Space size={8} wrap>
            <Typography.Text strong>报价单据</Typography.Text>
            <Typography.Text type="secondary">{pageStats.total} 张</Typography.Text>
            {selected.length > 0 && <StatusTag status={`已选 ${selected.length}`} tone="info" />}
          </Space>
        }
      >
        <Tabs
          activeKey={scene}
          onChange={(key) => {
            setScene(key as QuoteScene);
          }}
          items={(Object.keys(SCENE_LABELS) as QuoteScene[]).map((key) => ({
            key,
            label: (
              <Space size={6}>
                <span>{SCENE_LABELS[key]}</span>
                {sceneCount(key) !== undefined && (
                  <StatusTag
                    status={String(sceneCount(key))}
                    tone={key === "expired" ? "danger" : key === "expiring" ? "warning" : "neutral"}
                  />
                )}
              </Space>
            ),
          }))}
        />
        <ProTable<Quotation>
          rowKey="id"
          size="small"
          bordered
          search={false}
          options={{ reload: handleSearch, density: true, setting: true }}
          rowClassName={erpRowClass}
          rowSelection={{
            selectedRowKeys: selected,
            onChange: (keys) => setSelected(keys as number[]),
          }}
          scroll={{ x: "max-content" }}
          dataSource={query.data?.list || []}
          columns={columns}
          loading={query.isLoading || query.isFetching}
          pagination={{
            total: pageStats.total,
            showSizeChanger: true,
            onChange: () => query.refetch(),
          }}
        />
      </Card>
    </SalesModuleShell>
  );
}
