/**
 * 客户跟进记录列表页面
 * 路由: /customers/:customerId/follow-ups
 *
 * 服务端分页/筛选/计数版本——useApiQuery + 受控 ProTable
 * （详见 docs/frontend/followup-list-migration-plan.md）。
 */
import { useEffect, useState } from "react";

import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { App, Button, Space, Spin, Card, Popconfirm, Empty, Modal, DatePicker, Input, Select, Tag, Typography } from "antd";
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { StatusTag } from "../../ui";
import { ArrowLeftOutlined, CalendarOutlined, CheckCircleOutlined, EditOutlined, DeleteOutlined, PlusOutlined, SyncOutlined } from "@ant-design/icons";

import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { deleteFollowUp, updateFollowUp, getApiErrorMessage, type FollowUpListResp } from "../../api";
import type { FollowUp } from "../../types";
import { useApiQuery, useQueryClient } from "@/lib/queries";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";

const { Text } = Typography;

type DueBucket = "overdue" | "today" | "upcoming" | "unscheduled" | "closed";
type DueFilter = "all" | DueBucket;

const BUCKET_LABEL: Record<DueBucket, string> = {
  overdue: "逾期",
  today: "今日",
  upcoming: "未来",
  unscheduled: "未排期",
  closed: "已关闭",
};

const BUCKET_COLOR: Record<DueBucket, string> = {
  overdue: "red",
  today: "orange",
  upcoming: "blue",
  unscheduled: "default",
  closed: "default",
};

const PAGE_SIZE = 20;

export default function FollowUpList() {
  const { message } = App.useApp();
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

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

  // Server-side filter / pagination state
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [priorityFilter, setPriorityFilter] = useState<string | undefined>();
  const [dueFilter, setDueFilter] = useState<DueFilter>("all");

  const custId = Number(customerId);

  // Build query params for backend
  const apiParams: Record<string, unknown> = {
    page,
    page_size: PAGE_SIZE,
  };
  if (statusFilter) apiParams.status = statusFilter;
  if (priorityFilter) apiParams.priority = priorityFilter;
  if (dueFilter !== "all") apiParams.due_bucket = dueFilter;

  const query = useApiQuery<FollowUpListResp>(
    [
      "follow-ups",
      custId,
      page,
      statusFilter ?? "",
      priorityFilter ?? "",
      dueFilter,
    ],
    `/customers/${custId}/follow-ups`,
    apiParams,
    {
      enabled: !!customerId && !Number.isNaN(custId),
      staleTime: 30 * 1000,
    },
  );

  const list = query.data?.list ?? [];
  const total = query.data?.total ?? 0;
  const counts = query.data?.counts;

  // ------- Mutations (invalidate refetch instead of refetch) -------
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["follow-ups", custId] });

  const handleDelete = async (followupId: number) => {
    try {
      await deleteFollowUp(custId, followupId);
      message.success("删除成功");
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "删除失败"));
    }
  };

  const handleComplete = async (followupId: number) => {
    try {
      await updateFollowUp(custId, followupId, {
        status: "completed",
        completed_at: new Date().toISOString(),
      });
      message.success("已完成");
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "操作失败"));
    }
  };

  const openReschedule = (record: FollowUp) => {
    setRescheduleRecord(record);
    setRescheduleAt(record.planned_at ? dayjs(record.planned_at) : dayjs().add(1, "day").hour(9).minute(0).second(0));
    setReschedulePickerOpen(false);
    setRescheduleOpen(true);
  };

  const closeReschedule = () => {
    setReschedulePickerOpen(false);
    setRescheduleOpen(false);
  };

  const handleReschedule = async () => {
    if (!rescheduleRecord || !rescheduleAt) {
      message.warning("请选择新的跟进时间");
      return;
    }
    setReschedulePickerOpen(false);
    setRescheduling(true);
    try {
      await updateFollowUp(custId, rescheduleRecord.id, {
        status: "planned",
        planned_at: rescheduleAt.format("YYYY-MM-DD HH:mm:ss"),
      });
      message.success("跟进时间已更新");
      setRescheduling(false);
      closeReschedule();
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "更新跟进时间失败"));
    } finally {
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
    if (searchParams.has("update")) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("update");
      setSearchParams(nextParams, { replace: true });
    }
  };

  // ?update=<id> deep link: open update modal for that record once data is loaded
  useEffect(() => {
    if (updateOpen) return;
    const updateId = Number(searchParams.get("update"));
    if (!updateId || query.isLoading || !query.data) return;
    const record = list.find((item) => item.id === updateId);
    if (!record) {
      message.warning("未找到要更新的跟进记录");
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("update");
      setSearchParams(nextParams, { replace: true });
      return;
    }
    if (record.status !== "in_progress") {
      message.warning("只有进行中的跟进可以更新进展");
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("update");
      setSearchParams(nextParams, { replace: true });
      return;
    }
    openUpdate(record);
  }, [list, query.isLoading, query.data, message, searchParams, setSearchParams, updateOpen]);

  const appendUpdateText = (current: string | null, label: string, next: string) => {
    const text = next.trim();
    if (!text) return current || "";
    const stamp = dayjs().format("YYYY-MM-DD HH:mm");
    return [current, `[${stamp} ${label}]\n${text}`].filter(Boolean).join("\n\n");
  };

  const handleUpdateProgress = async () => {
    if (!updateRecord) return;
    if (
      !updateContent.trim() && !updateResult.trim() &&
      updateStatus === updateRecord.status && !updateNextAt
    ) {
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
      setUpdating(false);
      closeUpdate();
      invalidate();
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, "更新跟进失败"));
    } finally {
      setUpdating(false);
    }
  };

  const handleEdit = (followupId: number) => {
    navigate(`/customers/${custId}/follow-ups/${followupId}/edit`);
  };
  const handleCreate = () => {
    navigate(`/customers/${custId}/follow-ups/new`);
  };

  const columns: ProColumns<FollowUp>[] = [
    {
      title: "方式",
      dataIndex: "method",
      key: "method",
      width: 100,
      render: (_, r) => <FollowUpMethodTag method={r.method} />,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (_, r) => <FollowUpStatusTag status={r.status} />,
    },
    {
      title: "内容",
      dataIndex: "content",
      key: "content",
      ellipsis: true,
      render: (_, r) => r.content || "-",
    },
    {
      title: "结果",
      dataIndex: "result",
      key: "result",
      ellipsis: true,
      render: (_, r) => r.result || "-",
    },
    {
      title: "计划时间",
      dataIndex: "planned_at",
      key: "planned_at",
      width: 120,
      render: (_, r) => {
        const bucket = r.due_bucket as DueBucket | undefined;
        const color = bucket ? BUCKET_COLOR[bucket] : "default";
        return (
          <Space direction="vertical" size={0}>
            <Text>{r.planned_at ? r.planned_at.slice(0, 16) : "-"}</Text>
            {bucket && bucket !== "closed" && (
              <Tag color={color}>{BUCKET_LABEL[bucket]}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: "完成时间",
      dataIndex: "completed_at",
      key: "completed_at",
      width: 120,
      render: (_, r) => r.completed_at ? r.completed_at.slice(0, 16) : "-",
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (_, r) => <FollowUpPriorityTag priority={r.priority} />,
    },
    {
      title: "负责人",
      dataIndex: "assigned_to",
      key: "assigned_to",
      width: 100,
      render: (_, r) => r.assigned_to || "-",
    },
    {
      title: "操作",
      key: "actions",
      width: 260,
      fixed: "right",
      render: (_, r) => (
        <Space size="small">
          {r.status === "in_progress" && (
            <Button type="link" size="small" icon={<SyncOutlined />} onClick={() => openUpdate(r)}>
              更新跟进
            </Button>
          )}
          {r.status !== "completed" && (
            <>
              <Button type="link" size="small" icon={<CalendarOutlined />} onClick={() => openReschedule(r)}>
                改期
              </Button>
              <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleComplete(r.id)}>
                完成
              </Button>
            </>
          )}
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r.id)}>
            编辑
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (!customerId || Number.isNaN(custId)) {
    return (
      <Card>
        <Empty description="请先选择客户" />
      </Card>
    );
  }

  // Reset page to 1 whenever any filter changes
  const onFilterChange = (setter: () => void) => () => {
    setter();
    setPage(1);
  };

  return (
    <div className="followup-ledger">
      <div className="followup-ledger-command">
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/customers/${custId}`)}>
            返回客户详情
          </Button>
          <Button icon={<SyncOutlined />} onClick={() => query.refetch()} loading={query.isFetching}>
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
            onChange={onFilterChange(() => setStatusFilter(undefined as unknown as string))}
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
            onChange={onFilterChange(() => setPriorityFilter(undefined as unknown as string))}
            options={[
              { value: "high", label: "高" },
              { value: "medium", label: "中" },
              { value: "low", label: "低" },
            ]}
          />
          <Select
            value={dueFilter}
            style={{ width: 130 }}
            onChange={onFilterChange(() => setDueFilter("all" as DueFilter))}
            options={[
              { value: "all", label: "全部到期" },
              { value: "overdue", label: "逾期" },
              { value: "today", label: "今日" },
              { value: "upcoming", label: "未来" },
              { value: "unscheduled", label: "未排期" },
              { value: "closed", label: "已关闭" },
            ]}
          />
          <Button
            onClick={() => {
              setStatusFilter(undefined);
              setPriorityFilter(undefined);
              setDueFilter("all");
              setPage(1);
            }}
          >
            重置
          </Button>
        </Space>
      </div>

      <div className="followup-ledger-metrics">
        <div><span>全部记录</span><strong>{total}</strong></div>
        <div><span>未关闭</span><strong>{counts?.open ?? 0}</strong></div>
        <div className="is-danger"><span>逾期</span><strong>{counts?.overdue ?? 0}</strong></div>
        <div className="is-warning"><span>今日</span><strong>{counts?.today ?? 0}</strong></div>
        <div><span>高优先级</span><strong>{counts?.high ?? 0}</strong></div>
        <div><span>已完成</span><strong>{counts?.completed ?? 0}</strong></div>
      </div>

      {query.isLoading ? (
        <Spin style={{ display: "block", margin: "100px auto" }} />
      ) : total === 0 ? (
        <Card>
          <Empty description={
            (statusFilter || priorityFilter || dueFilter !== "all")
              ? "没有符合筛选条件的跟进记录"
              : "暂无跟进记录"
          }>
            <Button type="primary" onClick={handleCreate}>新建跟进</Button>
          </Empty>
        </Card>
      ) : (
        <ProTable<FollowUp>
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={query.isFetching}
          search={false}
          options={false}
          className="erp-table followup-ledger-table"
          bordered
          size="small"
          rowClassName={(r) => r.due_bucket === "overdue" ? "followup-row-overdue" : ""}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: (p) => setPage(p),
          }}
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
