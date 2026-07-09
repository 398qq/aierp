import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { StatusTag } from "../../ui";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  StopOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { generateCustomerWorkQueue, getCustomerAIRecommendationSummary, getCustomerWorkQueue, submitCustomerRecommendationFeedback, updateCustomerRecommendationStatus, getApiErrorMessage } from "../../api";
import type { CustomerAIRecommendationSummary, CustomerAIWorkQueueItem, CustomerAIWorkQueuePage } from "../../types";
import CustomerModuleShell from "./CustomerModuleShell";

type StatusType = "open" | "in_progress" | "done" | "dismissed" | "all";

const STATUS_COLORS: Record<string, string> = {
  open: "blue",
  in_progress: "gold",
  done: "green",
  dismissed: "red",
  superseded: "default",
};

const STATUS_LABELS: Record<string, string> = {
  open: "待执行",
  in_progress: "进行中",
  done: "已完成",
  dismissed: "已驳回",
  superseded: "已替换",
};

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  return value.slice(0, 16).replace("T", " ");
};

export default function CustomerAIWorkbench() {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [status, setStatus] = useState<StatusType>("open");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [queue, setQueue] = useState<CustomerAIWorkQueuePage>({
    list: [],
    total: 0,
    page: 1,
    page_size: 20,
    status_stats: {},
  });
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<CustomerAIWorkQueueItem | null>(null);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summary, setSummary] = useState<CustomerAIRecommendationSummary | null>(null);
  const [feedbackForm] = Form.useForm();
  const navigate = useNavigate();

  const fetchQueue = async (nextPage = page, nextStatus = status) => {
    setLoading(true);
    try {
      const resp = await getCustomerWorkQueue({
        page: nextPage,
        page_size: pageSize,
        status: nextStatus,
      });
      setQueue(resp.data.data);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载AI工作队列失败")); } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue(page, status);
  }, [page, pageSize, status]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const resp = await generateCustomerWorkQueue({ replace_open: true });
      const generated = resp.data.data.generated || 0;
      const replaced = resp.data.data.replaced || 0;
      message.success(`生成完成：新增 ${generated} 条，替换 ${replaced} 条`);
      setPage(1);
      fetchQueue(1, status);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "生成队列失败")); } finally {
      setGenerating(false);
    }
  };

  const setRecommendationStatus = async (item: CustomerAIWorkQueueItem, nextStatus: Exclude<StatusType, "all">) => {
    try {
      await updateCustomerRecommendationStatus(item.id, { status: nextStatus });
      message.success("状态已更新");
      fetchQueue(page, status);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "状态更新失败")); }
  };

  const openFeedback = (item: CustomerAIWorkQueueItem) => {
    setFeedbackTarget(item);
    feedbackForm.setFieldsValue({ verdict: "adopted", usefulness: 4 });
    setFeedbackOpen(true);
  };

  const submitFeedback = async () => {
    if (!feedbackTarget) return;
    const values = await feedbackForm.validateFields();
    setSubmittingFeedback(true);
    try {
      await submitCustomerRecommendationFeedback(feedbackTarget.id, values);
      message.success("反馈已提交");
      setFeedbackOpen(false);
      setFeedbackTarget(null);
      fetchQueue(page, status);
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "反馈提交失败")); } finally {
      setSubmittingFeedback(false);
    }
  };

  const openSummary = async (customerId: number) => {
    setSummaryOpen(true);
    setSummaryLoading(true);
    try {
      const resp = await getCustomerAIRecommendationSummary(customerId);
      setSummary(resp.data.data);
    } catch {
      message.error("加载客户AI摘要失败");
      setSummary(null);
    } finally {
      setSummaryLoading(false);
    }
  };

  const statOpen = queue.status_stats.open || 0;
  const statProgress = queue.status_stats.in_progress || 0;
  const statDone = queue.status_stats.done || 0;
  const statDismissed = queue.status_stats.dismissed || 0;

  const topPriority = useMemo(() => queue.list[0]?.priority_score || 0, [queue.list]);

  const columns: ColumnsType<CustomerAIWorkQueueItem> = [
    {
      title: "客户",
      key: "customer_name",
      width: 200,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => navigate(`/customers/${r.customer_id}`)}>{r.customer_name}</a>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {r.customer_level || "-"} | {r.customer_industry || "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "建议动作",
      key: "title",
      width: 240,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{r.title}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.reason}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "优先级",
      dataIndex: "priority_score",
      key: "priority_score",
      width: 100,
      sorter: (a, b) => a.priority_score - b.priority_score,
      render: (v: number) => <StatusTag tone={v >= 75 ? "danger" : v >= 60 ? "warning" : "info"}>{v.toFixed(1)}</StatusTag>,
    },
    {
      title: "评分拆解",
      key: "score_parts",
      width: 220,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Typography.Text style={{ fontSize: 12 }}>
            风险 {r.snapshot.churn_risk_score ?? "-"} / 价值 {r.snapshot.value_score ?? "-"} / 紧急 {r.snapshot.urgency_score ?? "-"}
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            逾期跟进 {r.snapshot.overdue_followups ?? 0}，商机 {r.snapshot.open_opportunities ?? 0}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "状态",
      key: "status",
      width: 100,
      render: (_, r) => <StatusTag status={r.status} tone={STATUS_COLORS[r.status] || "neutral"} label={STATUS_LABELS[r.status] || r.status} />,
    },
    {
      title: "截止",
      dataIndex: "due_at",
      key: "due_at",
      width: 140,
      render: (v: string | null) => formatDate(v),
    },
    {
      title: "操作",
      key: "actions",
      width: 250,
      render: (_, r) => (
        <Space size={4} wrap>
          <Button size="small" onClick={() => openSummary(r.customer_id)}>摘要</Button>
          <Button size="small" onClick={() => setRecommendationStatus(r, "in_progress")}>执行</Button>
          <Button size="small" type="primary" onClick={() => setRecommendationStatus(r, "done")}>完成</Button>
          <Button size="small" danger onClick={() => setRecommendationStatus(r, "dismissed")}>驳回</Button>
          <Button size="small" onClick={() => openFeedback(r)}>反馈</Button>
        </Space>
      ),
    },
  ];

  return (
    <CustomerModuleShell
      title="客户AI工作队列"
      subtitle="按优先级推进下一步动作，闭环记录执行与反馈"
      extra={(
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchQueue(page, status)}>刷新</Button>
          <Button type="primary" loading={generating} onClick={handleGenerate}>生成建议</Button>
        </Space>
      )}
    >
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        <Col xs={24} sm={12} xl={4}><Card size="small"><Statistic title="待执行" value={statOpen} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={24} sm={12} xl={4}><Card size="small"><Statistic title="进行中" value={statProgress} /></Card></Col>
        <Col xs={24} sm={12} xl={4}><Card size="small"><Statistic title="已完成" value={statDone} prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col xs={24} sm={12} xl={4}><Card size="small"><Statistic title="已驳回" value={statDismissed} prefix={<StopOutlined />} /></Card></Col>
        <Col xs={24} sm={12} xl={4}><Card size="small"><Statistic title="最高优先级" value={topPriority} precision={1} /></Card></Col>
        <Col xs={24} sm={12} xl={4}>
          <Card size="small">
            <Space direction="vertical" size={4}>
              <Typography.Text type="secondary">状态筛选</Typography.Text>
              <Select
                value={status}
                onChange={(v) => {
                  setStatus(v as StatusType);
                  setPage(1);
                }}
                options={[
                  { value: "open", label: "待执行" },
                  { value: "in_progress", label: "进行中" },
                  { value: "done", label: "已完成" },
                  { value: "dismissed", label: "已驳回" },
                  { value: "all", label: "全部" },
                ]}
                style={{ width: "100%" }}
              />
            </Space>
          </Card>
        </Col>
      </Row>

      <Card bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={queue.list}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无建议，点击“生成建议”开始" /> }}
          pagination={{
            current: page,
            total: queue.total,
            pageSize,
            showSizeChanger: true,
            pageSizeOptions: ["10", "20", "50"],
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 1250 }}
        />
      </Card>

      <Modal
        title={`建议反馈${feedbackTarget ? ` - ${feedbackTarget.customer_name}` : ""}`}
        open={feedbackOpen}
        onCancel={() => setFeedbackOpen(false)}
        onOk={submitFeedback}
        confirmLoading={submittingFeedback}
      >
        <Form form={feedbackForm} layout="vertical">
          <Form.Item name="verdict" label="处理结论" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "adopted", label: "采纳" },
                { value: "partial", label: "部分采纳" },
                { value: "rejected", label: "拒绝" },
              ]}
            />
          </Form.Item>
          <Form.Item name="usefulness" label="有用程度(1-5)">
            <Select options={[1, 2, 3, 4, 5].map((v) => ({ value: v, label: `${v}` }))} />
          </Form.Item>
          <Form.Item name="outcome" label="结果">
            <Select
              allowClear
              options={[
                { value: "improved", label: "改善" },
                { value: "neutral", label: "中性" },
                { value: "worse", label: "变差" },
              ]}
            />
          </Form.Item>
          <Form.Item name="comment" label="反馈说明">
            <Input.TextArea rows={4} placeholder="补充本次建议的执行结果和业务观察" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="客户AI摘要"
        width={560}
        open={summaryOpen}
        onClose={() => setSummaryOpen(false)}
      >
        {summaryLoading ? (
          <Card loading />
        ) : !summary ? (
          <Empty description="暂无摘要" />
        ) : (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Card size="small">
              <Typography.Text strong>{summary.customer.name}</Typography.Text>
              <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
                {summary.customer.level || "-"} | {summary.customer.industry || "-"} | 负责人: {summary.customer.owner || "-"}
              </div>
            </Card>

            <Row gutter={[8, 8]}>
              <Col span={8}><Card size="small"><Statistic title="健康分" value={summary.snapshot.health_score || 0} /></Card></Col>
              <Col span={8}><Card size="small"><Statistic title="流失风险" value={summary.snapshot.churn_risk_score || 0} /></Card></Col>
              <Col span={8}><Card size="small"><Statistic title="价值评分" value={summary.snapshot.value_score || 0} /></Card></Col>
            </Row>

            <Card size="small" title="下一步动作">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                {summary.next_actions.map((item) => (
                  <Card key={item.id} size="small" type="inner" title={item.title}>
                    <Typography.Paragraph style={{ marginBottom: 8 }}>{item.reason}</Typography.Paragraph>
                    <Space>
                      <StatusTag tone="info">优先级 {item.priority_score.toFixed(1)}</StatusTag>
                      <StatusTag status={item.status} tone={STATUS_COLORS[item.status] || "neutral"} label={STATUS_LABELS[item.status] || item.status} />
                      <StatusTag>截止 {formatDate(item.due_at)}</StatusTag>
                    </Space>
                  </Card>
                ))}
                {!summary.next_actions.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无下一步动作" />}
              </Space>
            </Card>
          </Space>
        )}
      </Drawer>
    </CustomerModuleShell>
  );
}
