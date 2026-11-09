---
type: active
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
---

# Contexto ativo

## Feature ativa

- Feature: [specs/NNN-nome ou nenhuma]
- Fase: [specify | plan approved | implementation | test | debug | verify | deploy]
- Plan approved: [AAAA-MM-DD | no]
- Branch: [nome da branch ou nenhuma]

## Onde estamos

[Uma a três frases sobre o estado atual do trabalho.]

## Eventos recentes

<!-- Mais recente primeiro. Formato: - AAAA-MM-DD — o que aconteceu — por quê. Acima de 256
     linhas, os eventos antigos são resumidos em changelog.md › Histórico consolidado. -->

- [AAAA-MM-DD] — [o que aconteceu] — [por quê]

## O que funciona

- [Funcionalidade ou parte do sistema que funciona e foi verificada.]

## O que falta

- [O que ainda precisa ser construído, em ordem de prioridade.]

## Próximos passos

- [O que vem a seguir. Isto é plano, não fato.]

## Problemas conhecidos

- Bug [slug]: [open | closed (verify AAAA-MM-DD)] — [.redevkit/bugs/slug/]
- [Limitação ou dívida técnica ainda não resolvida.]

## Últimos resultados

- Test: [PASS | FAIL] — [AAAA-MM-DD HH:MM] — [executado por redevkit-test | redevkit-verify (step 1)] — [comando] — [caminho do relatório]
- Verify: [converged+verified | gaps | failed] — [AAAA-MM-DD HH:MM] — [caminho do relatório]
- Debug: [specs/NNN-nome] — [slug do bug] — [AAAA-MM-DD HH:MM] — [verified | partial | failed] — [.redevkit/bugs/slug/]
- Correction cycle: [specs/NNN-nome] — failed after debug [N]/2 · rounds without convergence [N]/3 [· G5 reached AAAA-MM-DD HH:MM, waiting for the user]

## Preferências de fluxo

- Branch por feature: [always | never | ask]
- [Outra preferência de fluxo, por exemplo commit só quando pedido.]
