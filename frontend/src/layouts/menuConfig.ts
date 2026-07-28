// frontend/src/layouts/menuConfig.ts
import type { MenuProps } from "antd";

export const menuItems: MenuProps["items"] = [
  { key: "/", icon: "DashboardOutlined", label: "Dashboard" },
  { key: "/customers", icon: "TeamOutlined", label: "Customers" },
  { key: "/sales", icon: "ShopOutlined", label: "Sales" },
  { key: "/products", icon: "StockOutlined", label: "Products" },
  { key: "/suppliers", icon: "ShopOutlined", label: "Suppliers" },
  { key: "/brands", icon: "StarOutlined", label: "Brands" },
  { key: "/inventory", icon: "InboxOutlined", label: "Inventory" },
  { key: "/warehouse", icon: "HomeOutlined", label: "Warehouse" },
  { key: "/tickets", icon: "AlertOutlined", label: "Tickets" },
  { key: "/finance", icon: "AccountBookOutlined", label: "Finance" },
  { key: "/notifications", icon: "BellOutlined", label: "Notifications" },
  { key: "/reports", icon: "BarChartOutlined", label: "Reports" },
  { key: "/ai/chat", icon: "RobotOutlined", label: "AI Assistant" },
  { key: "/settings", icon: "SettingOutlined", label: "Settings" },
];
