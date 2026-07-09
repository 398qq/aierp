/**
 * 客户跟进记录列表页面
 * 路由: /customers/:customerId/follow-ups
 */
import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { useParams, useNavigate } from "react-router-dom";
import { App, Table, Button, Space, Spin, Card, Popconfirm, Empty, Modal, DatePicker, Input, Select, Tag, Typography } from "antd";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, CalendarOutlined, CheckCircleOutlined, EditOutlined, DeleteOutlined, PlusOutlined, SyncOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { TablePaginationConfig } from "antd/es/table/interface";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { getFollowUps, deleteFollowUp, updateFollowUp, getApiErrorMessage } from "../../api";
import type { FollowUp } from "../../types";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";

const { Text } = Typography;

type DueFilter = "all" | "overdue" | "today" | "upcoming" | "closed" | "unscheduled";

const OPEN_STATUSES = new Set(["planned", "in_progress", "", null]);
const TERMINAL_STATUSES = new Set(["completed", "cancelled"]);

function getDueFilter(record: FollowUp): DueFilter {
  if (record.status && TERMINAL_STATUSES.has(record.status)) return "closed";
  if (!record.planned_at) return "unscheduled";
  const planned = dayjs(record.planned_at);
  const today = dayjs();
  if (planned.isBefore(today, "day")) return "overdue";
  if (planned.isSame(today, "day")) return "today";
  return "upcoming";
}

function dueLabel(bucket: DueFilter) {
  const labels: Record<DueFilter, string> = {
    all: "全部",
    overdue: "逾期",
    today: "今日",
    upcoming: "未来",
    closed: "已关闭",
    unscheduled: "未排期",
  };
  return labels[bucket];
}

export default function FollowUpList() {
  const { message } = App.useApp();
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const [allData, setAllData] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [rescheduleRecord, setRescheduleRecord] = useState<FollowUp | null>(null);
  const [rescheduleAt, setRescheduleAt] = useState<Dayjs | null>(null);
  const [reschedulePickerOpen, setReschedulePickerOpen] = useState(false);
  const [rescheduling, setRescheduling] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [updateRecord, setUpdateRecord] = useState<FollowUp | null>(null);
  const [updateContent, setUpdateContent] = useState("");
  const [updateResult, setUpdateResult] = useState("");
  const [updateStatus, setUpdateStatus] = useState("in_progress");
  const [updateNextAt, setUpdateNextAt] = useState<Dayjs | null>(null);
  const [updating, setUpdating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [priorityFilter, setPriorityFilter] = useState<string | undefined>();
  const [dueFilter, setDueFilter] = useState<DueFilter>("all");

  const custId = Number(customerId);

  // 加载跟进记录
  const load = async (options: { silent?: boolean } = {}) => {
    const silent = options.silent === true;
    if (!silent) {
      setLoading(true);
    }
    try {
      const resp = await getFollowUps(custId);
      const result = resp.data;
      if (Array.isArray(result.data)) {
        setAllData(result.data);
      } else if (result.data && typeof result.data === "object") {
        const d = result.data as { list?: FollowUp[]; items?: FollowUp[] };
        setAllData(d.list || d.items || []);
      } else {
        setAllData([]);
      }
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "加载跟进记录失败")); } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (custId && !isNaN(custId)) {
      load();
    }
  }, [custId]);

  // 处理分页变化
  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1);
    setPageSize(pagination.pageSize || 10);
  };

  const filteredData = useMemo(() => {
    return [...allData]
      .filter((item) => !statusFilter || item.status === statusFilter)
      .filter((item) => !priorityFilter || item.priority === priorityFilter)
      .filter((item) => dueFilter === "all" || getDueFilter(item) === dueFilter)
      .sort((a, b) => {
        const aBucket = getDueFilter(a);
        const bBucket = getDueFilter(b);
        const weight: Record<DueFilter, number> = {
          overdue: 0,
          today: 1,
          upcoming: 2,
          unscheduled: 3,
          closed: 4,
          all: 5,
        };
        if (weight[aBucket] !== weight[bBucket]) return weight[aBucket] - weight[bBucket];
        return dayjs(a.planned_at || a.created_at).valueOf() - dayjs(b.planned_at || b.created_at).valueOf();
      });
  }, [allData, statusFilter, priorityFilter, dueFilter]);

  const summary = useMemo(() => {
    const open = allData.filter((item) => OPEN_STATUSES.has(item.status || "")).length;
    const overdue = allData.filter((item) => getDueFilter(item) === "overdue").length;
    const today = allData.filter((item) => getDueFilter(item) === "today").length;
    const completed = allData.filter((item) => item.status === "completed").length;
    const high = allData.filter((item) => item.priority === "high").length;
    return { open, overdue, today, completed, high };
  }, [allData]);

  // 删除跟进记录
  const handleDelete = async (followupId: number) => {
    try {
      await deleteFollowUp(custId, followupId);
      message.success("删除成功");
      load();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "删除失败")); }
  };

  const handleComplete = async (followupId: number) => {
    try {
      await updateFollowUp(custId, followupId, {
        status: "completed",
        completed_at: new Date().toISOString(),
      });
      message.success("已完成");
      load();
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "操作失败")); }
  };

  const openReschedule = (record: FollowUp) => {
    setRescheduleRecord(record);
    setRescheduleAt(record.planned_at ? dayjs(record.planned_at) : dayjs().add(1, "day").hour(9).minute(0).second(0));
    setReschedulePickerOpen(false);
    setRescheduleOpen(true);
  };

  const closeReschedule = () => {
    flushSync(() => setReschedulePickerOpen(false));
    setRescheduleOpen(false);
  };

  const handleReschedule = async () => {
    if (!rescheduleRecord || !rescheduleAt) {
      message.warning("请选择新的跟进时间");
      return;
    }
    flushSync(() => setReschedulePickerOpen(false));
    setRescheduling(true);
    try {
      await updateFollowUp(custId, rescheduleRecord.id, {
        status: "planned",
        planned_at: rescheduleAt.format("YYYY-MM-DD HH:mm:ss"),
      });
      message.success("跟进时间已更新");
      flushSync(() => setRescheduling(false));
      closeReschedule();
      load({ silent: true });
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "更新跟进时间失败")); } finally {
      setRescheduling(false);
    }
  };

  const openUpdate = (record: FollowUp) => {
    setUpdateRecord(record);
    setUpdateContent("");
    setUpdateResult("");
    setUpdateStatus(record.status || "in_progress");
    setUpdateNextAt(record.planned_at ? dayjs(record.planned_at) : null);
    setUpdateOpen(true);
  };

  const closeUpdate = () => {
    setUpdateOpen(false);
    setUpdateRecord(null);
    setUpdateContent("");
    setUpdateResult("");
    setUpdateStatus("in_progress");
    setUpdateNextAt(null);
  };

  const appendUpdateText = (current: string | null, label: string, next: string) => {
    const text = next.trim();
    if (!text) return current || "";
    const stamp = dayjs().format("YYYY-MM-DD HH:mm");
    return [current, `[${stamp} ${label}]\n${text}`].filter(Boolean).join("\n\n");
  };

  const handleUpdateProgress = async () => {
    if (!updateRecord) return;
    if (!updateContent.trim() && !updateResult.trim() && updateStatus === updateRecord.status && !updateNextAt) {
      message.warning("请填写本次更新内容、结果或下一次跟进时间");
      return;
    }
    setUpdating(true);
    try {
      const payload: Record<string, unknown> = {
        status: updateStatus,
        content: appendUpdateText(updateRecord.content, "更新", updateContent),
        result: appendUpdateText(updateRecord.result, "结果", updateResult),
      };
      if (updateNextAt && updateStatus !== "completed") {
        payload.planned_at = updateNextAt.format("YYYY-MM-DD HH:mm:ss");
      }
      if (updateStatus === "completed") {
        payload.completed_at = dayjs().format("YYYY-MM-DD HH:mm:ss");
      }
      await updateFollowUp(custId, updateRecord.id, payload);
      message.success("跟进已更新");
      flushSync(() => setUpdating(false));
      closeUpdate();
      load({ silent: true });
    } catch (e: unknown) { message.error(getApiErrorMessage(e, "更新跟进失败")); } finally {
      setUpdating(false);
    }
  };

  // 跳转到编辑页面
  const handleEdit = (followupId: number) => {
    navigate(`/customers/${custId}/follow-ups/${followupId}/edit`);
  };

  // 跳转到新建页面
  const handleCreate = () => {
    navigate(`/customers/${custId}/follow-ups/new`);
  };

  // 表格列定义
  const columns: ColumnsType<FollowUp> = [
    {
      title: "方式",
      dataIndex: "method",
      key: "method",
      width: 100,
      render: (method: string | null) => <FollowUpMethodTag method={method} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: string | null) => <FollowUpStatusTag status={status} />,
    },
    {
      title: "内容",
      dataIndex: "content",
      key: "content",
      ellipsis: true,
      render: (content: string) => content || "-",
    },
    {
      title: "结果",
      dataIndex: "result",
      key: "result",
      ellipsis: true,
      render: (result: string) => result || "-",
    },
    {
      title: "计划时间",
      dataIndex: "planned_at",
      key: "planned_at",
      width: 120,
      render: (planned_at: string, record) => {
        const bucket = getDueFilter(record);
        const color = bucket === "overdue" ? "red" : bucket === "today" ? "orange" : bucket === "upcoming" ? "blue" : "default";
        return (
          <Space direction="vertical" size={0}>
            <Text>{planned_at ? planned_at.slice(0, 16) : "-"}</Text>
            <Tag color={color}>{dueLabel(bucket)}</Tag>
          </Space>
        );
      },
    },
    {
      title: "完成时间",
      dataIndex: "completed_at",
      key: "completed_at",
      width: 120,
      render: (completed_at: string) => completed_at ? completed_at.slice(0, 16) : "-",
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (priority: string | null) => <FollowUpPriorityTag priority={priority} />,
    },
    {
      title: "负责人",
      dataIndex: "assigned_to",
      key: "assigned_to",
      width: 100,
      render: (assigned_to: string) => assigned_to || "-",
    },
    {
      title: "操作",
      key: "actions",
      width: 260,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
          {record.status === "in_progress" && (
            <Button type="link" size="small" icon={<SyncOutlined />} onClick={() => openUpdate(record)}>
              更新跟进
            </Button>
          )}
          {record.status !== "completed" && (
            <>
              <Button type="link" size="small" icon={<CalendarOutlined />} onClick={() => openReschedule(record)}>
                改期
              </Button>
              <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleComplete(record.id)}>
                完成
              </Button>
            </>
          )}
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record.id)}>
            编辑
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 无效的客户ID
  if (!customerId || isNaN(custId)) {
    return (
      <Card>
        <Empty description="请先选择客户" />
      </Card>
    );
  }

  // 计算当前页数据
  const startIndex = (page - 1) * pageSize;
  const currentData = filteredData.slice(startIndex, startIndex + pageSize);

  return (
    <div className="followup-ledger">
      <div className="followup-ledger-command">
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/customers/${custId}`)}>
            返回客户详情
          </Button>
          <Button icon={<SyncOutlined />} onClick={() => load()} loading={loading}>
            刷新
          </Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建跟进
        </Button>
      </div>

      <div className="followup-ledger-filters">
        <Space wrap size={8}>
          <Select
            allowClear
            placeholder="状态"
            style={{ width: 130 }}
            value={statusFilter}
            onChange={(value) => { setStatusFilter(value); setPage(1); }}
            options={[
              { value: "planned", label: "计划中" },
              { value: "in_progress", label: "进行中" },
              { value: "completed", label: "已完成" },
              { value: "cancelled", label: "已取消" },
            ]}
          />
          <Select
            allowClear
            placeholder="优先级"
            style={{ width: 120 }}
            value={priorityFilter}
            onChange={(value) => { setPriorityFilter(value); setPage(1); }}
            options={[
              { value: "high", label: "高" },
              { value: "medium", label: "中" },
              { value: "low", label: "低" },
            ]}
          />
          <Select
            value={dueFilter}
            style={{ width: 130 }}
            onChange={(value) => { setDueFilter(value); setPage(1); }}
            options={[
              { value: "all", label: "全部到期" },
              { value: "overdue", label: "逾期" },
              { value: "today", label: "今日" },
              { value: "upcoming", label: "未来" },
              { value: "unscheduled", label: "未排期" },
              { value: "closed", label: "已关闭" },
            ]}
          />
          <Button onClick={() => { setStatusFilter(undefined); setPriorityFilter(undefined); setDueFilter("all"); setPage(1); }}>重置</Button>
        </Space>
      </div>

      <div className="followup-ledger-metrics">
        <div><span>全部记录</span><strong>{allData.length}</strong></div>
        <div><span>未关闭</span><strong>{summary.open}</strong></div>
        <div className="is-danger"><span>逾期</span><strong>{summary.overdue}</strong></div>
        <div className="is-warning"><span>今日</span><strong>{summary.today}</strong></div>
        <div><span>高优先级</span><strong>{summary.high}</strong></div>
        <div><span>已完成</span><strong>{summary.completed}</strong></div>
      </div>

      {loading && <Spin style={{ display: "block", margin: "100px auto" }} />}

      {!loading && filteredData.length === 0 && (
        <Card>
          <Empty description={allData.length ? "没有符合筛选条件的跟进记录" : "暂无跟进记录"}>
            <Button type="primary" onClick={handleCreate}>新建跟进</Button>
          </Empty>
        </Card>
      )}

      {!loading && filteredData.length > 0 && (
        <Table
          className="erp-table followup-ledger-table"
          columns={columns}
          dataSource={currentData}
          rowKey="id"
          loading={loading}
          bordered
          size="small"
          rowClassName={(record) => getDueFilter(record) === "overdue" ? "followup-row-overdue" : ""}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: filteredData.length,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 1000 }}
        />
      )}

      <Modal
        title="更新跟进时间"
        open={rescheduleOpen}
        okText="保存"
        cancelText="取消"
        confirmLoading={rescheduling}
        onOk={handleReschedule}
        onCancel={closeReschedule}
        afterOpenChange={(open) => {
          if (!open) {
            setRescheduleRecord(null);
            setRescheduleAt(null);
            setReschedulePickerOpen(false);
          }
        }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>{rescheduleRecord?.content || "选择新的计划跟进时间"}</div>
          <DatePicker
            showTime
            format="YYYY-MM-DD HH:mm"
            value={rescheduleAt}
            onChange={setRescheduleAt}
            open={reschedulePickerOpen}
            onOpenChange={setReschedulePickerOpen}
            getPopupContainer={(trigger) => trigger.parentElement || document.body}
            style={{ width: "100%" }}
          />
        </Space>
      </Modal>

      <Modal
        title="更新进行中的跟进"
        open={updateOpen}
        okText="保存更新"
        cancelText="取消"
        confirmLoading={updating}
        onOk={handleUpdateProgress}
        onCancel={closeUpdate}
        width={640}
      >
        <Space direction="vertical" style={{ width: "100%" }} size={12}>
          <Input.TextArea
            rows={3}
            value={updateContent}
            onChange={(event) => setUpdateContent(event.target.value)}
            placeholder="记录本次新增跟进内容，例如：已电话沟通客户，确认需求型号和数量"
          />
          <Input.TextArea
            rows={3}
            value={updateResult}
            onChange={(event) => setUpdateResult(event.target.value)}
            placeholder="记录本次跟进结果，例如：客户要求明天补发报价，预计本周确认"
          />
          <Select
            value={updateStatus}
            onChange={setUpdateStatus}
            style={{ width: "100%" }}
            options={[
              { value: "in_progress", label: "仍在进行中" },
              { value: "planned", label: "转为计划中" },
              { value: "completed", label: "已完成" },
              { value: "cancelled", label: "已取消" },
            ]}
          />
          {updateStatus !== "completed" && (
            <DatePicker
              showTime
              format="YYYY-MM-DD HH:mm"
              value={updateNextAt}
              onChange={setUpdateNextAt}
              style={{ width: "100%" }}
              placeholder="下一次跟进时间"
            />
          )}
        </Space>
      </Modal>
    </div>
  );
}
