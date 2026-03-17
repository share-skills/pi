# Findings - visualize-search-navigation

## Initial architecture facts
- `AppStore` owns canonical session selection and timeline cursor (`selectedSessionKeyVar`, `timelineIndexVar`).
- `TreeNav` has date-grouped session list, flat ordering signal, and `selectAndReveal(session)` that currently only expands/selects.
- `DecisionCanvas` already maps node id to timeline index (`timelineIndexFor`) and tracks viewport in `viewportVar`.
- `App` is the integration point for top-level shortcuts and cross-component wiring.
- No existing keyboard event wiring/focus management helpers in frontend code.
- Added `AppStore.selectAdjacentSession(delta)` with date+createdAt ordering to keep keyboard session navigation aligned with TreeNav ordering.
- `resources/index.html` is the canonical stylesheet for frontend; no separate CSS bundle.
- Added stable DOM ids for keyboard focus/reveal integration: `tree-session-search`, `canvas-node-search`, `canvas-reveal-current`.
- TreeNav now owns filtered groups/flat ordering derived from search text and performs DOM `scrollIntoView` reveal for selected session keys.
- DecisionCanvas now supports node filtering and viewport centering for search-selected/current highlighted node.

## Heatmap + Metrics alignment findings
- HeatmapTimeline.computeBuckets slices `session.nodes` by raw index, so bucket timeline is node-index-based instead of honoring session.history when it exists.
- App uses HeatmapTimeline's onJump callback to set the store timeline cursor, and the rest of the timeline logic (Timeline/AppStore) prefers `session.history`, causing misalignment when history is present.

## Timeline source findings
- AppStore.timelineMaxFor and Timeline.itemsFrom both prioritize `session.history` when present, ensuring cursor ranges reflect history entries rather than raw nodes.
- When a session lacks history, timeline cursor range falls back to `session.nodes`, so any helper we add must mirror this precedence (history size else nodes size).

## Metrics findings
- MetricsPanel/CompareMetricsPanel take `session.nodes.take(cursor+1)` to determine active nodes, so when the timeline cursor refers to history entries the metrics stop responding correctly.
- Both panels only need to know "nodes highlighted up to cursor"; hooking this into history-highlighted node ids would keep counts aligned with actual visible timeline progression.

## Decision model + compare insights
- DecisionSession.history entries expose `highlightedNodeIds`, which can map history timeline positions back to concrete nodes.
- CompareViewModel already derives timeline items/history-prioritized cursor max and exposes helpers that find nodes linked to history entries, which we can mirror for MetricsPanel.

## Implementation notes
- Added `TimelineSource` helper to expose history-aware timeline entries and deduplicated cursor nodes for reuse across components.
- MetricsPanel now imports TimelineSource and will use the shared helper instead of slicing nodes by cursor index.

## Search confirmations
- Verified via `rg activeNodeCount` that the helper is fully removed from source directories (only generated JS bundles contain historical references).

## Docs updates
- Updated `visualize/CHANGELOG.md` with entries describing the history-aligned heatmap navigation and metrics fixes.
- Extended `visualize/SPEC.md` F05/F05a tables to spell out that both metrics and heatmap use the history-first timeline source, keeping UX consistent with the main timeline.
