const BLOCKING_ROOT_SELECTOR = [
  ".ant-modal-root",
  ".ant-drawer-root",
  ".ant-image-preview-root",
].join(",");

function isVisible(element: Element) {
  if (!(element instanceof HTMLElement)) return false;
  if (!element.isConnected) return false;
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
    return false;
  }
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function hasVisibleBlockingLayer(root: Element) {
  return [
    ".ant-modal",
    ".ant-modal-wrap",
    ".ant-modal-mask",
    ".ant-drawer",
    ".ant-drawer-mask",
    ".ant-image-preview-wrap",
    ".ant-image-preview-mask",
  ].some((selector) =>
    Array.from(root.querySelectorAll(selector)).some((element) => {
      if (element.getAttribute("aria-hidden") === "true") return false;
      return isVisible(element);
    }),
  );
}

function hasActiveBlockingLayer() {
  return Array.from(document.querySelectorAll(BLOCKING_ROOT_SELECTOR)).some(hasVisibleBlockingLayer);
}

function restoreBodyInteractionIfIdle() {
  if (hasActiveBlockingLayer()) return;
  document.body.classList.remove("ant-scrolling-effect");

  if (document.body.style.overflow === "hidden") {
    document.body.style.overflow = "";
  }
  if (document.body.style.pointerEvents === "none") {
    document.body.style.pointerEvents = "";
  }
}

export function cleanupStaleAntdOverlays() {
  restoreBodyInteractionIfIdle();
}
