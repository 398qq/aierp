/**
 * useCustomersFilter — Stage 3 Day 1
 *
 * Encapsulates 9 filter / sort / scene states for the customers list page.
 * Pulled out of index.tsx (1703 lines) to enable single-responsibility
 * testing and reuse across the workbench / search / list views.
 *
 * URL sync: writes `q` and `scene` back to window.history so the user
 * can share a filtered URL (the rest of the filters stay in-memory for
 * v1 — adding them to the URL is a follow-up).
 */

import { useEffect, useState } from "react";
import type { SceneValue } from "../pages/customers/constants";

// Stage 3 Day 1: SceneValue is re-exported from the existing
// `customers/constants.tsx` to keep one source of truth.
// (Originally a duplicate here; consolidated after the first typecheck.)
export type { SceneValue };

export interface CustomersFilterState {
  q: string;
  scene: SceneValue;
  industry: string | undefined;
  level: string | undefined;
  region: string | undefined;
  source: string | undefined;
  creditLevel: string | undefined;
  sortBy: string;
  sortOrder: "asc" | "desc";
}

export interface UseCustomersFilterResult extends CustomersFilterState {
  // Setters accept either a direct value OR an updater function
  // (matches useState signature, lets callers do `setQ(c => c + "x")`).
  setQ: React.Dispatch<React.SetStateAction<string>>;
  setScene: React.Dispatch<React.SetStateAction<SceneValue>>;
  setIndustry: React.Dispatch<React.SetStateAction<string | undefined>>;
  setLevel: React.Dispatch<React.SetStateAction<string | undefined>>;
  setRegion: React.Dispatch<React.SetStateAction<string | undefined>>;
  setSource: React.Dispatch<React.SetStateAction<string | undefined>>;
  setCreditLevel: React.Dispatch<React.SetStateAction<string | undefined>>;
  setSort: (by: string, order: "asc" | "desc") => void;
  reset: () => void;
  /** True if any non-q filter is active (used to show a "clear" button). */
  isAnyFilterActive: boolean;
}

const VALID_SCENES: SceneValue[] = ["all", "key_accounts", "east_region", "expo_leads", "high_credit"];

const initial = (): CustomersFilterState => {
  const params = new URLSearchParams(window.location.search);
  const sceneParam = params.get("scene") as SceneValue | null;
  return {
    q: params.get("q")?.trim() || "",
    scene: sceneParam && VALID_SCENES.includes(sceneParam) ? sceneParam : "all",
    industry: undefined,
    level: undefined,
    region: undefined,
    source: undefined,
    creditLevel: undefined,
    sortBy: "id",
    sortOrder: "desc",
  };
};

export function useCustomersFilter(): UseCustomersFilterResult {
  const [state, setState] = useState<CustomersFilterState>(initial);

  // Sync q + scene to URL on change (debounced via effect)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (state.q) {
      params.set("q", state.q);
    } else {
      params.delete("q");
    }
    if (state.scene && state.scene !== "all") {
      params.set("scene", state.scene);
    } else {
      params.delete("scene");
    }
    const newSearch = params.toString();
    const current = window.location.search.replace(/^\?/, "");
    if (newSearch !== current) {
      window.history.replaceState({}, "", `${window.location.pathname}${newSearch ? "?" + newSearch : ""}`);
    }
  }, [state.q, state.scene]);

  const setters = {
    setQ: (v: React.SetStateAction<string>) =>
      setState((s) => ({ ...s, q: typeof v === "function" ? v(s.q) : v })),
    setScene: (v: React.SetStateAction<SceneValue>) =>
      setState((s) => ({ ...s, scene: typeof v === "function" ? v(s.scene) : v })),
    setIndustry: (v: React.SetStateAction<string | undefined>) =>
      setState((s) => ({ ...s, industry: typeof v === "function" ? v(s.industry) : v })),
    setLevel: (v: React.SetStateAction<string | undefined>) =>
      setState((s) => ({ ...s, level: typeof v === "function" ? v(s.level) : v })),
    setRegion: (v: React.SetStateAction<string | undefined>) =>
      setState((s) => ({ ...s, region: typeof v === "function" ? v(s.region) : v })),
    setSource: (v: React.SetStateAction<string | undefined>) =>
      setState((s) => ({ ...s, source: typeof v === "function" ? v(s.source) : v })),
    setCreditLevel: (v: React.SetStateAction<string | undefined>) =>
      setState((s) => ({ ...s, creditLevel: typeof v === "function" ? v(s.creditLevel) : v })),
    setSort: (sortBy: string, sortOrder: "asc" | "desc") =>
      setState((s) => ({ ...s, sortBy, sortOrder })),
    reset: () => setState(initial()),
  };

  const isAnyFilterActive =
    state.industry !== undefined ||
    state.level !== undefined ||
    state.region !== undefined ||
    state.source !== undefined ||
    state.creditLevel !== undefined;

  return { ...state, ...setters, isAnyFilterActive };
}
