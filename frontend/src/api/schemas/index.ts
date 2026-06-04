/** API response validation with zod.

The audit §3.1 / §5.3 called out that the frontend was using
`Record<string, unknown>` as a type escape hatch in 9 places
across `types/index.ts` and 60+ across `api/`. The structural
fix is:

1. Define a zod schema for the response data shape.
2. Derive the TypeScript type from the schema (`z.infer<...>`).
3. Wrap the `client.get`/`client.post` call in a `safeGet` /
   `safePost` helper that validates the response.

This file is the helper. The schemas live in sibling files
(`schemas/customer.ts`, `schemas/brand.ts`, …) and are imported
where they're needed.

The pilot (v6.3): only `customer.ts` and `brand.ts` schemas are
written. Adding more is a mechanical task — for each API
endpoint that needs runtime validation, write the schema,
import the helper, swap the call. No new patterns to learn.

**When to use `safeGet` vs `client.get`**:

- `safeGet`  : when you need runtime validation of the response
               shape. Use it for critical paths (write endpoints,
               user-facing lists, anything that powers a render
               decision).
- `client.get`: when the response is already type-checked by
               TypeScript (no `Record<string, unknown>` in the
               type chain) AND the cost of adding a zod schema
               isn't worth the runtime safety. The default for
               the ~17 existing API files.

The wider migration is documented in `docs/architecture/001-design-audit-2026-06-03.md`
§17 (next steps).
*/

import type { ZodType } from "zod";
import client from "../client";

/** Unwrap a `safeGet` response: returns just the `data` field,
 * validated by the zod schema. Throws on validation failure. */
export async function safeGet<T>(
  url: string,
  schema: ZodType<T>,
  config?: { params?: Record<string, unknown> },
): Promise<T> {
  const resp = await client.get(url, config);
  // Backend wraps every response in `{ code, msg, data }`; see
  // `app/schemas/common.py::ok()`. The `data` field is what we
  // want to validate.
  const payload = resp.data as { data?: unknown };
  return schema.parse(payload.data);
}

export async function safePost<TIn, TOut>(
  url: string,
  schema: ZodType<TOut>,
  data: TIn,
): Promise<TOut> {
  const resp = await client.post(url, data);
  const payload = resp.data as { data?: unknown };
  return schema.parse(payload.data);
}
