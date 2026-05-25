# Frontend — Next.js dashboard plan

This README is a **plan**, not an implemented project. The Next.js scaffold
itself lands on Day 8 of the [build plan](../build-plan.md). This file
locks the routes, components, and dependencies in advance so the Day-8
work is execution, not design.

## Stack

- **Next.js 15** with the App Router (RSC by default).
- **TypeScript** strict mode.
- **Tailwind CSS** 3.x (Tailwind 4 if it's stable enough by Day 8).
- **shadcn/ui** for the component primitives (Button, Card, Input, Dialog,
  Tabs, Badge, Skeleton, ScrollArea, Toast).
- **lucide-react** for icons.
- **`@tanstack/react-query`** for server state (history, replay).
- **Native `EventSource`** (no extra lib) for SSE consumption.
- **`recharts`** for the small line-chart inside each finding card.
- **`zod`** for parsing SSE event payloads at the boundary.

Why the App Router: SSR-by-default keeps the dashboard fast and lets us
stream the initial HTML while the SSE connection warms up.

## Routes

```
/                           Marketing landing page. CTA "Try the demo".
/dashboard                  Live diagnosis chat. The main interactive surface.
/diagnoses/[id]             Read-only render of a stored diagnosis.
/api/proxy/diagnose         Edge route that proxies SSE to the agent service
                            (so the browser uses a same-origin URL and CORS
                            stays simple).
```

### `/`  marketing

- Hero: "Diagnose your DTC brand in 90 seconds." with a 3-second clip from
  the demo video.
- Three feature blocks: "Auto-wires your stack" / "Cross-platform reasoning"
  / "Dollar-quantified fixes".
- "Try with VelvetMint" button — kicks the user into `/dashboard?brand=velvetmint`.
- Footer: GitHub link, hackathon disclosure.

### `/dashboard`  the agent

- **Left column (chat):** message history, input box. Submitting opens an
  `EventSource` to `/api/proxy/diagnose`.
- **Right column (reasoning panel):** vertical timeline of `AgentEvent`
  cards. Each event type has its own visual:
  - `thought` — italic, monospace, light-grey background.
  - `tool_call` — pill with the tool name + collapsible JSON args.
  - `tool_result` — pill, color-coded by success / error.
  - `final_report` — three big finding cards (see component below).
  - `error` — red banner with an "ask again" button.
- **Top bar:** brand selector (defaults to VelvetMint), connector status
  chips ("Shopify [synced 2 min ago]", "Klaviyo [syncing]", ...).

### `/diagnoses/[id]`  replay

- Server-rendered from MongoDB by `id`.
- Same reasoning panel as `/dashboard`, played back at 1x or 2x speed
  (a small speed control). No live agent.
- Permalink-friendly: judges can see a polished result without running the
  live demo.

## Components

Owned in `frontend/src/components/`. shadcn primitives live in
`components/ui/` per shadcn conventions.

| Component | Purpose |
|---|---|
| `<ChatComposer>` | The input + send button. Disables on in-flight diagnosis. |
| `<MessageBubble>` | One user / agent message in the chat column. |
| `<ReasoningTimeline>` | Vertical list of `<EventCard>` items. |
| `<EventCard variant>` | Renders one of `thought \| tool_call \| tool_result \| final_report \| error`. |
| `<ConnectorChip>` | Small pill: name, status icon, last-sync time. |
| `<FindingCard>` | The big card per finding (title / category / chart / impact / fix). |
| `<MetricSparkline>` | Tiny line chart powered by recharts; takes `{points, anomalyAt}`. |
| `<DiagnosisHeader>` | Question + timestamp + brand. |
| `<EmptyState>` | Used on the dashboard before the first diagnosis. |
| `<DemoBadge>` | Visible-only-when-`?demo=1` ribbon: "Demo mode: pre-warmed data". |

## Pages-to-components matrix

| Page | Components |
|---|---|
| `/` | `<MarketingHero>`, `<FeatureGrid>`, `<DemoEmbed>`, `<Footer>` |
| `/dashboard` | `<DiagnosisHeader>`, `<ChatComposer>`, `<MessageBubble>`, `<ReasoningTimeline>`, `<EventCard>`, `<FindingCard>`, `<ConnectorChip>` |
| `/diagnoses/[id]` | `<DiagnosisHeader>`, `<ReasoningTimeline>`, `<EventCard>`, `<FindingCard>`, `<MetricSparkline>` |

## SSE event handling

The client opens `new EventSource('/api/proxy/diagnose?...')` and listens
for the agent event types. Pseudo:

```ts
const es = new EventSource('/api/proxy/diagnose?brand=velvetmint&q=...');
es.addEventListener('thought',      e => append(parseEvent(e, 'thought')));
es.addEventListener('tool_call',    e => append(parseEvent(e, 'tool_call')));
es.addEventListener('tool_result',  e => append(parseEvent(e, 'tool_result')));
es.addEventListener('final_report', e => setReport(parseEvent(e, 'final_report')));
es.addEventListener('error',        e => surfaceError(parseEvent(e, 'error')));
es.addEventListener('done',         () => es.close());
```

Each `parseEvent` validates with a `zod` schema that mirrors the
`AgentEvent` shape from `agent/src/agent/agent_loop.py`. If the schema
fails, we drop the event and surface a developer-only console warning —
the demo never breaks because of an unexpected event shape.

## Visual polish (Day 13)

- Typewriter effect on `thought` events (~25ms / char).
- Connector chips animate from "creating" -> "syncing" -> "complete" with
  a small progress dot.
- Finding cards reveal staggered (1, 2, 3) with a subtle fade.
- Color palette: warm-neutral, evoke a skincare brand. No bright primary
  colors that compete with the data viz.

## What we explicitly do NOT need

- No auth — the demo is single-tenant. We add a "Built for the Google
  Cloud Rapid Agent Hackathon" disclosure banner instead.
- No database in the frontend — it reads/writes via the agent service.
- No internationalization, mobile breakpoints below 768px, or dark mode in
  v1. (We may add dark mode if Day 13 has slack.)

## Folder layout (target)

```
frontend/
├── README.md            (this file)
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  /
│   ├── dashboard/
│   │   └── page.tsx              /dashboard
│   ├── diagnoses/[id]/
│   │   └── page.tsx              /diagnoses/[id]
│   └── api/proxy/diagnose/route.ts
├── src/components/
│   ├── ui/                       (shadcn primitives)
│   ├── chat/
│   ├── reasoning/
│   └── findings/
├── src/lib/
│   ├── sse.ts
│   ├── schemas.ts                (zod schemas mirroring AgentEvent)
│   └── env.ts
├── public/
│   └── demo-assets/              (VelvetMint logo + product imagery)
└── e2e/
    └── dashboard.spec.ts         (playwright; run before Day 16)
```

## Day-of-build checklist

When Day 8 begins:

- [ ] `npx create-next-app@latest frontend --ts --eslint --tailwind --app`
- [ ] `npx shadcn@latest init` then add: button, card, input, dialog, tabs,
      badge, skeleton, scroll-area, toast.
- [ ] Drop in this README's component skeletons.
- [ ] Wire `app/api/proxy/diagnose/route.ts` to forward SSE from the agent
      Cloud Run URL (server-only env var so the agent URL never reaches the
      browser).
- [ ] Build the empty dashboard with hard-coded events. Confirm the visual
      pass before plumbing real SSE on Day 9.
