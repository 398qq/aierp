import { Tag } from "antd";

export const FOLLOW_UP_METHOD_OPTIONS = [
  { value: "phone", label: "电话拜访" },
  { value: "visit", label: "上门拜访" },
  { value: "video", label: "视频会议" },
  { value: "email", label: "邮件" },
  { value: "wechat", label: "微信" },
  { value: "other", label: "其他" },
];

export const FOLLOW_UP_STATUS_OPTIONS = [
  { value: "planned", label: "计划中" },
  { value: "in_progress", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "cancelled", label: "已取消" },
];

export const FOLLOW_UP_PRIORITY_OPTIONS = [
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

export const FOLLOW_UP_METHOD_META: Record<string, { label: string; color: string }> = {
  phone: { label: "电话拜访", color: "blue" },
  visit: { label: "上门拜访", color: "green" },
  video: { label: "视频会议", color: "purple" },
  email: { label: "邮件", color: "cyan" },
  wechat: { label: "微信", color: "geekblue" },
  other: { label: "其他", color: "default" },
};

export const FOLLOW_UP_STATUS_META: Record<string, { label: string; color: string }> = {
  planned: { label: "计划中", color: "default" },
  in_progress: { label: "进行中", color: "processing" },
  completed: { label: "已完成", color: "green" },
  cancelled: { label: "已取消", color: "red" },
};

export const FOLLOW_UP_PRIORITY_META: Record<string, { label: string; color: string }> = {
  high: { label: "高", color: "red" },
  medium: { label: "中", color: "orange" },
  low: { label: "低", color: "default" },
};

export function getHealthColor(value?: number | null) {
  if (value == null) return "default";
  if (value >= 80) return "green";
  if (value >= 60) return "gold";
  return "red";
}

export function getLevelColor(level?: string | null) {
  if (!level) return "default";
  if (level === "A") return "red";
  if (level === "B") return "orange";
  if (level === "C") return "gold";
  return "default";
}

export function FollowUpMethodTag({ method }: { method?: string | null }) {
  const meta = FOLLOW_UP_METHOD_META[method || ""] || { label: method || "-", color: "default" };
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

export function FollowUpStatusTag({ status }: { status?: string | null }) {
  const meta = FOLLOW_UP_STATUS_META[status || ""] || { label: status || "-", color: "default" };
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

export function FollowUpPriorityTag({ priority }: { priority?: string | null }) {
  if (!priority) return <>-</>;
  const meta = FOLLOW_UP_PRIORITY_META[priority] || { label: priority, color: "default" };
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

export function CustomerHealthBadge({ value }: { value?: number | null }) {
  return <Tag color={getHealthColor(value)}>{value != null ? `${value}` : "-"}</Tag>;
}
