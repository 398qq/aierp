/** UOM (Unit of Measure) Select — fetches from /api/v1/uoms and renders a grouped dropdown.

Usage:
    <UomSelect uomType="count" value={unit} onChange={setUnit} />
    <UomSelect uomType="package" value={minPackUnit} onChange={setMinPackUnit} />
*/

import { useEffect, useRef, useState } from "react";
import { Select, Spin, Typography } from "antd";
import client from "../api/client";

interface UomItem {
  code: string;
  name: string;
  uom_type: string;
  category: string | null;
}

interface UomSelectProps {
  uomType?: "count" | "package";
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  style?: React.CSSProperties;
  allowClear?: boolean;
}

export function UomSelect({
  uomType,
  value,
  onChange,
  placeholder,
  style,
  allowClear = true,
}: UomSelectProps) {
  const [items, setItems] = useState<UomItem[]>([]);
  const [loading, setLoading] = useState(false);
  const fetched = useRef(false);

  useEffect(() => {
    if (fetched.current) return;
    fetched.current = true;
    setLoading(true);
    const params = uomType ? { uom_type: uomType } : {};
    client
      .get<{ code: number; msg: string; data: UomItem[] }>("/uoms", { params })
      .then((r) => setItems(r.data.data || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [uomType]);

  // Group by category for better UX
  const grouped = items.reduce<Record<string, UomItem[]>>((acc, item) => {
    const cat = item.category || "other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  const categoryLabels: Record<string, string> = {
    count: "计数单位",
    unit: "台/部/卡/板/模组",
    sheet: "张/卷",
    batch: "批次",
    reel: "盘装",
    tube: "管装",
    tray: "托盘装",
    box: "盒装",
    bag: "袋装",
    carton: "箱装",
    tape: "编带",
    bulk: "散装",
    pack: "包装",
    bundle: "捆",
    container: "罐/瓶/桶",
    loose: "零散",
    other: "其他",
  };

  if (loading) return <Spin size="small" />;

  return (
    <Select
      showSearch
      value={value || undefined}
      onChange={onChange}
      placeholder={placeholder || "选择单位"}
      style={{ width: "100%", ...style }}
      allowClear={allowClear}
      optionFilterProp="label"
    >
      {Object.entries(grouped).map(([cat, catItems]) => (
        <Select.OptGroup key={cat} label={categoryLabels[cat] || cat}>
          {catItems.map((item) => (
            <Select.Option
              key={item.code}
              value={item.code}
              label={`${item.name} (${item.code})`}
            >
              {item.name}{" "}
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {item.code}
              </Typography.Text>
            </Select.Option>
          ))}
        </Select.OptGroup>
      ))}
    </Select>
  );
}
