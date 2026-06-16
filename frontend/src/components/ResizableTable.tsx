import { useState, useCallback, type CSSProperties } from "react";
import { Resizable } from "react-resizable";
import type { ColumnsType, ColumnType } from "antd/es/table";
import "react-resizable/css/styles.css";

const handleStyle: CSSProperties = {
  position: "absolute", right: -5, bottom: 0, top: 0, zIndex: 1,
  width: 10, cursor: "col-resize",
};

function ResizableTitle(props: {
  onResize: (width: number) => void;
  width: number;
  children?: React.ReactNode;
  style?: CSSProperties;
  className?: string;
}) {
  const { onResize, width, ...rest } = props;
  return (
    <Resizable
      width={width}
      height={0}
      onResize={(_, { size }) => onResize(Math.max(60, size.width))}
      handle={<span className="react-resizable-handle" style={handleStyle} />}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...rest} style={{ ...rest.style, position: "relative" }} />
    </Resizable>
  );
}

/**
 * Makes Ant Design Table columns resizable by dragging header cell edges.
 *
 * Usage:
 *   const { columns, components } = useResizableColumns(baseColumns);
 *   <Table columns={columns} components={components} ... />
 */
export function useResizableColumns<T extends object>(
  baseColumns: ColumnsType<T>,
): { columns: ColumnsType<T>; components: Record<string, unknown> } {
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    for (const col of baseColumns) {
      const c = col as ColumnType<T>;
      const key = String(c.key || c.dataIndex || "");
      if (c.width) init[key] = Number(c.width);
    }
    return init;
  });

  const onResize = useCallback(
    (key: string) => (w: number) => setWidths((prev) => ({ ...prev, [key]: w })),
    [],
  );

  const columns = baseColumns.map((col) => {
    const c = col as ColumnType<T>;
    const key = String(c.key || c.dataIndex || "");
    const w = widths[key] ?? (col as ColumnType<T>).width;
    const patched: ColumnType<T> = { ...col, width: w };
    if (col.title) {
      patched.onHeaderCell = () => ({
        width: w,
        onResize: onResize(key),
      } as any);
    }
    return patched;
  }) as ColumnsType<T>;

  const components = { header: { cell: ResizableTitle } };

  return { columns, components };
}
