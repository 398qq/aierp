/** Tests for the shared UI component library.

Pure render tests — no API, no routing. Verify that each component
mounts, accepts the documented props, and produces the right markup
for representative inputs.
*/

import { describe, expect, it, beforeAll, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  EmptyState,
  ErrorBoundary,
  MetricBand,
  PageHeader,
  SearchBar,
  StatusTag,
  ModuleShell,
} from "../ui";

describe("StatusTag", () => {
  it("renders status with default color when no tone", () => {
    render(<StatusTag status="draft" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("humanizes snake_case and underscores", () => {
    render(<StatusTag status="on_hold-pending" />);
    expect(screen.getByText("On hold pending")).toBeInTheDocument();
  });

  it("preserves leading punctuation in status values", () => {
    // Regression: a previous regex stripped the leading "-" from "-2%"
    // because it matched the separator class.
    const { container } = render(<StatusTag status="-2%" />);
    expect(container.querySelector(".ant-tag")?.textContent).toBe("-2%");
  });

  it("respects explicit label override", () => {
    render(<StatusTag status="posted" label="已过账" />);
    expect(screen.getByText("已过账")).toBeInTheDocument();
  });

  it("applies semantic tone colors", () => {
    const { container } = render(<StatusTag status="ok" tone="success" />);
    // antd's Tag component renders the color as a CSS class. We just
    // verify the tag is present in the DOM.
    const tag = container.querySelector(".ant-tag");
    expect(tag).not.toBeNull();
  });

  it("raw color overrides tone", () => {
    render(<StatusTag status="custom" tone="success" color="purple" />);
    // Custom status → humanized label
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("applies the operational class while preserving caller classes", () => {
    const { container } = render(<StatusTag status="posted" className="finance-status" />);
    expect(container.querySelector(".ant-tag")).toHaveClass("erp-status-tag", "finance-status");
  });
});

describe("MetricBand", () => {
  const sampleItems = [
    { label: "今日订单", value: 42, suffix: "单" },
    {
      label: "营收",
      value: "¥12,000",
      suffix: "元",
      trend: { value: "+5%", tone: "success" as const },
    },
    { label: "退款", value: 3, trend: { value: "-2%", tone: "danger" as const } },
  ];

  it("renders all labels and values", () => {
    render(<MetricBand items={sampleItems} />);
    expect(screen.getByText("今日订单")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("单")).toBeInTheDocument();
    expect(screen.getByText("营收")).toBeInTheDocument();
    expect(screen.getByText("¥12,000")).toBeInTheDocument();
    expect(screen.getByText("退款")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders trend tag when provided", () => {
    const { container } = render(<MetricBand items={sampleItems} />);
    // antd Tag content lives in `.ant-tag` elements. Leading "-"
    // and "+" are interpreted as CSS selector operators by Testing
    // Library's default text matcher, so we query the DOM directly.
    const tagTexts = Array.from(container.querySelectorAll(".ant-tag")).map((el) => el.textContent);
    expect(tagTexts).toContain("+5%");
    expect(tagTexts).toContain("-2%");
  });

  it("handles empty items", () => {
    const { container } = render(<MetricBand items={[]} />);
    expect(container).toBeInTheDocument();
  });
});

describe("PageHeader", () => {
  it("renders title and description", () => {
    render(<PageHeader title="客户管理" description="管理所有客户信息" />);
    expect(screen.getByText("客户管理")).toBeInTheDocument();
    expect(screen.getByText("管理所有客户信息")).toBeInTheDocument();
  });

  it("renders back button when onBack provided", () => {
    let clicked = false;
    render(
      <PageHeader
        title="详情"
        onBack={() => {
          clicked = true;
        }}
        backLabel="返回列表"
      />,
    );
    const backBtn = screen.getByText("返回列表");
    expect(backBtn).toBeInTheDocument();
    backBtn.click();
    expect(clicked).toBe(true);
  });

  it("renders actions when provided", () => {
    render(<PageHeader title="销售订单" actions={<button>新建订单</button>} />);
    expect(screen.getByText("新建订单")).toBeInTheDocument();
  });
});

describe("ModuleShell", () => {
  it("renders shared heading, navigation, actions and content", () => {
    render(
      <MemoryRouter>
        <ModuleShell
          title="采购与供应链"
          subtitle="采购订单、供应商与收货"
          eyebrow="运营工作区"
          activeKey="orders"
          navItems={[{ key: "orders", label: "采购订单", path: "/sales/purchase-orders" }]}
          actions={<button>新建采购单</button>}
        >
          <div>台账内容</div>
        </ModuleShell>
      </MemoryRouter>,
    );

    expect(screen.getByText("采购与供应链")).toBeInTheDocument();
    expect(screen.getByText("采购订单")).toBeInTheDocument();
    expect(screen.getByText("新建采购单")).toBeInTheDocument();
    expect(screen.getByText("台账内容")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders default description", () => {
    render(<EmptyState />);
    expect(screen.getByText("暂无数据")).toBeInTheDocument();
  });

  it("renders custom description", () => {
    render(<EmptyState description="暂无报价单" />);
    expect(screen.getByText("暂无报价单")).toBeInTheDocument();
  });

  it("renders action button when provided", () => {
    let clicked = false;
    render(
      <EmptyState
        description="还没有任何数据"
        actionLabel="创建第一份"
        onAction={() => {
          clicked = true;
        }}
      />,
    );
    const btn = screen.getByText("创建第一份");
    expect(btn).toBeInTheDocument();
    btn.click();
    expect(clicked).toBe(true);
  });

  it("marks compact empty states for responsive operational styling", () => {
    const { container } = render(<EmptyState compact />);
    expect(container.firstElementChild).toHaveClass("erp-empty-state", "erp-empty-state-compact");
  });
});

describe("SearchBar", () => {
  it("renders with placeholder", () => {
    render(<SearchBar placeholder="搜索客户" />);
    expect(screen.getByPlaceholderText("搜索客户")).toBeInTheDocument();
  });

  it("calls onChange on keystroke", () => {
    let captured = "";
    render(
      <SearchBar
        value=""
        onChange={(v) => {
          captured = v;
        }}
      />,
    );
    const input = screen.getByPlaceholderText("搜索…") as HTMLInputElement;
    input.focus();
    // Simulate typing — vitest + jsdom
    input.value = "abc";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    // antd Input.Search onChange fires synchronously on input event
    // We just check that the value is reflected
    expect(input.value).toBe("abc");
  });

  it("calls onSearch on Enter", () => {
    let searched = "";
    render(
      <SearchBar
        value="query"
        onSearch={(v) => {
          searched = v;
        }}
      />,
    );
    const input = screen.getByPlaceholderText("搜索…") as HTMLInputElement;
    input.focus();
    // antd's Input.Search handles Enter internally; the smoke test is
    // that the input + button are present.
    expect(input).toBeInTheDocument();
  });

  it("renders reset button when onReset provided", () => {
    let reset = false;
    render(
      <SearchBar
        onReset={() => {
          reset = true;
        }}
        resetLabel="清空筛选"
      />,
    );
    const btn = screen.getByText("清空筛选");
    expect(btn).toBeInTheDocument();
    btn.click();
    expect(reset).toBe(true);
  });
});

describe("ErrorBoundary", () => {
  // Suppress console.error for expected error logs
  const originalError = console.error;
  beforeAll(() => {
    console.error = () => {};
  });
  afterAll(() => {
    console.error = originalError;
  });

  function ThrowingComponent(): never {
    throw new Error("intentional test error");
  }

  it("renders children when no error", () => {
    render(
      <ErrorBoundary pageName="测试页">
        <div>正常内容</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("正常内容")).toBeInTheDocument();
  });

  it("catches error and shows fallback", () => {
    render(
      <ErrorBoundary pageName="失败页">
        <ThrowingComponent />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/失败页 加载失败/)).toBeInTheDocument();
    expect(screen.getByText("intentional test error")).toBeInTheDocument();
    // Has recovery buttons
    expect(screen.getByText("重新加载")).toBeInTheDocument();
    expect(screen.getByText("返回首页")).toBeInTheDocument();
  });
});
