// Access control definitions for umi-plugin-access
// Used by routes/components to gate features by user roles.

interface CurrentUser {
  roles?: string[];
}

interface InitialState {
  currentUser?: CurrentUser;
}

export default function access(initialState: InitialState | undefined): {
  canAdmin: boolean;
  canSales: boolean;
  canFinance: boolean;
  canPurchase: boolean;
  canInventory: boolean;
} {
  const { currentUser } = initialState ?? {};
  const roles: string[] = currentUser?.roles ?? [];
  return {
    canAdmin: roles.includes("admin"),
    canSales: roles.includes("admin") || roles.includes("sales"),
    canFinance: roles.includes("admin") || roles.includes("finance"),
    canPurchase: roles.includes("admin") || roles.includes("purchase"),
    canInventory: roles.includes("admin") || roles.includes("inventory"),
  };
}
