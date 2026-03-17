# Task Plan - visualize-fix-heatmap-metrics

## Goal
Align the PI visualizer heatmap navigation and cursor-scoped metrics with the unified timeline/history model so clicking heatmap buckets and viewing metrics always reflects the same progression as the main timeline.

## Acceptance Criteria
- [ ] Heatmap bucket calculations and navigation operate on the same timeline data (history when present, nodes otherwise) used by the main timeline cursor.
- [ ] Clicking a heatmap bucket moves the timeline cursor to the correct history-based position.
- [ ] MetricsPanel derives active nodes from history-highlighted nodes when history exists, otherwise from nodes before the cursor index.
- [ ] CompareMetricsPanel uses the same corrected active-node derivation for each compared session.
- [ ] No regressions to compare/navigation/heatmap responsiveness.
- [ ] Relevant docs (SPEC/CHANGELOG) updated if semantics visible to users change.
- [ ] Focused verification (tests or targeted commands) executed and attached.
- [ ] SQL todo `visualize-fix-heatmap-metrics` updated to `done`.

## Phases
1. Inspect HeatmapTimeline, App store/timeline helpers, MetricsPanel, CompareMetricsPanel to understand current data sources.
2. Design a shared helper or data selection strategy for "timeline source" (history-over-nodes) and for "active nodes up to cursor".
3. Update HeatmapTimeline bucket computation + click handler to use the shared timeline source.
4. Update MetricsPanel and CompareMetricsPanel to derive active nodes from the history timeline representation.
5. Run focused verification (tests or targeted commands) covering heatmap/metrics changes.
6. Update docs/CHANGELOG if needed and finalize SQL todo update.

## Risks
- Bucket calculations might expect contiguous node indices; switching to history lengths must preserve bucket sizing.
- Metrics panels may have memoized computations; changing inputs could affect performance if not memoized carefully.
- Compare view may have bespoke cursor logic; avoid regressions by keeping unrelated navigation untouched.
