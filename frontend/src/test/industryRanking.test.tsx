import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildIndustryRanking, IndustryRanking } from "../ui/IndustryRanking";

describe("IndustryRanking", () => {
  it("sorts values without mutating the caller and aggregates the remainder", () => {
    const source = [
      { name: "零售", value: 2 },
      { name: "制造", value: 8 },
      { name: "医疗", value: 5 },
      { name: "教育", value: 3 },
    ];

    expect(buildIndustryRanking(source, 2)).toEqual([
      { name: "制造", value: 8 },
      { name: "医疗", value: 5 },
      { name: "其他", value: 5 },
    ]);
    expect(source.map((item) => item.name)).toEqual(["零售", "制造", "医疗", "教育"]);
  });

  it("ignores invalid values and prevents negative progress", () => {
    expect(
      buildIndustryRanking([
        { name: "有效", value: 4 },
        { name: "负数", value: -2 },
        { name: "无效", value: Number.NaN },
      ]),
    ).toEqual([
      { name: "有效", value: 4 },
      { name: "负数", value: 0 },
    ]);
  });

  it("renders ranked values through the shared visual implementation", () => {
    render(
      <IndustryRanking
        items={[
          { name: "医疗", value: 5 },
          { name: "制造", value: 8 },
        ]}
      />,
    );

    expect(screen.getByText("1. 制造")).toBeInTheDocument();
    expect(screen.getByText("2. 医疗")).toBeInTheDocument();
    expect(screen.getByLabelText("制造 8")).toBeInTheDocument();
  });

  it("renders a stable empty state", () => {
    render(<IndustryRanking items={[]} emptyDescription="没有行业统计" />);
    expect(screen.getByText("没有行业统计")).toBeInTheDocument();
  });
});
