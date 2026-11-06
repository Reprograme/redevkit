export const API_URL = "https://example.test";
export const MAX_ITEMS = 10;
export async function load(id: string) {
  const user = await fetchUser(id);
  const orders = await fetchOrders(user.accountId);
  return { user, orders };
}
