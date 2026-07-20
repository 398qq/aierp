import type { PropsWithChildren } from "react";
import { createPortal } from "react-dom";

export function SalesPrintPortal({ children }: PropsWithChildren) {
  return createPortal(children, document.body);
}
