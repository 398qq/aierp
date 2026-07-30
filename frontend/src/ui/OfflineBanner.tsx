/** OfflineBanner — floating warning when the browser loses network.

Uses useSyncExternalStore to subscribe to online/offline events —
no state library, no effects. Renders nothing while online.

Pattern source: ant-design-pro v6.0.1 (#11756).
*/

import { useSyncExternalStore } from "react";
import { Alert } from "antd";

function subscribeOnlineStatus(callback: () => void): () => void {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getOnlineStatus(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export function OfflineBanner() {
  const isOnline = useSyncExternalStore(subscribeOnlineStatus, getOnlineStatus, () => true);

  if (isOnline) return null;

  return (
    <Alert
      type="warning"
      showIcon
      title="网络连接已断开，部分功能可能不可用"
      style={{
        position: "fixed",
        top: 8,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 1100,
        maxWidth: 480,
      }}
    />
  );
}
