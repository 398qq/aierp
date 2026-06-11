/**
 * useColumnResize — drag-to-resize columns for Ant Design Table.
 *
 * Injects resize handles into the DOM after render via useEffect,
 * bypassing Ant Design's internal title rendering constraints.
 * Only commits width on mouse-up. Minimum width: 60px.
 */

import { useEffect, useRef, useState } from "react";

export function useColumnResize<T>(baseColumns: T[]): T[] {
  const [widths, setWidths] = useState<Record<string, number>>({});
  const dragRef = useRef<{ key: string; originX: number; originW: number } | null>(null);

  const patchedRef = useRef(new Set<Element>());

  useEffect(() => {
    const ths = document.querySelectorAll(".ant-table-thead th");
    ths.forEach((th, i) => {
      if (patchedRef.current.has(th)) return;
      const col = baseColumns[i] as Record<string, unknown> | undefined;
      if (!col) return;
      const key = (col.dataIndex as string) || (col.key as string) || "";
      if (!key || key === "actions") return;
      patchedRef.current.add(th);

      const handle = document.createElement("span");
      handle.setAttribute("data-resize-handle", "");
      Object.assign(handle.style, {
        position: "absolute",
        right: "0",
        top: "0",
        bottom: "0",
        width: "8px",
        cursor: "col-resize",
        zIndex: "1",
        borderRight: "2px solid transparent",
        transition: "border-color 0.15s",
      } as CSSStyleDeclaration);
      handle.addEventListener("mouseenter", () => {
        handle.style.borderRightColor = "#1677ff";
      });
      handle.addEventListener("mouseleave", () => {
        handle.style.borderRightColor = "transparent";
      });

      let originX = 0;
      let originW = 0;

      handle.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        e.preventDefault();
        originX = e.pageX;
        originW = (th as HTMLElement).offsetWidth;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";

        const onMove = (ev: MouseEvent) => {
          const newW = Math.max(60, originW + ev.pageX - originX);
          const idx = Array.from(th.parentElement?.children || []).indexOf(th);
          document.querySelectorAll(".ant-table-thead th").forEach((hdr, j) => {
            if (j === idx) {
              (hdr as HTMLElement).style.width = `${newW}px`;
              (hdr as HTMLElement).style.minWidth = `${newW}px`;
            }
          });
          document.querySelectorAll("colgroup col").forEach((cl, j) => {
            if (j === idx) {
              (cl as HTMLElement).style.width = `${newW}px`;
            }
          });
        };

        const onUp = (ev: MouseEvent) => {
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
          document.removeEventListener("mousemove", onMove);
          document.removeEventListener("mouseup", onUp);
          const finalW = Math.max(60, originW + ev.pageX - originX);
          setWidths((prev) => ({ ...prev, [key]: finalW }));
        };

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
      });

      (th as HTMLElement).style.position = "relative";
      th.appendChild(handle);
    });
  }, [baseColumns]);

  return baseColumns.map((col) => {
    const c = col as Record<string, unknown>;
    const key = (c.dataIndex as string) || (c.key as string) || "";
    const override = key ? widths[key] : undefined;
    return override ? ({ ...c, width: override } as unknown as T) : col;
  }) as T[];
}
