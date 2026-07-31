import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScanHeader } from "@/pages/dashboard/components/ScanHeader";

describe("ScanHeader", () => {
  it("renders title and timestamp", () => {
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={false} onRefresh={() => {}} />);
    expect(screen.getByText("全局监控中心")).toBeInTheDocument();
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it("calls onRefresh when refresh button clicked", async () => {
    const onRefresh = vi.fn();
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={false} onRefresh={onRefresh} />);
    await userEvent.click(screen.getByRole("button", { name: /刷新/ }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("shows loading state on refresh button", () => {
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={true} onRefresh={() => {}} />);
    expect(screen.getByRole("button", { name: /刷新/ })).toHaveAttribute("aria-busy", "true");
  });
});
