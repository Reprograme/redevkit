# Migração para o REDEVKIT

Como trazer para o REDEVKIT um projeto que já usa o AG Kit, o Spec Kit, um `memory-bank/` ou
um `CLAUDE.md` com conteúdo. Os caminhos legados aparecem aqui só para você saber o que
procurar; o kit instalado não os usa.

## Antes de começar

1. Faça commit (ou uma cópia) do estado atual. A CLI faz backup do que sobrescreve, mas um
   commit é o jeito mais simples de comparar depois.
2. Rode a simulação no projeto:

   ```bash
   redevkit init --dry-run
   ```

   Ela lista os arquivos novos, os conflitos, a migração do `CLAUDE.md` (com o diff) e as
   entradas de config, sem gravar nada. A memória legada encontrada é só informada: quem a
   importa é o comando `redevkit-new`, depois do `init`.
3. Entenda como a CLI trata arquivos que já existem:
   - Um arquivo seu no mesmo caminho de um arquivo do kit, com conteúdo diferente, é um
     **conflito**: o seu fica intacto e a versão do kit vai para `.redevkit/conflicts/`.
   - Com `--force`, os arquivos em conflito são sobrescritos depois do backup em
     `.redevkit/backups/<id>/`.
   - Arquivos que o kit não instala nunca são tocados pela CLI.
   - Um `AGENTS.md` existente só recebe o bloco gerenciado (`<!-- REDEVKIT:BEGIN … -->` …
     `<!-- REDEVKIT:END -->`), inserido no topo; o resto do arquivo é preservado.

Ordem geral: `init` → `/redevkit-new` (ou `$redevkit-new`) escolhendo **projeto existente**
→ escolha da importação de memória (gate G7) → revisão da constituição (gate G1) → limpeza
manual do que sobrou do kit anterior.

## Vindo do AG Kit (`.agents/`)

### O que vai para onde

| No AG Kit | No REDEVKIT |
| --- | --- |
| `rules/core-protocol.md` | Bloco do `AGENTS.md` (início de sessão, precedência) e `redevkit-memanager` |
| `rules/request-routing.md` | Fase `redevkit-route` |
| `rules/universal-rules.md` | Bloco do `AGENTS.md` (idioma, clean code essencial) |
| `rules/code-rules.md` | Perguntas do `redevkit-new`, plano e tarefas do `redevkit-plan`, checklist final do `redevkit-verify`, TDD por padrão |
| `rules/design-rules.md` | Gate do `DESIGN.md` no plan, regra no `AGENTS.md`; Purple Ban na skill `frontend-design` e na constituição |
| `rules/quick-reference.md` | Removido (redundante com o `AGENTS.md`) |
| `workflows/` brainstorm, plan, create, enhance, test, debug, verify, preview, deploy, status | Os comandos `redevkit-*` de mesmo nome |
| `workflows/orchestrate.md` e `coordinate.md` | Fase `redevkit-orchestrate` |
| `workflows/remember.md` | Operação save do `redevkit-memanager` ("lembre disso") |
| `agent/*.md` | Personas em `.claude/agents/<persona>.md` e `.codex/agents/<persona>.toml`; `product-manager` foi fundido em `product-owner` |
| `skills/` | Skills de conhecimento; sub-skills viraram `references/` dentro da skill-mãe; `memory-system` e `memory-manager` viraram o `redevkit-memanager`; `behavioral-modes` foi removida |
| `memory/` | Importada pelo `redevkit-new` (abaixo) |
| `scripts/checklist.py`, `verify_all.py`, `validation_runner.py` e as auditorias | `.redevkit/audits/` |
| `scripts/auto_preview.py`, `session_manager.py` | Removidos; o `redevkit-preview` usa as ferramentas nativas do agente |
| Hooks, schemas, manifestos e config de runtime do AG Kit | Removidos. A segurança fica com o sistema nativo do agente, as regras do `AGENTS.md` e os gates |
| Config de MCP | Documentação: [mcp.md](mcp.md) |

Comandos: o que era `/plan`, `/create`, `/debug` etc. passa a ser `/redevkit-plan`,
`/redevkit-create`, `/redevkit-debug` no Claude Code e `$redevkit-plan`, `$redevkit-create`,
`$redevkit-debug` no Codex. O prefixo evita colisão com comandos nativos dos agentes.

### Passo a passo

1. **Skills no mesmo diretório.** O alvo codex instala skills em `.agents/skills/`, o mesmo
   diretório onde o AG Kit guarda as dele. Skills com o mesmo nome e conteúdo diferente
   aparecem como conflito no `--dry-run`. Escolha um caminho:
   - mover `.agents/skills/` do AG Kit para fora de `.agents/` antes do `init`; ou
   - rodar o `init` com `--force`, que sobrescreve os conflitos depois do backup.

   Mantenha `.agents/memory/` no lugar até a importação.
2. **Instale:** `redevkit init` (com `--target` e `--lang` se quiser).
3. **Importe a memória:** rode `/redevkit-new` (ou `$redevkit-new`), escolha projeto
   existente e, no gate G7, uma das opções:
   - **importar e arquivar** (recomendado): importa e move os arquivos de memória para
     `.redevkit/memory/archive/agents-memory-<AAAA-MM-DD>/`; o resto de `.agents/` não é
     tocado;
   - **importar e manter os originais**: importa e deixa os originais onde estão, sem
     manutenção;
   - **não importar**: nada é tocado, e a escolha fica registrada para não ser perguntada de
     novo.
4. **Limpe o que sobrou.** A CLI não apaga nada do AG Kit. Depois da importação, remova à mão
   o que não é mais usado em `.agents/` (`rules/`, `workflows/`, `agent/`, hooks, schemas,
   scripts, manifestos e as skills do AG Kit que o REDEVKIT não instala). Skills antigas que
   ficarem em `.agents/skills/` continuam visíveis para o Codex.

Mapa da memória do AG Kit:

| Origem (`.agents/memory/`) | Destino (`.redevkit/memory/`) |
| --- | --- |
| `MEMORY.md` | `MEMORY.md` (merge; cada entrada vai para a seção do seu tipo) |
| `user-preferences.md` | `user.md` |
| `feedback-history.md` | `user.md` › Feedback registrado |
| `project-conventions.md` | `system.md` › Convenções de código (hábitos de fluxo, como branches, vão para `active.md` › Preferências de fluxo) |
| `tech-decisions.md` | `system.md` › Decisões de design; o raciocínio longo vai para `changelog.md` › Decisões de arquitetura |
| Outros tópicos | `topics/<tema>.md`, mantendo o `type` |

## Vindo do Spec Kit (`.specify/`)

### O que vai para onde

| No Spec Kit | No REDEVKIT |
| --- | --- |
| `specs/NNN-nome/` | Fica como está: o REDEVKIT usa o mesmo layout e continua a numeração a partir do maior número |
| `.specify/memory/constitution.md` | `.redevkit/memory/constitution.md`, importada pelo `redevkit-new` |
| `.specify/templates/*-template.md` | `.redevkit/templates/` (instalados pela CLI); personalizações vão para `.redevkit/templates/overrides/<nome>` |
| `.specify/scripts/` | Não usados: o agente numera features e checa pré-requisitos seguindo as skills |
| Ponteiro da feature ativa | `.redevkit/memory/active.md`, linha `- Feature: specs/NNN-nome` |
| Bugs e avaliações da extensão (`.specify/bugs/`, `.specify/assessments/`) | `.redevkit/bugs/` e `.redevkit/assessments/` |
| Workflows e presets | Removidos; o `--auto` e os `overrides/` de template ocupam o lugar |

Comandos do Spec Kit e equivalentes:

| Spec Kit | REDEVKIT |
| --- | --- |
| constitution | `redevkit-new` (cria, ou emenda quando a memória já existe) |
| specify, plan, tasks, analyze, checklist | `redevkit-plan` (todas como fases de um só comando) |
| clarify | `redevkit-brainstorm` com uma feature ativa (modo clarify) |
| implement | `redevkit-create` |
| converge | `redevkit-verify` |
| extensão bug | `redevkit-debug` |
| extensão assess | `redevkit-brainstorm` sem feature ativa (modo assess) |
| extensão git | Oferta de branch no `redevkit-plan`; sem `git init` |

### Passo a passo

1. **Instale:** `redevkit init`. As skills `speckit-*` em `.claude/skills/` e
   `.agents/skills/` têm outros nomes e não são tocadas.
2. **Importe a constituição:** rode `/redevkit-new` (ou `$redevkit-new`), escolha projeto
   existente e, no gate G7, uma das três opções. A constituição importada mantém a versão; o
   `redevkit-new` a revisa como emenda, e nada é gravado sem a sua confirmação (G1). Se já
   existir uma constituição do REDEVKIT, você escolhe qual prevalece (manter a atual,
   recomendado; usar a legada; ou juntar as duas). Com "importar e arquivar", só os arquivos
   de memória vão para `.redevkit/memory/archive/specify-memory-<AAAA-MM-DD>/`; o resto de
   `.specify/` fica como está.
3. **Feature em andamento:** o ponteiro de feature ativa do Spec Kit não é importado. Diga
   ao agente qual é a feature (por exemplo, `/redevkit-memanager a feature ativa é
   specs/004-checkout`) ou edite a linha `- Feature:` de `.redevkit/memory/active.md`.
4. **Tarefas no formato do REDEVKIT:** as linhas de tarefa do Spec Kit não têm
   `— caminho — @persona — VERIFY:`. Para uma feature em andamento, rode `/redevkit-plan`
   com ela ativa: se o `plan.md` existe, o plan pergunta se atualiza (recomendado) ou
   recria; se o `tasks.md` já tem tarefas `[X]`, a fase de tarefas oferece manter as
   concluídas com seus IDs e regenerar só as abertas (recomendado). Features já concluídas
   podem ficar como estão.
5. **Numeração por timestamp:** o REDEVKIT só usa `NNN` sequencial. O próximo número sai do
   maior prefixo numérico em `specs/`, então diretórios no formato `AAAAMMDD-HHMMSS-nome`
   fariam o número saltar. Renomeie-os para `NNN-nome` antes de criar features novas.
6. **Templates personalizados:** se você alterou os templates do Spec Kit, leve as mudanças
   para `.redevkit/templates/overrides/` com os nomes do REDEVKIT (`spec.md`, `plan.md`,
   `tasks.md`, `constitution.md`, `checklist.md`), partindo dos templates instalados em
   `.redevkit/templates/` para manter as seções que as fases leem.
7. **Limpe o que sobrou:** bugs e avaliações em `.specify/` podem ser movidos para
   `.redevkit/bugs/` e `.redevkit/assessments/` se você quiser o histórico junto. Quando não
   precisar mais do Spec Kit, remova à mão `.specify/` e as skills `speckit-*`, para não ter
   dois pipelines visíveis no agente.

## Vindo de um `memory-bank/`

O `redevkit-new` detecta `memory-bank/`, mostra o mapa abaixo e pergunta (gate G7):
importar e arquivar (recomendado, os originais vão para
`.redevkit/memory/archive/memory-bank-<AAAA-MM-DD>/`), importar e manter os originais, ou
não importar. Nada é apagado.

| Origem (`memory-bank/`) | Destino (`.redevkit/memory/`) |
| --- | --- |
| `projectBrief.md` + `productContext.md` | `project.md` |
| `systemPatterns.md` | `system.md` (preferências e feedback do usuário vão para `user.md`) |
| `techContext.md` | `tech.md` |
| `activeContext.md` + `progress.md` | `active.md` |
| `changeLog.md` | `changelog.md` |

Como a importação trabalha:

- Lê todos os arquivos de origem antes de gravar e casa as seções pelo sentido, mesmo em
  outro idioma.
- Mantém fatos, datas e motivos; reescreve no idioma do projeto, preservando citações de
  feedback.
- Aplica a lista do que nunca se grava (segredos, logs, código, caminhos absolutos…) e
  informa quantos itens pulou e por quê, sem repetir nenhum segredo.
- Mantém os marcadores `<PENDENTE DE ENTREVISTA — motivo>` da origem.
- Invariantes copiadas literalmente estão cobertas pela escolha do G7; reescrever uma
  invariante ainda pede confirmação.
- No fim, atualiza o índice `MEMORY.md` e registra a importação em `changelog.md`.

## `CLAUDE.md` existente

No REDEVKIT, o `CLAUDE.md` só aponta para o `AGENTS.md`:

```markdown
@AGENTS.md

As instruções deste projeto ficam no AGENTS.md. Leia e escreva lá; não acrescente conteúdo a este arquivo.
```

Quando o `init` (alvo claude) encontra um `CLAUDE.md` com outro conteúdo:

1. Mostra o diff e pede confirmação. Com `--yes`, aceita direto.
2. Grava um backup em `.redevkit/backups/<id>/CLAUDE.md`.
3. Anexa o conteúdo ao `AGENTS.md`, fora do bloco gerenciado, sob
   `## Notas do projeto (migrado de CLAUDE.md em AAAA-MM-DD)` (em projetos `en`,
   `## Project notes (migrated from CLAUDE.md on YYYY-MM-DD)`). Uma linha `@AGENTS.md`
   solta é descartada; os demais `@imports` são mantidos, e continuam válidos porque os dois
   arquivos ficam no mesmo diretório.
4. Reescreve o `CLAUDE.md` como ponteiro.

Se você recusar, o `CLAUDE.md` fica como está e a CLI avisa que o Claude Code não vai ler o
`AGENTS.md` enquanto o `CLAUDE.md` não apontar para ele. O `redevkit update` nunca faz essa
migração; o `redevkit target add claude --yes` faz. O `redevkit doctor` avisa quando o
`CLAUDE.md` tem conteúdo além do ponteiro. O `CLAUDE.local.md` nunca é tocado.

Daí em diante, escreva as instruções do projeto no `AGENTS.md`, fora do bloco `REDEVKIT`
(a CLI reescreve o bloco a cada `update`). Assim elas valem para o Claude Code, para o Codex
e para qualquer outro agente que leia o `AGENTS.md`.
