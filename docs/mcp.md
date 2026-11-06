# Servidores MCP

O REDEVKIT não instala nem sincroniza configuração de MCP. Cada agente mantém a sua, e você
registra os servidores explicitamente. A referência completa, em inglês, está na skill
`mcp-builder`: [configure-mcp.md](../kit/skills/mcp-builder/references/configure-mcp.md). No
projeto instalado, ela fica em `.claude/skills/mcp-builder/references/configure-mcp.md`
(Claude Code) e em `.agents/skills/mcp-builder/references/configure-mcp.md` (Codex).

## Regras para os dois agentes

- Nunca faça commit de segredos: use variáveis de ambiente em vez de tokens literais.
- Use o escopo de projeto só para servidores que o time inteiro precisa; os pessoais vão no
  escopo do usuário.
- Adicionar um servidor que roda código ou acessa a rede é uma decisão de segurança: confira
  a entrada exata antes de gravá-la.
- Depois de adicionar, confirme que o servidor sobe e lista as ferramentas.
- Na linha de comando, as opções vêm **antes** do nome do servidor; tudo depois de `--` é a
  linha de comando do próprio servidor.

## Claude Code

| Escopo | Vale em | Fica em |
| --- | --- | --- |
| `local` (padrão) | Projeto atual, só para você | `~/.claude.json` (sob o caminho do projeto) |
| `project` | Projeto atual, compartilhado pelo git | `.mcp.json` na raiz do projeto |
| `user` | Todos os seus projetos | `~/.claude.json` |

```bash
claude mcp add --transport stdio <nome> -- <comando> [args...]
claude mcp add --transport http <nome> <url>
claude mcp add --transport http <nome> --scope project <url>   # grava .mcp.json
claude mcp list
claude mcp remove <nome>
```

No `.mcp.json`, `${VAR}` expande uma variável de ambiente. O Claude Code pede aprovação antes
de usar servidores de projeto; `claude mcp reset-project-choices` desfaz essas escolhas. Para
conferir: `claude mcp list` ou `/mcp` dentro de uma sessão.

## Codex

Cada servidor é uma tabela `[mcp_servers.<nome>]` em `~/.codex/config.toml` (todos os
projetos) ou em `.codex/config.toml` do projeto, que **só vale com o projeto marcado como
confiável**. Servidores stdio usam `command` e `args`; servidores HTTP usam `url` e, para
autenticação, `bearer_token_env_var`. `startup_timeout_sec`, `tool_timeout_sec` e
`enabled = false` ajustam o comportamento.

```bash
codex mcp add <nome> --env VAR1=VALOR1 -- <comando do servidor stdio>
codex mcp list
```

## Exemplo: context7, sem chave de API

O context7 serve documentação atualizada de bibliotecas e funciona sem chave de API (uma
chave só aumenta os limites de uso e, se usada, vem de variável de ambiente). Precisa de
Node.js com `npx` no `PATH`.

Claude Code:

```bash
claude mcp add --transport stdio context7 -- npx -y @upstash/context7-mcp
```

Codex:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
```

Ou, no `config.toml` do Codex:

```toml
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
```

Se o `npx` não subir no Windows nativo, tente `cmd /c npx -y @upstash/context7-mcp`.

## Problemas comuns

| Sintoma | O que conferir |
| --- | --- |
| O servidor nunca sobe | Rode à mão, num terminal, o comando que vem depois de `--` e leia o stderr |
| Sobe, mas sem ferramentas | Timeout curto (`startup_timeout_sec` no Codex) ou o servidor caiu depois de subir |
| Servidor de projeto ignorado no Codex | O projeto não é confiável, então o `.codex/config.toml` não é aplicado |
| Servidor de projeto ignorado no Claude Code | A aprovação foi recusada; rode `claude mcp reset-project-choices` |
| Erro de autenticação em HTTP | A variável de `bearer_token_env_var` ou do `${VAR}` não está definida no shell que abriu o agente |
