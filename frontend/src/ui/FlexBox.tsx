/**
 * FlexBox — drop-in replacements for the 3 most common inline-style patterns:
 *
 *   <FlexBox full>           → width:"100%" (153 occurrences)
 *   <FlexBox between>        → display:flex + justify-content:space-between
 *   <FlexBox gap={16}>       → display:flex + gap
 *   <FlexBox col gap={8}>     → vertical flex column
 *
 * Import as { FlexBox } from "@/ui".  All props forward to antd Flex.
 */

import React from "react";
import { Flex } from "antd";
import type { FlexProps } from "antd";

type FlexBoxProps = FlexProps & {
  full?: boolean;
  between?: boolean;
  col?: boolean;
};

export const FlexBox: React.FC<FlexBoxProps> = ({
  full,
  between,
  col,
  style,
  ...rest
}) => {
  const merged: React.CSSProperties = {
    ...(full ? { width: "100%" } : {}),
    ...(between ? { justifyContent: "space-between" } : {}),
    ...(typeof style === "object" && style !== null ? (style as React.CSSProperties) : {}),
  };

  return (
    <Flex
      vertical={col}
      {...(Object.keys(merged).length > 0 ? { style: merged } : {})}
      {...rest}
    />
  );
};

export default FlexBox;
