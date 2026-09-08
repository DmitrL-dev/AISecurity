# Public Entry Polish Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan
> in the existing isolated clone. The owner delegates routine design and publish
> decisions and requests minimal subagents.

**Goal:** Make the existing public front door useful, accurate and polished.

**Architecture:** Extend the existing static landing and Markdown entrances.
Use native HTML controls and one CSS file; keep artwork separate from content.

**Tech Stack:** HTML, CSS, Markdown, Python unittest, Playwright CLI.

**Spec:** [Public entry polish](../specs/2026-09-09-public-entry-polish.md).

## Global Constraints

- No runtime JavaScript, trackers, external fonts or new framework.
- No commercial implementation, private corpus, credentials or quality claims.
- Heavy tests, browser rendering and image encoding run on the owner's VPS.
- Preserve the hero, headline, palette, historical lessons and Git history.
- Branch: `codex/aisecurity-front-door-polish`; normal merge only.

## Task 1: Useful, accessible public entrances

**Files:** `docs/index.html`, `docs/assets/landing.css`, `README.md`,
`docs/academy/{en,ru}/index.md`, `.github/tests/test_public_entry.py`,
`.github/tests/public_entry_browser.js`.

**Interfaces:** Existing GitHub lesson paths and pinned Guard Lab report contract;
native `#academy`, `#guard-lab`, `#research`, `#pause-motion` and `#main` anchors.

- [ ] Add tests for valid academy/repository destinations and rendered behavior.
  The browser assertions include real keyboard entry and narrow viewport bounds:
  ```js
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  require(await page.locator('main').evaluate(el => el === document.activeElement),
    'Skip link does not focus main content');
  ```
- [ ] On the VPS, run `python3 .github/tests/test_public_entry.py -v` and
  `playwright-cli run-code --filename .github/tests/public_entry_browser.js`
  against unchanged markup. Record failing behavior before implementation.
- [ ] Add the four bilingual topic rows and the native synthetic example panel.
  Use the actual executed excerpt, not its perfect synthetic accuracy metric:
  ```json
  {"test_records":4,"counts":{"tp":2,"tn":2,"fp":0,"fn":0,"errors":0},"synthetic_demo":true}
  ```
- [ ] Fix header layout, full-width mobile actions and vertical flow. Preserve
  logical DOM order; use `tabindex="-1"` on main, never positive tabindex.
  ```css
  .skip-link:hover { color: var(--bg); }
  #pause-motion:checked ~ .flow-track .signal i { animation-play-state: paused; }
  ```
- [ ] Rewrite only EN/RU academy entrances and README routes. Use the same
  verified lesson paths in both languages and `../../../papers/...` for the paper.
- [ ] Re-run the tests and inspect 320/390/768/1024/1536px renders, keyboard,
  contrast and reduced motion. Compare the two new sections with their concepts.

## Task 2: Share image and publication

**Files:** `docs/images/aisecurity-social.jpg`, `docs/images/ASSETS.md`,
`docs/index.html`, `.github/tests/test_public_entry.py`.

**Interfaces:** Absolute Pages image URL, JPEG dimensions and social metadata;
existing GitHub CI and Pages deployment from main `/docs`.

- [ ] Assert large-card metadata, JPEG format/weight and valid dimensions before
  adding the asset. Generate a dedicated optical-boundary composition; encode
  JPEG on the VPS without replacing the original generated source.
- [ ] Add matching metadata and provenance, using actual image dimensions:
  ```html
  <meta name="twitter:card" content="summary_large_image">
  <meta property="og:image:type" content="image/jpeg">
  ```
- [ ] Run all `.github/tests` and the browser suite on the final candidate. Audit
  links and network/console errors. Save desktop/mobile and section screenshots.
- [ ] Review the complete diff, then commit the explicit in-scope paths:
  `git commit -m "feat: refine public learning and evaluation entry points"`.
- [ ] Push the branch without force, open a PR with actual evidence, and wait for
  all seven existing required check names to pass. Recheck base/head/tree before
  normal merge; do not claim advisory legacy lint/pytest steps are strict gates.
- [ ] Read back the merge, About, Pages deployment commit, image metadata and live
  desktop/mobile result. Stop only task-owned preview resources. Close the goal
  only after all seven acceptance items pass.
