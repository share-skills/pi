---
name: visualize
description: "Open the local PI decision visualizer. Build the standalone frontend, embed ~/.pi/decisions into the HTML, and open the result in the browser unless --no-open is passed."
---

# PI Visualize Command

Launch the local PI decision-history visualizer backed by `visualize/`.

## Behavior

1. Locate the visualizer tool:
   - If `./visualize/build.mill` exists in the current workspace, use `./visualize`.
   - Else if `~/.pi/visualize.sh` exists, use that directly.
   - Else if `~/.pi/visualize/visualize` exists, use that as the Mill project directory.
   - Else if `~/.pi/visualize` exists **and** contains `build.mill`, use that.
   - Else, fail and tell the user to run `curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash`.
     - The standalone bootstrap requires both `git` and `mill`.
2. Build or refresh the standalone frontend when running from source:
   - `cd [detected-visualize-dir] && mill frontend.standaloneHtml`
3. Run the visualizer CLI:
   - Offline HTML: `cd [detected-visualize-dir] && mill cli.run`
   - Live local preview: `cd [detected-visualize-dir] && mill cli.run --live`
   - Or if using the wrapper: `~/.pi/visualize.sh [args]`
4. If the user provides additional flags, forward them exactly as provided.
    - Example: `/visualize --no-open --output /tmp/pi.html`
5. On success, report:
    - generated HTML path
    - whether the browser auto-opened
    - session count and warning count from CLI output
6. If the local `mill` launcher warns that it does not match `.mill-version`, report the warning honestly, but continue when the command still succeeds.

## Default CLI behavior

- source: `~/.pi/decisions`
- template: `visualize/out/frontend/standaloneHtml.dest/index.html`
- output: `visualize/out/cli/pi-visualize.html`
- browser: auto-open enabled

## Live preview mode

Use `--live` when you want a browser view that keeps polling sanitized archive updates from a local loopback server:

```bash
cd visualize && mill cli.run --live
```

- The CLI serves on `http://127.0.0.1:<ephemeral-port>/`
- The frontend polls `/api/archive`
- This is distinct from the default offline `file://` HTML flow

## Installation & Updates

The one-click PI installer now provisions `~/.pi/visualize.sh` as a bootstrap launcher. The first run can set up the standalone runtime for you.

For standalone usage (without the full PI skill environment), you can also use the setup script directly:

```bash
curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash
```

This installs the visualizer to `~/.pi/visualize` and creates a wrapper at `~/.pi/visualize.sh`. The standalone bootstrap requires both `git` and `mill`.

## Troubleshooting

- **"mill: command not found"**: The standalone visualizer requires Mill to build the frontend. Install [Mill](https://com-lihaoyi.github.io/mill) or ensure it's in your PATH.
- **"git: command not found"**: The standalone setup script clones or refreshes the PI repository. Install Git before running the bootstrap command.
- **Browser not opening**: Use `--no-open` and check the output path.
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
- The generated HTML is fully self-contained and can later be re-opened via `file://`.
