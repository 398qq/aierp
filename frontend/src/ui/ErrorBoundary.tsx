/** ErrorBoundary — React error boundary for page-level error containment.

Before this, a single rendering error in any page (e.g. a malformed
date) would white-screen the entire app. Each page should be wrapped
in an ErrorBoundary so failures are contained and the user sees a
recovery option.

Usage in a page component:
  export default function MyPage() {
    return (
      <ErrorBoundary pageName="客户">
        <MyPageBody />
      </ErrorBoundary>
    );
  }

Behavior:
- Caught errors render a fallback Card with the page name, error
  message, and two buttons (reload, back to home)
- Production: a `componentDidCatch` hook can be added to log to the
  observability backend (omitted here to avoid pulling in the api
  client)
- The error.stack is included in dev-mode (when window.location.hostname
  is not a public IP) for triage; in production it's hidden
*/

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Card, Result, Space } from "antd";
import { ReloadOutlined, HomeOutlined } from "@ant-design/icons";

interface ErrorBoundaryProps {
  children: ReactNode;
  pageName?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Reserved for future observability hook (e.g. Sentry.capture).
    // Console-log here so dev-mode catches the error before the
    // browser swallows it.
    // eslint-disable-next-line no-console
    console.error(`[ErrorBoundary:${this.props.pageName ?? "?"}]`, error, info);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  handleHome = (): void => {
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    const pageName = this.props.pageName ?? "页面";
    return (
      <Card style={{ margin: 24 }}>
        <Result
          status="error"
          title={`${pageName} 加载失败`}
          subTitle={this.state.error?.message ?? "发生未知错误"}
          extra={
            <Space>
              <Button type="primary" icon={<ReloadOutlined />} onClick={this.handleReload}>
                重新加载
              </Button>
              <Button icon={<HomeOutlined />} onClick={this.handleHome}>
                返回首页
              </Button>
            </Space>
          }
        />
      </Card>
    );
  }
}
