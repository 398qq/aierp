/**
 * 客户跟进记录列表页面
 * 路由: /customers/:customerId/follow-ups
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Table, Button, Space, Spin, Tag, Card, Popconfirm, message, Empty } from "antd";
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { TablePaginationConfig } from "antd/es/table/interface";
import { getFollowUps, deleteFollowUp } from "../../api";
import type { FollowUp } from "../../types";

// 跟进方式映射
const METHOD_OPTIONS: Record<string, { label: string; color: string }> = {
  phone: { label: "电话拜访", color: "blue" },
  visit: { label: "上门拜访", color: "green" },
  video: { label: "视频会议", color: "purple" },
  email: { label: "邮件", color: "cyan" },
  other: { label: "其他", color: "default" },
};

// 状态映射
const STATUS_OPTIONS: Record<string, { label: string; color: string }> = {
  planned: { label: "计划中", color: "default" },
  in_progress: { label: "进行中", color: "processing" },
  completed: { label: "已完成", color: "green" },
  cancelled: { label: "已取消", color: "red" },
};

// 优先级映射
const PRIORITY_OPTIONS: Record<string, { label: string; color: string }> = {
  low: { label: "低", color: "default" },
  medium: { label: "中", color: "orange" },
  high: { label: "高", color: "red" },
};

export default function FollowUpList() {
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();
  const [allData, setAllData] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

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
      render: (method: string) => {
        const opt = METHOD_OPTIONS[method] || { label: method || "-", color: "default" };
        return <Tag color={opt.color}>{opt.label}</Tag>;
      },
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: string) => {
        const opt = STATUS_OPTIONS[status] || { label: status || "-", color: "default" };
        return <Tag color={opt.color}>{opt.label}</Tag>;
      },
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
      render: (priority: string) => {
        if (!priority) return "-";
        const opt = PRIORITY_OPTIONS[priority] || { label: priority, color: "default" };
        return <Tag color={opt.color}>{opt.label}</Tag>;
      },
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
      width: 120,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
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
    </div>
  );
}
