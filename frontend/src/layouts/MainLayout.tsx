import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router";
import {
  Button,
  Input,
  Avatar,
  Tooltip,
  Badge,
  Drawer,
  Card,
  Tag,
  Spin,
  Space,
  List,
  Typography,
  theme,
} from "antd";
import { BellOutlined, LogoutOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import { ProLayout } from "@ant-design/pro-components";
import { useAuthStore } from "../store/auth";
import { getUnreadCount, naturalLanguageQuery } from "../api";
import type { NLPQueryResult } from "../types";
import type { MenuDataItem } from "@ant-design/pro-components";
import {
  findNavigationTarget,
  getMenuItemTarget,
  navigationMenuItems,
  resolveSelectedNavigationKey,
} from "../navigation/appNavigation";
import "../styles/app-shell.css";

const { Text } = Typography;
const { useToken } = theme;

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const roles = useAuthStore((s) => s.roles);
  const { token } = useToken();

  const [nlpDrawerOpen, setNlpDrawerOpen] = useState(false);
  const [nlpQuery, setNlpQuery] = useState("");
  const [nlpLoading, setNlpLoading] = useState(false);
  const [nlpResult, setNlpResult] = useState<NLPQueryResult | null>(null);

  const handleNlpSubmit = async () => {
    if (!nlpQuery.trim()) return;
    setNlpLoading(true);
    setNlpResult(null);
    try {
      const resp = await naturalLanguageQuery(nlpQuery);
      if (resp.data.code === 0) setNlpResult(resp.data.data);
    } catch {
      /* ignore */
    } finally {
      setNlpLoading(false);
    }
  };

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const resp = await getUnreadCount();
        setUnreadCount(resp.data.data.count || 0);
      } catch {
        /* ignore */
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, []);

  const selectedKey = resolveSelectedNavigationKey(location.pathname);

  const handleClick = (item: MenuDataItem) => {
    const target = getMenuItemTarget(item);
    if (target) {
      navigate(target);
    }
  };

  return (
    <>
      <ProLayout
        layout="mix"
        splitMenus={false}
        fixSiderbar
        contentWidth="Fluid"
        siderWidth={224}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        menuDataRender={() => navigationMenuItems}
        location={{ pathname: selectedKey }}
        logo="/icon-192.png"
        title="AIERP"
        onMenuHeaderClick={() => navigate("/")}
        menuItemRender={(item, dom) => <a onClick={() => handleClick(item)}>{dom}</a>}
        headerTitleRender={(logo, title) => (
          <a
            onClick={() => navigate("/")}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 32,
                height: 32,
                borderRadius: 6,
                background: token.colorPrimary,
                color: "#fff",
                fontWeight: 700,
                fontSize: 16,
              }}
            >
              AI
            </span>
            <strong style={{ fontSize: 18 }}>{title}</strong>
          </a>
        )}
        actionsRender={() => [
          <Input.Search
            className="erp-layout-menu-search"
            key="search"
            placeholder="搜索菜单"
            allowClear
            onSearch={(v) => {
              const target = findNavigationTarget(v);
              if (target) navigate(target);
            }}
            style={{ width: 200 }}
          />,
          <Tooltip key="ai" title="AI 助手">
            <Button type="text" icon={<RobotOutlined />} onClick={() => setNlpDrawerOpen(true)} />
          </Tooltip>,
          <Badge key="notif" count={unreadCount} size="small">
            <Button
              type="text"
              icon={<BellOutlined />}
              onClick={() => navigate("/notifications")}
            />
          </Badge>,
          <Tooltip key="user" title={`${username || "用户"} · ${roles[0] || "业务用户"}`}>
            <Avatar size={30} icon={<UserOutlined />} style={{ cursor: "pointer" }} />
          </Tooltip>,
          <Button
            key="logout"
            type="text"
            icon={<LogoutOutlined />}
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            退出
          </Button>,
        ]}
        contentStyle={{ margin: 0, padding: 0, minHeight: "calc(100vh - 64px)" }}
      >
        <div className="erp-app-content">
          <Outlet />
        </div>
      </ProLayout>

      <Drawer
        title="AI 问答"
        open={nlpDrawerOpen}
        onClose={() => setNlpDrawerOpen(false)}
        width={480}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="输入您的问题"
              value={nlpQuery}
              onChange={(e) => setNlpQuery(e.target.value)}
              onPressEnter={handleNlpSubmit}
            />
            <Button type="primary" loading={nlpLoading} onClick={handleNlpSubmit}>
              发送
            </Button>
          </Space.Compact>
          {nlpLoading && (
            <div style={{ textAlign: "center", padding: 24 }}>
              <Spin tip="AI 正在分析..." />
            </div>
          )}
          {nlpResult && (
            <>
              <Card
                size="small"
                title="回答"
                extra={
                  <Tag color={nlpResult.confidence > 0.7 ? "green" : "orange"}>
                    {(nlpResult.confidence * 100).toFixed(0)}%
                  </Tag>
                }
              >
                <Text>{nlpResult.answer}</Text>
              </Card>
              {nlpResult.data_summary && (
                <Card size="small" title="数据摘要">
                  <Text>{nlpResult.data_summary}</Text>
                </Card>
              )}
              {nlpResult.related_entities?.length > 0 && (
                <Card size="small" title="相关实体">
                  <Space wrap>
                    {nlpResult.related_entities.map((e, i) => (
                      <Tag
                        key={i}
                        color="blue"
                        style={{ cursor: "pointer" }}
                        onClick={() => {
                          setNlpDrawerOpen(false);
                          navigate(`/${e.type}s/${e.id}`);
                        }}
                      >
                        {e.type}: {e.name}
                      </Tag>
                    ))}
                  </Space>
                </Card>
              )}
              {nlpResult.actions?.length > 0 && (
                <Card size="small" title="建议操作">
                  <List
                    size="small"
                    dataSource={nlpResult.actions}
                    renderItem={(a) => (
                      <List.Item>
                        <Text strong>{a.action}</Text> <Tag color="orange">{a.urgency}</Tag>
                      </List.Item>
                    )}
                  />
                </Card>
              )}
              {nlpResult.suggested_followups?.length > 0 && (
                <Card size="small" title="追问建议">
                  <Space wrap>
                    {nlpResult.suggested_followups.map((q, i) => (
                      <Button key={i} size="small" onClick={() => setNlpQuery(q)}>
                        {q}
                      </Button>
                    ))}
                  </Space>
                </Card>
              )}
            </>
          )}
        </Space>
      </Drawer>
    </>
  );
}
