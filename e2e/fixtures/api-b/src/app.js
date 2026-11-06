// Minimal inventory API (no dependencies).
import { appVersion } from "./version.js";

const items = [
  { id: 1, name: "parafuso", qty: 120 },
  { id: 2, name: "porca", qty: 80 },
];

export const handle = (method, url) => {
  const { pathname } = new URL(url, "http://localhost");
  if (method === "GET" && pathname === "/items") return { status: 200, body: items };
  if (method === "GET" && pathname.startsWith("/items/")) {
    const item = items.find((i) => i.id === Number(pathname.split("/")[2]));
    return item ? { status: 200, body: item } : { status: 404, body: { error: "not found" } };
  }
  if (method === "GET" && pathname === "/about") return { status: 200, body: { name: "inventario-api", version: appVersion() } };
  return { status: 404, body: { error: "not found" } };
};
