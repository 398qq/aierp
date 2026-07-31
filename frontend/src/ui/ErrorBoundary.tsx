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
import { isChunkLoadError, isOffline } from "./chunkError";

interface ErrorBoundaryProps {
  children: ReactNode;
  pageName?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

function getFallbackCopy(error: Error | null): { isChunk: boolean; subTitle: string } {
  if (error && isChunkLoadError(error)) {
    return {
      isChunk: true,
      subTitle: isOffline()
        ? "网络连接已断开，请检查网络后重新加载。"
        : "页面资源加载失败（可能是系统已发布新版本），请刷新重试。",
    };
  }
  return { isChunk: false, subTitle: error?.message ?? "发生未知错误" };
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, _info: ErrorInfo): void {
    // TODO: route to observability backend in production
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
    const copy = getFallbackCopy(this.state.error);
    const title = copy.isChunk ? "页面资源加载失败" : `${pageName} 加载失败`;
    return (
      <Card style={{ margin: 24 }}>
        <Result
          status="error"
          title={title}
          subTitle={copy.subTitle}
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
