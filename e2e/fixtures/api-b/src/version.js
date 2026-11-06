import { readFileSync } from "node:fs";

// Reads the application version from package.json.
export const appVersion = () => {
  const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
  return pkg.verison;
};
