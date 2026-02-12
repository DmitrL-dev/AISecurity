# SaaS Landing Pages — Requirements

> **Компонент:** saas/landing/
> **Статус:** Implemented
> **Дата:** 2026-02-12

---

## 1. Обзор

Три статических HTML лендинга для SENTINEL SaaS:
- **index.html** — Western market (Matrix-style, hacker aesthetic)
- **index-ru.html** — Российский рынок (community-focused)
- **index-en.html** — English community

---

## 2. Функциональные требования

### FR-1: Western Landing (index.html)

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-1.1 | Hero: "Thinks Faster Than Attacks" + terminal demo | P0 |
| FR-1.2 | HACKER/BUSINESS mode toggle (green ↔ blue accents) | P0 |
| FR-1.3 | 4-tier pricing: Free $0, Personal $4.99, Developer $49, Team $149 | P0 |
| FR-1.4 | Competitor comparison table (Lakera, Wardstone, LLM Guard) | P0 |
| FR-1.5 | Integration channels grid (Extension, IDE, MCP, API) | P0 |
| FR-1.6 | Key metrics: <1ms latency, 36 engines, open-source | P0 |
| FR-1.7 | CTA buttons: Install Extension, View on GitHub | P0 |

### FR-2: Russian Landing (index-ru.html)

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-2.1 | Community open-source messaging | P0 |
| FR-2.2 | Feature grid | P0 |
| FR-2.3 | Russian language | P0 |
| FR-2.4 | Links to docs, GitHub, Telegram | P0 |

### FR-3: English Community (index-en.html)

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-3.1 | English version of community landing | P0 |
| FR-3.2 | Same structure as RU landing | P0 |

### FR-4: Design System

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-4.1 | Responsive (mobile-first) | P0 |
| FR-4.2 | Dark theme с neon accents | P0 |
| FR-4.3 | Google Fonts: JetBrains Mono (code), Inter (text) | P1 |
| FR-4.4 | Smooth animations и hover effects | P1 |
| FR-4.5 | Zero JavaScript dependencies | P0 |

---

## 3. Нефункциональные требования

| ID | Требование |
|----|------------|
| NFR-1 | Lighthouse Performance score > 90 |
| NFR-2 | < 100KB total page size (gzipped) |
| NFR-3 | No external JS dependencies |
| NFR-4 | SEO: meta tags, OG tags, structured data |
| NFR-5 | Accessible (WCAG 2.1 AA) |

---

## 4. Файловая структура

```
saas/landing/
├── index.html          # Western market (Matrix-style)
├── index-ru.html       # Russian community
└── index-en.html       # English community
```

---

## 5. Acceptance Criteria

- [x] AC-1: Western landing с HACKER/BUSINESS toggle
- [x] AC-2: Matrix-style dark theme с green accents
- [x] AC-3: 4-tier pricing display
- [x] AC-4: Competitor comparison table
- [x] AC-5: Responsive layout
- [x] AC-6: RU and EN community landings
- [ ] AC-7: Deploy to Vercel/Cloudflare Pages
- [ ] AC-8: Lighthouse audit > 90
