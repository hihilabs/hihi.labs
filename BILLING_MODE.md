# Billing Mode for Projects — 3-Level Design (research, 2026-06-10)

Reference: `/projects/value/` (`value_board` in `apps/projects/views.py`). The value board
is a pure **revenue lens** — `hours × Project.hourly_rate`, unbilled value, extrapolated
potential. Billing mode adds the missing **cost lens** and derives pricing from it.
Same board, three stacked modes: `?mode=cost | sustain | pricing`.

---

## What already exists (audit of current models)

| Data | Where | Usable for |
|---|---|---|
| `hourly_rate` (default $150) | `Project` | L3 comparison baseline |
| Hours worked, `billed` flag | `TimeEntry` | L1 labor input |
| `tokens_used` per AI message | `apps/claude_ai/models.py Message` | L1 AI cost (needs $ conversion + project link) |
| Recurring services per project | `Service` / `ProjectService` | L2 — **but no cost field** |
| Server inventory | `apps/servers/models.py Server` | L2 — **but no cost field, no project link** |
| Invoices (qty × rate) | `Invoice` / `InvoiceLine` | L3 actual-revenue comparison |
| Client-facing SaaS plans ($0/29/79/149) | `subscriptions.Plan` | revenue side only |
| `entity` (binsky/fckry/community/clients) | `Project` | overhead allocation by entity |

**Gaps:** no labor *cost* rate (only bill rate), no expense ledger, no $ on servers/services,
no overhead/fixed-cost settings, no margin target, no per-client pricing factor.

---

## Level 1 — Raw cost calculator (what a project actually costs to deliver)

```
raw_cost = labor + ai + infra_direct + expenses
  labor        = total_hours × CostSettings.labor_cost_per_hour
  ai           = Σ tokens_used (project-linked convos) × ai_cost_per_1k / 1000
  infra_direct = Σ Server.monthly_cost share, for servers assigned to the project
  expenses     = Σ ProjectExpense (one-off: domains, stock, contractors, hardware)
```

New pieces needed:
- `CostSettings` (singleton): `labor_cost_per_hour` (your real cost basis — what an hour
  of your time costs *you*, not the $150 bill rate), `ai_cost_per_1k_tokens`,
  `overhead_monthly`, `target_margin_pct`, `default_client_factor`.
- `ProjectExpense`: `project FK, kind ('one-off'|'monthly'), description, amount, date`.
- `Server.monthly_cost` Decimal + `Server.projects` M2M (cost split evenly across linked
  projects, or weighted later).
- `ProjectService.monthly_cost` Decimal (what *you pay* to provide that service).
- AI attribution: cheapest viable path is `Conversation.project FK (null=True)` +
  a fallback bucket "unattributed AI" allocated like overhead.

Board columns (mode=cost): raw cost, revenue (existing total_value), **gross margin $ / %**,
cost per hour. Health flag: `margin < 0 → 'underwater'`.

## Level 2 — Cost to sustain in-house (monthly run-rate to keep it alive)

The recurring slice of L1 plus an allocated share of fixed overhead:

```
sustain_monthly = maintenance_labor + recurring_expenses + infra_share + overhead_share
  maintenance_labor  = avg hours/mo over trailing 90d (stage='maintaining' projects)
                       × labor_cost_per_hour
  recurring_expenses = Σ ProjectExpense kind='monthly' + Σ ProjectService.monthly_cost
  infra_share        = Σ linked Server.monthly_cost shares
  overhead_share     = CostSettings.overhead_monthly ÷ active project count
                       (overhead_monthly = VPS hosting, Unraid electricity, software
                       subs, accounting, insurance — one hand-entered number to start)
```

Board columns (mode=sustain): sustain/mo, recurring revenue/mo (retainer invoices or
trailing-90d invoiced ÷ 3), **monthly margin**, break-even retainer. This answers
"which 'maintaining' projects quietly cost more than they bring in."

## Level 3 — Ideal service pricing scaled to client

Price = cost floor × margin, scaled by a per-client factor, sanity-checked against value:

```
cost_floor       = L2 sustain_monthly  (retainer) or L1 cost/hr  (hourly)
base_price       = cost_floor × (1 + target_margin_pct)        # e.g. 2.5–3×
client_factor    = Client.pricing_factor (default 1.0)
                   # scaled by org size, # linked companies, strategic value —
                   # Greg with 3 linked entities ≠ a single-site shop
suggested_price  = base_price × client_factor
floor_guard      = never below cost_floor × 1.2
```

New piece: `Client.pricing_factor` Decimal (default 1.0) — set manually per client at
first; could later be suggested from linked-company count / invoice history.

Board columns (mode=pricing): current `hourly_rate`, suggested rate, suggested monthly
retainer, delta %, flag **`underpriced`** when current < suggested × 0.8. Totals row:
"repricing opportunity" = Σ positive deltas across active projects.

---

## Implementation sketch (when greenlit)

1. Migration pass: `CostSettings`, `ProjectExpense`, `Server.monthly_cost` + M2M,
   `ProjectService.monthly_cost`, `Client.pricing_factor`, `Conversation.project`.
2. `apps/billing/costing.py`: pure functions `raw_cost(project)`, `sustain_monthly(project)`,
   `suggested_pricing(project)` — keeps `value_board` view thin, unit-testable on the
   local SQLite dev instance before touching production.
3. `value_board` view: `mode = request.GET.get('mode', 'value')`; existing behavior is
   the default so nothing breaks. Template gets a 4-tab toggle (Value / Cost / Sustain /
   Pricing) and per-mode column sets.
4. Seed: enter `labor_cost_per_hour`, `overhead_monthly`, server costs once; everything
   else degrades gracefully to 0 (board still renders, costs just read low until filled in).

Order of value: L2 first surfaces money-losing retainers immediately with ~5 hand-entered
numbers; L1 precision (AI attribution, expense ledger) can be backfilled; L3 falls out of
L2 almost for free.
