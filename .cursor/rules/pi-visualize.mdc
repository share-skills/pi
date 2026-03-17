---
description: "PI Visualizer usage in Cursor (local offline + optional live preview)"
alwaysApply: true
---

# PI Visualizer in Cursor

To visualize your PI decision history locally:

## 1) Generate a standalone (offline) HTML

```bash
/pi visualize
```

This builds the standalone frontend, embeds your local archive (default: `~/.pi/decisions`), and opens the resulting `file://` HTML unless `--no-open` is passed.

Headless / CI usage:

```bash
/pi visualize --no-open --output /tmp/pi.html
```

## 2) Live local preview (opt-in)

When you want the browser to auto-refresh as sanitized archive files change, use the CLI live mode (loopback HTTP server + polling):

```bash
cd visualize && npm run dev
```

Notes:
- Development server runs on Vite with hot module replacement.
- Production server uses `npm run server` on port 3141.

## 3) Source selection

Default source is `~/.pi/decisions`. You can point to a specific directory:

```bash
/pi visualize --source path/to/.pi/decisions
```

## Privacy / sync

- The visualizer runs locally.
- `--bind-github` / `--github-worktree` currently perform **local** git worktree history sync (sanitized sessions + local commits). Remote push is manual / out of scope.
