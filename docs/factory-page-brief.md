# Factory page — positioning & design brief

**Page:** `https://miidas.ru/factory/` · **Slot:** Tier 3 of the umbrella ladder («Фабрики агентов под ключ»), which until now had no page — its CTA pointed straight at a Telegram DM.
**Source material:** meta-factory product docs — `docs/product.md` (the four products), `docs/best-practices.md` (P1–P33), `docs/growth-stages.md` (Stages 0–4), `docs/quality-criteria.md` (19 criteria / 6 families / 0–4), `docs/stories/01-anatomy-of-an-ai-factory.md` (the 10.4 h finding), `evidence/scores/2026-09-17.md` (fleet scorecard), `ONTOLOGY.md` (canonical terms).

---

## 1. The strategic problem this page solves

Tier 2 (`/agent/`) sells **a worker**: one agent, one Telegram chat, a lease. Tier 3 sells something categorically different — **a delivery line**: several agents, named roles, a written process, and a supervisor. A prospect arriving from the umbrella page currently sees four feature bullets and a "discuss it" button, which is exactly what every agency landing page looks like.

The page must make one thing unmistakable: **this is not more agents, it is a different machine** — and it is measured.

## 2. The single differentiator to lead with

The market sells automations, prompt packs, and chatbots. None of them can answer "is it getting better, and how do you know?" The meta-factory material answers it with a number: **19 criteria across 6 families, scored 0–4 daily, per contour.**

So the lead is not "we build agents". It is:

> **A factory is measured, or it is not a factory.** A contour with no numbers is Provisional by definition.

Everything else on the page exists to make that claim believable: the anatomy (three legs), the failure physics (the 10.4 h queue), the growth map (roadblocks by throughput band), and the scorecard (our own contours, weak spots included).

## 3. Audience

| Segment | State of mind | What the page must do |
|---|---|---|
| SMB owner with recurring ops (real estate, services, trade, construction) | "We tried ChatGPT; it wrote text and changed nothing." | Show the difference between output and side effects — and that the loop runs without a human pressing go |
| Operator already running one agent (Tier 2 lease) | "It works, but I still dispatch everything by hand." | Sell the missing layer: dispatch, locking, quality gates, measurement |
| Technical founder / CTO | "Show me the engineering, not the deck." | Give real mechanisms: `fcntl.flock` single-writer, `ledger.jsonl`, atomic subprocesses, pacemaker crons, ontology gate |

## 4. Message hierarchy (top to bottom)

1. **Hook** — the bottleneck was never the model. It was the queue: 10.4 h average lead time, 20–25 min of actual agent work, ~95% of the duration spent waiting for a human to kick off a session.
2. **Anatomy** — a factory is three things paired: process law (a versioned file reloaded after every compaction) × chat surface (one named place per work unit, the name carries the state) × issue board (issues *are* the task list). Remove one leg and it is not a factory.
3. **Three pillars** — Autonomous (pacemakers wake the lanes) · Self-improving (every failure becomes a rule, a test, or a gate) · Factory discipline (one writer per state surface, atomic steps, verifiable deliverables).
4. **What it looks like in Telegram** — the HQ topic, `Worker — #42` renamed to `Done — #42`, an approval card on an irreversible act. The human supervises a surface, not a queue.
5. **Growth map** — Stages 0–4, each with the roadblock that ends it and the mechanism that breaks through. Sells judgement: we know what breaks at your throughput before you hit it.
6. **Measurement** — the 19 criteria, the 0–4 scale, the four bands, and our own scorecard. This is the trust engine of the page.
7. **Deliverables** — what physically changes in the client's business.
8. **Engagement** — audit → bootstrap → first lane → gates → cadence, with the owner's approval gates named explicitly.
9. **Fit** — who it is for, and who should not buy it (protects margin and credibility).
10. **FAQ + CTA.**

## 5. Design decisions

- **Reuse the design system, add nothing global.** `style.css` tokens and components (`.umbrella-section`, `.product-card`, `.proof-grid`, `.case-grid`, `.steps`, `.faq-list`, `.community-box`, `.final-cta`, `.tg-chat`) carry the page. Page-specific pieces (stat tiles, stage rows, score rows, anatomy triad) go into a new `factory/factory.css` — same pattern as `recipes/recipe.css`. The shared 62 KB stylesheet is not touched.
- **Every claim carries a source in the copy.** Numbers on the page come from the meta-factory's own evidence files, dated. No invented pricing, no invented logos, no client names.
- **One visual anchor per section.** The Telegram mockup and the scorecard table are the two sections a visitor should remember; both use existing components.
- **Russian, plain business language** — the audience is the SMB owner, not the engineer; mechanism names appear as proof, not as the pitch.

## 6. Open decisions for the owner

1. **Publishing the fleet scorecard.** The page shows our own six contours (93% / 83% / 71% / 71% / 70% / 50%, dated 2026-09-17), including the weakest. Rationale: a rubric that only ever reports good news is decoration. **If you prefer, this section collapses to the method alone, with no numbers.**
2. **Pricing.** The page states scope and process, never a price — Tier 3 is a consulting engagement. If you want anchor pricing, give me the band.
3. **The private repo link.** `leshchenko1979/agent-factories` is private, so the page does **not** link it; credibility rests on the deployed contours instead.
