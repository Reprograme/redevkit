---
name: geo-fundamentals
description: Generative Engine Optimization - make public content citable by AI answer engines. Use when optimizing for AI search.
---

# GEO Fundamentals

> Optimization for AI-powered search engines.

---

## 1. What is GEO?

**GEO** = Generative Engine Optimization

| Goal | Platform |
|------|----------|
| Be cited in AI responses | ChatGPT, Claude, Perplexity, Google AI Overviews |

### SEO vs GEO

| Aspect | SEO | GEO |
|--------|-----|-----|
| Goal | #1 ranking | AI citations |
| Platform | Google | AI engines |
| Metrics | Rankings, CTR | Citation rate |
| Focus | Keywords | Entities, data |

---

## 2. AI Engine Landscape

| Engine | Citation Style | Opportunity |
|--------|----------------|-------------|
| **Perplexity** | Numbered `[1][2]` | Highest citation rate |
| **ChatGPT** | Inline/footnotes | Custom GPTs |
| **Claude** | Contextual | Long-form content |
| **Google AI Overviews** | Linked sources | SEO crossover |

---

## 3. RAG Retrieval Factors

How AI engines select content to cite (rough heuristic weights, not published by any engine):

| Factor | Weight |
|--------|--------|
| Semantic relevance | ~40% |
| Keyword match | ~20% |
| Authority signals | ~15% |
| Freshness | ~10% |
| Source diversity | ~15% |

---

## 4. Content That Gets Cited

| Element | Why It Works |
|---------|--------------|
| **Original statistics** | Unique, citable data |
| **Expert quotes** | Authority transfer |
| **Clear definitions** | Easy to extract |
| **Step-by-step guides** | Actionable value |
| **Comparison tables** | Structured info |
| **FAQ sections** | Direct answers |

---

## 5. GEO Content Checklist

### Content Elements

- [ ] Question-based titles
- [ ] Summary/TL;DR at top
- [ ] Original data with sources
- [ ] Expert quotes (name, title)
- [ ] FAQ section (3-5 Q&A)
- [ ] Clear definitions
- [ ] "Last updated" timestamp
- [ ] Author with credentials

### Technical Elements

- [ ] Article schema with dates
- [ ] Person schema for author
- [ ] FAQPage schema
- [ ] Fast loading (< 2.5s)
- [ ] Clean HTML structure

---

## 6. Entity Building

| Action | Purpose |
|--------|---------|
| Google Knowledge Panel | Entity recognition |
| Wikipedia (if notable) | Authority source |
| Consistent info across web | Entity consolidation |
| Industry mentions | Authority signals |

---

## 7. AI Crawler Access

### Key AI User-Agents

| Crawler | Engine |
|---------|--------|
| GPTBot | OpenAI (model training) |
| OAI-SearchBot | ChatGPT search |
| ClaudeBot | Anthropic (model training) |
| Claude-SearchBot | Claude search |
| PerplexityBot | Perplexity |
| Googlebot | Google Search and Google AI Overviews (shared) |
| Google-Extended | robots.txt token for Google AI model use (does not affect Search) |

Crawler names change; confirm them against each vendor's current documentation before editing
`robots.txt`.

### Access Decision

| Strategy | When |
|----------|------|
| Allow all | Want AI citations |
| Block GPTBot | Don't want OpenAI training |
| Selective | Allow some, block others |

---

## 8. Measurement

| Metric | How to Track |
|--------|--------------|
| AI citations | Manual monitoring |
| "According to [Brand]" mentions | Search in AI |
| Competitor citations | Compare share |
| AI-referred traffic | UTM parameters |

---

## 9. Anti-Patterns

| ❌ Don't | ✅ Do |
|----------|-------|
| Publish without dates | Add timestamps |
| Vague attributions | Name sources |
| Skip author info | Show credentials |
| Thin content | Comprehensive coverage |

---

> **Remember:** AI cites content that's clear, authoritative, and easy to extract. Be the best answer.

## Related Skills

| Need | Skill |
| --- | --- |
| Classic search ranking, meta, sitemap | `{{SKILL:seo-fundamentals}}` |

## Audit

| Audit | Purpose |
| --- | --- |
| `geo_checker.py` | AI citation readiness of public pages: structured data, author, dates, FAQ |

In the test and verify commands (not during implementation), run `.redevkit/audits/geo_checker.py <project_path>` with the Python interpreter detected per
`.redevkit/audits/README.md`. If no Python is available, the audit is `SKIPPED (no Python)`:
say so and fall back to manual checks (validate structured data with the project's tooling,
review the checklist above page by page). Never report a skipped audit as PASS.
