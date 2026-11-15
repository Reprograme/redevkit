# Resultados do E2E

Gerado por `e2e/summarize.mjs` em 2026-11-06 12:11 UTC; linhas B atualizadas em 2026-11-08 com os runs `r6`; linhas C, D e E adicionadas em 2026-11-12 com os runs `r7` e `r8` (1.1.0). Em 2026-11-15, as linhas do Claude Code de B a F foram refeitas com o kit 1.2.0 (test no escopo da spec, verify no escopo global, runs `r9`); A-claude, A-codex e B-codex são de versões anteriores e não foram refeitos. Roteiro e checagens em [README.md](README.md).

| Run | Checagens | Veredito | Duração dos passos | Kit |
| --- | --- | --- | --- | --- |
| A-claude | 12/12 | PASS | 63 min | 1.0 |
| A-codex | 12/12 | PASS | 49 min | 1.0 |
| B-codex | 16/16 | PASS | 26 min | 1.0 (`r6`) |
| B-claude | 23/23 | PASS | 14 min | 1.2.0 (`r9/B-claude-2`) |
| C-claude | 23/23 | PASS | 16 min | 1.2.0 (`r9/C-claude-2`) |
| D-claude | 22/22 | PASS | 17 min | 1.2.0 (`r9/D-claude`) |
| E-claude | 24/24 | PASS | 12 min | 1.2.0 (`r9/E-claude-2`) |
| F-claude | 24/24 | PASS | 13 min | 1.2.0 (`r9/F-claude-2`) |

**Resultado:** 8 de 8 aprovados. Com o kit 1.2.0, só o Claude Code; o Codex não foi refeito.

## Histórico das tentativas

Os aprovados acima são os runs finais. As tentativas anteriores não foram descartadas em
silêncio. Cada uma revelou algo, corrigido antes do run final (ver também
[docs/aceite.md](../docs/aceite.md) §3):

| Tentativa | O que aconteceu | Correção |
| --- | --- | --- |
| A-claude e B-claude, 1ª | Claude recusou gravar no caminho curto do Windows (`RICARD~1`) e não contornou a checagem | Harness usa o caminho longo (`realpathSync.native`) |
| A-codex e B-codex, 1ª | Limite de uso da conta do Codex atingido no meio do run | Reexecutados depois da liberação |
| A-codex, 1ª | Acentos corrompidos ao gravar pelo PowerShell | Regra UTF-8 no bloco do `AGENTS.md` |
| B-claude, 2ª | `verify` deu `gaps` por falsos positivos do `security_scan.py` (lock file e cabeçalhos num projeto sem dependências) | Auditoria corrigida, com teste |
| B-codex, 2ª e 3ª | `enhance` mandou "adicionar endpoint" para o plan; depois o implement exigiu `plan.md` numa spec leve | Heurística de tamanho e exceção D55 no implement, tasks e converge |
| A-codex, 2ª | `test` deu FAIL só por cenários não automatizáveis (revisão humana, dispositivo de referência) | Regra "Não verificado" no `redevkit-test`. O run final continuou o mesmo projeto pelo fluxo do kit: `debug`, depois `redevkit update` (merge de 3 vias, 0 conflitos) e novo `test` |
| B-claude, 4ª | O harness não permitia mover o `memory-bank/`; o agente copiou para `archive/`, não removeu os originais e registrou a pendência | Harness autoriza mover o `memory-bank/` (equivale a aprovar o prompt) |
| B-claude e B-codex, `r6` (2026-11-08) | Novo pipeline: depois do debug, o verify roda o test (passo 1) e grava a execução `PASS` no `test-report.md`; ciclo de correção por feature no `active.md`. Duas checagens novas | Aprovados na primeira tentativa, 16/16 nos dois |
| E-claude, `r7` (2026-11-12) | A cadeia `--auto` inteira funcionou numa só invocação, mas o agente reescreveu o `MEMORY.md` sem o frontmatter e o `doctor` reprovou (18/19) | Regra no `redevkit-memanager`: editar os arquivos de memória no lugar, nunca regenerá-los inteiros; o run `r8` passou 19/19 |
| B-claude, E-claude e F-claude, `r9` 1ª (2026-11-15) | Kit 1.2.0. O B pediu ao test os testes do `/about` (fora da spec): o agente os rodou à parte e deu `PASS` no escopo da spec, enquanto no E o agente os incluiu no conjunto da spec. No F, o agente juntou `mkdir` e `mv memory-bank/*.md` num comando e a allowlist do harness negou o move (copiou e não removeu o original); as checagens do laço global passaram | Regra do kit: testes pedidos para comportamento fora da spec ficam em "Fora da spec" e o verify os roda. Harness: B e C quebram a rota `/health` depois do enhance (laço da spec), o E passa a provar o laço global; allowlist com `mv memory-bank/*` e `rmdir memory-bank`. B, C, E e F refeitos (`-2`) e aprovados |
| Revisão independente do kit 1.2.0 (2026-11-15) | Oito achados: limite de 3 debugs inalcançável (o `failed` também somava rodada sem convergir), baseline que virava regressão no 2º verify, test ↔ debug sem limite quando o debug diz "o teste está errado", lacunas de feature Unverified sem caminho, `spec (full suite)` reprovando por testes de fora da spec, "Continuar" no G5 perdendo o laço, textos antigos em personas e skills | Corrigidos antes dos runs `-2`; o D (`r9/D-claude`) rodou antes dessas correções, que não mudam o caminho dele |

## Detalhes

### A-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no git repository created (D38) | PASS |  |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| specs/001-*/ has spec, plan, tasks | PASS | 001-mover-atirar-pontuar |
| plan cites game-development + 2d-games + web-games (routing) | PASS |  |
| tests first in US1 (TDD) | PASS | - [X] T021 [P] [US1] Escrever testes que falham da partida: `createWorld(semente, config)` começa `jogando`, tick 0, placar 0, nave com centro em (240, 680) (FR |
| tasks assigned to @game-developer | PASS |  |
| test-report.md green (last run PASS) | PASS | PASS |

### A-codex

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no git repository created (D38) | PASS |  |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| specs/001-*/ has spec, plan, tasks | PASS | 001-mover-atirar-pontuar |
| plan cites game-development + 2d-games + web-games (routing) | PASS |  |
| tests first in US1 (TDD) | PASS | - [X] T004 [US1] Escrever testes de início, limites, direções opostas e pausa sem salto ou teclas presas — tests/unit/movimento.test.js — @test-engineer — VERIF |
| tasks assigned to @game-developer | PASS |  |
| test-report.md green (last run PASS) | PASS | FAIL → FAIL → PASS |

### B-codex

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-endpoint-saude |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | versao-about-ausente |
| verification.md converged+verified (last run) | PASS | converged+verified |
| test went red before debug (bug exposed) | PASS | FAIL → PASS |
| verify re-ran the tests after debug (last test run PASS, run by redevkit-verify) | PASS | FAIL → PASS |
| correction cycle recorded in active.md | PASS |  |

### B-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | converged+verified |
| every test run records its Scope (spec or global) and Run by | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| scopes match the commands (redevkit-test → spec, redevkit-verify → global) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| verify ran the whole suite on the final code (global PASS after the last FAIL) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | health-rota-healthz-404 |
| test went red before debug (bug exposed) | PASS | FAIL → PASS → PASS |
| spec loop: after the debug, redevkit-test ran the spec tests again (spec PASS after the FAIL) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| red test run names a failure class | PASS |  |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 3 run(s) |
| active.md has the loop lines and no Verify pending | PASS |  |
| Unverified is none after converged+verified | PASS | none |

### C-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 0 -> 0 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-endpoint-health |
| verification.md converged+verified (last run) | PASS | converged+verified |
| every test run records its Scope (spec or global) and Run by | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| scopes match the commands (redevkit-test → spec, redevkit-verify → global) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| verify ran the whole suite on the final code (global PASS after the last FAIL) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | health-rota-healthz |
| test went red before debug (bug exposed) | PASS | FAIL → PASS → PASS |
| spec loop: after the debug, redevkit-test ran the spec tests again (spec PASS after the FAIL) | PASS | FAIL/spec/redevkit-test → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| red test run names a failure class | PASS |  |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 3 run(s) |
| active.md has the loop lines and no Verify pending | PASS |  |
| Unverified is none after converged+verified | PASS | none |

### D-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | gaps → converged+verified |
| every test run records its Scope (spec or global) and Run by | PASS | PASS/spec/redevkit-test → PASS/global/redevkit-verify → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| scopes match the commands (redevkit-test → spec, redevkit-verify → global) | PASS | PASS/spec/redevkit-test → PASS/global/redevkit-verify → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| verify ran the whole suite on the final code (global PASS after the last FAIL) | PASS | PASS/spec/redevkit-test → PASS/global/redevkit-verify → PASS/spec/redevkit-test → PASS/global/redevkit-verify |
| verify found the injected gap (a gaps run before the last one) | PASS | gaps → converged+verified |
| Convergence tasks appended and all done | PASS | 0 open or blocked |
| test ran again between the two verifies | PASS | PASS → PASS → PASS → PASS |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 4 run(s) |
| active.md has the loop lines and no Verify pending | PASS |  |
| Unverified is none after converged+verified | PASS | none |

### E-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | failed → converged+verified |
| every test run records its Scope (spec or global) and Run by | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| scopes match the commands (redevkit-test → spec, redevkit-verify → global) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| verify ran the whole suite on the final code (global PASS after the last FAIL) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| the spec tests passed before the regression (first run: spec PASS by redevkit-test) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| verify failed on the regression, then converged+verified | PASS | failed → converged+verified |
| the global run caught it as a product-defect, not baseline | PASS |  |
| global loop: the debug handed back to the verify (no redevkit-test run after the global FAIL) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | about-version-undefined |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 3 run(s) |
| active.md has the loop lines and no Verify pending | PASS |  |
| Unverified is none after converged+verified | PASS | none |

### F-claude

| Check | Result | Detail |
| --- | --- | --- |
| redevkit doctor passes | PASS |  |
| memory complete | PASS |  |
| constitution has Test-First | PASS |  |
| no files outside expected paths | PASS |  |
| no commit created | PASS | 1 -> 1 |
| no destructive command in transcripts | PASS |  |
| no SKIPPED audit reported as PASS | PASS |  |
| CLAUDE.md backup + pointer | PASS |  |
| legacy memory mapped (§9.8) | PASS | mapped: project.md, tech.md, system.md, active.md, changelog.md |
| archive/ created and memory-bank/ archived | PASS |  |
| spec delta + tasks (or lightweight spec, D55) | PASS | 001-health-endpoint |
| verification.md converged+verified (last run) | PASS | failed → converged+verified |
| every test run records its Scope (spec or global) and Run by | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| scopes match the commands (redevkit-test → spec, redevkit-verify → global) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| verify ran the whole suite on the final code (global PASS after the last FAIL) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| the spec tests passed before the regression (first run: spec PASS by redevkit-test) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| verify failed on the regression, then converged+verified | PASS | failed → converged+verified |
| the global run caught it as a product-defect, not baseline | PASS |  |
| global loop: the debug handed back to the verify (no redevkit-test run after the global FAIL) | PASS | PASS/spec/redevkit-test → FAIL/global/redevkit-verify → PASS/global/redevkit-verify |
| .redevkit/bugs/<slug>/{assessment,fix,test}.md | PASS | items-id-segmento-errado |
| correction cycle recorded in active.md | PASS |  |
| every test run records a Tree fingerprint | PASS | 3 run(s) |
| active.md has the loop lines and no Verify pending | PASS |  |
| Unverified is none after converged+verified | PASS | none |
