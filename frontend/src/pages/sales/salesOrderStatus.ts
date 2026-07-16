export const SALES_ORDER_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  pending: "待确认",
  confirmed: "已确认",
  partially_shipped: "部分发货",
  shipped: "已发货",
  delivered: "已签收",
  completed: "已完成",
  cancelled: "已取消",
};

const SALES_ORDER_TRANSITIONS: Record<string, string[]> = {
  draft: ["confirmed", "cancelled"],
  pending: ["confirmed", "cancelled"],
  confirmed: ["partially_shipped", "shipped", "cancelled"],
  partially_shipped: ["shipped", "cancelled"],
  shipped: ["delivered", "completed"],
  delivered: ["completed"],
  invoiced: ["completed"],
  completed: [],
  cancelled: [],
};

export function getSalesOrderStatusOptions(currentStatus: string, isEdit: boolean) {
  const values = isEdit
    ? [currentStatus, ...(SALES_ORDER_TRANSITIONS[currentStatus] || [])]
    : ["pending"];
  return [...new Set(values)].map((value) => ({
    value,
    label: SALES_ORDER_STATUS_LABELS[value] || value,
  }));
}
