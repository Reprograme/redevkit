// redevkitCLI entry (commander). Exit codes: 0 ok, 1 error, 2 usage, 130 interrupted.
import { Command, CommanderError } from "commander";
import { runDoctor } from "./commands/doctor.js";
import { runInit } from "./commands/init.js";
import { runRollback } from "./commands/rollback.js";
import { runStatus, runVersion } from "./commands/status.js";
import { runTarget } from "./commands/target.js";
import { runUninstall } from "./commands/uninstall.js";
import { runUpdate } from "./commands/update.js";
import { runValidateKit } from "./commands/validate-kit.js";
import { cleanupPendingTemps } from "./core/fsutil.js";
import { t } from "./core/i18n.js";
import { packageVersion } from "./core/render.js";

let sigintInstalled = false;
export const installSigint = () => {
  if (sigintInstalled) return;
  sigintInstalled = true;
  process.on("SIGINT", () => {
    cleanupPendingTemps(); // C2: temp files live next to their targets and are removed here
    process.stderr.write(`\n${t("interrupted")}\n`);
    process.exit(130);
  });
};

export const buildProgram = () => {
  const program = new Command();
  program
    .name("redevkit")
    .description("REDEVKIT: Markdown-first kit for Claude Code and Codex (spec-driven process, personas, quality, memory).")
    .version(packageVersion(), "-v, --version")
    .showHelpAfterError()
    // Parse errors throw instead of exiting with commander's code 1, so main() can map them to
    // exit code 2 (usage). Set before the subcommands are added: they inherit it.
    .exitOverride();

  program
    .command("init [dir]")
    .description("install REDEVKIT in a project (new or existing)")
    .option("--here", "install in the current directory")
    .option("--target <target>", "claude | codex | both")
    .option("--lang <lang>", "artifact language: pt-BR | en")
    .option("--dry-run", "show what would change, write nothing")
    .option("-y, --yes", "accept defaults and confirmations (required without a TTY)")
    .option("--force", "overwrite conflicting files and restore missing managed files (after backup)")
    .option("--verbose", "list every file action")
    .action((dir, opts) => runInit(dir, opts));

  program
    .command("update")
    .description("three-way update of managed files (memory, specs and DESIGN.md are never touched)")
    .option("--dry-run", "show what would change, write nothing")
    .option("--no-backup", "skip the backup")
    .option("--restore", "re-add managed files that are missing locally (local changes are kept)")
    .option("--conflict-report <file>", "write a JSON report of actions and conflicts")
    .option("--verbose", "list every file action")
    .action((opts) => runUpdate(opts));

  program
    .command("rollback")
    .description("restore a backup (the current state is saved first)")
    .option("--backup <id>", "backup id (default: most recent)")
    .option("--list", "list backups")
    .option("--dry-run", "show what would be restored")
    .action((opts) => runRollback(opts));

  program
    .command("status")
    .description("installed version, targets, language and managed-file drift")
    .option("--quiet", "one-line output")
    .option("--json", "JSON output")
    .action((opts) => runStatus(opts));

  program
    .command("doctor")
    .description("check tools, installation, AGENTS.md, memory, specs numbering and config")
    .option("--json", "JSON output")
    .action(async (opts) => {
      const report = await runDoctor(opts);
      if (!report.ok) process.exitCode = 1;
    });

  const target = program.command("target").description("add or remove a target (AGENTS.md always stays)");
  for (const action of ["add", "remove"]) {
    const sub = target
      .command(`${action} <target>`)
      .description(`${action} claude or codex`)
      .option("--dry-run", "show what would change, write nothing")
      .option("--verbose", "list every file action");
    if (action === "add") sub.option("-y, --yes", "accept the CLAUDE.md migration when adding claude");
    sub.action((name, opts) => runTarget(action, name, opts));
  }

  program
    .command("version")
    .description("print the version; --check queries npm (optional, honest when offline)")
    .option("--check", "check the latest published version")
    .action((opts) => runVersion(opts));

  program
    .command("uninstall")
    .description("remove managed files and config entries; keeps memory, specs, DESIGN.md and notes")
    .option("--dry-run", "show what would be removed")
    .option("-y, --yes", "do not ask for confirmation")
    .option("--force", "also remove managed files you modified")
    .action((opts) => runUninstall(opts));

  program
    .command("validate-kit", { hidden: true })
    .description("validate the bundled kit (maintainers, CI)")
    .option("--json", "JSON output")
    .action(async (opts) => {
      const r = await runValidateKit(opts);
      if (!r.ok) process.exitCode = 1;
    });

  return program;
};

export const main = async (argv = process.argv) => {
  if (process.stdout.setDefaultEncoding) process.stdout.setDefaultEncoding("utf8"); // Y15
  installSigint();
  try {
    await buildProgram().parseAsync(argv);
  } catch (err) {
    if (err instanceof CommanderError) {
      // commander already printed the error (or the help/version text): 0 for --help and
      // --version, 2 for every usage error (unknown option or command, missing argument...).
      process.exitCode = err.exitCode === 0 ? 0 : 2;
      return;
    }
    process.stderr.write(`${err.message}\n`);
    process.exitCode = err.exitCode ?? 1;
  }
};
