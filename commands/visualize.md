---
name: visualize
description: "Open the local PI decision visualizer. Start the visualizer server backed by ~/.pi/decisions data, and open the result in the browser unless --no-open is passed."
---

# PI Visualize Command

Launch the local PI decision-history visualizer backed by `visualize/`.

## Behavior

1. Locate the visualizer tool:
   - If `./visualize/package.json` exists in the current workspace, use `./visualize`.
   - Else if `~/.pi/visualize.sh` exists, use that directly.
   - Else if `~/.pi/visualize/visualize` exists and contains `package.json`, use that.
   - Else, fail and tell the user to run `curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash`.
     - The standalone bootstrap requires `git` and `node`/`npm`.
2. Install dependencies and build if needed:
   - `cd [detected-visualize-dir] && npm install && npm run build`
3. Run the visualizer:
   - Production server: `cd [detected-visualize-dir] && npm run server` (serves on port 3141)
   - Development mode: `cd [detected-visualize-dir] && npm run dev`
   - Or if using the wrapper: `~/.pi/visualize.sh [args]`
4. If the user provides additional flags, forward them exactly as provided.
    - Example: `/visualize --no-open`
5. On success, report:
    - server URL (default: http://localhost:3141)
    - whether the browser auto-opened
    - session count and warning count from server output

## Default behavior

- source: `~/.pi/decisions`
- server port: 3141
- browser: auto-open enabled

## Live development mode

Use `npm run dev` when you want hot-reloading during development:

```bash
cd visualize && npm run dev
```

- Vite dev server starts on an ephemeral port
- Hot module replacement enabled
- This is distinct from the production `npm run server` flow

## Installation & Updates

The one-click PI installer now provisions `~/.pi/visualize.sh` as a bootstrap launcher. The first run can set up the standalone runtime for you.

For standalone usage (without the full PI skill environment), you can also use the setup script directly:

```bash
curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash
```

This installs the visualizer to `~/.pi/visualize` and creates a wrapper at `~/.pi/visualize.sh`. The standalone bootstrap requires `git` and `node`/`npm`.

## Troubleshooting

- **"node: command not found"**: The visualizer requires Node.js. Install [Node.js](https://nodejs.org/) or ensure it's in your PATH.
- **"git: command not found"**: The standalone setup script clones or refreshes the PI repository. Install Git before running the bootstrap command.
- **Browser not opening**: Use `--no-open` and check the server URL.
- **Missing data**: Ensure `~/.pi/decisions` exists and is populated by PI hooks.

## Host Integration

`/visualize` is a host-wired shortcut, not a universally installed shell command.

If your host loads `commands/visualize.md` and `commands/pi.md` as slash-style commands, you can use:

```text
/visualize
/pi visualize
```

Otherwise, use the guaranteed local entrypoint:

```bash
~/.pi/visualize.sh
```

## Notes

- This command is the standalone sibling of `/pi visualize` when the host has wired both command files.
- The visualizer serves a React SPA backed by a Node.js/Express server reading `~/.pi/decisions`.
