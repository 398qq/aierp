import { Component } from "react";
import { Button, Result } from "antd";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Result
          status="error"
          title="页面发生错误"
          subTitle={this.state.error.message}
          extra={
            <Button type="primary" onClick={() => this.setState({ error: null })}>
              重试
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
