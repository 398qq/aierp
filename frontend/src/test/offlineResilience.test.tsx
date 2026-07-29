/** Tests for the offline resilience utilities:
- chunkError detection (pure function)
- OfflineBanner online / offline transitions
- ErrorBoundary chunk vs generic copy
*/

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ErrorBoundary, OfflineBanner } from "../ui";
import { isChunkLoadError, isOffline } from "../ui/chunkError";

function ChunkThrower(): React.ReactElement {
  throw new Error("Loading chunk 42 failed.");
}

function GenericThrower(): React.ReactElement {
  throw new Error("boom");
}

describe("isChunkLoadError", () => {
  it("matches ChunkLoadError by name", () => {
    const err = new Error("ignored message");
    err.name = "ChunkLoadError";
    expect(isChunkLoadError(err)).toBe(true);
  });

  it("matches the webpack-style 'Loading chunk ... failed.'", () => {
    expect(isChunkLoadError(new Error("Loading chunk 42 failed."))).toBe(true);
  });

  it("matches the Vite/Umi 'Failed to fetch dynamically imported module'", () => {
    expect(
      isChunkLoadError(new Error("Failed to fetch dynamically imported module: /pages/foo.js")),
    ).toBe(true);
  });

  it("returns false for unrelated errors", () => {
    expect(isChunkLoadError(new Error("boom"))).toBe(false);
  });
});

describe("isOffline", () => {
  const originalOnLine = navigator.onLine;
  afterEach(() => {
    Object.defineProperty(navigator, "onLine", {
      value: originalOnLine,
      configurable: true,
    });
  });

  it("returns true when navigator.onLine is false", () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
    expect(isOffline()).toBe(true);
  });

  it("returns false when navigator.onLine is true", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    expect(isOffline()).toBe(false);
  });
});

describe("OfflineBanner", () => {
  const originalOnLine = navigator.onLine;
  let addedEvents: string[] = [];

  beforeEach(() => {
    addedEvents = [];
    window.addEventListener = vi.fn((event: string) => {
      addedEvents.push(event);
    }) as typeof window.addEventListener;
    window.removeEventListener = vi.fn() as typeof window.removeEventListener;
  });

  afterEach(() => {
    Object.defineProperty(navigator, "onLine", {
      value: originalOnLine,
      configurable: true,
    });
  });

  it("renders nothing while online", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    const { container } = render(<OfflineBanner />);
    expect(container.querySelector(".ant-alert-warning")).toBeNull();
  });

  it("renders an alert when offline", () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
    render(<OfflineBanner />);
    expect(screen.getByText(/网络连接已断开/)).toBeInTheDocument();
  });

  it("subscribes to online and offline events", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    render(<OfflineBanner />);
    expect(addedEvents).toContain("online");
    expect(addedEvents).toContain("offline");
  });
});

describe("ErrorBoundary chunk awareness", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows generic copy with pageName for non-chunk errors", () => {
    render(
      <ErrorBoundary pageName="测试页">
        <GenericThrower />
      </ErrorBoundary>,
    );
    expect(screen.getByText("测试页 加载失败")).toBeInTheDocument();
  });

  it("shows chunk-aware copy when ChunkLoadError fires", () => {
    render(
      <ErrorBoundary>
        <ChunkThrower />
      </ErrorBoundary>,
    );
    expect(screen.getByText("页面资源加载失败")).toBeInTheDocument();
  });

  it("does not error from the reload button when clicked", () => {
    render(
      <ErrorBoundary>
        <GenericThrower />
      </ErrorBoundary>,
    );
    fireEvent.click(screen.getByRole("button", { name: /重新加载/ }));
  });
});
