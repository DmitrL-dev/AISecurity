# Public entry polish

Baseline: `236d48be4a41394b0a6c7f8ae83d15dd8f51a9c6`.

Improve the existing README, academy entrances and Pages landing without
changing the legacy engines or publishing commercial implementations.

## Fixed acceptance list

1. Show four concrete academy topics with direct English and Russian routes:
   prompt injection, RAG, tool-using agents and memory. Preserve lesson bodies.
2. Show the documented Guard Lab demo command and an actual synthetic result:
   four records, two true positives, two true negatives, no false predictions or
   errors. State that this checks execution, not detection quality.
3. At 320/390px, keep AISecurity and Spectorn together in the header, make header
   targets at least 44px tall and stack full-width hero actions. No horizontal
   overflow at 320, 390, 768, 1024 or 1536px.
4. Make the narrow-screen evaluation flow vertical, including arrows and motion.
   Verify keyboard entry, visible focus, readable skip-link hover, pause and
   reduced-motion behavior. Text/control contrast must be at least 4.5:1.
5. Make both academy indexes reading-first. Remove unverified headline claims
   about test counts, performance and uniqueness; correct the paper destination
   to the root `papers/sentinel-lattice/main.pdf`.
6. Add a dedicated JPEG social image, at least 1200px wide, ratio 1.85–2.0 and
   under 250KB. Supply matching Open Graph dimensions and Twitter large-card
   metadata. Preserve the existing hero and README artwork.
7. Explain the current-product handoff and invite concrete contributions without
   implying the historical public engines are current Spectorn detectors.

## Design and operational constraints

Keep “Understand the attack. Build the defense.”, the optical-boundary artwork,
system fonts and the existing palette: background `#09110f`, text `#edf4ef`,
mint `#b8ffd0`, muted `#99aaa2`, borders `#42564b`.

The academy uses open ruled rows beside an editorial introduction, not a card
grid. Guard Lab uses a single native HTML code panel. Generated section concepts
guide the layout; they are not shipped as screenshots of the interface.

Static HTML/CSS only: no runtime JavaScript, trackers, external fonts, framework,
API key, account or live inference request. Spectorn links go to its region
selector at `https://spectorn.ai/`. Large work runs on the owner's VPS.

Completion requires fresh tests, desktop/mobile visual inspection, verified
destinations, normal merge of the reviewed tree and public deployment readback.
