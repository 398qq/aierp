// Re-exports from per-bounded-context API client files.
// Each file is the canonical home for one bounded context.
// Importing from this index is equivalent to importing the file directly
// (TypeScript re-exports are transparent). Existing import sites work unchanged.

export { getApiErrorMessage } from "./client";
export * from "./ai";
export * from "./auth";
export * from "./brands";
export * from "./customers";
export * from "./dashboard";
export * from "./finance";
export * from "./notifications";
export * from "./products";
export * from "./purchase-orders";
export * from "./sales";
export * from "./samples";
export * from "./suppliers";
export * from "./tickets";
export * from "./users";
export * from "./visits";
