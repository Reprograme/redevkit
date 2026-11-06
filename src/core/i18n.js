// CLI messages in the manifest language (pt-BR default, en).
const M = {
  "pt-BR": {
    noTtyNeedsYes: "Sem terminal interativo: use --yes (e, se quiser, --target e --lang). Nada foi alterado.",
    askTarget: "Alvo da instalação [both/claude/codex] (padrão: both): ",
    askLang: "Idioma dos artefatos [pt-BR/en] (padrão: pt-BR): ",
    invalidTarget: "Alvo inválido: {v}. Use claude, codex ou both.",
    invalidLang: "Idioma inválido: {v}. Use pt-BR ou en.",
    detected: "Detectado neste projeto: {v}",
    legacyMemory: "Memória legada encontrada ({v}). Quem importa é o comando redevkit-new; nada foi alterado nela.",
    dryRun: "Simulação (--dry-run): nada foi gravado.",
    planSummary: "Arquivos: {add} novos, {update} atualizados, {del} removidos, {same} iguais, {conf} conflitos, {keep} preservados.",
    conflictsHeader: "Conflitos (seu arquivo foi preservado; a versão nova ficou em {dir}):",
    preservedHeader: "Preservados:",
    claudeMigrateAsk: "O CLAUDE.md atual tem conteúdo. Ele será movido para o AGENTS.md (seção Notas do projeto) e o CLAUDE.md virará só um ponteiro. Continuar? [s/N] ",
    claudeMigrated: "CLAUDE.md migrado para o AGENTS.md (backup em {v}).",
    claudeMigrateSkipped: "CLAUDE.md não foi migrado (recusado). O Claude Code não lerá o AGENTS.md até o CLAUDE.md apontar para ele.",
    configInvalid: "{file}: {err}. O passo de configuração foi abortado e o arquivo não foi alterado.",
    configKept: "{file}: a chave {key} já tem um valor seu ({val}); ele foi mantido.",
    configAdded: "{file}: {n} entrada(s) gerenciada(s) adicionada(s).",
    backupAt: "Backup em {v}",
    done: "REDEVKIT {version} instalado ({targets}, {lang}).",
    updated: "REDEVKIT atualizado para {version}.",
    upToDate: "Nada a fazer: a instalação já está igual à versão {version}.",
    nextStepClaude: "Próximo passo no Claude Code: /redevkit-new",
    nextStepCodex: "Próximo passo no Codex: $redevkit-new",
    codexTrust: "Codex: os agentes em .codex/ e o .codex/config.toml só valem com o projeto marcado como confiável (trusted). Sem isso, as personas são aplicadas inline.",
    claudeTrust: "Claude Code: as permissões de .claude/settings.json só valem depois que você confiar no projeto.",
    notInstalled: "REDEVKIT não está instalado aqui (falta .redevkit/manifest.json). Rode: redevkit init",
    manifestError: "Manifesto inválido: {v}",
    alreadyTarget: "O alvo {v} já está instalado.",
    notTarget: "O alvo {v} não está instalado.",
    lastTarget: "Não é possível remover o último alvo. Use redevkit uninstall.",
    uninstallAsk: "Remover os arquivos gerenciados do REDEVKIT? Memória, specs, DESIGN.md e as notas do AGENTS.md serão preservados. [s/N] ",
    uninstallDone: "REDEVKIT removido. Preservados: .redevkit/memory/, specs/, DESIGN.md, notas do AGENTS.md, CLAUDE.md.",
    aborted: "Cancelado. Nada foi alterado.",
    rollbackDone: "Backup {v} restaurado. Estado anterior salvo em {safety}.",
    noBackups: "Nenhum backup encontrado.",
    interrupted: "Interrompido. Arquivos temporários removidos.",
    yesNo: "s",
  },
  en: {
    noTtyNeedsYes: "No interactive terminal: pass --yes (and optionally --target and --lang). Nothing was changed.",
    askTarget: "Install target [both/claude/codex] (default: both): ",
    askLang: "Artifact language [pt-BR/en] (default: pt-BR): ",
    invalidTarget: "Invalid target: {v}. Use claude, codex or both.",
    invalidLang: "Invalid language: {v}. Use pt-BR or en.",
    detected: "Detected in this project: {v}",
    legacyMemory: "Legacy memory found ({v}). The redevkit-new command imports it; nothing was changed there.",
    dryRun: "Dry run (--dry-run): nothing was written.",
    planSummary: "Files: {add} new, {update} updated, {del} removed, {same} unchanged, {conf} conflicts, {keep} preserved.",
    conflictsHeader: "Conflicts (your file was kept; the new version is in {dir}):",
    preservedHeader: "Preserved:",
    claudeMigrateAsk: "The current CLAUDE.md has content. It will move to AGENTS.md (Project notes) and CLAUDE.md will become a pointer. Continue? [y/N] ",
    claudeMigrated: "CLAUDE.md migrated to AGENTS.md (backup at {v}).",
    claudeMigrateSkipped: "CLAUDE.md was not migrated (declined). Claude Code will not read AGENTS.md until CLAUDE.md points to it.",
    configInvalid: "{file}: {err}. The configuration step was aborted and the file was not changed.",
    configKept: "{file}: key {key} already has your value ({val}); it was kept.",
    configAdded: "{file}: {n} managed entr(ies) added.",
    backupAt: "Backup at {v}",
    done: "REDEVKIT {version} installed ({targets}, {lang}).",
    updated: "REDEVKIT updated to {version}.",
    upToDate: "Nothing to do: the installation already matches version {version}.",
    nextStepClaude: "Next step in Claude Code: /redevkit-new",
    nextStepCodex: "Next step in Codex: $redevkit-new",
    codexTrust: "Codex: agents in .codex/ and .codex/config.toml only apply when the project is trusted. Without it, personas are applied inline.",
    claudeTrust: "Claude Code: .claude/settings.json permissions apply only after you trust the project.",
    notInstalled: "REDEVKIT is not installed here (missing .redevkit/manifest.json). Run: redevkit init",
    manifestError: "Invalid manifest: {v}",
    alreadyTarget: "Target {v} is already installed.",
    notTarget: "Target {v} is not installed.",
    lastTarget: "Cannot remove the last target. Use redevkit uninstall.",
    uninstallAsk: "Remove REDEVKIT managed files? Memory, specs, DESIGN.md and AGENTS.md notes are kept. [y/N] ",
    uninstallDone: "REDEVKIT removed. Kept: .redevkit/memory/, specs/, DESIGN.md, AGENTS.md notes, CLAUDE.md.",
    aborted: "Cancelled. Nothing was changed.",
    rollbackDone: "Backup {v} restored. Previous state saved at {safety}.",
    noBackups: "No backups found.",
    interrupted: "Interrupted. Temporary files removed.",
    yesNo: "y",
  },
};

let current = "pt-BR";
export const setLang = (lang) => {
  if (M[lang]) current = lang;
};
export const getLang = () => current;

export const t = (key, vars = {}) => {
  const s = M[current][key] ?? M.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] !== undefined ? String(vars[k]) : `{${k}}`));
};

export const isYes = (answer) => {
  const a = String(answer ?? "").trim().toLowerCase();
  return a === "y" || a === "yes" || a === "s" || a === "sim";
};
