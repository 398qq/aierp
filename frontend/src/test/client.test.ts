import type { AxiosAdapter } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import client from "../api/client";

const originalAdapter = client.defaults.adapter;

function mockUnauthorizedAdapter(): AxiosAdapter {
  return (config) => Promise.reject({
    config,
    response: {
      status: 401,
      data: { msg: "Missing token" },
      headers: {},
    },
  });
}

describe("api client auth handling", () => {
  afterEach(() => {
    client.defaults.adapter = originalAdapter;
    window.history.pushState({}, "", "/");
    vi.restoreAllMocks();
  });

  it("does not hard-redirect when the auth probe fails on a public page", async () => {
    window.history.pushState({}, "", "/inquiry");
    client.defaults.adapter = mockUnauthorizedAdapter();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await expect(client.get("/auth/me")).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(window.location.pathname).toBe("/inquiry");
    expect(consoleError).not.toHaveBeenCalled();
  });
});
