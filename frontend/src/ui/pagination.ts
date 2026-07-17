import type { TablePaginationConfig } from "antd/es/table";

export const ERP_PAGE_SIZE = 20;
export const ERP_PAGE_SIZE_OPTIONS = [20, 50, 100];

export const erpPagination = (
  config: TablePaginationConfig = {},
): TablePaginationConfig => ({
  pageSize: ERP_PAGE_SIZE,
  showSizeChanger: true,
  pageSizeOptions: ERP_PAGE_SIZE_OPTIONS,
  showQuickJumper: true,
  showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条 / 共 ${total} 条`,
  locale: { items_per_page: "条/页", jump_to: "跳至", page: "页" },
  ...config,
});
