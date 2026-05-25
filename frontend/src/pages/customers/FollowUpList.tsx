/**
 * 客户跟进记录列表页面
 * 路由: /customers/:customerId/follow-ups
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { App, Table, Button, Space, Spin, Card, Popconfirm, Empty, Modal, DatePicker } from "antd";
import { ArrowLeftOutlined, CalendarOutlined, CheckCircleOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { TablePaginationConfig } from "antd/es/table/interface";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { getFollowUps, deleteFollowUp, updateFollowUp } from "../../api";
import type { FollowUp } from "../../types";
import { FollowUpMethodTag, FollowUpPriorityTag, FollowUpStatusTag } from "./customerUi";

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
  const [rescheduling, setRescheduling] = useState(false);

  const custId = Number(customerId);

  // 加载跟进记录
  const load = async () => {
    setLoading(true);
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
    } catch {
      message.error("加载跟进记录失败");
    } finally {
      setLoading(false);
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

  // 删除跟进记录
  const handleDelete = async (followupId: number) => {
    try {
      await deleteFollowUp(custId, followupId);
      message.success("删除成功");
      load();
    } catch {
      message.error("删除失败");
    }
  };

  const handleComplete = async (followupId: number) => {
    try {
      await updateFollowUp(custId, followupId, {
        status: "completed",
        completed_at: new Date().toISOString(),
      });
      message.success("已完成");
      load();
    } catch {
      message.error("操作失败");
    }
  };

  const openReschedule = (record: FollowUp) => {
    setRescheduleRecord(record);
    setRescheduleAt(record.planned_at ? dayjs(record.planned_at) : dayjs().add(1, "day").hour(9).minute(0).second(0));
    setRescheduleOpen(true);
  };

  const handleReschedule = async () => {
    if (!rescheduleRecord || !rescheduleAt) {
      message.warning("请选择新的跟进时间");
      return;
    }
    setRescheduling(true);
    try {
      await updateFollowUp(custId, rescheduleRecord.id, {
        status: "planned",
        planned_at: rescheduleAt.format("YYYY-MM-DD HH:mm:ss"),
      });
      message.success("跟进时间已更新");
      setRescheduleOpen(false);
      setRescheduleRecord(null);
      setRescheduleAt(null);
      load();
    } catch {
      message.error("更新跟进时间失败");
    } finally {
      setRescheduling(false);
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
      render: (planned_at: string) => planned_at ? planned_at.slice(0, 16) : "-",
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
      width: 180,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
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
  const currentData = allData.slice(startIndex, startIndex + pageSize);

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/customers/${custId}`)}>
          返回客户详情
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建跟进
        </Button>
      </Space>

      {loading && <Spin style={{ display: "block", margin: "100px auto" }} />}

      {!loading && allData.length === 0 && (
        <Card>
          <Empty description="暂无跟进记录">
            <Button type="primary" onClick={handleCreate}>新建跟进</Button>
          </Empty>
        </Card>
      )}

      {!loading && allData.length > 0 && (
        <Table
          columns={columns}
          dataSource={currentData}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: allData.length,
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
        onCancel={() => {
          setRescheduleOpen(false);
          setRescheduleRecord(null);
          setRescheduleAt(null);
        }}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>{rescheduleRecord?.content || "选择新的计划跟进时间"}</div>
          <DatePicker
            showTime
            format="YYYY-MM-DD HH:mm"
            value={rescheduleAt}
            onChange={setRescheduleAt}
            style={{ width: "100%" }}
          />
        </Space>
      </Modal>
    </div>
  );
}
