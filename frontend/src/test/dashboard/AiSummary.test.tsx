import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AiSummary } from "@/pages/dashboard/components/AiSummary";

describe("AiSummary", () => {
  it("renders the AI summary text", () => {
    render(<AiSummary text="今日系统运行正常。" />);
    expect(screen.getByText("今日系统运行正常。")).toBeInTheDocument();
    expect(screen.getByText("AI 分析摘要")).toBeInTheDocument();
  });

  it("renders empty text fallback without crashing", () => {
    render(<AiSummary text="" />);
    expect(screen.getByText("AI 分析摘要")).toBeInTheDocument();
  });
});
