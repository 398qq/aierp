import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { App, Button, Card, Space, Typography } from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  ProForm,
  ProFormDigit,
  ProFormDatePicker,
  ProFormSelect,
} from "@ant-design/pro-components";
import dayjs, { type Dayjs } from "dayjs";
import { useApiMutation, useApiQuery } from "@/lib/queries";
import { getApiErrorMessage } from "@/api";
import type { SalesTarget } from "@/types";
import { SalesModuleShell } from "./salesUi";

const TYPE_OPTIONS = [
  { value: "monthly", label: "月度" },
  { value: "quarterly", label: "季度" },
  { value: "annual", label: "年度" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "cancelled", label: "已取消" },
];

type TargetType = "monthly" | "quarterly" | "annual";
type TargetStatus = "active" | "completed" | "cancelled";

interface FormValues {
  user_id: number;
  target_amount: number;
  actual_amount?: number;
  target_type: TargetType;
  period_start?: Dayjs | null;
  period_end?: Dayjs | null;
  status: TargetStatus;
}

const toIso = (v: unknown): string | null =>
  v && dayjs.isDayjs(v) ? (v as Dayjs).toISOString() : null;

export default function TargetForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const isEdit = !!id;

  const detailQuery = useApiQuery<SalesTarget | null>(
    ["target", id ?? "new"],
    `/api/v1/sales/targets/${id}`,
    undefined,
    { enabled: isEdit, staleTime: 60 * 1000 },
  );

  const [form] = ProForm.useForm<FormValues>();

  useEffect(() => {
    if (isEdit && detailQuery.data) {
      const t = detailQuery.data;
      form.setFieldsValue({
        user_id: t.user_id,
        target_amount: t.target_amount,
        actual_amount: t.actual_amount,
        target_type: t.target_type as TargetType,
        period_start: t.period_start ? dayjs(t.period_start) : null,
        period_end: t.period_end ? dayjs(t.period_end) : null,
        status: t.status as TargetStatus,
      });
    }
  }, [detailQuery.data, isEdit, form]);

  const createMut = useApiMutation<SalesTarget, Record<string, unknown>>(
    "post",
    "/api/v1/sales/targets",
    {
      invalidateKeys: [["sales", "targets"], ["target"]],
      onSuccess: () => {
        message.success("目标已创建");
        navigate("/sales/targets");
      },
      onError: (err) => message.error(getApiErrorMessage(err, "保存失败")),
    },
  );

  const updateMut = useApiMutation<SalesTarget, Record<string, unknown>>(
    "put",
    () => `/api/v1/sales/targets/${id}`,
    {
      invalidateKeys: [
        ["sales", "targets"],
        ["target", id ?? "new"],
      ],
      onSuccess: () => {
        message.success("目标已更新");
        navigate("/sales/targets");
      },
      onError: (err) => message.error(getApiErrorMessage(err, "保存失败")),
    },
  );

  const submitting = createMut.isPending || updateMut.isPending;

  const onFinish = async (values: FormValues): Promise<void> => {
    const payload: Record<string, unknown> = {
      ...values,
      period_start: toIso(values.period_start),
      period_end: toIso(values.period_end),
    };
    if (isEdit) {
      await updateMut.mutateAsync(payload);
    } else {
      await createMut.mutateAsync(payload);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑销售目标" : "新增销售目标"}
      subtitle="设定销售人员的月度/季度/年度业绩目标，跟踪完成进度"
      activeKey="targets"
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/targets")}>
          返回
        </Button>
      }
    >
      <ProForm<FormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        loading={detailQuery.isLoading || submitting}
        initialValues={{
          status: "active",
          target_type: "monthly",
        }}
        submitter={{
          render: () => (
            <Card size="small" style={{ marginTop: 16 }}>
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Button
                  block
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={submitting}
                  htmlType="submit"
                >
                  {isEdit ? "保存目标" : "创建目标"}
                </Button>
                <Button block onClick={() => navigate("/sales/targets")}>
                  取消
                </Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  目标保存后可在销售目标列表中查看达成进度。
                </Typography.Text>
              </Space>
            </Card>
          ),
        }}
      >
        <Card size="small" title="负责人与类型">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <ProFormDigit
              name="user_id"
              label="用户ID"
              rules={[{ required: true, message: "请输入用户ID" }]}
              min={1}
            />
            <ProFormSelect
              name="target_type"
              label="目标类型"
              options={TYPE_OPTIONS}
              width="md"
            />
            <ProFormSelect
              name="status"
              label="状态"
              options={STATUS_OPTIONS}
              width="md"
            />
          </div>
        </Card>

        <Card size="small" title="金额与期间" style={{ marginTop: 12 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <ProFormDigit
              name="target_amount"
              label="目标金额"
              rules={[{ required: true, message: "请输入目标金额" }]}
              min={0}
              fieldProps={{ prefix: "¥", precision: 2 }}
            />
            <ProFormDigit
              name="actual_amount"
              label="实际完成"
              min={0}
              fieldProps={{ prefix: "¥", precision: 2 }}
            />
            <ProFormDatePicker name="period_start" label="期间开始" width="md" />
            <ProFormDatePicker name="period_end" label="期间结束" width="md" />
          </div>
        </Card>
      </ProForm>
    </SalesModuleShell>
  );
}
