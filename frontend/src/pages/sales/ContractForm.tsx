import { useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { App, Button, Card, Space, Typography } from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  ProForm,
  ProFormDatePicker,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
} from "@ant-design/pro-components";
import dayjs, { type Dayjs } from "dayjs";
import { useApiMutation, useApiQuery } from "@/lib/queries";
import { getApiErrorMessage } from "@/api";
import type { Contract, PageData, SalesOrder } from "@/types";
import { CustomerSelect, SalesModuleShell, shortDate } from "./salesUi";

const STATUS_OPTIONS = [
  { value: "draft", label: "草稿" },
  { value: "signed", label: "已签署" },
  { value: "active", label: "履行中" },
  { value: "terminated", label: "已终止" },
];

const INVOICE_TYPE_OPTIONS = [
  { value: "增值税专用发票", label: "增值税专用发票" },
  { value: "增值税普通发票", label: "增值税普通发票" },
];

type ContractStatus = "draft" | "signed" | "active" | "terminated";

interface FormValues {
  customer_id?: number;
  sales_order_id?: number;
  title: string;
  contract_no?: string;
  amount?: number;
  status: ContractStatus;
  signed_date?: Dayjs | null;
  expire_date?: Dayjs | null;
  file_url?: string;
  delivery_address?: string;
  invoice_type?: string;
  payment_terms?: string;
  delivery_terms?: string;
  acceptance_terms?: string;
  warranty_terms?: string;
  dispute_terms?: string;
  notes?: string;
}

const toIsoOrNull = (v: unknown): string | null =>
  v && dayjs.isDayjs(v) ? (v as Dayjs).toISOString() : null;

const EMPTY_ORDERS: SalesOrder[] = [];

export default function ContractForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const isEdit = !!id;

  const detailQuery = useApiQuery<Contract | null>(
    ["contract", id ?? "new"],
    `/api/v1/contracts/${id}`,
    undefined,
    { enabled: isEdit, staleTime: 60 * 1000 },
  );

  const ordersQuery = useApiQuery<PageData<SalesOrder>>(
    ["sales-orders", "all"],
    "/api/v1/sales-orders",
    { page: 1, page_size: 100 },
    { staleTime: 5 * 60 * 1000 },
  );
  const orders = useMemo(
    () => ordersQuery.data?.list ?? EMPTY_ORDERS,
    [ordersQuery.data],
  );
  const orderById = useMemo(
    () => new Map(orders.map((order) => [order.id, order])),
    [orders],
  );

  const [form] = ProForm.useForm<FormValues>();

  useEffect(() => {
    if (isEdit && detailQuery.data) {
      const c = detailQuery.data;
      form.setFieldsValue({
        customer_id: c.customer_id ?? undefined,
        sales_order_id: c.sales_order_id ?? undefined,
        title: c.title,
        contract_no: c.contract_no ?? undefined,
        amount: c.amount ?? undefined,
        status: c.status as ContractStatus,
        signed_date: c.signed_date ? dayjs(c.signed_date) : null,
        expire_date: c.expire_date ? dayjs(c.expire_date) : null,
        file_url: c.file_url ?? undefined,
        delivery_address: c.delivery_address ?? undefined,
        invoice_type: c.invoice_type ?? undefined,
        payment_terms: c.payment_terms ?? undefined,
        delivery_terms: c.delivery_terms ?? undefined,
        acceptance_terms: c.acceptance_terms ?? undefined,
        warranty_terms: c.warranty_terms ?? undefined,
        dispute_terms: c.dispute_terms ?? undefined,
        notes: c.notes ?? undefined,
      });
    }
  }, [detailQuery.data, isEdit, form]);

  const createMut = useApiMutation<Contract, Record<string, unknown>>(
    "post",
    "/api/v1/contracts",
    {
      invalidateKeys: [["contracts"], ["contract", id ?? "new"]],
      onSuccess: () => {
        message.success("合同已创建");
        navigate("/sales/contracts");
      },
      onError: (err) => message.error(getApiErrorMessage(err, "保存失败")),
    },
  );

  const updateMut = useApiMutation<Contract, Record<string, unknown>>(
    "put",
    () => `/api/v1/contracts/${id}`,
    {
      invalidateKeys: [["contracts"], ["contract", id ?? "new"]],
      onSuccess: () => {
        message.success("合同已更新");
        navigate("/sales/contracts");
      },
      onError: (err) => message.error(getApiErrorMessage(err, "保存失败")),
    },
  );

  const submitting = createMut.isPending || updateMut.isPending;

  const onFinish = async (values: FormValues): Promise<void> => {
    const payload: Record<string, unknown> = {
      ...values,
      signed_date: toIsoOrNull(values.signed_date),
      expire_date: toIsoOrNull(values.expire_date),
    };
    if (isEdit) {
      await updateMut.mutateAsync(payload);
    } else {
      await createMut.mutateAsync(payload);
    }
  };

  const applyOrder = (orderId?: number): void => {
    const order = orderById.get(Number(orderId));
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      amount: (form.getFieldValue("amount") as number | undefined) ?? order.total_amount,
    });
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑合同" : "新增合同"}
      subtitle={isEdit ? "修改合同信息" : "创建新合同，关联客户和订单"}
      activeKey="contracts"
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/sales/contracts")}>
          返回
        </Button>
      }
    >
      <ProForm<FormValues>
        form={form}
        layout="vertical"
        onFinish={onFinish}
        loading={detailQuery.isLoading || ordersQuery.isLoading || submitting}
        initialValues={{ status: "draft" }}
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
                  {isEdit ? "保存合同" : "创建合同"}
                </Button>
                <Button block onClick={() => navigate("/sales/contracts")}>
                  取消
                </Button>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  合同保存后可在合同管理中查看履行进度与到期提醒。
                </Typography.Text>
              </Space>
            </Card>
          ),
        }}
      >
        <Card size="small" title="客户与订单">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 12,
            }}
          >
            <ProForm.Item
              name="customer_id"
              label="客户"
              rules={[{ required: true, message: "请选择客户" }]}
            >
              <CustomerSelect />
            </ProForm.Item>
            <ProForm.Item name="sales_order_id" label="关联订单">
              <ProFormSelect
                showSearch
                allowClear
                placeholder="选择订单"
                options={orders.map((order) => ({
                  value: order.id,
                  label: `${order.order_no || `#${order.id}`} / 客户 #${order.customer_id} / ${shortDate(order.delivery_date)}`,
                }))}
                fieldProps={{
                  optionFilterProp: "label",
                  onChange: (value) => applyOrder(value as number | undefined),
                }}
              />
            </ProForm.Item>
            <ProFormText
              name="title"
              label="标题"
              rules={[{ required: true, message: "请输入合同标题" }]}
            />
            <ProFormText name="contract_no" label="合同号" placeholder="留空自动生成" />
            <ProFormDigit
              name="amount"
              label="金额"
              fieldProps={{ prefix: "¥", precision: 2 }}
            />
            <ProFormSelect
              name="status"
              label="状态"
              options={STATUS_OPTIONS}
              width="md"
            />
          </div>
        </Card>

        <Card size="small" title="签署与到期" style={{ marginTop: 12 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <ProFormDatePicker name="signed_date" label="签署日期" width="md" />
            <ProFormDatePicker name="expire_date" label="到期日期" width="md" />
          </div>
          <ProFormText name="file_url" label="文件URL" style={{ marginTop: 12 }} />
        </Card>

        <Card size="small" title="商务条款" style={{ marginTop: 12, marginBottom: 16 }}>
          <ProFormTextArea
            name="delivery_address"
            label="交货地址"
            fieldProps={{ rows: 2 }}
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 12,
            }}
          >
            <ProFormSelect
              name="invoice_type"
              label="发票类型"
              allowClear
              options={INVOICE_TYPE_OPTIONS}
            />
            <ProFormText
              name="payment_terms"
              label="付款条款"
              placeholder="货到验收后30日付款"
            />
          </div>
          <ProFormTextArea
            name="delivery_terms"
            label="交付条款"
            fieldProps={{ rows: 2 }}
            placeholder="交货方式、分批交付和运输责任"
          />
          <ProFormTextArea
            name="acceptance_terms"
            label="验收条款"
            fieldProps={{ rows: 2 }}
            placeholder="验收期限、标准和异议期限"
          />
          <ProFormTextArea
            name="warranty_terms"
            label="质保与售后"
            fieldProps={{ rows: 2 }}
          />
          <ProFormTextArea
            name="dispute_terms"
            label="违约与争议解决"
            fieldProps={{ rows: 2 }}
          />
        </Card>

        <ProFormTextArea
          name="notes"
          label="备注"
          fieldProps={{ rows: 2 }}
        />
      </ProForm>
    </SalesModuleShell>
  );
}