import { useEffect } from "react";
import { cleanupStaleAntdOverlays } from "./antdOverlayCleanup";

export default function AntdOverlayGuard() {
  useEffect(() => {
    let frame = 0;
    const scheduleCleanup = () => {
      window.clearTimeout(frame);
      frame = window.setTimeout(cleanupStaleAntdOverlays, 180);
    };

    const observer = new MutationObserver(scheduleCleanup);
    observer.observe(document.body, {
      attributes: true,
      childList: true,
      subtree: true,
      attributeFilter: ["class", "style", "aria-hidden"],
    });

    document.addEventListener("transitionend", scheduleCleanup, true);
    document.addEventListener("animationend", scheduleCleanup, true);
    window.addEventListener("focus", scheduleCleanup);
    scheduleCleanup();

    return () => {
      window.clearTimeout(frame);
      observer.disconnect();
      document.removeEventListener("transitionend", scheduleCleanup, true);
      document.removeEventListener("animationend", scheduleCleanup, true);
      window.removeEventListener("focus", scheduleCleanup);
    };
  }, []);

  return null;
}
