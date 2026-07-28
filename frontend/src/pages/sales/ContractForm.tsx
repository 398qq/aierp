import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button, Space, message } from "antd";
import {
  ProCard,
  ProForm,
  ProFormDatePicker,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
} from "@ant-design/pro-components";
import { getContract, createContract, updateContract, getSalesOrders } from "../../api";
import dayjs from "dayjs";
import type { SalesOrder } from "../../types";
import { CustomerSelect, SalesModuleShell, shortDate } from "./salesUi";

const STATUS_OPTIONS = [
  { value: "draft", label: "草稿" },
  { value: "signed", label: "已签署" },
  { value: "active", label: "履行中" },
  { value: "terminated", label: "已终止" },
];

const INVOICE_OPTIONS = [
  { value: "增值税专用发票", label: "增值税专用发票" },
  { value: "增值税普通发票", label: "增值税普通发票" },
];

export default function ContractForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = ProForm.useForm();
  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const isEdit = !!id;

  useEffect(() => {
    getSalesOrders({ page: 1, page_size: 100 }).then((r) => setOrders(r.data.data.list || []));
    if (isEdit) {
      getContract(Number(id)).then((r) => {
        const contract = r.data.data;
        form.setFieldsValue({
          ...contract,
          signed_date: contract.signed_date ? dayjs(contract.signed_date) : null,
          expire_date: contract.expire_date ? dayjs(contract.expire_date) : null,
        });
      });
    }
  }, [form, id, isEdit]);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);

  const applyOrder = (orderId?: number) => {
    const order = orderById.get(Number(orderId));
    if (!order) return;
    form.setFieldsValue({
      customer_id: order.customer_id,
      amount: form.getFieldValue("amount") ?? order.total_amount,
    });
  };

  const onFinish = async (values: Record<string, unknown>) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        signed_date: values.signed_date ? (values.signed_date as string) : null,
        expire_date: values.expire_date ? (values.expire_date as string) : null,
      };
      if (isEdit) {
        await updateContract(Number(id), payload);
        message.success("合同已更新");
      } else {
        await createContract(payload);
        message.success("合同已创建");
      }
      navigate("/sales/contracts");
    } catch {
      message.error("保存失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <SalesModuleShell
      title={isEdit ? "编辑合同" : "新增合同"}
      subtitle={isEdit ? "修改合同信息" : "创建新合同，关联客户和订单"}
      activeKey="contracts"
    >
      <ProCard size="small">
        <ProForm
          form={form}
          layout="vertical"
          size="small"
          onFinish={onFinish}
          initialValues={{ status: "draft" }}
          style={{ maxWidth: 720 }}
          submitter={{
            render: () => (
              <Space>
                <Button type="primary" loading={loading} onClick={() => form.submit()}>
                  {isEdit ? "保存" : "创建"}
                </Button>
                <Button onClick={() => navigate("/sales/contracts")}>取消</Button>
              </Space>
            ),
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <ProForm.Item name="customer_id" label="客户" rules={[{ required: true }]}>
              <CustomerSelect />
            </ProForm.Item>
            <ProFormSelect
              name="sales_order_id"
              label="关联订单"
              options={orders.map((order) => ({
                value: order.id,
                label: `${order.order_no || `#${order.id}`} / 客户 #${order.customer_id} / ${shortDate(order.delivery_date)}`,
              }))}
              fieldProps={{
                showSearch: true,
                allowClear: true,
                placeholder: "选择订单",
                optionFilterProp: "label",
                onChange: applyOrder,
              }}
            />
            <ProFormText name="title" label="标题" rules={[{ required: true }]} />
            <ProFormText name="contract_no" label="合同号" placeholder="留空自动生成" />
            <ProFormDigit name="amount" label="金额" fieldProps={{ prefix: "¥" }} />
            <ProFormSelect name="status" label="状态" options={STATUS_OPTIONS} />
            <ProFormDatePicker name="signed_date" label="签署日期" width="md" />
            <ProFormDatePicker name="expire_date" label="到期日期" width="md" />
          </div>
          <ProFormText name="file_url" label="文件URL" />
          <ProCard size="small" title="商务条款" style={{ marginBottom: 16 }}>
            <ProFormTextArea name="delivery_address" label="交货地址" fieldProps={{ rows: 2 }} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
              <ProFormSelect
                name="invoice_type"
                label="发票类型"
                allowClear
                options={INVOICE_OPTIONS}
              />
              <ProFormText name="payment_terms" label="付款条款" placeholder="货到验收后30日付款" />
            </div>
            <ProFormTextArea
              name="delivery_terms"
              label="交付条款"
              placeholder="交货方式、分批交付和运输责任"
              fieldProps={{ rows: 2 }}
            />
            <ProFormTextArea
              name="acceptance_terms"
              label="验收条款"
              placeholder="验收期限、标准和异议期限"
              fieldProps={{ rows: 2 }}
            />
            <ProFormTextArea name="warranty_terms" label="质保与售后" fieldProps={{ rows: 2 }} />
            <ProFormTextArea name="dispute_terms" label="违约与争议解决" fieldProps={{ rows: 2 }} />
          </ProCard>
          <ProFormTextArea name="notes" label="备注" fieldProps={{ rows: 2 }} />
        </ProForm>
      </ProCard>
    </SalesModuleShell>
  );
}
