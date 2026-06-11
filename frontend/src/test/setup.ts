import { vi } from "vitest";
import "@testing-library/jest-dom/vitest";

// localStorage stub
const store: Record<string, string> = {};
vi.stubGlobal("localStorage", {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value; },
  removeItem: (key: string) => { delete store[key]; },
  clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
  get length() { return Object.keys(store).length; },
  key: (i: number) => Object.keys(store)[i] ?? null,
});

// Suppress act() warnings in tests
const originalError = console.error;
console.error = (...args: unknown[]) => {
  const msg = typeof args[0] === "string" ? args[0] : "";
  if (msg.includes("act(")) return;
  originalError.call(console, ...args);
};

// window.matchMedia stub (Ant Design uses it for responsive)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ResizeObserver stub (required by Ant Design's @rc-component/resize-observer)
class ResizeObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

// IntersectionObserver stub
class IntersectionObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  root = null;
  rootMargin = "";
  thresholds = [];
  takeRecords = () => [];
}
vi.stubGlobal("IntersectionObserver", IntersectionObserverStub);

// scrollIntoView stub
Element.prototype.scrollIntoView = vi.fn();

// getComputedStyle stub (Ant Design uses it for some utils)
const origGetComputedStyle = window.getComputedStyle;
window.getComputedStyle = ((el: Element, pseudoElt?: string | null) => {
  try {
    return origGetComputedStyle(el, pseudoElt);
  } catch {
    return {} as CSSStyleDeclaration;
  }
}) as typeof window.getComputedStyle;
