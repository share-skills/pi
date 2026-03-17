---
description: PI Wisdom-in-Action Engine v19 — nine chapters (Dao-Fa-Shu-Qi-Shi-Ling-He-Ren-Tu), top-5 mandates with ⚡PI-01~05 KV-Cache anchors, scene router, delivery quality gates, anti-pattern decalogue, six-tier battle momentum, Loop/Auto interaction modes. Invoke to activate structured methodology with positive motivation.
---

Unless the first argument is `visualize`, invoke the pi skill and follow it exactly as presented to you.

## Project Context (Auto-Injected)

> The following is auto-injected at invocation to assist 启动三查·查境. Use it to understand the current project state.

**Current branch**: !`git branch --show-current 2>/dev/null || echo '(not a git repo)'`

**Recent commits**:
!`git log --oneline -5 2>/dev/null || echo '(no git history)'`

**Working state**:
!`git diff --stat HEAD 2>/dev/null | tail -5 || echo '(clean or not a git repo)'`

**Project files** (top-level):
!`ls -1 2>/dev/null | head -15 || echo '(empty)'`

## Argument Routing

If the user provided arguments after `/pi`, parse them as follows:

| Argument | Effect |
|----------|--------|
| `visualize` | Launch the PI decision visualizer instead of the normal PI skill flow |
| `loop` | Activate **Loop mode** (§8.2) — every output must end with a question, never auto-exit |
| `auto` | Activate **Auto mode** (§8.2) — default autonomous interaction |
| Scene keyword (编程/ 开发 / fleet /测试/产品/运营/创意/交互/调试/协作/陪伴) | Force-activate that scene (§1.3), skip auto-routing |
| Any other text | Treat as the user's task description, proceed with auto scene routing |

Multiple arguments combine: `/pi loop 编程` = Loop mode + 编程开发 scene.

If no arguments provided, default to Auto mode with auto scene routing.

## Special Route: `/pi visualize`

If the first argument is `visualize`, **do not** activate the generic PI scene router. Instead, treat the remaining arguments as visualizer CLI flags and execute the local visualizer flow:

1. Locate the visualizer tool:
   - If `./visualize/build.mill` exists in current path, use `./visualize`.
   - Else if `~/.pi/visualize.sh` exists, use that directly.
   - Else if `~/.pi/visualize/visualize` exists, use that as the Mill project directory.
   - Else if `~/.pi/visualize` exists **and** contains `build.mill`, use that.
   - Else, fail and tell the user to run `curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash`.
     - *Note: The standalone bootstrap requires both `git` and `mill`.*

2. Build or refresh the standalone frontend (if running from source):
   - `cd [detected-visualize-dir] && mill frontend.standaloneHtml`

3. Run the visualizer CLI:
   - Offline HTML: `cd [detected-visualize-dir] && mill cli.run [args]`
   - Live local preview: `cd [detected-visualize-dir] && mill cli.run --live [args]`
   - Or if using the wrapper: `~/.pi/visualize.sh [args]`
   - `--live` starts a loopback HTTP preview server and continuously refreshes from `/api/archive`; it is not `file://` auto-refresh.

4. If the user passed additional flags after `visualize`, forward them exactly as provided.
   - Example: `/pi visualize --no-open --output /tmp/pi.html`

5. On success, report:
   - generated HTML path
   - whether the browser was opened automatically
   - session / warning counts printed by the CLI

6. If the local `mill` launcher warns that it is older than `.mill-version`, surface the warning honestly, but continue when the build/run command still succeeds.

If the user says `/pi visualize` with no extra flags, use the default CLI behavior from `visualize/cli/Main.scala`:
- source: `~/.pi/decisions`
- template: `visualize/out/frontend/standaloneHtml.dest/index.html`
- output: `visualize/out/cli/pi-visualize.html`
- browser: auto-open enabled

**After loading PI skill, always output the scene announcement (场景公示) so the user can see which mode and scene are active.**
