// @ts-expect-error - Outlet is a Umi convention, not in @umijs/max type definitions
import { Outlet } from "@umijs/max";
import type { ReactElement } from "react";

export default function BlankLayout(): ReactElement {
  return <Outlet />;
}
