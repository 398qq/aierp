export default function access(initialState: { currentUser?: { roles?: string[] } }) {
  const { currentUser } = initialState ?? {};
  const roles = currentUser?.roles ?? [];
  return {
    canAdmin: roles.includes("admin"),
    canSales: roles.includes("admin") || roles.includes("sales"),
    canFinance: roles.includes("admin") || roles.includes("finance"),
  };
}
