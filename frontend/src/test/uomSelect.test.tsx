import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import client from "../api/client";
import { UomSelect } from "../ui/UomSelect";

vi.mock("../api/client", () => ({
  default: { get: vi.fn() },
}));

const mockedGet = vi.mocked(client.get);

describe("UomSelect", () => {
  beforeEach(() => mockedGet.mockReset());

  it("loads and renders grouped UOM options", async () => {
    mockedGet.mockResolvedValue({
      data: {
        code: 0,
        msg: "ok",
        data: [{ code: "PCS", name: "个", uom_type: "count", category: "count" }],
      },
    });

    render(<UomSelect uomType="count" />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/uoms", { params: { uom_type: "count" } }));
    fireEvent.mouseDown(await screen.findByRole("combobox"));

    expect(await screen.findByText("计数单位")).toBeInTheDocument();
    expect(screen.getByText("个")).toBeInTheDocument();
    expect(screen.getAllByText("PCS")).not.toHaveLength(0);
  });

  it("reloads options when the UOM type changes", async () => {
    mockedGet.mockResolvedValue({ data: { code: 0, msg: "ok", data: [] } });
    const { rerender } = render(<UomSelect uomType="count" />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(1));

    rerender(<UomSelect uomType="package" />);

    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));
    expect(mockedGet).toHaveBeenLastCalledWith("/uoms", { params: { uom_type: "package" } });
  });
});
