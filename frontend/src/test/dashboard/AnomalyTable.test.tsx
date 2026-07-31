import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnomalyTable } from "@/pages/dashboard/components/AnomalyTable";
import type { AnomalyRow } from "@/types/watchtower";

const sampleRows: AnomalyRow[] = [
  { domain: "churn_risk", domainLabel: "客户流失风险", name: "客户A", signal: "90天无订单" },
  { domain: "low_stock", domainLabel: "低库存", name: "SKU-X", signal: "qty=2 / safety=10" },
];

describe("AnomalyTable", () => {
  it("renders all rows", () => {
    render(<AnomalyTable rows={sampleRows} />);
    expect(screen.getByText("客户A")).toBeInTheDocument();
    expect(screen.getByText("SKU-X")).toBeInTheDocument();
  });

  it("renders empty state when rows empty", () => {
    render(<AnomalyTable rows={[]} />);
    expect(screen.getByText(/未检测到异常/)).toBeInTheDocument();
  });
});
