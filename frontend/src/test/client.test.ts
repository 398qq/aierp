import type { AxiosAdapter, AxiosResponse } from "axios";
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

describe("api client network resilience", () => {
  afterEach(() => {
    client.defaults.adapter = originalAdapter;
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("retries a transient GET failure and keeps the request id", async () => {
    vi.useFakeTimers();
    const requestIds: Array<unknown> = [];
    let attempts = 0;
    client.defaults.adapter = async (config) => {
      attempts += 1;
      requestIds.push(config.headers.get("X-Request-ID"));
      if (attempts === 1) {
        return Promise.reject({
          config,
          response: { status: 503, data: {}, headers: { "retry-after": "0" } },
        });
      }
      return { config, status: 200, statusText: "OK", headers: {}, data: { ok: true } } as AxiosResponse;
    };

    const responsePromise = client.get("/health");
    await vi.runAllTimersAsync();

    await expect(responsePromise).resolves.toMatchObject({ status: 200 });
    expect(attempts).toBe(2);
    expect(requestIds[0]).toMatch(/^req_[a-f0-9-]+$/);
    expect(requestIds[1]).toBe(requestIds[0]);
  });

  it("never automatically retries a write request", async () => {
    let attempts = 0;
    client.defaults.adapter = (config) => {
      attempts += 1;
      return Promise.reject({ config, code: "ERR_NETWORK", message: "Network Error" });
    };

    await expect(client.post("/sales-orders", { customer_id: 1 })).rejects.toBeTruthy();
    expect(attempts).toBe(1);
  });
});
