/** SearchBar — consistent filter input row.

Standardizes the search input pattern that appears at the top of every
list page:

  [🔍 搜索 / keyword …]                                    [筛选] [重置]

Wraps antd `Input.Search` with sensible defaults (allowClear, debounced
onChange, placeholder). The `onSearch` callback fires on Enter or
clicking the search icon; `onChange` fires on every keystroke for
pages that need live filtering.

Usage:
  <SearchBar
    placeholder="搜索客户名 / 编码 / 联系人"
    value={q}
    onChange={setQ}
    onSearch={() => fetch(1)}
    onReset={resetFilters}
  />
*/

import { Button, Input, Space } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { ChangeEvent } from "react";

export interface SearchBarProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (value: string) => void;
  onReset?: () => void;
  resetLabel?: string;
  width?: number | string;
}

export function SearchBar({
  placeholder = "搜索…",
  value,
  onChange,
  onSearch,
  onReset,
  resetLabel = "重置",
  width = 280,
}: SearchBarProps) {
  return (
    <Space style={rootStyle}>
      <Input.Search
        placeholder={placeholder}
        value={value}
        allowClear
        enterButton={<SearchOutlined />}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange?.(e.target.value)}
        onSearch={(v: string) => onSearch?.(v)}
        style={{ width }}
      />
      {onReset && (
        <Button icon={<ReloadOutlined />} onClick={onReset}>
          {resetLabel}
        </Button>
      )}
    </Space>
  );
}

const rootStyle = { marginBottom: 12 } as const;
