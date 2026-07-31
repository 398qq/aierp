import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { EmptyState, StatusTag } from "@/ui";
import { erpPagination } from "@/ui/pagination";
import type { AnomalyRow } from "@/types/watchtower";
import styles from "./AnomalyTable.module.css";

const columns: ProColumns<AnomalyRow>[] = [
  {
    title: "领域",
    dataIndex: "domainLabel",
    width: 120,
    render: (d) => <StatusTag>{d}</StatusTag>,
  },
  { title: "名称", dataIndex: "name", ellipsis: true, render: (n) => n ?? "-" },
  { title: "详情", dataIndex: "signal", ellipsis: true, render: (s) => s ?? "-" },
];

export interface AnomalyTableProps {
  rows: AnomalyRow[];
}

export function AnomalyTable({ rows }: AnomalyTableProps) {
  if (rows.length === 0) {
    return <EmptyState description="未检测到异常，系统运行正常" />;
  }
  return (
    <div className={styles.wrapper}>
      <ProTable<AnomalyRow>
        columns={columns}
        dataSource={rows}
        rowKey={(_r, i) => String(i)}
        pagination={erpPagination()}
        search={false}
        options={false}
      />
    </div>
  );
}
