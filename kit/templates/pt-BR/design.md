---
type: design
version: "[VERSAO_DO_DESIGN, ex.: 1.0.0]"
created: "[DATA]"
updated: "[DATA]"
---

# Design System de [NOME_DO_PROJETO]

<!--
  O DESIGN.md é a fonte única da verdade da linguagem visual do projeto e fica na raiz (um
  por projeto). Ele precisa existir antes de qualquer interface ser construída; o código de
  interface usa os nomes de token abaixo, nunca valores avulsos. Os nomes de token são
  normativos; o texto explica a intenção. O plano de cada feature registra os deltas deste
  arquivo em "Design Source-of-Truth". As seções seguem a ordem do formato DESIGN.md
  (Visão geral, Cores, Tipografia, Layout, Elevação, Formas, Movimento, Componentes,
  Acessibilidade, Faça e Não faça); apague o que não se aplica.
  Os nomes de token ficam em inglês (são usados no código). Substitua todo [CAMPO]; apague
  estes comentários depois de preencher.
-->

## Visão Geral

**Produto**: [o que é e para quem]

**Personalidade**: [três adjetivos, ex.: calmo, preciso, acolhedor]

**Notas da marca**: [uso do logo, tom de voz, estilo de imagens, referências que inspiraram a direção]

**Plataformas**: [web | iOS | Android | desktop | canvas de jogo]

**Política de cor (Purple Ban)**: LIGADA por padrão. Tons de roxo e violeta, e degradês
roxo-azulados de "brilho de IA", não são usados, a menos que a marca diga o contrário.
Exceção da marca: [nenhuma | "a cor da marca é roxa: proibição suspensa só para colors.primary"]

## Cores

| Token | Valor | Papel | Usar em | Par de contraste |
| --- | --- | --- | --- | --- |
| `colors.primary` | [#RRGGBB] | Marca e ação principal | Botões primários, links principais | `colors.on-primary` |
| `colors.on-primary` | [#RRGGBB] | Texto sobre a primária | Rótulos de botão | - |
| `colors.secondary` | [#RRGGBB] | Destaque de apoio | Ações secundárias, realces | `colors.on-primary` |
| `colors.surface` | [#RRGGBB] | Fundo base | Páginas, cards | `colors.on-surface` |
| `colors.on-surface` | [#RRGGBB] | Texto principal | Texto corrido, ícones | - |
| `colors.muted` | [#RRGGBB] | Texto secundário | Legendas, placeholders | `colors.surface` |
| `colors.border` | [#RRGGBB] | Divisórias | Bordas, separadores | - |
| `colors.success` | [#RRGGBB] | Estado positivo | Confirmações | `colors.on-surface` |
| `colors.warning` | [#RRGGBB] | Estado de atenção | Avisos | `colors.on-surface` |
| `colors.error` | [#RRGGBB] | Estado de erro | Erros, ações destrutivas | `colors.on-primary` |

**Modo escuro**: [não suportado | sobrescritas de token listadas abaixo]

## Tipografia

**Famílias**: [fonte de títulos], [fonte de texto], [fonte mono]; fallback: [pilha do sistema]

| Token | Tamanho | Peso | Altura de linha | Espaçamento entre letras | Usar em |
| --- | --- | --- | --- | --- | --- |
| `typography.display` | [48px] | [700] | [1.1] | [-0.02em] | Títulos de destaque |
| `typography.headline-lg` | [32px] | [600] | [1.2] | [-0.01em] | Títulos de página |
| `typography.headline-md` | [24px] | [600] | [1.3] | [0] | Títulos de seção |
| `typography.body-lg` | [18px] | [400] | [1.6] | [0] | Parágrafos de abertura |
| `typography.body-md` | [16px] | [400] | [1.6] | [0] | Texto corrido |
| `typography.body-sm` | [14px] | [400] | [1.5] | [0] | Texto secundário |
| `typography.label-md` | [14px] | [600] | [1.2] | [0.01em] | Botões, rótulos |
| `typography.label-sm` | [12px] | [600] | [1.2] | [0.02em] | Tags, legendas |

## Layout

| Token | Valor | Usar em |
| --- | --- | --- |
| `spacing.xs` | [4px] | Espaço entre ícones |
| `spacing.sm` | [8px] | Grupos compactos |
| `spacing.md` | [16px] | Padding padrão |
| `spacing.lg` | [24px] | Padding de cards, espaço entre seções |
| `spacing.xl` | [48px] | Seções da página |

**Grid**: [ex.: 12 colunas, gutter de 24px, largura máxima de conteúdo 1200px]

**Breakpoints**: [ex.: sm 640px, md 768px, lg 1024px, xl 1280px]

## Elevação e Profundidade

| Token | Valor | Usar em |
| --- | --- | --- |
| `elevation.none` | [none] | Superfícies planas |
| `elevation.sm` | [0 1px 2px rgba(0,0,0,0.08)] | Cards em repouso |
| `elevation.md` | [0 4px 12px rgba(0,0,0,0.12)] | Dropdowns, hover |
| `elevation.lg` | [0 12px 32px rgba(0,0,0,0.16)] | Modais, diálogos |

**Alternativa plana**: [bordas, camadas tonais ou contraste usados no lugar de sombras, se houver]

## Formas

| Token | Valor | Usar em |
| --- | --- | --- |
| `rounded.none` | [0] | Tabelas, mídia de borda a borda |
| `rounded.sm` | [4px] | Inputs, tags |
| `rounded.md` | [8px] | Botões, cards |
| `rounded.lg` | [16px] | Modais, painéis grandes |
| `rounded.full` | [9999px] | Avatares, pílulas |

## Movimento

| Token | Duração | Easing | Usar em |
| --- | --- | --- | --- |
| `motion.fast` | [120ms] | [ease-out] | Feedback de hover e clique |
| `motion.base` | [200ms] | [ease-in-out] | Expandir, recolher, fades |
| `motion.slow` | [320ms] | [cubic-bezier(0.2, 0, 0, 1)] | Transições de página e de modal |

**Movimento reduzido**: quando o usuário prefere menos movimento, [desligar animações não
essenciais; manter mudanças de opacidade abaixo de 120ms].

## Componentes

| Componente | Tokens | Variantes e estados | Status |
| --- | --- | --- | --- |
| Botão | `colors.primary`, `typography.label-md`, `rounded.md`, `spacing.md` | primary, secondary, ghost; hover, focus, disabled, loading | [planejado / construído] |
| Input | `colors.surface`, `colors.border`, `rounded.sm` | default, focus, error, disabled | [planejado / construído] |
| Card | `colors.surface`, `elevation.sm`, `rounded.md`, `spacing.lg` | default, interativo | [planejado / construído] |
| [Componente] | [tokens] | [variantes e estados] | [planejado / construído] |

## Acessibilidade

- **Contraste**: [WCAG 2.2 AA: 4.5:1 para texto corrido, 3:1 para texto grande e partes de interface]
- **Foco**: [anel de foco visível usando `colors.primary`, com pelo menos 2px]
- **Alvos de toque**: [pelo menos 44 × 44 px]
- **Teclado**: [toda ação alcançável e operável pelo teclado]
- **Movimento**: [respeita a preferência de movimento reduzido]
- **Conteúdo**: [texto alternativo nas imagens, rótulo em todo input, idioma definido na página]

## Faça e Não Faça

- Faça: use só os tokens deste arquivo; crie o token aqui antes de usar um valor novo.
- Faça: mantenha uma única ação principal por tela.
- Não faça: usar roxo ou violeta, a menos que a Política de cor acima suspenda o Purple Ban.
- Não faça: misturar cantos arredondados e retos na mesma tela.
- [Regra específica do projeto]

## Histórico de Mudanças

| Data | Feature | Mudança |
| --- | --- | --- |
| [DATA] | [###-nome-da-feature] | [Criado / tokens ou componentes adicionados ou alterados] |
