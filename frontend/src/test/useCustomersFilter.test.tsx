/**
 * useCustomersFilter tests — Stage 3 Day 1.
 *
 * Verifies the extracted filter hook matches the original inline
 * behavior of customers/index.tsx (lines 170-180 of the legacy file).
 */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useCustomersFilter } from "../hooks/useCustomersFilter";

describe("useCustomersFilter", () => {
  beforeEach(() => {
    // Clean URL
    window.history.replaceState({}, "", "/");
  });
  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  it("initializes with empty filters + default sort", () => {
    const { result } = renderHook(() => useCustomersFilter());
    expect(result.current.q).toBe("");
    expect(result.current.scene).toBe("all");
    expect(result.current.industry).toBeUndefined();
    expect(result.current.sortBy).toBe("id");
    expect(result.current.sortOrder).toBe("desc");
    expect(result.current.isAnyFilterActive).toBe(false);
  });

  it("initializes q from URL on mount", () => {
    window.history.replaceState({}, "", "/?q=acme");
    const { result } = renderHook(() => useCustomersFilter());
    expect(result.current.q).toBe("acme");
  });

  it("setQ updates q state", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setQ("hello"));
    expect(result.current.q).toBe("hello");
  });

  it("setQ accepts updater function (matches useState API)", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setQ("acme"));
    act(() => result.current.setQ((c) => c + "-corp"));
    expect(result.current.q).toBe("acme-corp");
  });

  it("setScene switches scene", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setScene("key_accounts"));
    expect(result.current.scene).toBe("key_accounts");
  });

  it("setIndustry marks filter active", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setIndustry("电子"));
    expect(result.current.industry).toBe("电子");
    expect(result.current.isAnyFilterActive).toBe(true);
  });

  it("q alone does NOT count as filter active (search is separate)", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setQ("test"));
    expect(result.current.isAnyFilterActive).toBe(false);
  });

  it("setSort changes both by and order", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setSort("name", "asc"));
    expect(result.current.sortBy).toBe("name");
    expect(result.current.sortOrder).toBe("asc");
  });

  it("reset clears all filters back to default", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => {
      result.current.setIndustry("电子");
      result.current.setLevel("A");
      result.current.setSort("name", "asc");
    });
    expect(result.current.isAnyFilterActive).toBe(true);
    act(() => result.current.reset());
    expect(result.current.industry).toBeUndefined();
    expect(result.current.level).toBeUndefined();
    expect(result.current.sortBy).toBe("id");
    expect(result.current.sortOrder).toBe("desc");
    expect(result.current.isAnyFilterActive).toBe(false);
  });

  it("URL syncs q to history.replaceState on change", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setQ("acme"));
    // Effect runs after render
    return Promise.resolve().then(() => {
      const url = new URL(window.location.href);
      expect(url.searchParams.get("q")).toBe("acme");
    });
  });

  it("URL syncs scene to history.replaceState", () => {
    const { result } = renderHook(() => useCustomersFilter());
    act(() => result.current.setScene("key_accounts"));
    return Promise.resolve().then(() => {
      const url = new URL(window.location.href);
      expect(url.searchParams.get("scene")).toBe("key_accounts");
    });
  });

  it("URL removes q when q is cleared", () => {
    window.history.replaceState({}, "", "/?q=old");
    const { result } = renderHook(() => useCustomersFilter());
    expect(result.current.q).toBe("old");
    act(() => result.current.setQ(""));
    return Promise.resolve().then(() => {
      const url = new URL(window.location.href);
      expect(url.searchParams.get("q")).toBeNull();
    });
  });

  it("URL removes scene when scene goes back to all", () => {
    window.history.replaceState({}, "", "/?scene=key_accounts");
    const { result } = renderHook(() => useCustomersFilter());
    expect(result.current.scene).toBe("key_accounts");
    act(() => result.current.setScene("all"));
    return Promise.resolve().then(() => {
      const url = new URL(window.location.href);
      expect(url.searchParams.get("scene")).toBeNull();
    });
  });
});
