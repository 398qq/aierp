import { Component } from "react";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router";
import { Button, ConfigProvider, App as AntdApp, Result } from "antd";
import zhCN from "antd/locale/zh_CN";

import { antdTheme, fontSize, fontWeight, lineHeight, typography } from "./design-tokens";
import AppRoutes from "./routes/AppRoutes";
import AntdOverlayGuard from "./ui/AntdOverlayGuard";

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面加载异常"
          subTitle={this.state.error?.message || "未知错误"}
          extra={
            <Button
              type="primary"
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
            >
              刷新页面
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}

function ThemeVariables() {
  return (
    <style>{`
      :root {
        --color-primary: ${antdTheme.token.colorPrimary};
        --color-success: ${antdTheme.token.colorSuccess};
        --color-warning: ${antdTheme.token.colorWarning};
        --color-error: ${antdTheme.token.colorError};
        --color-info: ${antdTheme.token.colorInfo};
        --color-text: ${antdTheme.token.colorText};
        --color-text-secondary: ${antdTheme.token.colorTextSecondary};
        --color-text-tertiary: ${antdTheme.token.colorTextTertiary};
        --color-border: ${antdTheme.token.colorBorder};
        --color-canvas: ${antdTheme.token.colorBgContainer};
        --color-bg-layout: ${antdTheme.token.colorBgLayout};
        --color-primary-bg: #edf3fa;
        --radius-card: ${antdTheme.token.borderRadius}px;
        --radius-input: ${antdTheme.token.borderRadiusSM}px;
        --radius-tag: ${antdTheme.token.borderRadiusXS}px;
        --font-size-page-title: ${fontSize.headingMd}px;
        --font-size-section-title: ${fontSize.section}px;
        --font-size-card-title: ${fontSize.cardTitle}px;
        --font-size-body: ${fontSize.body}px;
        --font-size-body-sm: ${fontSize.bodySm}px;
        --font-size-caption: ${fontSize.caption}px;
        --font-size-table: ${fontSize.table}px;
        --font-size-table-header: ${fontSize.tableHeader}px;
        --font-size-metric: ${fontSize.metric}px;
        --font-weight-medium: ${fontWeight.medium};
        --font-weight-semibold: ${fontWeight.semibold};
        --font-weight-bold: ${fontWeight.bold};
        --line-height-heading: ${lineHeight.heading};
        --line-height-body: ${lineHeight.body};
        --line-height-compact: ${lineHeight.compact};
        --line-height-caption: ${lineHeight.caption};
        --type-report-size: ${typography.reportTitle.fontSize}px;
        --type-report-line: ${typography.reportTitle.lineHeight}px;
        --type-page-size: ${typography.pageTitle.fontSize}px;
        --type-page-line: ${typography.pageTitle.lineHeight}px;
        --type-subsection-size: ${typography.subsectionTitle.fontSize}px;
        --type-subsection-line: ${typography.subsectionTitle.lineHeight}px;
        --type-section-size: ${typography.sectionTitle.fontSize}px;
        --type-section-line: ${typography.sectionTitle.lineHeight}px;
        --type-card-size: ${typography.cardTitle.fontSize}px;
        --type-card-line: ${typography.cardTitle.lineHeight}px;
        --type-body-size: ${typography.body.fontSize}px;
        --type-body-line: ${typography.body.lineHeight}px;
        --type-support-size: ${typography.supporting.fontSize}px;
        --type-support-line: ${typography.supporting.lineHeight}px;
        --type-table-size: ${typography.table.fontSize}px;
        --type-table-line: ${typography.table.lineHeight}px;
        --type-table-header-size: ${typography.tableHeader.fontSize}px;
        --type-table-header-line: ${typography.tableHeader.lineHeight}px;
        --type-caption-size: ${typography.caption.fontSize}px;
        --type-caption-line: ${typography.caption.lineHeight}px;
        --type-metric-size: ${typography.metric.fontSize}px;
        --type-metric-line: ${typography.metric.lineHeight}px;
      }
    `}</style>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ConfigProvider
        locale={zhCN}
        theme={antdTheme}
        pagination={{ showSizeChanger: true, totalBoundaryShowSizeChanger: 0 }}
      >
        <ThemeVariables />
        <AntdApp>
          <AntdOverlayGuard />
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </ErrorBoundary>
  );
}
