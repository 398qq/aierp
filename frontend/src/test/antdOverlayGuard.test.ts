import { afterEach, describe, expect, it } from "vitest";
import { cleanupStaleAntdOverlays } from "@/ui/antdOverlayCleanup";

afterEach(() => {
  document.body.innerHTML = "";
  document.body.removeAttribute("class");
  document.body.removeAttribute("style");
});

describe("AntdOverlayGuard", () => {
  it("restores body interaction without removing Antd portal nodes", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.style.pointerEvents = "none";
    document.body.innerHTML = `
      <div class="ant-picker-dropdown ant-picker-dropdown-hidden"></div>
      <div class="ant-modal-root">
        <div class="ant-modal-mask" style="display: none;"></div>
        <div class="ant-modal-wrap" style="display: none;"></div>
      </div>
    `;

    cleanupStaleAntdOverlays();

    expect(document.querySelector(".ant-picker-dropdown")).not.toBeNull();
    expect(document.querySelector(".ant-modal-root")).not.toBeNull();
    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(false);
    expect(document.body.style.overflow).toBe("");
    expect(document.body.style.pointerEvents).toBe("");
  });

  it("keeps body locked when drawer root is visible", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-drawer-root">
        <div class="ant-drawer-mask" style="display: block; width: 100px; height: 100px;"></div>
        <div class="ant-drawer" style="display: block; width: 100px; height: 100px;"></div>
      </div>
    `;
    document.querySelectorAll<HTMLElement>(".ant-drawer-root *").forEach((el) => {
      el.getBoundingClientRect = () =>
        ({ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    });

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body when no blocking layers exist", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.style.pointerEvents = "none";
    document.body.innerHTML = `<div></div>`;

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(false);
    expect(document.body.style.overflow).toBe("");
    expect(document.body.style.pointerEvents).toBe("");
  });

  it("ignores aria-hidden blocking layers", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-modal-root">
        <div class="ant-modal-mask" aria-hidden="true" style="display: block; width: 100px; height: 100px;"></div>
        <div class="ant-modal-wrap" aria-hidden="true" style="display: block; width: 100px; height: 100px;">
          <div class="ant-modal" aria-hidden="true" style="display: block; width: 100px; height: 100px;"></div>
        </div>
      </div>
    `;
    document.querySelectorAll<HTMLElement>(".ant-modal-root *").forEach((el) => {
      el.getBoundingClientRect = () =>
        ({ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    });

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(false);
    expect(document.body.style.overflow).toBe("");
  });

  it("keeps body locked when image preview is visible", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-image-preview-root">
        <div class="ant-image-preview-mask" style="display: block; width: 100px; height: 100px;"></div>
        <div class="ant-image-preview-wrap" style="display: block; width: 100px; height: 100px;"></div>
      </div>
    `;
    document.querySelectorAll<HTMLElement>(".ant-image-preview-root *").forEach((el) => {
      el.getBoundingClientRect = () =>
        ({ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    });

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("keeps body locked when modal has visible mask but hidden wrap", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-modal-root">
        <div class="ant-modal-mask" style="display: block; width: 100px; height: 100px;"></div>
        <div class="ant-modal-wrap" style="display: none;"></div>
      </div>
    `;
    const mask = document.querySelector(".ant-modal-mask") as HTMLElement;
    mask.getBoundingClientRect = () =>
      ({ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("keeps body locked when modal has hidden mask but visible wrap", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-modal-root">
        <div class="ant-modal-mask" style="display: none;"></div>
        <div class="ant-modal-wrap" style="display: block; width: 100px; height: 100px;">
          <div class="ant-modal" style="display: block; width: 100px; height: 100px;"></div>
        </div>
      </div>
    `;
    document.querySelectorAll<HTMLElement>(".ant-modal-wrap, .ant-modal").forEach((el) => {
      el.getBoundingClientRect = () =>
        ({ width: 100, height: 100, top: 0, left: 0, right: 100, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    });

    cleanupStaleAntdOverlays();

    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("keeps visible blocking layers mounted", () => {
    document.body.className = "ant-scrolling-effect";
    document.body.style.overflow = "hidden";
    document.body.innerHTML = `
      <div class="ant-modal-root">
        <div class="ant-modal-mask" style="display: block; width: 100px; height: 100px;"></div>
        <div class="ant-modal-wrap" style="display: block; width: 100px; height: 100px;">
          <div class="ant-modal" style="display: block; width: 100px; height: 100px;"></div>
        </div>
      </div>
    `;
    document.querySelectorAll<HTMLElement>(".ant-modal-root *").forEach((element) => {
      element.getBoundingClientRect = () =>
        ({
          width: 100,
          height: 100,
          top: 0,
          left: 0,
          right: 100,
          bottom: 100,
          x: 0,
          y: 0,
          toJSON: () => ({}),
        }) as DOMRect;
    });

    cleanupStaleAntdOverlays();

    expect(document.querySelector(".ant-modal-root")).not.toBeNull();
    expect(document.body.classList.contains("ant-scrolling-effect")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
  });
});
