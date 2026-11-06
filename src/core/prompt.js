// Interactive prompts. Never blocks without a TTY (C4): callers check isInteractive() first.
import readline from "node:readline/promises";

export const isInteractive = () => Boolean(process.stdin.isTTY && process.stdout.isTTY) && process.env.REDEVKIT_NO_TTY !== "1";

export const ask = async (question) => {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    return (await rl.question(question)).trim();
  } finally {
    rl.close();
  }
};
