import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopActions } from "@/pages/dashboard/components/TopActions";

describe("TopActions", () => {
  it("renders list of items in order", () => {
    render(<TopActions items={["联系客户A", "补货 SKU-X"]} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("1. 联系客户A");
    expect(items[1]).toHaveTextContent("2. 补货 SKU-X");
  });

  it("renders nothing when items empty", () => {
    const { container } = render(<TopActions items={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
