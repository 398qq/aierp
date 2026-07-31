import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiCards } from "@/pages/dashboard/components/KpiCards";

describe("KpiCards", () => {
  it("renders total_alerts and severity with correct tone", () => {
    render(
      <KpiCards
        totalAlerts={5}
        severity="紧急"
        riskAreas={["sales"]}
        domainDistribution={[["low_stock", 3]]}
      />,
    );
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("紧急")).toBeInTheDocument();
  });

  it("renders risk_areas as danger tags", () => {
    render(
      <KpiCards totalAlerts={0} severity="正常" riskAreas={["a", "b"]} domainDistribution={[]} />,
    );
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
  });

  it("renders no-risk fallback when riskAreas is empty", () => {
    render(<KpiCards totalAlerts={0} severity="正常" riskAreas={[]} domainDistribution={[]} />);
    expect(screen.getByText("无")).toBeInTheDocument();
  });
});
