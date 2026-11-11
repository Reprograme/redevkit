// Interactive prompts. Never blocks without a TTY (C4): callers check isInteractive() first.
import readline from "node:readline/promises";
import { t } from "./i18n.js";

export const isInteractive = () => Boolean(process.stdin.isTTY && process.stdout.isTTY) && process.env.REDEVKIT_NO_TTY !== "1";

const fail = (key, exitCode) => Object.assign(new Error(t(key)), { exitCode });

/**
 * Ask one question. In a terminal, readline takes Ctrl+C itself (raw mode), so the process SIGINT
 * handler never runs: Ctrl+C is mapped here to exit code 130, and end of input (Ctrl+D / Ctrl+Z)
 * to a cancellation, instead of an unsettled promise (exit 13) or a generic error (exit 1).
 */
export const ask = async (question, { input = process.stdin, output = process.stdout } = {}) => {
  const rl = readline.createInterface({ input, output });
  const ac = new AbortController();
  let cause = null;
  rl.once("SIGINT", () => {
    cause = "interrupted";
    ac.abort();
  });
  rl.once("close", () => {
    cause ??= "aborted";
    ac.abort();
  });
  try {
    return (await rl.question(question, { signal: ac.signal })).trim();
  } catch (err) {
    if (cause === "interrupted") throw fail("interrupted", 130);
    if (cause === "aborted") throw fail("aborted", 1);
    throw err;
  } finally {
    rl.close();
  }
};
