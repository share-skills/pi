# Changelog

## [2.1.0] - 2026-07-16

### Added
- Integrated into `install.sh` one-click installer: automatically places `~/.pi/visualize.sh` launcher
- Node.js availability check during install with user-friendly warning
- `scripts/setup-standalone-visualize.sh` standalone bootstrap (requires `git` + `node`/`npm`)
- Cursor rule `pi-visualize.mdc` auto-installed alongside `pi.mdc`
- `commands/visualize.md` command spec for `/pi visualize` host integration
- Links to `docs/WHY_PI_WORKS.md` and `docs/DESIGN_PHILOSOPHY.md` in README

### Changed
- Removed all legacy `mill`/Scala references from documentation
- Updated README.md and README.en.md visualizer sections with feature descriptions

## [2.0.0] - 2026-03-17

### Changed
- Complete rewrite from Scala.js to TypeScript + React
- New tech stack: Vite, Tailwind CSS, React Flow, Zustand, Express, WebSocket

### Added
- WebSocket-based live mode (replaces HTTP polling)
- Interactive decision graph with React Flow (drag, zoom, pan)
- Responsive single-viewport layout (no scrolling needed)
- Session activity indicators (green/gray dots)
- Session deletion
- Timeline slider at top of viewport
- Collapsible floating detail drawer
- Dark theme with glassmorphism effects
- Export/import with privacy sanitization
- Multi-agent interaction tracking
- Mock/simulation mode
- Bottom status bar with metrics

### Fixed
- Blank page area (previous Scala.js mount issue)
- UTC timestamp display → now uses local time
- Top bar pill crowding → redesigned layout
- Non-collapsible detail drawer → now collapsible
- Live mode not detecting changes → WebSocket + chokidar
