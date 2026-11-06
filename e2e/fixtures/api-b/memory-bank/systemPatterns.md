# System Patterns

SENTINEL-SYSTEM: roteamento manual em src/app.js, handler puro `handle(method, url)` testável sem servidor.

- Invariante: a API nunca expõe dados de custo.
- Preferência do usuário: respostas curtas.
