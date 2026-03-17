# PI Decision Visualizer — Specification

## Version: 2.0.0

### Overview
Interactive web-based visualizer for PI decision chains. Provides real-time
monitoring, timeline playback, and session analysis for AI workflow optimization.

### Tech Stack
- **Frontend**: React 19, TypeScript 5.7, Vite 6, Tailwind CSS 3.4, React Flow 12
- **Server**: Node.js, Express 4, WebSocket (ws), chokidar 4
- **State**: Zustand 5
- **Data**: JSON/JSONL files in `~/.pi/decisions/`

### Layout (single viewport, NO scrolling)
```
┌──────────────────────────────────────────────────────┐
│  ⚡ PI Visualizer   [Timeline ═══●══════]  metrics   │  TopBar
├────────┬─────────────────────────────────┬───────────┤
│ 📅 Date│                                 │ [Details] │
│ ├─ ses1│   Decision Graph Canvas         │ Floating  │
│ ├─ ses2│   (React Flow — drag/zoom)      │ Detail    │
│ └─ ses3│                                 │ Drawer    │
├────────┴─────────────────────────────────┴───────────┤
│  tokens: 12.4k  │  complexity: 3/5  │  status: ✅    │  StatusBar
└──────────────────────────────────────────────────────┘
```

### Features
1. Session tree navigation with date grouping
2. Interactive decision graph (drag, zoom, collapse/expand)
3. Real-time live mode via WebSocket + file watching
4. Timeline slider for temporal navigation
5. Decision detail floating panel (collapsible)
6. Session metrics and scoring
7. Active/inactive session indicators (green/gray dots)
8. Export/import with privacy sanitization
9. Session deletion
10. Responsive design (single viewport, no scrolling)
11. Multi-agent interaction tracking
12. Mock/simulation mode for testing

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET    | /api/archive | Full decision archive |
| GET    | /api/sessions | Session list |
| DELETE | /api/sessions/:id | Delete session data |
| WS     | /ws | Real-time updates |

### Data Format
See `src/types.ts` for TypeScript type definitions.

Decision data directory: `~/.pi/decisions/`
```
~/.pi/decisions/
├── 2026-03-16/
│   └── session-<UUID>.events.jsonl
└── 2026-03-17/
    ├── session-<name>.json
    ├── session-<name>.events.jsonl
    └── session-<name>.nodes.jsonl
```
